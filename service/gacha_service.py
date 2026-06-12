"""
service/gacha_service.py
가챠 시뮬레이터 비즈니스 로직

- 배너 초기화 (3성 학생 목록 기반 자동 생성)
- 가챠 알고리즘 구현 (실제 게임 확률 구조 반영)
  - 3성 3%, 픽업 0.7%, 200회 하드 파티
  - 73회부터 소프트 파티 (회당 +3%)
  - 10회 보장 (2성 이상)
- 뽑기 결과 DB 저장 및 보유 학생 관리
"""

import json
import os
import random
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from repository.interfaces import (
    IBannerRepository,
    IGachaPullRepository,
    ICultivationRepository,
    IStudentRepository,
)


@dataclass
class PullResult:
    """뽑기 1회 결과 데이터 클래스"""
    student_id: int
    student_name: str
    star_grade: int
    is_pickup: bool
    is_new: bool       # 최초 획득 여부
    eleph_gained: int  # 중복 시 지급 엘레프 수 (신규면 0)


class GachaService:
    """
    가챠 시뮬레이터 서비스
    - 실제 블루아카이브 가챠 확률 구조를 Python으로 구현
    - 뽑기 결과를 gacha_pull 테이블에 저장
    - 신규 학생 획득 시 cultivation 테이블에 레코드 생성
    """

    def __init__(
        self,
        banner_repo: IBannerRepository,
        gacha_repo: IGachaPullRepository,
        cultivation_repo: ICultivationRepository,
        student_repo: IStudentRepository,
    ):
        self._banner_repo = banner_repo
        self._gacha_repo = gacha_repo
        self._cultivation_repo = cultivation_repo
        self._student_repo = student_repo
        self._gacha_config: dict = {}
        self._pool_ids: dict = {}

    # -------------------------------------------------------------------------
    # 초기화
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        """
        배너 테이블 생성 + 3성 학생 배너 자동 생성 + 가챠 설정 로드
        """
        self._banner_repo.create_table()
        self._gacha_repo.create_table()

        # gacha_config.json 로드 (확률, 풀 ID 등)
        config_path = os.path.join("data", "gacha_config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                self._gacha_config = json.load(f)
            self._pool_ids = self._gacha_config.get("pool_ids", {})
        else:
            print(f"[GachaService] 경고: {config_path} 없음, 기본 설정 사용")

        # 3성 학생 목록 조회 후 배너 자동 생성
        if self._banner_repo.count() == 0:
            star3_df = self._student_repo.find_all(star_grade=3)
            star3_ids = star3_df["id"].tolist()
            self._banner_repo.init_banners(star3_ids)
            print(f"[GachaService] 배너 {len(star3_ids)}개 생성 완료")

    # -------------------------------------------------------------------------
    # 배너 조회
    # -------------------------------------------------------------------------

    def get_banners(self) -> pd.DataFrame:
        """활성 배너 목록 반환"""
        return self._banner_repo.find_all_active()

    def get_banner(self, banner_id: int) -> Optional[pd.Series]:
        """배너 ID로 단일 배너 조회"""
        return self._banner_repo.find_by_id(banner_id)

    def get_current_pull_count(self, banner_id: int) -> int:
        """
        현재 사이클 내 뽑기 수 계산
        - 현재 사이클 뽑기 수 = 총 뽑기 수 - (claimed_count × 200)
        """
        banner = self._banner_repo.find_by_id(banner_id)
        if banner is None:
            return 0
        total = self._gacha_repo.get_total_count(banner_id)
        claimed = int(banner["claimed_count"])
        return total - (claimed * 200)

    def get_stats(self, banner_id: int) -> dict:
        """배너별 뽑기 통계 반환"""
        total = self._gacha_repo.get_total_count(banner_id)
        recent = self._gacha_repo.find_recent(banner_id, limit=total if total < 1000 else 1000)
        star3_count = len(recent[recent["star_grade"] == 3]) if not recent.empty else 0
        return {
            "total_pulls": total,
            "star3_count": star3_count,
            "current_pull_count": self.get_current_pull_count(banner_id),
        }

    def get_recent_pulls(self, banner_id: int, limit: int = 20) -> pd.DataFrame:
        """최근 뽑기 기록 반환"""
        return self._gacha_repo.find_recent(banner_id, limit=limit)

    # -------------------------------------------------------------------------
    # 뽑기 실행
    # -------------------------------------------------------------------------

    def pull(self, banner_id: int, count: int = 1) -> list[PullResult]:
        """
        가챠 뽑기 실행 (1회 또는 10회)
        - 각 결과를 DB에 저장
        - 신규 학생이면 cultivation 레코드 생성
        - 중복 학생이면 엘레프 지급

        Args:
            banner_id: 뽑기를 실행할 배너 ID
            count: 뽑기 횟수 (1 또는 10)

        Returns:
            list[PullResult]: 뽑기 결과 목록
        """
        banner = self._banner_repo.find_by_id(banner_id)
        if banner is None:
            return []

        pickup_id = int(banner["pickup_student_id"])
        current_count = self.get_current_pull_count(banner_id)
        results = []

        for i in range(count):
            # 이번 뽑기의 사이클 내 순번
            pull_num = current_count + i + 1

            # 10회 뽑기에서 마지막 회차: 2성 이상 보장
            is_tenth = (pull_num % 10 == 0)

            # 가챠 알고리즘으로 학생 ID 결정
            student_id = self._gacha_algorithm(
                pull_num, pickup_id, is_tenth
            )

            # DB에 저장
            self._gacha_repo.insert(banner_id, student_id, pull_num)

            # 학생 정보 조회
            student = self._student_repo.find_by_id(student_id)
            if student is None:
                continue

            is_pickup = (student_id == pickup_id)
            is_new = not self._cultivation_repo.exists(student_id)
            eleph_gained = 0

            if is_new:
                # 신규 획득: cultivation 레코드 생성
                self._cultivation_repo.insert_on_acquire(student_id)

                # 3성 학생은 처음 획득 시 엘레프 100개 자동 지급 → 4성 시작
                if int(student["star_grade"]) == 3:
                    self._cultivation_repo.update_current(
                        student_id,
                        star=4,
                        eleph_count=100,
                    )
                    eleph_gained = 100
            else:
                # 중복 획득: 엘레프 지급
                eleph_gained = 100 if is_pickup else 30
                self._cultivation_repo.update_eleph(student_id, eleph_gained)

            results.append(PullResult(
                student_id=student_id,
                student_name=str(student["full_name"]),
                star_grade=int(student["star_grade"]),
                is_pickup=is_pickup,
                is_new=is_new,
                eleph_gained=eleph_gained,
            ))

        return results

    def _gacha_algorithm(
        self, pull_num: int, pickup_id: int, guarantee_2star: bool
    ) -> int:
        """
        가챠 알고리즘 구현
        - 200회 하드 파티: 픽업 학생 확정
        - 소프트 파티 (73회~): 회당 3% 추가
        - 3성 뽑히면 0.7%는 픽업, 나머지는 일반 3성 풀에서 랜덤
        - guarantee_2star: 10회 보장 (2성 이상)
        """
        base_rates = self._gacha_config.get("base_rates", {"3성": 3.0})
        pity = self._gacha_config.get("pity", {
            "hard_pity": 200,
            "soft_pity_start": 73,
            "soft_pity_add_per_pull": 3.0,
        })
        pickup_rate = self._gacha_config.get("pickup_rate", 0.7)

        hard_pity = pity.get("hard_pity", 200)
        soft_start = pity.get("soft_pity_start", 73)
        soft_add = pity.get("soft_pity_add_per_pull", 3.0)

        # 200회 하드 파티: 픽업 확정
        if pull_num % hard_pity == 0 and pull_num > 0:
            return pickup_id

        # 소프트 파티 계산
        base_3star = base_rates.get("3성", 3.0)
        base_2star = base_rates.get("2성", 18.5)

        if pull_num >= soft_start:
            extra = (pull_num - soft_start + 1) * soft_add
            rate_3star = min(base_3star + extra, 100.0)
        else:
            rate_3star = base_3star

        roll = random.uniform(0, 100)

        if roll < rate_3star:
            # ─── 3성 획득 ───
            # 픽업 확률: pickup_rate / rate_3star 비율
            if random.uniform(0, 100) < (pickup_rate / rate_3star * 100):
                return pickup_id
            else:
                pool = self._pool_ids.get("3성", [])
                return random.choice(pool) if pool else pickup_id

        elif roll < rate_3star + base_2star or guarantee_2star:
            # ─── 2성 획득 (또는 10회 보장) ───
            pool = self._pool_ids.get("2성", [])
            return random.choice(pool) if pool else pickup_id

        else:
            # ─── 1성 획득 ───
            pool = self._pool_ids.get("1성", [])
            return random.choice(pool) if pool else pickup_id

    # -------------------------------------------------------------------------
    # 픽업 확정 수령
    # -------------------------------------------------------------------------

    def claim_pickup(self, banner_id: int) -> Optional[PullResult]:
        """
        200회 모집 달성 시 픽업 학생 확정 수령
        - claimed_count 증가 (사이클 카운트 리셋)
        - 픽업 학생 cultivation 처리
        """
        current = self.get_current_pull_count(banner_id)
        if current < 200:
            return None

        banner = self._banner_repo.find_by_id(banner_id)
        if banner is None:
            return None

        # claimed_count 증가 → 사이클 리셋
        self._banner_repo.increment_claimed(banner_id)

        pickup_id = int(banner["pickup_student_id"])
        student = self._student_repo.find_by_id(pickup_id)
        if student is None:
            return None

        is_new = not self._cultivation_repo.exists(pickup_id)
        eleph_gained = 0

        if is_new:
            self._cultivation_repo.insert_on_acquire(pickup_id)
            if int(student["star_grade"]) == 3:
                self._cultivation_repo.update_current(
                    pickup_id, star=4, eleph_count=100
                )
                eleph_gained = 100
        else:
            eleph_gained = 100
            self._cultivation_repo.update_eleph(pickup_id, eleph_gained)

        return PullResult(
            student_id=pickup_id,
            student_name=str(student["full_name"]),
            star_grade=int(student["star_grade"]),
            is_pickup=True,
            is_new=is_new,
            eleph_gained=eleph_gained,
        )
