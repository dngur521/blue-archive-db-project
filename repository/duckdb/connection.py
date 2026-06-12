"""
repository/duckdb/connection.py
DuckDB 연결 관리 구현체

IDatabaseManager 인터페이스를 DuckDB로 구현 (Adapter Pattern)
- .env의 DUCKDB_PATH를 읽어 파일 기반 DuckDB에 연결
- 싱글 커넥션을 모든 Repository가 공유
"""

import os
import duckdb
from dotenv import load_dotenv
from repository.interfaces import IDatabaseManager

# .env 파일에서 환경 변수 로드
load_dotenv()


class DuckDBManager(IDatabaseManager):
    """DuckDB 연결 관리 클래스 (IDatabaseManager 구현체)"""

    def __init__(self):
        # .env에서 DB 경로 읽기 (기본값: data/blueachive.db)
        db_path = os.getenv("DUCKDB_PATH", "data/blueachive.db")

        # DB 파일 저장 디렉토리가 없으면 자동 생성
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # DuckDB 파일 기반 연결 (파일이 없으면 자동 생성)
        self._con = duckdb.connect(db_path)
        print(f"[DuckDB] 연결 완료: {db_path}")

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """현재 DuckDB 커넥션 반환"""
        return self._con

    def close(self) -> None:
        """DuckDB 연결 종료"""
        self._con.close()
        print("[DuckDB] 연결 종료")
