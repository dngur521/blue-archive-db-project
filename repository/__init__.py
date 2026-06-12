"""
repository/__init__.py
DB_TYPE 환경 변수에 따른 Repository 구현체 동적 할당 (Strategy Pattern)

.env의 DB_TYPE 설정:
  - DUCKDB: DuckDB 로컬 파일 기반 (기본값)

확장 예시 (현재 미구현):
  - MYSQL, POSTGRESQL 등 추가 시 이 파일만 수정하면 됨
  - Service/View 코드 변경 불필요 (DIP 원칙 준수)
"""

import os
from dotenv import load_dotenv

# .env 환경 변수 로드
load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "DUCKDB").upper()

# =============================================================================
# DB_TYPE에 따른 구현체 매핑
# =============================================================================

if DB_TYPE == "DUCKDB":
    from .duckdb.connection import DuckDBManager as DatabaseManager
    from .duckdb.student import DuckDBStudentRepository as StudentRepository
    from .duckdb.skill import DuckDBSkillRepository as SkillRepository
    from .duckdb.student_image import DuckDBStudentImageRepository as StudentImageRepository
    from .duckdb.banner import DuckDBBannerRepository as BannerRepository
    from .duckdb.gacha_pull import DuckDBGachaPullRepository as GachaPullRepository
    from .duckdb.cultivation import DuckDBCultivationRepository as CultivationRepository
    from .duckdb.cultivation_goal import DuckDBCultivationGoalRepository as CultivationGoalRepository
    from .duckdb.join import DuckDBQueryRepository as QueryRepository
else:
    raise ValueError(f"지원하지 않는 DB_TYPE 설정입니다: {DB_TYPE}")

print(f"[INFO] Database: {DB_TYPE}")

# =============================================================================
# 패키지 외부 노출
# =============================================================================
__all__ = [
    "DatabaseManager",
    "StudentRepository",
    "SkillRepository",
    "StudentImageRepository",
    "BannerRepository",
    "GachaPullRepository",
    "CultivationRepository",
    "CultivationGoalRepository",
    "QueryRepository",
]
