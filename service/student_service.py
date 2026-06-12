"""
service/student_service.py
학생 도감 관련 비즈니스 로직

- JSON 데이터를 읽어 DB 초기화
- 학생 목록 필터링, 상세 조회
- SchaleDB 이미지 URL 생성 및 저장
"""

import json
import os
from typing import Optional
import pandas as pd

from repository.interfaces import (
    IStudentRepository,
    ISkillRepository,
    IStudentImageRepository,
    IQueryRepository,
)

# SchaleDB 이미지 URL 패턴
SCHALEDB_BASE = "https://schaledb.com/images/student"

# 인게임 스킬 유형 → DB skill_type 코드 매핑
SKILL_KEY_MAP = {
    "EX스킬":   "ex_skill",
    "기본스킬": "normal_skill",
    "강화스킬": "enhance_skill",
    "서브스킬": "sub_skill",
}


class StudentService:
    """
    학생 도감 서비스 (비즈니스 로직)
    - 의존성 주입(DI): 인터페이스를 통해 Repository 사용 → DIP 준수
    - Service는 어떤 DB를 사용하는지 알 필요 없음
    """

    def __init__(
        self,
        student_repo: IStudentRepository,
        skill_repo: ISkillRepository,
        image_repo: IStudentImageRepository,
        query_repo: IQueryRepository,
    ):
        # 인터페이스 타입으로 주입받아 구현체에 독립적
        self._student_repo = student_repo
        self._skill_repo = skill_repo
        self._image_repo = image_repo
        self._query_repo = query_repo

    # -------------------------------------------------------------------------
    # DB 초기화: JSON → DuckDB 로드
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        """
        앱 최초 실행 시 DB 테이블 생성 + JSON 데이터 로드
        - student 테이블이 비어있으면 students.json에서 로드
        """
        # 테이블 생성 (없으면)
        self._student_repo.create_table()
        self._skill_repo.create_table()
        self._image_repo.create_table()

        # 이미 데이터가 있으면 스킵
        if self._student_repo.count() > 0:
            print(f"[StudentService] 학생 데이터 이미 로드됨: {self._student_repo.count()}명")
            return

        # students.json 경로 결정
        data_path = os.path.join("data", "students.json")
        if not os.path.exists(data_path):
            print(f"[StudentService] 경고: {data_path} 파일 없음")
            return

        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)

        students = data.get("students", [])
        print(f"[StudentService] {len(students)}명 학생 데이터 로드 중...")

        # 학생 기본 정보 일괄 삽입
        self._student_repo.bulk_insert(students)

        # 스킬 및 이미지 삽입
        for s in students:
            self._load_skills(s)
            self._load_images(s)

        print(f"[StudentService] 초기화 완료: {self._student_repo.count()}명")

    def _load_skills(self, s: dict) -> None:
        """
        학생 스킬 데이터 DB 삽입
        - skills 딕셔너리에서 4가지 주요 스킬 타입만 추출
        - skill_icon: SchaleDB 스킬 아이콘 URL 생성
        """
        skills_raw = s.get("skills", {})
        skills_to_insert = []

        for kor_type, db_type in SKILL_KEY_MAP.items():
            skill_data = skills_raw.get(kor_type, {})
            # 스킬 아이콘은 skill_type 기반으로 URL 생성
            icon_url = (
                f"{SCHALEDB_BASE}/skill/{s['path_name']}_{db_type}.webp"
                if s.get("path_name") else None
            )
            skills_to_insert.append({
                "skill_type": db_type,
                "skill_name": skill_data.get("name", ""),
                "skill_desc": skill_data.get("desc", ""),
                "skill_icon": icon_url,
            })

        self._skill_repo.bulk_insert(s["id"], skills_to_insert)

    def _load_images(self, s: dict) -> None:
        """
        학생 이미지 URL DB 삽입 (SchaleDB URL 형식으로 생성)
        - collection: 초상화 이미지 (도감 상세 화면)
        - icon: 아이콘 이미지 (학생 목록, 보유 학생 버튼)
        - weapon: 고유 무기 이미지
        """
        path = s.get("path_name", "")
        if not path:
            return

        images = [
            {
                "image_type": "collection",
                "image_url": f"{SCHALEDB_BASE}/collection/{path}.webp",
            },
            {
                "image_type": "icon",
                "image_url": f"{SCHALEDB_BASE}/icon/{path}.webp",
            },
            {
                "image_type": "weapon",
                "image_url": f"{SCHALEDB_BASE}/weapon/_weapon_{path}.webp",
            },
        ]
        self._image_repo.bulk_insert(s["id"], images)

    # -------------------------------------------------------------------------
    # 학생 목록 조회
    # -------------------------------------------------------------------------

    def get_students(
        self,
        star_grade: Optional[int] = None,
        school: Optional[str] = None,
        tactic_role: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        조건 필터링된 학생 목록 반환 (아이콘 URL 포함)
        - student LEFT JOIN student_image (icon)
        """
        return self._query_repo.get_students_with_icons(
            star_grade=star_grade,
            school=school,
            tactic_role=tactic_role,
            keyword=keyword,
        )

    def get_student_detail(self, student_id: int) -> pd.DataFrame:
        """
        학생 상세 정보 + 스킬 목록 조회 (student JOIN skill)
        - Use Case 3.1.1: 학생 상세 정보 및 스킬 조회
        """
        return self._query_repo.get_student_with_skills(student_id)

    def get_collection_image_url(self, student_id: int) -> Optional[str]:
        """학생 초상화 이미지 URL 반환"""
        return self._image_repo.find_url(student_id, "collection")

    def get_schools(self) -> list[str]:
        """학교 목록 반환 (필터 드롭다운용)"""
        return self._student_repo.find_distinct_schools()

    def get_roles(self) -> list[str]:
        """전술 역할 목록 반환 (필터 드롭다운용)"""
        return self._student_repo.find_distinct_roles()
