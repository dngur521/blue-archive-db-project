"""
repository/duckdb/gacha_pull.py
DuckDB gacha_pull 테이블 구현체

Relationship 1: gacha_pull (banner ↔ student N:M 관계 테이블)
- 가챠 뽑기 결과 1건당 1레코드
- pull_count: 해당 배너에서 이번 뽑기까지의 누적 뽑기 수
- is_pickup 컬럼 미포함: banner.pickup_student_id = student_id 비교로 도출 가능 (BCNF 준수)
"""

import pandas as pd
from repository.interfaces import IGachaPullRepository, IDatabaseManager


class DuckDBGachaPullRepository(IGachaPullRepository):
    """gacha_pull 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def create_table(self) -> None:
        """
        gacha_pull 테이블 생성 (DDL)
        - banner_id FK: 어느 배너에서 뽑았는지
        - student_id FK: 뽑힌 학생
        - pull_count: 뽑기 시점의 배너 누적 뽑기 수 (파티 계산용)
        - pulled_at: 뽑기 일시 (기록 보관용)
        """
        self._con.execute("CREATE SEQUENCE IF NOT EXISTS seq_gacha_pull START 1")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS gacha_pull (
                id          INTEGER PRIMARY KEY DEFAULT nextval('seq_gacha_pull'),
                banner_id   INTEGER NOT NULL REFERENCES banner(id),
                student_id  INTEGER NOT NULL REFERENCES student(id),
                pulled_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pull_count  INTEGER NOT NULL
            )
        """)

    def count(self) -> int:
        """gacha_pull 테이블 전체 레코드 수 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM gacha_pull").fetchone()
        return result[0] if result else 0

    def insert(self, banner_id: int, student_id: int, pull_count: int) -> None:
        """
        뽑기 결과 1건 DB 저장
        - pulled_at은 DEFAULT CURRENT_TIMESTAMP로 자동 설정
        """
        self._con.execute("""
            INSERT INTO gacha_pull (banner_id, student_id, pull_count)
            VALUES (?, ?, ?)
        """, [banner_id, student_id, pull_count])

    def get_total_count(self, banner_id: int) -> int:
        """
        해당 배너의 총 누적 뽑기 수 반환
        - 현재 사이클 내 뽑기 수 = total_count - (banner.claimed_count × 200)
        """
        result = self._con.execute(
            "SELECT COUNT(*) FROM gacha_pull WHERE banner_id = ?",
            [banner_id]
        ).fetchone()
        return result[0] if result else 0

    def find_recent(self, banner_id: int, limit: int = 10) -> pd.DataFrame:
        """
        최근 뽑기 기록 조회 (가챠 결과 표시용)
        - 학생 이름과 성급도 JOIN해서 반환
        """
        return self._con.execute("""
            SELECT gp.id, gp.pull_count, gp.pulled_at,
                   s.full_name, s.star_grade,
                   (b.pickup_student_id = gp.student_id) AS is_pickup
            FROM gacha_pull gp
            JOIN student s ON s.id = gp.student_id
            JOIN banner b ON b.id = gp.banner_id
            WHERE gp.banner_id = ?
            ORDER BY gp.id DESC
            LIMIT ?
        """, [banner_id, limit]).df()
