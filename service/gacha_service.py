"""
service/gacha_service.py
가챠 시뮬레이터 비즈니스 로직

- 배너 초기화 (3성 학생 목록 기반 자동 생성)
- 가챠 알고리즘 구현 (Nexon 공식 확률표 기반, 소프트 파티 없음)
  - 픽업 3성 0.7%, 비픽업 3성/2성은 풀 크기에 따라 동적 계산
  - 매 뽑기 확률 고정 (누적 횟수에 따라 확률이 오르지 않음)
  - 10회 보장 (2성 이상), 200회 하드 파티 (픽업 확정)
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
        - 확률: 매 뽑기 고정 (소프트 파티 없음)
        - 10연 보장: 10회차에 2성 이상 확정
        - 200회 천장: 픽업 학생 확정
        """
        banner = self._banner_repo.find_by_id(banner_id)
        if banner is None:
            return []

        pickup_id = int(banner["pickup_student_id"])
        current_count = self.get_current_pull_count(banner_id)

        results = []
        for i in range(count):
            pull_num = current_count + i + 1
            is_tenth = (pull_num % 10 == 0)

            # 200회 천장: 픽업 확정
            if pull_num == 200:
                student_id = pickup_id
            else:
                student_id = self._gacha_algorithm(pickup_id, is_tenth)

            self._gacha_repo.insert(banner_id, student_id, pull_num)

            student = self._student_repo.find_by_id(student_id)
            if student is None:
                continue

            is_pickup = (student_id == pickup_id)
            star_grade = int(student["star_grade"])
            is_new, eleph_gained = self._process_acquisition(student_id, star_grade, is_pickup)

            results.append(PullResult(
                student_id=student_id,
                student_name=str(student["full_name"]),
                star_grade=star_grade,
                is_pickup=is_pickup,
                is_new=is_new,
                eleph_gained=eleph_gained,
            ))

        return results

    def _process_acquisition(
        self, student_id: int, star_grade: int, is_pickup: bool,
    ) -> tuple[bool, int]:
        """
        학생 획득(신규/중복) 공통 처리 — pull()과 claim_pickup() 양쪽에서 호출.
        예전엔 두 메서드에 거의 동일한 if/else 블록이 그대로 중복되어 있었는데,
        이 메서드 하나로 합쳤다.

        - 신규 획득: cultivation 레코드를 새로 만든다. 그중 3성 학생은 인게임 규칙상
          모집 즉시 4성으로 승급되며 부족한 인연각인용 엘레프 100개를 함께 받는다.
        - 중복 획득: 신규 생성 없이 엘레프만 적립한다 (픽업 중복 100개, 일반 중복 30개).

        Returns:
            (is_new, eleph_gained) — PullResult 생성에 그대로 쓰인다.
        """
        is_new = not self._cultivation_repo.exists(student_id)
        if is_new:
            self._cultivation_repo.insert_on_acquire(student_id)
            if star_grade == 3:
                self._cultivation_repo.update_current(student_id, star=4, eleph_count=100)
                return True, 100
            return True, 0

        eleph_gained = 100 if is_pickup else 30
        self._cultivation_repo.update_eleph(student_id, eleph_gained)
        return False, eleph_gained

    def _gacha_algorithm(self, pickup_id: int, guarantee_2star: bool) -> int:
        """
        가챠 알고리즘 — 소프트 파티 없음, 매 뽑기 확률 고정

        공식 확률 (Nexon 확률표 기준):
          픽업 3성:    0.7%       (1명 × 0.700000%)
          비픽업 3성:  캐릭터 수 × 0.022772% (풀 크기에 따라 동적 계산)
          2성:         캐릭터 수 × 0.804348%
          1성:         나머지
          ※ 10회차: 2성 이상 확정 (guarantee_2star=True)
          ※ 200회차: 픽업 확정 (pull()에서 직접 처리)
        """
        PICKUP_RATE          = 0.7
        PER_NONPICKUP_3STAR  = 0.022772  # 비픽업 3성 1명당 확률 (Nexon 확률표)
        PER_2STAR            = 0.804348  # 2성 1명당 확률 (Nexon 확률표)

        pool_3 = self._pool_ids.get("3성", [])
        pool_2 = self._pool_ids.get("2성", [])
        nonpickup_count = max(len(pool_3) - 1, 0)  # 픽업 1명 제외

        NONPICKUP_3STAR_RATE = nonpickup_count * PER_NONPICKUP_3STAR
        BASE_2STAR           = len(pool_2) * PER_2STAR

        roll = random.uniform(0, 100)

        if roll < PICKUP_RATE:
            return pickup_id
        elif roll < PICKUP_RATE + NONPICKUP_3STAR_RATE:
            pool = self._pool_ids.get("3성", [])
            return random.choice(pool) if pool else pickup_id
        elif roll < PICKUP_RATE + NONPICKUP_3STAR_RATE + BASE_2STAR or guarantee_2star:
            pool = self._pool_ids.get("2성", [])
            return random.choice(pool) if pool else pickup_id
        else:
            pool = self._pool_ids.get("1성", [])
            return random.choice(pool) if pool else pickup_id

    # -------------------------------------------------------------------------
    # 뽑기 초기화
    # -------------------------------------------------------------------------

    def reset_banner(self, banner_id: int) -> None:
        """
        해당 배너의 뽑기 기록 전체 초기화
        - gacha_pull 레코드 전체 삭제
        - banner.claimed_count 0으로 리셋
        """
        self._gacha_repo.delete_by_banner(banner_id)
        self._banner_repo.reset_claimed(banner_id)

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

        star_grade = int(student["star_grade"])
        is_new, eleph_gained = self._process_acquisition(pickup_id, star_grade, is_pickup=True)

        return PullResult(
            student_id=pickup_id,
            student_name=str(student["full_name"]),
            star_grade=star_grade,
            is_pickup=True,
            is_new=is_new,
            eleph_gained=eleph_gained,
        )
