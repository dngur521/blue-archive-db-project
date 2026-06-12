"""
service/cultivation_service.py
육성 시뮬레이터 비즈니스 로직

- 보유 학생 현황 조회 (cultivation JOIN student LEFT JOIN cultivation_goal)
- 육성 목표 설정 및 저장
- 육성 비용 계산 (레벨업 크레딧, 스킬 재료, 인연 선물)
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from repository.interfaces import (
    ICultivationRepository,
    ICultivationGoalRepository,
    IQueryRepository,
)


@dataclass
class CostSummary:
    """육성 비용 계산 결과 데이터 클래스"""
    credit: int = 0                         # 총 필요 크레딧
    exp_items: dict = field(default_factory=dict)   # 활동 보고서 아이템별 수량
    skill_credits: int = 0                  # 스킬 강화 크레딧
    skill_items: dict = field(default_factory=dict)  # 스킬 재료 아이템별 수량
    eleph_needed: int = 0                   # 필요 엘레프 (성급 상승)
    eleph_current: int = 0                  # 현재 보유 엘레프
    bond_gifts: dict = field(default_factory=dict)   # 인연 랭크 필요 선물 수


class CultivationService:
    """
    육성 시뮬레이터 서비스
    - Use Case 3.3: 보유 학생 현황 조회
    - Use Case 3.3.1: 육성 목표 설정
    - Use Case 3.3.2: 육성 비용 계산
    """

    def __init__(
        self,
        cultivation_repo: ICultivationRepository,
        goal_repo: ICultivationGoalRepository,
        query_repo: IQueryRepository,
    ):
        self._cultivation_repo = cultivation_repo
        self._goal_repo = goal_repo
        self._query_repo = query_repo
        self._costs: dict = {}
        self._students_data: list[dict] = []

    # -------------------------------------------------------------------------
    # 초기화
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        """
        테이블 생성 + 비용 데이터 로드
        """
        self._cultivation_repo.create_table()
        self._goal_repo.create_table()

        # costs.json 로드 (레벨업 비용, 스킬 강화 비용 등)
        costs_path = os.path.join("data", "costs.json")
        if os.path.exists(costs_path):
            with open(costs_path, encoding="utf-8") as f:
                self._costs = json.load(f)

        # students.json 로드 (학생별 스킬 재료 비용)
        students_path = os.path.join("data", "students.json")
        if os.path.exists(students_path):
            with open(students_path, encoding="utf-8") as f:
                data = json.load(f)
            self._students_data = data.get("students", [])

    # -------------------------------------------------------------------------
    # 보유 학생 조회
    # -------------------------------------------------------------------------

    def get_owned_students(self) -> pd.DataFrame:
        """
        보유 학생 목록 조회 (cultivation JOIN student LEFT JOIN cultivation_goal)
        Use Case 3.3: 보유 학생 현황 조회
        """
        return self._query_repo.get_owned_students()

    def reset_all_owned(self) -> None:
        """보유 학생 전체 초기화 (cultivation + cultivation_goal 전체 삭제)"""
        self._goal_repo.delete_all()
        self._cultivation_repo.delete_all()

    def get_cultivation(self, student_id: int) -> Optional[pd.Series]:
        """현재 육성 현황 조회"""
        return self._cultivation_repo.find_by_student(student_id)

    def get_goal(self, student_id: int) -> Optional[pd.Series]:
        """목표 육성 현황 조회 (미설정이면 None)"""
        return self._goal_repo.find_by_student(student_id)

    # -------------------------------------------------------------------------
    # 육성 목표 설정 및 비용 계산
    # -------------------------------------------------------------------------

    def calculate_and_save(
        self,
        student_id: int,
        current_fields: dict,
        goal_fields: dict,
    ) -> CostSummary:
        """
        Use Case 3.3.1 / 3.3.2: 육성 목표 저장 + 비용 계산
        1. 현재 육성 수치를 cultivation 테이블에 업데이트
        2. 목표 수치를 cultivation_goal 테이블에 UPSERT
        3. 비용 계산 결과 반환

        Args:
            student_id: 대상 학생 ID
            current_fields: 현재 수치 딕셔너리 (level, ex_skill, ...)
            goal_fields: 목표 수치 딕셔너리 (level, ex_skill, ...)
        """
        # 현재 육성 수치 저장
        if current_fields:
            self._cultivation_repo.update_current(student_id, **current_fields)

        # 목표 육성 수치 UPSERT
        if goal_fields:
            self._goal_repo.upsert(student_id, **goal_fields)

        # 비용 계산
        return self._compute_costs(student_id, current_fields, goal_fields)

    def _compute_costs(
        self,
        student_id: int,
        current: dict,
        goal: dict,
    ) -> CostSummary:
        """
        육성 비용 계산
        - 레벨업: char_level 비용 테이블 기반
        - 스킬: skill 크레딧 + 학생별 재료 비용
        - 인연: gift 수량 계산
        """
        summary = CostSummary()

        # ── 레벨업 비용 계산 ─────────────────────────────────────────────────
        cur_level = int(current.get("level", 1))
        goal_level = int(goal.get("level", cur_level))
        if goal_level > cur_level:
            summary.credit += self._calc_level_credit(cur_level, goal_level)

        # ── 스킬 강화 비용 계산 ──────────────────────────────────────────────
        skill_costs = self._costs.get("skill", {})
        normal_credits = skill_costs.get("normal_credit_per_level", [])
        ex_credits = skill_costs.get("ex_credit_per_level", [])

        # 일반/강화/서브 스킬 (최대 레벨 10)
        for skill_key in ["normal_skill", "enhance_skill", "sub_skill"]:
            cur_lv = int(current.get(skill_key, 1))
            goal_lv = int(goal.get(skill_key, cur_lv))
            if goal_lv > cur_lv and normal_credits:
                for i in range(cur_lv - 1, min(goal_lv - 1, len(normal_credits))):
                    summary.skill_credits += normal_credits[i]

        # EX 스킬 (최대 레벨 5)
        cur_ex = int(current.get("ex_skill", 1))
        goal_ex = int(goal.get("ex_skill", cur_ex))
        if goal_ex > cur_ex and ex_credits:
            for i in range(cur_ex - 1, min(goal_ex - 1, len(ex_credits))):
                summary.skill_credits += ex_credits[i]

        # 학생별 스킬 재료 계산 (기본/강화/서브 + EX)
        summary.skill_items = self._calc_skill_items(
            student_id,
            current.get("normal_skill",  1), goal.get("normal_skill",  1),
            current.get("enhance_skill", 1), goal.get("enhance_skill", 1),
            current.get("sub_skill",     1), goal.get("sub_skill",     1),
            current.get("ex_skill",      1), goal.get("ex_skill",      1),
        )

        summary.credit += summary.skill_credits

        # ── 성급 상승 엘레프 계산 ────────────────────────────────────────────
        cur_star = int(current.get("star", 1))
        goal_star = int(goal.get("star", cur_star))
        cultivation = self._cultivation_repo.find_by_student(student_id)
        eleph_now = int(cultivation["eleph_count"]) if cultivation is not None else 0

        if goal_star > cur_star:
            # 1성 → 5성까지 각 성급별 필요 엘레프: 20, 40, 60, 80개
            eleph_per_star = [20, 40, 60, 80]
            needed = sum(eleph_per_star[i] for i in range(cur_star - 1, goal_star - 1))
            summary.eleph_needed = needed
            summary.eleph_current = eleph_now

        # ── 인연 랭크 선물 계산 ──────────────────────────────────────────────
        cur_bond = int(current.get("bond_rank", 1))
        goal_bond = int(goal.get("bond_rank", cur_bond))
        if goal_bond > cur_bond:
            summary.bond_gifts = self._calc_bond_gifts(cur_bond, goal_bond)

        return summary

    def _calc_level_credit(self, cur: int, goal: int) -> int:
        """레벨 구간 크레딧 합산"""
        credit_per_level = self._costs.get("char_level", {}).get("credit_per_level", [])
        total = 0
        for i in range(cur - 1, min(goal - 1, len(credit_per_level))):
            total += credit_per_level[i]
        return total

    def _calc_skill_items(
        self,
        student_id: int,
        cur_normal: int,  goal_normal: int,
        cur_enhance: int, goal_enhance: int,
        cur_sub: int,     goal_sub: int,
        cur_ex: int,      goal_ex: int,
    ) -> dict:
        """
        학생별 스킬 강화 재료 계산
        - 기본/강화/서브 스킬: skill_upgrade_cost (같은 재료 테이블 공유)
        - EX 스킬: ex_upgrade_cost
        """
        student_data = next(
            (s for s in self._students_data if s["id"] == student_id), None
        )
        if student_data is None:
            return {}

        items = self._load_items()
        item_totals: dict[str, int] = {}

        # 기본/강화/서브 스킬 재료 (동일 테이블)
        skill_cost_table = student_data.get("skill_upgrade_cost", [])
        for cur_lv, goal_lv in [
            (cur_normal,  goal_normal),
            (cur_enhance, goal_enhance),
            (cur_sub,     goal_sub),
        ]:
            for level_idx in range(cur_lv - 1, min(goal_lv - 1, len(skill_cost_table))):
                for item in skill_cost_table[level_idx]:
                    item_id = str(item["item_id"])
                    item_name = items.get(item_id, {}).get("name", f"아이템{item_id}")
                    item_totals[item_name] = item_totals.get(item_name, 0) + item["amount"]

        # EX 스킬 재료
        ex_cost_table = student_data.get("ex_upgrade_cost", [])
        for level_idx in range(cur_ex - 1, min(goal_ex - 1, len(ex_cost_table))):
            for item in ex_cost_table[level_idx]:
                item_id = str(item["item_id"])
                item_name = items.get(item_id, {}).get("name", f"아이템{item_id}")
                item_totals[item_name] = item_totals.get(item_name, 0) + item["amount"]

        return item_totals

    def _calc_bond_gifts(self, cur: int, goal: int) -> dict:
        """인연 랭크 달성을 위한 선물 수 계산 (SR급 기준)"""
        bond_data = self._costs.get("bond_rank", {})
        thresholds = bond_data.get("exp_thresholds", [])
        gift_values = bond_data.get("gift_exp_values", {"SR급 선물": 20})

        if len(thresholds) < goal + 1:
            return {}

        # cur → goal 달성에 필요한 총 EXP
        total_exp = thresholds[goal] - thresholds[cur]
        if total_exp <= 0:
            return {}

        sr_value = gift_values.get("SR급 선물", 20)
        r_value = gift_values.get("R급 선물", 5)
        n_value = gift_values.get("N급 선물", 1)

        sr_count = total_exp // sr_value
        remainder = total_exp % sr_value
        r_count = remainder // r_value
        n_count = remainder % r_value

        result = {}
        if sr_count > 0:
            result["SR급 선물"] = sr_count
        if r_count > 0:
            result["R급 선물"] = r_count
        if n_count > 0:
            result["N급 선물"] = n_count
        return result

    def _load_items(self) -> dict:
        """items.json 로드 (아이템 이름 조회용)"""
        items_path = os.path.join("data", "items.json")
        if not os.path.exists(items_path):
            return {}
        with open(items_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", {})
