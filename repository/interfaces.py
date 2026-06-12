"""
repository/interfaces.py
레포지토리 인터페이스 정의 모듈

SOLID 원칙 중 DIP(의존성 역전 원칙) 적용:
- 상위 모듈(Service)이 하위 구현체(DuckDB)에 직접 의존하지 않고
  이 추상 인터페이스에 의존하도록 설계
- 어떤 DBMS를 사용하더라도 Service 코드 변경 없이 Repository만 교체 가능
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


# =============================================================================
# 데이터베이스 연결 인터페이스
# =============================================================================

class IDatabaseManager(ABC):
    """데이터베이스 연결 관리 인터페이스 (Adapter Pattern 적용)"""

    @abstractmethod
    def get_connection(self):
        """데이터베이스 커넥션 객체 반환"""
        ...

    @abstractmethod
    def close(self) -> None:
        """현재 활성화된 데이터베이스 커넥션 닫기"""
        ...


# =============================================================================
# 공통 레포지토리 인터페이스
# =============================================================================

class IRepository(ABC):
    """
    모든 Repository의 공통 기반 인터페이스
    DI(의존성 주입): __init__에서 IDatabaseManager를 받아 커넥션 저장
    """

    def __init__(self, db: IDatabaseManager):
        # IDatabaseManager 인터페이스를 통해 커넥션 획득 → DIP 준수
        self._con = db.get_connection()

    @abstractmethod
    def create_table(self) -> None:
        """테이블 생성 (없으면 CREATE, 있으면 SKIP)"""
        ...

    @abstractmethod
    def count(self) -> int:
        """테이블의 레코드 수(Cardinality) 반환"""
        ...


# =============================================================================
# 학생(student) 테이블 인터페이스
# =============================================================================

class IStudentRepository(IRepository):
    """학생 기본 정보 테이블 접근 인터페이스"""

    @abstractmethod
    def bulk_insert(self, students: list[dict]) -> None:
        """JSON에서 로드한 학생 데이터 일괄 삽입"""
        ...

    @abstractmethod
    def find_all(
        self,
        star_grade: Optional[int] = None,
        school: Optional[str] = None,
        tactic_role: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> pd.DataFrame:
        """조건 필터링 후 학생 목록 반환"""
        ...

    @abstractmethod
    def find_by_id(self, student_id: int) -> Optional[pd.Series]:
        """ID로 단일 학생 조회"""
        ...

    @abstractmethod
    def find_distinct_schools(self) -> list[str]:
        """학교 목록 조회 (필터 드롭다운용)"""
        ...

    @abstractmethod
    def find_distinct_roles(self) -> list[str]:
        """전술 역할 목록 조회 (필터 드롭다운용)"""
        ...


# =============================================================================
# 스킬(skill) 테이블 인터페이스
# =============================================================================

class ISkillRepository(IRepository):
    """학생 스킬 정보 테이블 접근 인터페이스"""

    @abstractmethod
    def bulk_insert(self, student_id: int, skills: list[dict]) -> None:
        """한 학생의 스킬 목록 일괄 삽입"""
        ...

    @abstractmethod
    def find_by_student(self, student_id: int) -> pd.DataFrame:
        """학생 ID로 스킬 목록 조회"""
        ...


# =============================================================================
# 학생 이미지(student_image) 테이블 인터페이스
# =============================================================================

class IStudentImageRepository(IRepository):
    """학생 이미지 URL 저장 테이블 접근 인터페이스"""

    @abstractmethod
    def bulk_insert(self, student_id: int, images: list[dict]) -> None:
        """한 학생의 이미지 목록 일괄 삽입"""
        ...

    @abstractmethod
    def find_by_student(self, student_id: int) -> pd.DataFrame:
        """학생 ID로 이미지 목록 조회"""
        ...

    @abstractmethod
    def find_url(self, student_id: int, image_type: str) -> Optional[str]:
        """특정 타입의 이미지 URL 반환"""
        ...


# =============================================================================
# 배너(banner) 테이블 인터페이스
# =============================================================================

class IBannerRepository(IRepository):
    """가챠 배너 테이블 접근 인터페이스"""

    @abstractmethod
    def init_banners(self, student_ids: list[int]) -> None:
        """3성 학생 목록으로 배너 자동 생성 (앱 초기화 시 1회)"""
        ...

    @abstractmethod
    def find_all_active(self) -> pd.DataFrame:
        """활성 배너 목록 조회"""
        ...

    @abstractmethod
    def find_by_id(self, banner_id: int) -> Optional[pd.Series]:
        """배너 ID로 단일 배너 조회"""
        ...

    @abstractmethod
    def increment_claimed(self, banner_id: int) -> None:
        """픽업 확정 수령 시 claimed_count 증가"""
        ...

    @abstractmethod
    def reset_claimed(self, banner_id: int) -> None:
        """뽑기 초기화 시 claimed_count를 0으로 리셋"""
        ...


# =============================================================================
# 가챠 뽑기 기록(gacha_pull) 테이블 인터페이스
# =============================================================================

class IGachaPullRepository(IRepository):
    """가챠 뽑기 기록 테이블 접근 인터페이스"""

    @abstractmethod
    def insert(self, banner_id: int, student_id: int, pull_count: int) -> None:
        """뽑기 결과 1건 저장"""
        ...

    @abstractmethod
    def get_total_count(self, banner_id: int) -> int:
        """해당 배너의 총 누적 뽑기 수 반환"""
        ...

    @abstractmethod
    def find_recent(self, banner_id: int, limit: int = 10) -> pd.DataFrame:
        """최근 뽑기 기록 조회"""
        ...

    @abstractmethod
    def delete_by_banner(self, banner_id: int) -> None:
        """해당 배너의 뽑기 기록 전체 삭제"""
        ...


# =============================================================================
# 현재 육성 현황(cultivation) 테이블 인터페이스
# =============================================================================

class ICultivationRepository(IRepository):
    """보유 학생의 현재 육성 현황 테이블 접근 인터페이스"""

    @abstractmethod
    def insert_on_acquire(self, student_id: int) -> None:
        """학생 최초 획득 시 cultivation 레코드 생성"""
        ...

    @abstractmethod
    def update_current(self, student_id: int, **fields) -> None:
        """현재 육성 수치 갱신"""
        ...

    @abstractmethod
    def update_eleph(self, student_id: int, delta: int) -> None:
        """엘레프 수량 증감 (뽑기 결과 반영)"""
        ...

    @abstractmethod
    def find_by_student(self, student_id: int) -> Optional[pd.Series]:
        """학생 ID로 현재 육성 현황 조회"""
        ...

    @abstractmethod
    def exists(self, student_id: int) -> bool:
        """보유 여부 확인"""
        ...

    @abstractmethod
    def delete_all(self) -> None:
        """보유 학생 전체 삭제 (초기화)"""
        ...


# =============================================================================
# 목표 육성 현황(cultivation_goal) 테이블 인터페이스
# =============================================================================

class ICultivationGoalRepository(IRepository):
    """목표 육성 현황 테이블 접근 인터페이스"""

    @abstractmethod
    def upsert(self, student_id: int, **fields) -> None:
        """목표 육성 수치 삽입 또는 갱신 (UPSERT)"""
        ...

    @abstractmethod
    def find_by_student(self, student_id: int) -> Optional[pd.Series]:
        """학생 ID로 목표 육성 현황 조회 (미설정이면 None)"""
        ...

    @abstractmethod
    def delete_all(self) -> None:
        """목표 육성 수치 전체 삭제 (초기화)"""
        ...


# =============================================================================
# JOIN 전용 쿼리 레포지토리 인터페이스
# =============================================================================

class IQueryRepository(ABC):
    """
    여러 테이블을 JOIN하는 복합 쿼리 전담 레포지토리
    - cultivation JOIN student LEFT JOIN cultivation_goal :
      보유 학생 현황 + 목표 통합 조회 (3개 이상 테이블 JOIN + LEFT JOIN)
    - student JOIN skill : 학생 상세 + 스킬 목록
    """

    def __init__(self, db: IDatabaseManager):
        self._con = db.get_connection()

    @abstractmethod
    def get_student_with_skills(self, student_id: int) -> pd.DataFrame:
        """
        student JOIN skill
        학생 상세 정보 + 스킬 목록 한 번에 조회
        """
        ...

    @abstractmethod
    def get_owned_students(self) -> pd.DataFrame:
        """
        cultivation
          JOIN student ON student.id = cultivation.student_id
          LEFT JOIN cultivation_goal ON cultivation_goal.student_id = cultivation.student_id
          LEFT JOIN student_image ON student_image.student_id = cultivation.student_id
                                  AND student_image.image_type = 'icon'
        보유 학생 현황 + 목표 + 아이콘 통합 조회
        """
        ...

    @abstractmethod
    def get_students_with_icons(
        self,
        star_grade: Optional[int] = None,
        school: Optional[str] = None,
        tactic_role: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        student LEFT JOIN student_image (icon)
        학생 도감 목록 + 아이콘 URL
        """
        ...


# =============================================================================
# 학생 능력치(student_stat) 테이블 인터페이스
# =============================================================================

class IStudentStatRepository(IRepository):
    """학생 능력치 테이블 접근 인터페이스 (Lv.1 / MAX 스탯)"""

    @abstractmethod
    def bulk_insert(self, stats: list[dict]) -> None:
        """학생 스탯 데이터 일괄 삽입"""
        ...

    @abstractmethod
    def find_by_student(self, student_id: int) -> Optional[pd.Series]:
        """학생 ID로 능력치 조회"""
        ...
