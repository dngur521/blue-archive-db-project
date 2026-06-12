"""
repository/duckdb/cultivation_goal.py
DuckDB cultivation_goal 테이블 구현체

Relationship 3: cultivation_goal (목표 육성 현황, student 1:0..1)
- 목표를 설정한 경우에만 레코드 생성
- 미설정 학생도 보유 목록에 표시 → cultivation LEFT JOIN cultivation_goal 사용
- upsert(): 목표 설정/변경 시 INSERT 또는 UPDATE (UPSERT)
"""

from typing import Optional
from datetime import datetime
import pandas as pd
from repository.interfaces import ICultivationGoalRepository, IDatabaseManager


class DuckDBCultivationGoalRepository(ICultivationGoalRepository):
    """cultivation_goal 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def create_table(self) -> None:
        """
        cultivation_goal 테이블 생성 (DDL)
        - cultivation과 동일한 구조지만 acquired_at 없음
        - student_id UNIQUE: 학생당 목표 1개 (1:0..1 관계)
        """
        self._con.execute("CREATE SEQUENCE IF NOT EXISTS seq_cultivation_goal START 1")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS cultivation_goal (
                id            INTEGER PRIMARY KEY DEFAULT nextval('seq_cultivation_goal'),
                student_id    INTEGER UNIQUE NOT NULL REFERENCES student(id),
                star          INTEGER DEFAULT 1  CHECK (star         BETWEEN 1 AND 5),
                weapon_star   INTEGER DEFAULT 0  CHECK (weapon_star  BETWEEN 0 AND 4),
                level         INTEGER DEFAULT 1  CHECK (level        BETWEEN 1 AND 90),
                ex_skill      INTEGER DEFAULT 1  CHECK (ex_skill     BETWEEN 1 AND 5),
                normal_skill  INTEGER DEFAULT 1  CHECK (normal_skill BETWEEN 1 AND 10),
                enhance_skill INTEGER DEFAULT 1  CHECK (enhance_skill BETWEEN 1 AND 10),
                sub_skill     INTEGER DEFAULT 1  CHECK (sub_skill    BETWEEN 1 AND 10),
                weapon_level  INTEGER DEFAULT 1  CHECK (weapon_level BETWEEN 1 AND 50),
                gear_level    INTEGER DEFAULT 0  CHECK (gear_level   BETWEEN 0 AND 2),
                bond_rank     INTEGER DEFAULT 1  CHECK (bond_rank    BETWEEN 1 AND 50),
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def count(self) -> int:
        """cultivation_goal 테이블 레코드 수 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM cultivation_goal").fetchone()
        return result[0] if result else 0

    def upsert(self, student_id: int, **fields) -> None:
        """
        목표 육성 수치 삽입 또는 갱신 (UPSERT)
        - 처음 설정이면 INSERT, 이미 있으면 UPDATE
        - DuckDB의 ON CONFLICT DO UPDATE 문법 사용
        """
        if not fields:
            return

        # 삽입할 컬럼 목록 (student_id + 전달된 필드)
        columns = ["student_id"] + list(fields.keys()) + ["updated_at"]
        placeholders = ", ".join(["?"] * len(columns))
        values = [student_id] + list(fields.values()) + [datetime.now()]

        # 업데이트할 컬럼 목록 (student_id 제외)
        update_clause = ", ".join(
            f"{k} = excluded.{k}" for k in list(fields.keys()) + ["updated_at"]
        )

        self._con.execute(f"""
            INSERT INTO cultivation_goal ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (student_id) DO UPDATE SET {update_clause}
        """, values)

    def find_by_student(self, student_id: int) -> Optional[pd.Series]:
        """학생 ID로 목표 육성 현황 조회, 미설정이면 None"""
        df = self._con.execute(
            "SELECT * FROM cultivation_goal WHERE student_id = ?",
            [student_id]
        ).df()
        return df.iloc[0] if not df.empty else None

    def delete_all(self) -> None:
        """목표 육성 수치 전체 삭제 (초기화)"""
        self._con.execute("DELETE FROM cultivation_goal")
