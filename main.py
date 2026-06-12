"""
main.py
블루아카이브 가챠 & 육성 시뮬레이터 — Entry Point

아키텍처:
  Flet View (main.py + views/)
      ↓ 의존성 주입 (DI)
  Service Layer (service/)
      ↓ 인터페이스 (DIP)
  Repository Layer (repository/)
      ↓
  DuckDB (data/bluearchive.db)

실행 방법:
  uv run flet run main.py
  또는
  flet run main.py
"""

import flet as ft

# 의존성 주입: DB_TYPE에 따른 구현체 자동 선택 (.env 기반)
from repository import (
    StudentStatRepository,
    DatabaseManager,
    StudentRepository,
    SkillRepository,
    StudentImageRepository,
    BannerRepository,
    GachaPullRepository,
    CultivationRepository,
    CultivationGoalRepository,
    QueryRepository,
)

# 서비스 레이어
from service import StudentService, GachaService, CultivationService

# 뷰 레이어
from views import (
    create_student_view,
    create_gacha_view,
    create_cultivation_view,
)


def main(page: ft.Page) -> None:
    """
    Flet 앱 메인 함수 (Controller 역할)
    - 페이지 기본 설정
    - 의존성 주입 및 서비스 초기화
    - NavigationBar + 탭 콘텐츠 기반 3-화면 레이아웃
    """

    # ── 페이지 기본 설정 ─────────────────────────────────────────────────────
    page.title = "블루아카이브 가챠 & 육성 시뮬레이터"
    page.padding = 12
    page.window.width = 1000
    page.window.height = 700
    page.window.min_width = 800
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = None

    # 로딩 화면 표시
    page.add(ft.Column([
        ft.ProgressRing(),
        ft.Text("데이터 로드 중... 잠시만 기다려주세요.", size=14),
    ], alignment=ft.MainAxisAlignment.CENTER,
       horizontal_alignment=ft.CrossAxisAlignment.CENTER,
       expand=True))
    page.update()

    # ── 의존성 주입 (Dependency Injection) ──────────────────────────────────
    # .env의 DB_TYPE 설정에 맞는 구현체 자동 선택 (Strategy Pattern)
    db_manager = DatabaseManager()

    # 각 Repository에 DB 매니저 주입 (DIP: 인터페이스에 의존)
    student_repo   = StudentRepository(db_manager)
    skill_repo     = SkillRepository(db_manager)
    image_repo     = StudentImageRepository(db_manager)
    stat_repo      = StudentStatRepository(db_manager)
    banner_repo    = BannerRepository(db_manager)
    gacha_repo     = GachaPullRepository(db_manager)
    cultiv_repo    = CultivationRepository(db_manager)
    goal_repo      = CultivationGoalRepository(db_manager)
    query_repo     = QueryRepository(db_manager)

    # Service에 Repository 주입
    student_service = StudentService(
        student_repo=student_repo,
        skill_repo=skill_repo,
        image_repo=image_repo,
        stat_repo=stat_repo,
        query_repo=query_repo,
    )
    gacha_service = GachaService(
        banner_repo=banner_repo,
        gacha_repo=gacha_repo,
        cultivation_repo=cultiv_repo,
        student_repo=student_repo,
    )
    cultivation_service = CultivationService(
        cultivation_repo=cultiv_repo,
        goal_repo=goal_repo,
        query_repo=query_repo,
    )

    # ── 서비스 초기화 (DB 테이블 생성 + 데이터 로드) ─────────────────────────
    student_service.initialize()      # student, skill, student_image 테이블 + JSON 로드
    gacha_service.initialize()        # banner, gacha_pull 테이블 + 배너 자동 생성
    cultivation_service.initialize()  # cultivation, cultivation_goal 테이블

    # ── 뷰 빌더 생성 (page 객체 전달) ────────────────────────────────────────
    student_build   = create_student_view(student_service)
    gacha_build     = create_gacha_view(gacha_service)
    cultiv_build    = create_cultivation_view(cultivation_service)

    # 컨트롤 생성 (페이지에 추가 전이므로 .update() 호출 없음)
    student_content   = student_build(page)
    gacha_content     = gacha_build(page)
    cultiv_content    = cultiv_build(page)

    # ── NavigationBar + 콘텐츠 스와핑 방식 (Flet 0.85 호환) ─────────────────
    contents = [
        ft.Container(content=student_content, expand=True, padding=ft.Padding(top=8)),
        ft.Container(content=gacha_content,   expand=True, padding=ft.Padding(top=8)),
        ft.Container(content=cultiv_content,  expand=True, padding=ft.Padding(top=8)),
    ]

    # 콘텐츠 영역 (현재 탭 내용 표시)
    content_area = ft.Container(content=contents[0], expand=True)

    def on_nav_change(e) -> None:
        """NavigationBar 탭 변경 시 콘텐츠 교체"""
        idx = e.control.selected_index
        content_area.content = contents[idx]
        page.update()

    # NavigationBar 설정
    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                label="학생 도감",
                icon=ft.Icons.MENU_BOOK_OUTLINED,
                selected_icon=ft.Icons.MENU_BOOK,
            ),
            ft.NavigationBarDestination(
                label="가챠 시뮬",
                icon=ft.Icons.CASINO_OUTLINED,
                selected_icon=ft.Icons.CASINO,
            ),
            ft.NavigationBarDestination(
                label="육성 시뮬",
                icon=ft.Icons.FITNESS_CENTER_OUTLINED,
                selected_icon=ft.Icons.FITNESS_CENTER,
            ),
        ],
        selected_index=0,
        on_change=on_nav_change,
    )

    # 로딩 화면 제거 후 메인 UI 표시
    page.controls.clear()
    page.add(content_area)
    page.update()


# 앱 실행 진입점 (Flet 0.80+: ft.run() 사용)
ft.run(main)
