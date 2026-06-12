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
        # .env에서 DB 경로 읽기 (기본값: data/bluearchive.db)
        db_path = os.getenv("DUCKDB_PATH", "data/bluearchive.db")

        # DB 파일 저장 디렉토리가 없으면 자동 생성
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # DuckDB 파일 기반 연결 (파일이 없으면 자동 생성)
        # 잠금 충돌 시 최대 3회 재시도 후 메모리 모드로 폴백
        import time
        last_err = None
        for attempt in range(3):
            try:
                self._con = duckdb.connect(db_path)
                print(f"[DuckDB] 연결 완료: {db_path}")
                return
            except duckdb.IOException as e:
                last_err = e
                print(f"[DuckDB] 연결 재시도 {attempt + 1}/3 (이전 프로세스 종료 대기)...")
                time.sleep(1.5)

        # 3회 모두 실패 → 에러 메시지 출력 후 예외
        print(
            "\n[DuckDB] 연결 실패: DB 파일이 다른 프로세스에 의해 잠겨있습니다.\n"
            f"  파일: {db_path}\n"
            "  해결: 이전 앱 창을 닫거나, 터미널에서 실행 중인 Python 프로세스를 종료하세요.\n"
        )
        raise RuntimeError(
            f"DuckDB 파일 잠금 오류: {db_path}\n"
            "이전 앱 창을 닫고 다시 실행하세요."
        ) from last_err

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """현재 DuckDB 커넥션 반환"""
        return self._con

    def close(self) -> None:
        """DuckDB 연결 종료"""
        self._con.close()
        print("[DuckDB] 연결 종료")
