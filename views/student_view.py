"""
views/student_view.py
학생 도감 탭 Flet UI

Use Case 3.1: 학생 목록 조회 및 필터링
Use Case 3.1.1: 학생 상세 정보 및 스킬 조회

구성:
- 상단: 검색 바 + 필터 (학교, 역할, 성급)
- 좌측: 학생 카드 목록 (스크롤 가능)
- 우측: 학생 상세 패널 (이미지 + 정보 + 스킬 버튼)
"""

import flet as ft
import pandas as pd
from service.student_service import StudentService


def create_student_view(service: StudentService) -> ft.Control:
    """
    학생 도감 탭 컨트롤 생성
    - service를 통해 학생 목록 및 상세 정보 조회
    """

    # ── 필터 상태 ────────────────────────────────────────────────────────────
    filter_state = {
        "star": None,      # 성급 필터 (None = 전체)
        "school": None,    # 학교 필터
        "role": None,      # 역할 필터
        "keyword": "",     # 검색어
    }

    # ── 학생 목록 ListView ───────────────────────────────────────────────────
    student_list = ft.ListView(
        expand=True,
        spacing=4,
        padding=ft.padding.only(right=8),
    )

    # ── 상세 정보 패널 (우측) ────────────────────────────────────────────────
    detail_image = ft.Image(
        src="https://schaledb.com/images/common/default.webp",
        width=180,
        height=180,
        fit=ft.ImageFit.CONTAIN,
        border_radius=8,
        error_content=ft.Icon(ft.icons.PERSON, size=80, color=ft.colors.GREY_400),
    )

    detail_name = ft.Text("학생을 선택하세요", size=20, weight=ft.FontWeight.BOLD)
    detail_school = ft.Text("", size=13, color=ft.colors.GREY_600)
    detail_info = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO)
    skill_buttons = ft.Row([], spacing=8, wrap=True)

    detail_panel = ft.Column(
        [
            ft.Row([detail_image], alignment=ft.MainAxisAlignment.CENTER),
            detail_name,
            detail_school,
            ft.Divider(height=1),
            skill_buttons,
            ft.Divider(height=1),
            detail_info,
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # ── 상세 정보 업데이트 함수 ──────────────────────────────────────────────

    def update_detail(student_id: int, page: ft.Page) -> None:
        """선택한 학생의 상세 정보를 우측 패널에 표시"""
        df = service.get_student_detail(student_id)
        if df.empty:
            return

        # 학생 기본 정보 (첫 번째 행)
        s = df.iloc[0]
        path = str(s.get("path_name", ""))

        # 초상화 이미지 URL 설정
        if path:
            detail_image.src = (
                f"https://schaledb.com/images/student/collection/{path}.webp"
            )
        detail_image.update()

        detail_name.value = str(s.get("full_name", ""))
        detail_school.value = (
            f"{s.get('school', '')}  ·  {s.get('club', '')}  ·  "
            f"{s.get('school_year', '')}"
        )

        # 기본 정보 텍스트 목록 구성
        detail_info.controls = [
            _info_row("무기",   str(s.get("weapon_type_code", ""))),
            _info_row("장갑",   str(s.get("armor_type", ""))),
            _info_row("역할",   str(s.get("tactic_role", ""))),
            _info_row("위치",   str(s.get("position", ""))),
            _info_row("속성",   str(s.get("bullet_type", ""))),
            _info_row("지형",   (
                f"시가지 {s.get('terrain_street','?')}  "
                f"야외 {s.get('terrain_outdoor','?')}  "
                f"실내 {s.get('terrain_indoor','?')}"
            )),
            ft.Divider(height=1),
            _info_row("고유무기", str(s.get("weapon_name", ""))),
            _info_row("애용품",  str(s.get("gear_name", "-") or "-")),
            ft.Divider(height=1),
            _info_row("성우",   str(s.get("voice", ""))),
            _info_row("생일",   str(s.get("birthday", ""))),
            _info_row("나이",   str(s.get("age", ""))),
            _info_row("키",     str(s.get("height", ""))),
            _info_row("취미",   str(s.get("hobby", ""))),
        ]

        # 스킬 버튼 생성 (클릭 시 AlertDialog로 스킬 정보 팝업)
        skill_buttons.controls = []
        skill_type_labels = {
            "ex_skill":      "EX",
            "normal_skill":  "기본",
            "enhance_skill": "강화",
            "sub_skill":     "서브",
        }

        for _, row in df.iterrows():
            sk_type = str(row.get("skill_type", ""))
            sk_label = skill_type_labels.get(sk_type, sk_type)
            sk_name = str(row.get("skill_name", ""))
            sk_desc = str(row.get("skill_desc", ""))

            def make_skill_handler(label, name, desc):
                def handler(e):
                    # AlertDialog로 스킬 상세 팝업 표시
                    dlg = ft.AlertDialog(
                        title=ft.Text(f"[{label}] {name}", weight=ft.FontWeight.BOLD),
                        content=ft.Text(desc or "(설명 없음)", size=13),
                        actions=[ft.TextButton("닫기", on_click=lambda e: close_dlg(e, dlg, page))],
                    )
                    page.overlay.append(dlg)
                    dlg.open = True
                    page.update()
                return handler

            skill_buttons.controls.append(
                ft.ElevatedButton(
                    text=sk_label,
                    on_click=make_skill_handler(sk_label, sk_name, sk_desc),
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.BLUE_700,
                        color=ft.colors.WHITE,
                        padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    ),
                )
            )

        detail_name.update()
        detail_school.update()
        skill_buttons.update()
        detail_info.update()

    def _info_row(label: str, value: str) -> ft.Control:
        """라벨-값 쌍을 표시하는 Row 위젯"""
        return ft.Row([
            ft.Text(label, size=12, color=ft.colors.GREY_600, width=60),
            ft.Text(value, size=12, expand=True),
        ], spacing=8)

    def close_dlg(e, dlg, page):
        """AlertDialog 닫기"""
        dlg.open = False
        page.update()

    # ── 학생 목록 업데이트 함수 ──────────────────────────────────────────────

    def refresh_list(page: ft.Page) -> None:
        """필터 조건에 맞는 학생 카드 목록을 다시 렌더링"""
        df = service.get_students(
            star_grade=filter_state["star"],
            school=filter_state["school"],
            tactic_role=filter_state["role"],
            keyword=filter_state["keyword"] or None,
        )

        student_list.controls = []

        for _, row in df.iterrows():
            sid = int(row["id"])
            name = str(row["full_name"])
            star = int(row["star_grade"])
            role = str(row.get("tactic_role", ""))
            icon_url = str(row.get("icon_url", "")) or None
            stars_str = "★" * star

            # 성급별 색상
            star_color = {3: ft.colors.YELLOW_700, 2: ft.colors.ORANGE_400}.get(
                star, ft.colors.GREY_500
            )

            def make_card_handler(student_id):
                def handler(e):
                    update_detail(student_id, page)
                return handler

            card = ft.Container(
                content=ft.Row([
                    # 아이콘 이미지
                    ft.Image(
                        src=icon_url or "https://schaledb.com/images/common/default.webp",
                        width=40,
                        height=40,
                        fit=ft.ImageFit.COVER,
                        border_radius=20,
                        error_content=ft.Icon(ft.icons.PERSON, size=24),
                    ),
                    # 이름 + 성급
                    ft.Column([
                        ft.Text(name, size=13, weight=ft.FontWeight.W_500),
                        ft.Text(
                            stars_str + f"  {role}",
                            size=11,
                            color=star_color,
                        ),
                    ], spacing=2, expand=True),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
                border_radius=6,
                ink=True,
                on_click=make_card_handler(sid),
                bgcolor=ft.colors.SURFACE_VARIANT,
            )
            student_list.controls.append(card)

        student_list.update()

    # ── 필터 컨트롤 생성 ─────────────────────────────────────────────────────

    def build_filters(page: ft.Page) -> ft.Row:
        """검색 바 + 필터 드롭다운 Row 생성"""
        schools = ["전체"] + service.get_schools()
        roles   = ["전체"] + service.get_roles()
        stars   = ["전체", "3성", "2성", "1성"]

        search = ft.TextField(
            hint_text="이름 검색...",
            expand=True,
            height=38,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
            on_change=lambda e: (
                filter_state.update(keyword=e.control.value),
                refresh_list(page),
            ),
        )

        def make_dropdown(options: list[str], key: str, none_val):
            def on_change(e):
                v = e.control.value
                filter_state[key] = None if v == "전체" else (
                    int(v[0]) if key == "star" else v
                )
                refresh_list(page)
            return ft.Dropdown(
                options=[ft.dropdown.Option(o) for o in options],
                value="전체",
                width=110,
                height=38,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=2),
                on_change=on_change,
            )

        return ft.Row([
            search,
            make_dropdown(schools, "school", None),
            make_dropdown(roles,   "role",   None),
            make_dropdown(stars,   "star",   None),
        ], spacing=8)

    # ── 탭 전체 레이아웃 조립 ───────────────────────────────────────────────

    def build(page: ft.Page) -> ft.Control:
        filters = build_filters(page)
        refresh_list(page)

        return ft.Column([
            filters,
            ft.Row([
                # 좌측: 학생 목록
                ft.Container(
                    content=student_list,
                    width=240,
                    expand=False,
                    border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=4,
                ),
                # 우측: 상세 정보
                ft.Container(
                    content=detail_panel,
                    expand=True,
                    border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=12,
                ),
            ], expand=True, spacing=8),
        ], expand=True, spacing=8)

    # build 함수를 호출하는 래퍼 (Page 접근이 필요해서 지연 생성)
    # main.py에서 page를 넘겨서 생성
    return build
