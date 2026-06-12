"""
repository/duckdb/join.py
DuckDB JOIN 전용 쿼리 레포지토리 구현체

[설계 제한요소 충족]
- 세 개 이상 테이블 JOIN (LEFT JOIN 포함) 필수 조건 충족:

  1) get_owned_students():
     cultivation JOIN student
     LEFT JOIN cultivation_goal
     LEFT JOIN student_image (icon)
     → 4개 테이블 JOIN + LEFT JOIN ✓

  2) get_student_with_skills():
     student JOIN skill
     → 2개 테이블 JOIN (상세 화면용)

  3) get_students_with_icons():
     student LEFT JOIN student_image
     → 2개 테이블 LEFT JOIN (학생 목록용)
"""

from typing import Optional
import pandas as pd
from repository.interfaces import IQueryRepository, IDatabaseManager


class DuckDBQueryRepository(IQueryRepository):
    """JOIN 전용 쿼리 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def get_student_with_skills(self, student_id: int) -> pd.DataFrame:
        """
        student JOIN skill — 학생 상세 정보 + 스킬 목록

        Use Case 3.1.1: 학생 상세 정보 및 스킬 조회
        한 번의 JOIN 쿼리로 학생 정보와 스킬 4종을 동시에 조회
        """
        return self._con.execute("""
            SELECT
                s.id, s.full_name, s.star_grade, s.school,
                s.tactic_role, s.position, s.bullet_type,
                s.armor_type, s.weapon_type_code,
                s.terrain_street, s.terrain_outdoor, s.terrain_indoor,
                s.weapon_name, s.weapon_desc,
                s.gear_name, s.gear_desc,
                s.school_year, s.voice, s.birthday, s.age, s.height, s.hobby,
                sk.skill_type, sk.skill_name, sk.skill_desc, sk.skill_icon
            FROM student s
            JOIN skill sk ON sk.student_id = s.id
            WHERE s.id = ?
            ORDER BY sk.id
        """, [student_id]).df()

    def get_owned_students(self) -> pd.DataFrame:
        """
        보유 학생 현황 + 목표 + 아이콘 통합 조회

        [핵심 JOIN 쿼리] - 설계 제한요소 (세 개 이상 테이블 JOIN) 충족:
          cultivation          (보유 학생 목록 기준)
          JOIN  student        (학생 기본 정보)
          LEFT JOIN cultivation_goal (목표 미설정 학생도 포함)
          LEFT JOIN student_image    (아이콘 없는 학생도 포함)

        Use Case 3.3: 보유 학생 현황 조회
        - cultivation이 있으면 반드시 포함 (LEFT JOIN으로 nullable 처리)
        - 육성 목표 미설정 학생 → goal_* 컬럼이 NULL
        - 아이콘 이미지 미등록 학생 → icon_url이 NULL
        """
        return self._con.execute("""
            SELECT
                c.student_id,
                s.full_name,
                s.star_grade        AS base_star,
                s.path_name,
                c.star              AS current_star,
                c.weapon_star,
                c.eleph_count,
                c.level             AS current_level,
                c.ex_skill, c.normal_skill, c.enhance_skill, c.sub_skill,
                c.weapon_level, c.gear_level, c.bond_rank,
                c.acquired_at, c.updated_at,
                cg.star             AS goal_star,
                cg.level            AS goal_level,
                cg.ex_skill         AS goal_ex_skill,
                cg.normal_skill     AS goal_normal_skill,
                cg.enhance_skill    AS goal_enhance_skill,
                cg.sub_skill        AS goal_sub_skill,
                cg.weapon_level     AS goal_weapon_level,
                cg.bond_rank        AS goal_bond_rank,
                si.image_url        AS icon_url
            FROM cultivation c
            JOIN student s
                ON s.id = c.student_id
            LEFT JOIN cultivation_goal cg
                ON cg.student_id = c.student_id
            LEFT JOIN student_image si
                ON si.student_id = c.student_id
                AND si.image_type = 'icon'
            ORDER BY c.acquired_at DESC
        """).df()

    def get_students_with_icons(
        self,
        star_grade: Optional[int] = None,
        school: Optional[str] = None,
        tactic_role: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        학생 도감 목록 + 아이콘 URL (student LEFT JOIN student_image)

        Use Case 3.1: 학생 목록 조회 및 필터링
        - LEFT JOIN: 이미지 없는 학생도 목록에 표시
        - WHERE 조건: 필터 적용
        """
        query = """
            SELECT
                s.id, s.full_name, s.star_grade, s.school,
                s.tactic_role, s.position, s.bullet_type,
                s.is_limited, s.path_name,
                si.image_url AS icon_url
            FROM student s
            LEFT JOIN student_image si
                ON si.student_id = s.id
                AND si.image_type = 'icon'
            WHERE 1=1
        """
        params = []

        if star_grade is not None:
            query += " AND s.star_grade = ?"
            params.append(star_grade)
        if school:
            query += " AND s.school = ?"
            params.append(school)
        if tactic_role:
            query += " AND s.tactic_role = ?"
            params.append(tactic_role)
        if keyword:
            query += " AND s.full_name LIKE ?"
            params.append(f"%{keyword}%")

        query += " ORDER BY s.star_grade DESC, s.full_name"
        return self._con.execute(query, params).df()
