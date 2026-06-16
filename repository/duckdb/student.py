"""
repository/duckdb/student.py
DuckDB student 테이블 구현체

Entity 1: student (학생 기본 정보)
- SchaleDB API에서 사전 수집한 260명의 학생 정보 저장
- star_grade: 1성/2성/3성 (3성만 배너 생성 대상)
- weapon_name, gear_name: UNIQUE 제약 없음 (의상/코스튬 버전 학생이 원본
  학생과 동일한 고유 무기·애용품 이름을 그대로 공유하기 때문에, 실제
  SchaleDB 데이터 적재 중 UNIQUE 위반이 발생하여 설계서 대비 제거함)
"""

from typing import Optional
import pandas as pd
from repository.interfaces import IStudentRepository, IDatabaseManager


class DuckDBStudentRepository(IStudentRepository):
    """student 테이블 DuckDB 구현체"""

    def __init__(self, db: IDatabaseManager):
        # 부모 클래스 __init__ 호출로 self._con 설정 (DIP 준수)
        super().__init__(db)

    def create_table(self) -> None:
        """
        student 테이블 생성 (DDL)
        - id: SchaleDB 학생 고유 ID를 그대로 PK로 사용 (별도 SEQUENCE 불필요)
        - star_grade: CHECK 제약으로 1~3 성급만 허용
        - weapon_name/gear_name: UNIQUE 제약 없음 (코스튬 학생 공유 가능 → 위 모듈
          docstring 참고)
        - IF NOT EXISTS이므로 앱을 여러 번 실행해도 안전 (중복 생성 안 됨)
        """
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS student (
                id                     INTEGER PRIMARY KEY,
                path_name              VARCHAR,
                full_name              VARCHAR NOT NULL,
                star_grade             INTEGER NOT NULL CHECK (star_grade IN (1, 2, 3)),
                is_limited             VARCHAR NOT NULL,
                weapon_type_code       VARCHAR,
                armor_type             VARCHAR,
                tactic_role            VARCHAR,
                position               VARCHAR,
                bullet_type            VARCHAR,
                terrain_street         VARCHAR,
                terrain_outdoor        VARCHAR,
                terrain_indoor         VARCHAR,
                weapon_name            VARCHAR,
                weapon_desc            TEXT,
                weapon_stat_level_type VARCHAR DEFAULT 'Standard',
                gear_name              VARCHAR,
                gear_desc              TEXT,
                school                 VARCHAR,
                club                   VARCHAR,
                school_year            VARCHAR,
                voice                  VARCHAR,
                birthday               VARCHAR,
                age                    VARCHAR,
                height                 VARCHAR,
                hobby                  TEXT
            )
        """)

    def count(self) -> int:
        """student 테이블 레코드 수 반환"""
        result = self._con.execute("SELECT COUNT(*) FROM student").fetchone()
        return result[0] if result else 0

    def bulk_insert(self, students: list[dict]) -> None:
        """
        students.json에서 로드한 학생 데이터 260명 일괄 삽입
        이미 존재하는 데이터는 스킵 (INSERT OR IGNORE 효과)
        """
        for s in students:
            profile = s.get("profile", {})
            terrain = s.get("terrain", {})
            weapon = s.get("weapon", {})

            self._con.execute("""
                INSERT INTO student VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING
            """, [
                s["id"],
                s.get("path_name"),
                s.get("full_name", ""),
                s.get("star_grade", 1),
                s.get("is_limited", "통상 모집"),
                s.get("weapon_type_code"),
                s.get("armor_type"),
                s.get("tactic_role"),
                s.get("position"),
                s.get("bullet_type"),
                terrain.get("시가지"),
                terrain.get("야외"),
                terrain.get("실내"),
                weapon.get("name"),
                weapon.get("desc"),
                weapon.get("stat_level_type", "Standard"),
                s.get("gear_name") if s.get("has_gear") else None,
                s.get("gear_desc") if s.get("has_gear") else None,
                profile.get("school"),
                profile.get("club"),
                profile.get("school_year"),
                profile.get("voice"),
                profile.get("birthday"),
                profile.get("age"),
                profile.get("height"),
                profile.get("hobby"),
            ])

    def find_all(
        self,
        star_grade: Optional[int] = None,
        school: Optional[str] = None,
        tactic_role: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        조건 필터링 후 학생 목록 반환
        - star_grade: 성급 필터 (1/2/3)
        - school: 학교 이름 필터
        - tactic_role: 전술 역할 필터
        - keyword: 이름 검색 (LIKE)
        """
        # 기본 쿼리: 모든 학생
        query = "SELECT * FROM student WHERE 1=1"
        params = []

        # 조건별 WHERE 절 동적 추가
        if star_grade is not None:
            query += " AND star_grade = ?"
            params.append(star_grade)
        if school:
            query += " AND school = ?"
            params.append(school)
        if tactic_role:
            query += " AND tactic_role = ?"
            params.append(tactic_role)
        if keyword:
            query += " AND full_name LIKE ?"
            params.append(f"%{keyword}%")

        query += " ORDER BY star_grade DESC, full_name"
        return self._con.execute(query, params).df()

    def find_by_id(self, student_id: int) -> Optional[pd.Series]:
        """ID로 단일 학생 조회, 없으면 None"""
        df = self._con.execute(
            "SELECT * FROM student WHERE id = ?", [student_id]
        ).df()
        return df.iloc[0] if not df.empty else None

    def find_distinct_schools(self) -> list[str]:
        """학교 목록 반환 (드롭다운 필터용)"""
        result = self._con.execute(
            "SELECT DISTINCT school FROM student WHERE school IS NOT NULL ORDER BY school"
        ).fetchall()
        return [r[0] for r in result]

    def find_distinct_roles(self) -> list[str]:
        """전술 역할 목록 반환 (드롭다운 필터용)"""
        result = self._con.execute(
            "SELECT DISTINCT tactic_role FROM student WHERE tactic_role IS NOT NULL ORDER BY tactic_role"
        ).fetchall()
        return [r[0] for r in result]
