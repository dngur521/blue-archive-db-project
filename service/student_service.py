"""
service/student_service.py
학생 도감 관련 비즈니스 로직

- JSON 데이터를 읽어 DB 초기화
- 학생 목록 필터링, 상세 조회
- SchaleDB 이미지 URL, 스탯, 스킬 파라미터 저장
"""

import json
import os
from typing import Optional
import pandas as pd

from repository.interfaces import (
    IStudentRepository,
    ISkillRepository,
    IStudentImageRepository,
    IStudentStatRepository,
    IQueryRepository,
)

SCHALEDB_BASE = "https://schaledb.com/images/student"

SKILL_KEY_MAP = {
    "EX스킬":    "ex_skill",
    "기본스킬":  "normal_skill",   # Normal (자동공격) — 뷰에서 숨김
    "강화스킬":  "enhance_skill",  # Public → 인게임 "기본 스킬"
    "서브스킬":  "sub_skill",      # Passive → 인게임 "강화 스킬"
    "서브스킬2": "extra_skill",    # ExtraPassive → 인게임 "서브 스킬"
}


class StudentService:
    """
    학생 도감 서비스 (비즈니스 로직)
    DI: 인터페이스를 통해 Repository 사용 → DIP 준수
    """

    def __init__(
        self,
        student_repo: IStudentRepository,
        skill_repo: ISkillRepository,
        image_repo: IStudentImageRepository,
        stat_repo: IStudentStatRepository,
        query_repo: IQueryRepository,
    ):
        self._student_repo = student_repo
        self._skill_repo = skill_repo
        self._image_repo = image_repo
        self._stat_repo = stat_repo
        self._query_repo = query_repo

    # -------------------------------------------------------------------------
    # 초기화
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        """테이블 생성 + JSON 데이터 로드"""
        self._student_repo.create_table()
        self._skill_repo.create_table()
        self._image_repo.create_table()
        self._stat_repo.create_table()

        data_path = os.path.join("data", "students.json")

        if self._student_repo.count() > 0:
            print(f"[StudentService] 학생 데이터 이미 로드됨: {self._student_repo.count()}명")
            self._migrate_extra_skill(data_path)
            return
        if not os.path.exists(data_path):
            print(f"[StudentService] 경고: {data_path} 없음")
            return

        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)

        students = data.get("students", [])
        print(f"[StudentService] {len(students)}명 로드 중...")

        self._student_repo.bulk_insert(students)

        for s in students:
            self._load_skills(s)
            self._load_images(s)

        # 스탯 + 스킬 파라미터 로드 (student_extras.json)
        self._load_extras(students)

        print(f"[StudentService] 초기화 완료: {self._student_repo.count()}명")

    def _migrate_extra_skill(self, data_path: str) -> None:
        """extra_skill 레코드 삽입 + NULL params 업데이트 (마이그레이션)"""
        try:
            extra_count = self._skill_repo._con.execute(
                "SELECT COUNT(*) FROM skill WHERE skill_type = 'extra_skill'"
            ).fetchone()[0]
        except Exception:
            return

        # extra_skill 행이 없으면 삽입
        if extra_count == 0:
            if not os.path.exists(data_path):
                return
            with open(data_path, encoding="utf-8") as f:
                data = json.load(f)

            count = 0
            for s in data.get("students", []):
                skill_data = s.get("skills", {}).get("서브스킬2", {})
                if not skill_data:
                    continue
                self._skill_repo.bulk_insert(s["id"], [{
                    "skill_type": "extra_skill",
                    "skill_name": skill_data.get("name", ""),
                    "skill_desc": skill_data.get("desc", ""),
                    "skill_icon": skill_data.get("icon"),
                    "params_lv1": None,
                    "params_max": None,
                }])
                count += 1
            print(f"[StudentService] extra_skill 행 삽입 완료: {count}명")

        # params_lv1 이 NULL인 extra_skill 행을 student_extras.json으로 업데이트
        try:
            null_params = self._skill_repo._con.execute(
                "SELECT COUNT(*) FROM skill WHERE skill_type = 'extra_skill' AND params_lv1 IS NULL"
            ).fetchone()[0]
        except Exception:
            return
        if null_params == 0:
            return

        extras_path = os.path.join("data", "student_extras.json")
        if not os.path.exists(extras_path):
            return
        with open(extras_path, encoding="utf-8") as f:
            extras = json.load(f)

        updated = 0
        for sid_str, entry in extras.items():
            ep = entry.get("skill_params", {}).get("extra_skill")
            if not ep:
                continue
            lv1_json = json.dumps(ep.get("lv1", []), ensure_ascii=False)
            max_json  = json.dumps(ep.get("max", []),  ensure_ascii=False)
            self._skill_repo._con.execute("""
                UPDATE skill SET params_lv1 = ?, params_max = ?
                WHERE student_id = ? AND skill_type = 'extra_skill'
            """, [lv1_json, max_json, int(sid_str)])
            updated += 1
        print(f"[StudentService] extra_skill params 업데이트 완료: {updated}명")

    def _load_skills(self, s: dict) -> None:
        """
        스킬 데이터 삽입 (파라미터 제외 - _load_extras에서 업데이트)
        skill_icon: SchaleDB Skills.{타입}.Icon 코드 기반 실제 아이콘 URL
        (fetch_students.py의 parse_skills()가 students.json에 미리 저장해 둠)
        """
        skills_raw = s.get("skills", {})
        skills_to_insert = []
        for kor_type, db_type in SKILL_KEY_MAP.items():
            skill_data = skills_raw.get(kor_type, {})
            skills_to_insert.append({
                "skill_type": db_type,
                "skill_name": skill_data.get("name", ""),
                "skill_desc": skill_data.get("desc", ""),
                "skill_icon": skill_data.get("icon"),
                "params_lv1": None,
                "params_max": None,
            })
        self._skill_repo.bulk_insert(s["id"], skills_to_insert)

    def _load_images(self, s: dict) -> None:
        """이미지 URL 삽입 (ID 기반 URL)"""
        sid = s.get("id")
        if not sid:
            return
        images = [
            {"image_type": "collection", "image_url": f"{SCHALEDB_BASE}/collection/{sid}.webp"},
            {"image_type": "icon",       "image_url": f"{SCHALEDB_BASE}/icon/{sid}.webp"},
            {"image_type": "weapon",     "image_url": f"{SCHALEDB_BASE}/weapon/{sid}.webp"},
        ]
        self._image_repo.bulk_insert(sid, images)

    def _load_extras(self, students: list[dict]) -> None:
        """
        student_extras.json에서 스탯 + 스킬 파라미터 로드
        - student_stat 테이블: Lv.1 / MAX 능력치 삽입
        - skill 테이블: params_lv1, params_max 업데이트
        """
        extras_path = os.path.join("data", "student_extras.json")
        if not os.path.exists(extras_path):
            print("[StudentService] student_extras.json 없음, fetch_extras.py 실행 필요")
            return

        with open(extras_path, encoding="utf-8") as f:
            extras = json.load(f)

        # 스탯 일괄 삽입
        stat_list = []
        for s in students:
            sid = str(s["id"])
            if sid in extras:
                stat = extras[sid].get("stats", {})
                stat["student_id"] = s["id"]
                stat_list.append(stat)
        if stat_list:
            self._stat_repo.bulk_insert(stat_list)

        # 스킬 파라미터 업데이트
        for s in students:
            sid = str(s["id"])
            if sid not in extras:
                continue
            skill_params = extras[sid].get("skill_params", {})
            for skill_type, params in skill_params.items():
                lv1_json = json.dumps(params.get("lv1", []), ensure_ascii=False)
                max_json  = json.dumps(params.get("max", []), ensure_ascii=False)
                self._skill_repo._con.execute("""
                    UPDATE skill SET params_lv1 = ?, params_max = ?
                    WHERE student_id = ? AND skill_type = ?
                """, [lv1_json, max_json, s["id"], skill_type])

        print(f"[StudentService] 스탯/파라미터 로드 완료: {len(stat_list)}명")

    # -------------------------------------------------------------------------
    # 조회
    # -------------------------------------------------------------------------

    def get_students(
        self,
        star_grade: Optional[int] = None,
        school: Optional[str] = None,
        tactic_role: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Use Case 3.1: 학생 목록 조회 및 필터링
        student LEFT JOIN student_image(icon)으로 아이콘까지 한 번에 받아온다.
        모든 필터 파라미터는 선택값(None이면 해당 조건 미적용).
        """
        return self._query_repo.get_students_with_icons(
            star_grade=star_grade, school=school,
            tactic_role=tactic_role, keyword=keyword,
        )

    def get_student_detail(self, student_id: int) -> pd.DataFrame:
        """학생 상세 + 스킬 목록 (student JOIN skill)"""
        return self._query_repo.get_student_with_skills(student_id)

    def get_student_stat(self, student_id: int) -> Optional[pd.Series]:
        """Lv.1 / MAX 능력치 조회"""
        return self._stat_repo.find_by_student(student_id)

    def get_collection_image_url(self, student_id: int) -> Optional[str]:
        """학생 상세 패널 상단에 띄울 초상화(collection) 이미지 URL 조회"""
        return self._image_repo.find_url(student_id, "collection")

    def get_schools(self) -> list[str]:
        """필터 드롭다운에 쓸 학교 목록 (DISTINCT)"""
        return self._student_repo.find_distinct_schools()

    def get_roles(self) -> list[str]:
        """필터 드롭다운에 쓸 전술 역할 목록 (DISTINCT)"""
        return self._student_repo.find_distinct_roles()
