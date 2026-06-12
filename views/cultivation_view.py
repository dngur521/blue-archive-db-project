"""
views/cultivation_view.py
육성 시뮬레이터 탭 Flet UI

Use Case 3.3: 보유 학생 현황 조회
Use Case 3.3.1: 육성 목표 설정
Use Case 3.3.2: 육성 비용 계산

개선 사항:
- 보유 학생 이름 검색 추가
- 폼 스크롤 가능 (잘림 없음)
- 육성 수치 초기화 버튼 추가
"""

import flet as ft

from service.cultivation_service import CostSummary, CultivationService


def create_cultivation_view(service: CultivationService) -> callable:
    """육성 시뮬레이터 탭 컨트롤 생성기 반환"""

    def build(page: ft.Page) -> ft.Control:

        # ── 선택된 학생 상태 ─────────────────────────────────────────────────
        state = {"student_id": None, "student_name": "", "search": ""}

        # ── 보유 학생 버튼 목록 ──────────────────────────────────────────────
        owned_row = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

        # 보유 학생 검색 필드
        owned_search = ft.TextField(
            hint_text="보유 학생 이름 검색...",
            height=36,
            width=200,
            content_padding=ft.Padding(left=10, right=10, top=4, bottom=4),
        )

        # ── 육성 입력 폼 필드 ────────────────────────────────────────────────
        selected_name = ft.Text("학생을 선택하세요", size=16, weight=ft.FontWeight.BOLD)

        FIELDS = [
            ("level",         "레벨",     1, 90),
            ("ex_skill",      "EX 스킬",  1, 5),
            ("normal_skill",  "기본 스킬", 1, 10),
            ("enhance_skill", "강화 스킬", 1, 10),
            ("sub_skill",     "서브 스킬", 1, 10),
            ("weapon_level",  "고유 무기", 1, 50),
            ("bond_rank",     "인연 랭크", 1, 100),
            ("star",          "성급",     1, 5),
        ]

        current_fields: dict[str, ft.TextField] = {}
        goal_fields: dict[str, ft.TextField] = {}

        def make_field(min_val: int, max_val: int) -> ft.TextField:
            def on_blur(e):
                try:
                    v = int(e.control.value or min_val)
                except ValueError:
                    v = min_val
                v = max(min_val, min(max_val, v))
                e.control.value = str(v)
                try:
                    e.control.update()
                except RuntimeError:
                    pass
            return ft.TextField(
                value=str(min_val),
                width=65,
                height=34,
                text_align=ft.TextAlign.CENTER,
                content_padding=ft.Padding(left=4, right=4, top=2, bottom=2),
                keyboard_type=ft.KeyboardType.NUMBER,
                on_blur=on_blur,
            )

        form_rows = ft.Column([], spacing=4)

        for key, label, min_v, max_v in FIELDS:
            cur_field  = make_field(min_v, max_v)
            goal_field = make_field(min_v, max_v)
            current_fields[key] = cur_field
            goal_fields[key]    = goal_field
            form_rows.controls.append(
                ft.Row(
                    [
                        ft.Text(label, size=12, width=65),
                        ft.Text("현재", size=10, color=ft.Colors.GREY_600, width=28),
                        cur_field,
                        ft.Icon(
                            ft.Icons.ARROW_FORWARD, size=14, color=ft.Colors.GREY_400
                        ),
                        ft.Text("목표", size=10, color=ft.Colors.GREY_600, width=28),
                        goal_field,
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        # ── 비용 계산 결과 ───────────────────────────────────────────────────
        cost_result = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        # ── 헬퍼 ────────────────────────────────────────────────────────────

        def _safe_update(*controls) -> None:
            """페이지 미연결 시 RuntimeError 무시"""
            for ctrl in controls:
                try:
                    ctrl.update()
                except RuntimeError:
                    pass

        # ── 보유 학생 목록 갱신 ──────────────────────────────────────────────

        def refresh_owned(keyword: str = "") -> None:
            """보유 학생 버튼 목록 갱신 (키워드 필터 포함)"""
            df = service.get_owned_students()
            owned_row.controls = []

            if df.empty:
                owned_row.controls.append(
                    ft.Text(
                        "보유 학생 없음 — 가챠 탭에서 먼저 획득하세요.",
                        color=ft.Colors.GREY_500,
                        size=13,
                    )
                )
                _safe_update(owned_row)
                return

            for _, row in df.iterrows():
                sid = int(row["student_id"])
                name = str(row["full_name"])
                cur_star = int(row.get("current_star", 1))

                # 검색 필터
                if keyword and keyword.lower() not in name.lower():
                    continue

                # 아이콘 이미지 (로컬 캐시)
                raw_icon = row.get("icon_url")
                raw_icon = (
                    str(raw_icon) if raw_icon and str(raw_icon) != "None" else None
                )
                icon_src = raw_icon or ""

                stars_str = "★" * cur_star

                def make_handler(student_id, student_name):
                    def handler(e):
                        on_student_select(student_id, student_name)

                    return handler

                btn = ft.ElevatedButton(
                    content=ft.Column(
                        [
                            ft.Image(
                                src=icon_src,
                                width=44,
                                height=44,
                                fit="cover",
                                border_radius=22,
                                error_content=ft.Icon(ft.Icons.PERSON, size=24),
                            ),
                            ft.Text(
                                name,
                                size=10,
                                text_align=ft.TextAlign.CENTER,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                stars_str,
                                size=10,
                                color=ft.Colors.AMBER_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    width=82,
                    height=95,
                    style=ft.ButtonStyle(
                        padding=4,
                        bgcolor=(
                            ft.Colors.BLUE_100
                            if sid == state["student_id"]
                            else ft.Colors.SURFACE_CONTAINER
                        ),
                    ),
                    on_click=make_handler(sid, name),
                )
                owned_row.controls.append(btn)

            _safe_update(owned_row)

        # ── 학생 선택 시 폼 자동 입력 ────────────────────────────────────────

        def on_student_select(student_id: int, name: str) -> None:
            state["student_id"] = student_id
            state["student_name"] = name
            selected_name.value = name
            _safe_update(selected_name)

            cultivation = service.get_cultivation(student_id)
            if cultivation is not None:
                for key, *_ in FIELDS:
                    v = cultivation.get(key)
                    current_fields[key].value = str(int(v)) if v is not None else "1"

            goal = service.get_goal(student_id)
            if goal is not None:
                for key, *_ in FIELDS:
                    v = goal.get(key)
                    goal_fields[key].value = str(int(v)) if v is not None else "1"
            else:
                for key, *_ in FIELDS:
                    goal_fields[key].value = current_fields[key].value

            for key, *_ in FIELDS:
                _safe_update(current_fields[key], goal_fields[key])

            cost_result.controls = [
                ft.Text(
                    "[비용 계산하기] 버튼을 클릭하세요",
                    color=ft.Colors.GREY_500,
                    size=13,
                )
            ]
            _safe_update(cost_result)

            # 선택된 버튼 강조 갱신
            refresh_owned(state["search"])

        # ── 초기화 버튼 핸들러 ────────────────────────────────────────────────

        def on_reset(e) -> None:
            """수치 초기화 버튼 — 확인 모달 표시"""
            if state["student_id"] is None:
                cost_result.controls = [
                    ft.Text("먼저 학생을 선택하세요.", color=ft.Colors.GREY_500, size=13)
                ]
                _safe_update(cost_result)
                return

            name = state["student_name"]

            def do_reset(ev) -> None:
                dlg.open = False
                page.update()
                reset_dict = {}
                for key, _, min_v, *_ in FIELDS:
                    current_fields[key].value = str(min_v)
                    goal_fields[key].value    = str(min_v)
                    reset_dict[key] = min_v
                    _safe_update(current_fields[key], goal_fields[key])
                service.calculate_and_save(state["student_id"], reset_dict, reset_dict)
                cost_result.controls = [
                    ft.Text("수치가 초기화되었습니다.", color=ft.Colors.GREY_500, size=13)
                ]
                _safe_update(cost_result)

            def cancel(ev) -> None:
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("육성 수치 초기화", weight=ft.FontWeight.BOLD),
                content=ft.Text(
                    f"[{name}]의 현재·목표 수치가 모두 최솟값으로 초기화됩니다.\n"
                    "계속하시겠습니까?",
                    size=13,
                ),
                actions=[
                    ft.TextButton("취소", on_click=cancel),
                    ft.ElevatedButton(
                        "초기화",
                        on_click=do_reset,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.RED_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        # ── 비용 계산 ────────────────────────────────────────────────────────

        def on_calculate(e) -> None:
            sid = state["student_id"]
            if sid is None:
                return

            cur_dict, goal_dict = {}, {}
            for key, *_ in FIELDS:
                try:
                    cur_dict[key] = max(1, int(current_fields[key].value or 1))
                    goal_dict[key] = max(1, int(goal_fields[key].value or 1))
                except ValueError:
                    cur_dict[key] = 1
                    goal_dict[key] = 1

            summary = service.calculate_and_save(sid, cur_dict, goal_dict)
            cost_result.controls = _build_cost_rows(summary)
            _safe_update(cost_result)

        def _build_cost_rows(summary: CostSummary) -> list[ft.Control]:
            rows = [ft.Text("── 필요 재화 ──", weight=ft.FontWeight.BOLD, size=14)]

            if summary.credit > 0:
                rows.append(_cost_row("크레딧", f"{summary.credit:,}"))

            if summary.skill_items:
                rows.append(
                    ft.Text("· 스킬 강화 재료", size=12, color=ft.Colors.GREY_700)
                )
                for item_name, amount in summary.skill_items.items():
                    rows.append(_cost_row(f"  {item_name}", f"{amount:,}개"))

            if summary.eleph_needed > 0:
                rows.append(
                    ft.Text("── 성급 상승 ──", weight=ft.FontWeight.BOLD, size=14)
                )
                rows.append(_cost_row("필요 엘레프", f"{summary.eleph_needed}개"))
                short = summary.eleph_current < summary.eleph_needed
                rows.append(
                    _cost_row(
                        "보유 엘레프",
                        f"{summary.eleph_current}개 ({'부족' if short else '충분'})",
                    )
                )

            if summary.bond_gifts:
                rows.append(
                    ft.Text("── 인연 랭크 선물 ──", weight=ft.FontWeight.BOLD, size=14)
                )
                for gift_name, amount in summary.bond_gifts.items():
                    rows.append(_cost_row(gift_name, f"{amount}개"))

            if len(rows) <= 1:
                rows.append(
                    ft.Text("계산할 항목이 없습니다.", color=ft.Colors.GREY_500)
                )

            return rows

        def _cost_row(label: str, value: str) -> ft.Control:
            return ft.Row(
                [
                    ft.Text(label, size=12, expand=True),
                    ft.Text(
                        value,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.BLUE_700,
                    ),
                ]
            )

        def on_reset_all_owned(e) -> None:
            """보유 학생 전체 초기화 버튼 — 확인 모달"""
            def do_reset(ev) -> None:
                dlg.open = False
                page.update()
                service.reset_all_owned()
                state["student_id"] = None
                state["student_name"] = ""
                selected_name.value = "학생을 선택하세요"
                for key, _, min_v, *_ in FIELDS:
                    current_fields[key].value = str(min_v)
                    goal_fields[key].value    = str(min_v)
                cost_result.controls = [
                    ft.Text("보유 학생이 초기화되었습니다.", color=ft.Colors.GREY_500, size=13)
                ]
                _safe_update(selected_name, cost_result, *current_fields.values(), *goal_fields.values())
                refresh_owned()

            def cancel(ev) -> None:
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("보유 학생 전체 초기화", weight=ft.FontWeight.BOLD),
                content=ft.Text(
                    "모든 보유 학생과 육성 목표가 삭제됩니다.\n"
                    "이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?",
                    size=13,
                ),
                actions=[
                    ft.TextButton("취소", on_click=cancel),
                    ft.ElevatedButton(
                        "전체 초기화",
                        on_click=do_reset,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.RED_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        # 검색 이벤트
        def on_search(e) -> None:
            state["search"] = e.control.value.strip()
            refresh_owned(state["search"])

        owned_search.on_change = on_search

        # 초기 목록 로드
        refresh_owned()
        cost_result.controls = [
            ft.Text(
                "학생을 선택하면 육성 목표를 설정할 수 있습니다.",
                color=ft.Colors.GREY_500,
                size=13,
            )
        ]

        # ── 레이아웃 조립 ────────────────────────────────────────────────────
        return ft.Column(
            [
                # 상단: 보유 학생 버튼 목록 + 검색
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            "보유 학생",
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            expand=True,
                                        ),
                                        owned_search,
                                        ft.ElevatedButton(
                                            "새로고침",
                                            icon=ft.Icons.REFRESH,
                                            on_click=lambda e: refresh_owned(
                                                state["search"]
                                            ),
                                            height=36,
                                        ),
                                        ft.ElevatedButton(
                                            "전체 초기화",
                                            icon=ft.Icons.DELETE_SWEEP,
                                            on_click=on_reset_all_owned,
                                            height=36,
                                            style=ft.ButtonStyle(
                                                bgcolor=ft.Colors.RED_700,
                                                color=ft.Colors.WHITE,
                                            ),
                                        ),
                                    ],
                                    spacing=8,
                                ),
                                ft.Container(content=owned_row, height=105),
                            ],
                            spacing=6,
                        ),
                        padding=10,
                    ),
                ),
                # 선택된 학생명 + 초기화 버튼
                ft.Row(
                    [
                        selected_name,
                        ft.ElevatedButton(
                            "수치 초기화",
                            icon=ft.Icons.RESTART_ALT,
                            on_click=on_reset,
                            height=32,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                # 입력 폼 + 결과 패널 (expand=True로 남은 공간 채우기)
                ft.Row(
                    [
                        # 좌측: 현재/목표 수치 입력 폼 (스크롤 가능)
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "현재  →  목표 수치 설정",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Container(
                                        content=form_rows,
                                        expand=True,
                                    ),
                                    ft.ElevatedButton(
                                        "비용 계산하기",
                                        icon=ft.Icons.CALCULATE,
                                        on_click=on_calculate,
                                        style=ft.ButtonStyle(
                                            bgcolor=ft.Colors.GREEN_700,
                                            color=ft.Colors.WHITE,
                                            padding=ft.Padding(
                                                left=16, right=16, top=8, bottom=8
                                            ),
                                        ),
                                    ),
                                ],
                                spacing=8,
                                scroll=ft.ScrollMode.AUTO,
                                expand=True,
                            ),
                            width=320,
                            expand=False,
                            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                            border_radius=8,
                            padding=10,
                        ),
                        # 우측: 비용 계산 결과
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "필요 재화", size=13, weight=ft.FontWeight.BOLD
                                    ),
                                    ft.Container(content=cost_result, expand=True),
                                ],
                                spacing=8,
                                expand=True,
                            ),
                            expand=True,
                            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                            border_radius=8,
                            padding=12,
                        ),
                    ],
                    spacing=12,
                    expand=True,
                ),
            ],
            spacing=8,
            expand=True,
        )

    return build
