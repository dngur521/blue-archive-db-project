"""
repository/duckdb/student_image.py
DuckDB student_image 테이블 구현체

약한 엔티티: student_image (학생 종속)
- image_type: 'collection'(초상화), 'icon'(아이콘), 'weapon'(전용 무기)
- image_url: SchaleDB 이미지 URL 저장 → Flet ft.Image(src=url)로 출력
- 이미지가 없는 학생도 목록에 표시해야 하므로 조회 시 LEFT JOIN 사용

[설계 제한요소 충족]
- 미학: 이미지 경로를 DB에 저장 → Image 출력 (설계 제한요소 (2) 미학 충족)
- student LEFT JOIN student_image → 이미지 없는 학생도 표시 (LEFT JOIN 활용)
"""

from typing import Optional
import pandas as pd
from repository.interfaces import IStudentImageRepository, IDatabaseManager


class DuckDBStudentImageRepository(IStudentImageRepository):
    """student_image 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        super().__init__(db)

    def create_table(self) -> None:
        """
        student_image 테이블 생성 (DDL)
        - image_type: CHECK 제약으로 'collection'/'icon'/'weapon' 3종만 허용
        - UNIQUE(student_id, image_type): 중복 이미지 타입 방지
        """
        self._con.execute("CREATE SEQUENCE IF NOT EXISTS seq_student_image START 1")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS student_image (
                id          INTEGER PRIMARY KEY DEFAULT nextval('seq_student_image'),
                student_id  INTEGER NOT NULL REFERENCES student(id),
                image_type  VARCHAR NOT NULL
                            CHECK (image_type IN ('collection', 'icon', 'weapon')),
                image_url   VARCHAR NOT NULL,
                UNIQUE (student_id, image_type)
            )
        """)

    def count(self) -> int:
        """student_image 테이블 레코드 수 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM student_image").fetchone()
        return result[0] if result else 0

    def bulk_insert(self, student_id: int, images: list[dict]) -> None:
        """
        한 학생의 이미지 목록 일괄 삽입
        - images: [{"image_type": "collection", "image_url": "https://..."}, ...]
        - 이미 존재하면 스킵
        """
        for img in images:
            self._con.execute("""
                INSERT INTO student_image (student_id, image_type, image_url)
                VALUES (?, ?, ?)
                ON CONFLICT (student_id, image_type) DO NOTHING
            """, [student_id, img["image_type"], img["image_url"]])

    def find_by_student(self, student_id: int) -> pd.DataFrame:
        """학생 ID로 이미지 목록 전체 조회"""
        return self._con.execute(
            "SELECT * FROM student_image WHERE student_id = ?",
            [student_id]
        ).df()

    def find_url(self, student_id: int, image_type: str) -> Optional[str]:
        """
        특정 이미지 타입의 URL 반환
        - 없으면 None 반환 (Flet에서 에러 이미지로 대체)
        """
        result = self._con.execute(
            "SELECT image_url FROM student_image WHERE student_id = ? AND image_type = ?",
            [student_id, image_type]
        ).fetchone()
        return result[0] if result else None
