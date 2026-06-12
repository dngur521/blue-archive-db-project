"""
repository/duckdb/skill.py
DuckDB skill 테이블 구현체

약한 엔티티: skill (학생 종속)
- 한 학생은 4가지 스킬 유형(EX/기본/강화/서브)을 보유
- 후보키: {id}, {student_id, skill_type} - UNIQUE 복합 제약
- skill_icon: SchaleDB 아이콘 URL 저장
"""

import pandas as pd
from repository.interfaces import ISkillRepository, IDatabaseManager

# 인게임 한국어 명칭 → DB skill_type 코드 매핑
SKILL_TYPE_MAP = {
    "EX스킬":    "ex_skill",
    "기본스킬":  "normal_skill",
    "강화스킬":  "enhance_skill",
    "서브스킬":  "sub_skill",
}


class DuckDBSkillRepository(ISkillRepository):
    """skill 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def create_table(self) -> None:
        """
        skill 테이블 생성 (DDL)
        - SEQUENCE + nextval(): DuckDB 방식의 자동 증가 PK
        - UNIQUE(student_id, skill_type): 복합 후보키
        """
        self._con.execute("CREATE SEQUENCE IF NOT EXISTS seq_skill START 1")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS skill (
                id          INTEGER PRIMARY KEY DEFAULT nextval('seq_skill'),
                student_id  INTEGER NOT NULL REFERENCES student(id),
                skill_type  VARCHAR NOT NULL,
                skill_name  VARCHAR,
                skill_desc  TEXT,
                skill_icon  VARCHAR,
                UNIQUE (student_id, skill_type)
            )
        """)

    def count(self) -> int:
        """skill 테이블 레코드 수 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM skill").fetchone()
        return result[0] if result else 0

    def bulk_insert(self, student_id: int, skills: list[dict]) -> None:
        """
        한 학생의 스킬 목록 일괄 삽입
        - skills: [{"skill_type": "ex_skill", "skill_name": ..., ...}, ...]
        - 이미 존재하는 (student_id, skill_type) 조합은 스킵
        """
        for skill in skills:
            self._con.execute("""
                INSERT INTO skill (student_id, skill_type, skill_name, skill_desc, skill_icon)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (student_id, skill_type) DO NOTHING
            """, [
                student_id,
                skill.get("skill_type"),
                skill.get("skill_name"),
                skill.get("skill_desc"),
                skill.get("skill_icon"),
            ])

    def find_by_student(self, student_id: int) -> pd.DataFrame:
        """학생 ID로 스킬 목록 조회 (4종 스킬)"""
        return self._con.execute(
            "SELECT * FROM skill WHERE student_id = ? ORDER BY id",
            [student_id]
        ).df()
