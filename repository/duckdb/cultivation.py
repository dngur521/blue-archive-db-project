"""
repository/duckdb/cultivation.py
DuckDB cultivation 테이블 구현체

Relationship 2: cultivation (현재 육성 현황, student 1:0..1)
- 학생 최초 획득 시 자동 생성 (insert_on_acquire)
- student_id UNIQUE: 학생당 1개 레코드만 존재
- acquired_at: 최초 획득 일시 (보유 학생 목록 정렬 기준)
"""

from typing import Optional
from datetime import datetime
import pandas as pd
from repository.interfaces import ICultivationRepository, IDatabaseManager


class DuckDBCultivationRepository(ICultivationRepository):
    """cultivation 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def create_table(self) -> None:
        """
        cultivation 테이블 생성 (DDL)
        - student_id UNIQUE: 학생당 1개 (1:0..1 관계)
        - weapon_star CHECK: 전무 성급은 5성 달성 후에만 가능
        - acquired_at: NOT NULL (가챠 뽑기 시 자동 설정)
        """
        self._con.execute("CREATE SEQUENCE IF NOT EXISTS seq_cultivation START 1")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS cultivation (
                id            INTEGER PRIMARY KEY DEFAULT nextval('seq_cultivation'),
                student_id    INTEGER UNIQUE NOT NULL REFERENCES student(id),
                star          INTEGER DEFAULT 1  CHECK (star         BETWEEN 1 AND 5),
                weapon_star   INTEGER DEFAULT 0  CHECK (weapon_star  BETWEEN 0 AND 4),
                eleph_count   INTEGER DEFAULT 0  CHECK (eleph_count >= 0),
                level         INTEGER DEFAULT 1  CHECK (level        BETWEEN 1 AND 90),
                ex_skill      INTEGER DEFAULT 1  CHECK (ex_skill     BETWEEN 1 AND 5),
                normal_skill  INTEGER DEFAULT 1  CHECK (normal_skill BETWEEN 1 AND 10),
                enhance_skill INTEGER DEFAULT 1  CHECK (enhance_skill BETWEEN 1 AND 10),
                sub_skill     INTEGER DEFAULT 1  CHECK (sub_skill    BETWEEN 1 AND 10),
                weapon_level  INTEGER DEFAULT 1  CHECK (weapon_level BETWEEN 1 AND 50),
                gear_level    INTEGER DEFAULT 0  CHECK (gear_level   BETWEEN 0 AND 2),
                bond_rank     INTEGER DEFAULT 1  CHECK (bond_rank    BETWEEN 1 AND 50),
                acquired_at   TIMESTAMP NOT NULL,
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def count(self) -> int:
        """cultivation 테이블 레코드 수(보유 학생 수) 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM cultivation").fetchone()
        return result[0] if result else 0

    def insert_on_acquire(self, student_id: int) -> None:
        """
        학생 최초 획득 시 cultivation 레코드 생성
        - 이미 존재하면 스킵 (ON CONFLICT DO NOTHING)
        - 모든 육성 수치는 기본값(1 또는 0)으로 초기화
        - acquired_at: 현재 시각 자동 설정
        """
        self._con.execute("""
            INSERT INTO cultivation (student_id, acquired_at)
            VALUES (?, ?)
            ON CONFLICT (student_id) DO NOTHING
        """, [student_id, datetime.now()])

    def update_current(self, student_id: int, **fields) -> None:
        """
        현재 육성 수치 갱신
        - **fields: 변경할 컬럼명 = 값 (예: level=50, ex_skill=3)
        - updated_at 자동 갱신
        """
        if not fields:
            return

        # SET 절 동적 생성
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        params = list(fields.values()) + [datetime.now(), student_id]

        self._con.execute(
            f"UPDATE cultivation SET {set_clause}, updated_at = ? WHERE student_id = ?",
            params
        )

    def update_eleph(self, student_id: int, delta: int) -> None:
        """
        엘레프 수량 증감
        - 가챠 뽑기에서 중복 학생 획득 시 자동 호출
        - delta: 증가량 (픽업 중복 100개, 일반 중복 30개)
        """
        self._con.execute(
            "UPDATE cultivation SET eleph_count = eleph_count + ? WHERE student_id = ?",
            [delta, student_id]
        )

    def find_by_student(self, student_id: int) -> Optional[pd.Series]:
        """학생 ID로 현재 육성 현황 조회, 없으면 None"""
        df = self._con.execute(
            "SELECT * FROM cultivation WHERE student_id = ?",
            [student_id]
        ).df()
        return df.iloc[0] if not df.empty else None

    def exists(self, student_id: int) -> bool:
        """해당 학생을 보유 중인지 확인"""
        result = self._con.execute(
            "SELECT COUNT(*) FROM cultivation WHERE student_id = ?",
            [student_id]
        ).fetchone()
        return result[0] > 0 if result else False
