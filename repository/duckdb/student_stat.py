"""
repository/duckdb/student_stat.py
DuckDB student_stat 테이블 구현체

학생 능력치 (Lv.1 / MAX) - student와 1:1 관계
- student_image처럼 student를 슬림하게 유지하고 능력치만 별도 분리
- SchaleDB의 MaxHP1/MaxHP100 등 필드를 그대로 저장
"""

import pandas as pd
from repository.interfaces import IRepository, IDatabaseManager


class DuckDBStudentStatRepository(IRepository):
    """student_stat 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def create_table(self) -> None:
        """
        student_stat 테이블 생성 (DDL)
        - student와 1:1 (student_id = PRIMARY KEY)
        - Lv.1 수치와 MAX(Lv.100기준) 수치 각각 저장
        """
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS student_stat (
                student_id  INTEGER PRIMARY KEY REFERENCES student(id),
                max_hp_1    INTEGER DEFAULT 0,
                max_hp_max  INTEGER DEFAULT 0,
                atk_1       INTEGER DEFAULT 0,
                atk_max     INTEGER DEFAULT 0,
                def_1       INTEGER DEFAULT 0,
                def_max     INTEGER DEFAULT 0,
                heal_1      INTEGER DEFAULT 0,
                heal_max    INTEGER DEFAULT 0
            )
        """)

    def count(self) -> int:
        """student_stat 테이블 레코드 수 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM student_stat").fetchone()
        return result[0] if result else 0

    def bulk_insert(self, stats: list[dict]) -> None:
        """
        학생 스탯 데이터 일괄 삽입
        stats: [{"student_id": 10000, "max_hp_1": 2236, ...}, ...]
        """
        for s in stats:
            self._con.execute("""
                INSERT INTO student_stat VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (student_id) DO NOTHING
            """, [
                s["student_id"],
                s.get("max_hp_1", 0),
                s.get("max_hp_max", 0),
                s.get("atk_1", 0),
                s.get("atk_max", 0),
                s.get("def_1", 0),
                s.get("def_max", 0),
                s.get("heal_1", 0),
                s.get("heal_max", 0),
            ])

    def find_by_student(self, student_id: int) -> pd.Series | None:
        """학생 ID로 능력치 조회"""
        df = self._con.execute(
            "SELECT * FROM student_stat WHERE student_id = ?", [student_id]
        ).df()
        return df.iloc[0] if not df.empty else None
