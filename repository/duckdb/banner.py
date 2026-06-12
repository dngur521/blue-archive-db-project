"""
repository/duckdb/banner.py
DuckDB banner 테이블 구현체

Entity 2: banner (가챠 배너)
- 3성 학생 1명당 배너 1개 (pickup_student_id UNIQUE)
- claimed_count: 픽업 확정 수령 횟수 → 현재 사이클 내 뽑기 수 계산에 사용
  현재 사이클 뽑기 수 = 총 뽑기 수 - (claimed_count × 200)
"""

from typing import Optional
import pandas as pd
from repository.interfaces import IBannerRepository, IDatabaseManager


class DuckDBBannerRepository(IBannerRepository):
    """banner 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def create_table(self) -> None:
        """
        banner 테이블 생성 (DDL)
        - pickup_student_id: UNIQUE → 후보키 (3성 학생마다 배너 1개)
        - is_active: 활성 배너 여부
        - claimed_count: 픽업 확정 수령 횟수
        """
        self._con.execute("CREATE SEQUENCE IF NOT EXISTS seq_banner START 1")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS banner (
                id                INTEGER PRIMARY KEY DEFAULT nextval('seq_banner'),
                pickup_student_id INTEGER NOT NULL UNIQUE REFERENCES student(id),
                is_active         BOOLEAN DEFAULT TRUE,
                claimed_count     INTEGER DEFAULT 0 CHECK (claimed_count >= 0)
            )
        """)

    def count(self) -> int:
        """banner 테이블 레코드 수 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM banner").fetchone()
        return result[0] if result else 0

    def init_banners(self, student_ids: list[int]) -> None:
        """
        3성 학생 ID 목록으로 배너 자동 생성
        - 이미 배너가 존재하는 학생은 스킵 (ON CONFLICT DO NOTHING)
        - 앱 초기화 시 1회만 실행
        """
        for sid in student_ids:
            self._con.execute("""
                INSERT INTO banner (pickup_student_id, is_active, claimed_count)
                VALUES (?, TRUE, 0)
                ON CONFLICT (pickup_student_id) DO NOTHING
            """, [sid])

    def find_all_active(self) -> pd.DataFrame:
        """활성 배너 목록 조회 (픽업 학생 이름·성급 포함)"""
        return self._con.execute("""
            SELECT b.id, b.pickup_student_id, s.full_name AS pickup_name,
                   s.star_grade, b.is_active, b.claimed_count
            FROM banner b
            JOIN student s ON s.id = b.pickup_student_id
            WHERE b.is_active = TRUE
            ORDER BY s.full_name
        """).df()

    def find_by_id(self, banner_id: int) -> Optional[pd.Series]:
        """배너 ID로 단일 배너 조회 (픽업 학생 이름·성급 포함)"""
        df = self._con.execute("""
            SELECT b.id, b.pickup_student_id, s.full_name AS pickup_name,
                   s.star_grade, b.is_active, b.claimed_count
            FROM banner b
            JOIN student s ON s.id = b.pickup_student_id
            WHERE b.id = ?
        """, [banner_id]).df()
        return df.iloc[0] if not df.empty else None

    def increment_claimed(self, banner_id: int) -> None:
        """픽업 확정 수령 시 claimed_count 1 증가"""
        self._con.execute(
            "UPDATE banner SET claimed_count = claimed_count + 1 WHERE id = ?",
            [banner_id]
        )

    def reset_claimed(self, banner_id: int) -> None:
        """뽑기 초기화 시 claimed_count를 0으로 리셋"""
        self._con.execute(
            "UPDATE banner SET claimed_count = 0 WHERE id = ?",
            [banner_id]
        )
