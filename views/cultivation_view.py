"""
views/cultivation_view.py
육성 시뮬레이터 탭 Flet UI

Use Case 3.3: 보유 학생 현황 조회
Use Case 3.3.1: 육성 목표 설정
Use Case 3.3.2: 육성 비용 계산

구성:
- 상단: 보유 학생 버튼 목록 (아이콘 + 이름)
- 하단 좌측: 현재/목표 수치 입력 폼
- 하단 우측: 비용 계산 결과 테이블
"""

import flet as ft
import pandas as pd
from service.cultivation_service import CultivationService, CostSummary


def create_cultivation_view(service: CultivationService) -> callable:
    """육성 시뮬레이터 탭 컨트롤 생성기 반환"""

    def build(page: ft.Page) -> ft.Control:

        # ── 선택된 학생 상태 ─────────────────────────────────────────────────
        state = {"student_id": None, "student_name": ""}

        # ── 보유 학생 버튼 목록 ──────────────────────────────────────────────
        owned_row = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

        # ── 육성 입력 폼 필드 ────────────────────────────────────────────────
        selected_name = ft.Text("학생을 선택하세요", size=16, weight=ft.FontWeight.BOLD)

        # 현재/목표 수치 입력 필드 정의
        # (필드 ID, 표시 라벨, 현재 최솟값, 최댓값)
        FIELDS = [
            ("level",         "레벨",        1,  90),
            ("ex_skill",      "EX 스킬",     1,   5),
            ("normal_skill",  "기본 스킬",   1,  10),
            ("enhance_skill", "강화 스킬",   1,  10),
            ("sub_skill",     "서브 스킬",   1,  10),
            ("weapon_level",  "고유 무기",   1,  50),
            ("bond_rank",     "인연 랭크",   1,  50),
            ("star",          "성급",         1,   5),
        ]

        # 현재/목표 TextField 딕셔너리
        current_fields: dict[str, ft.TextField] = {}
        goal_fields: dict[str, ft.TextField] = {}

        form_rows = ft.Column([], spacing=6, scroll=ft.ScrollMode.AUTO)

        def make_field(key: str, is_goal: bool) -> ft.TextField:
            """숫자 입력 TextField 생성"""
            return ft.TextField(
                value="1",
                width=70,
                height=36,
                text_align=ft.TextAlign.CENTER,
                content_padding=ft.padding.symmetric(horizontal=4, vertical=4),
                keyboard_type=ft.KeyboardType.NUMBER,
            )

        for key, label, min_v, max_v in FIELDS:
            cur_field = make_field(key, False)
            goal_field = make_field(key, True)
            current_fields[key] = cur_field
            goal_fields[key] = goal_field

            form_rows.controls.append(ft.Row([
                ft.Text(label, size=13, width=70),
                ft.Text("현재", size=11, color=ft.colors.GREY_600, width=30),
                cur_field,
                ft.Icon(ft.icons.ARROW_FORWARD, size=16, color=ft.colors.GREY_400),
                ft.Text("목표", size=11, color=ft.colors.GREY_600, width=30),
                goal_field,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        # ── 비용 계산 결과 ───────────────────────────────────────────────────
        cost_result = ft.Column(
            [],
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # ── 보유 학생 목록 갱신 ──────────────────────────────────────────────

        def refresh_owned() -> None:
            """보유 학생 버튼 목록 갱신"""
            df = service.get_owned_students()
            owned_row.controls = []

            if df.empty:
                owned_row.controls.append(
                    ft.Text("보유 학생 없음\n가챠 탭에서 학생을 먼저 획득하세요.",
                            color=ft.colors.GREY_500, size=13)
                )
                owned_row.update()
                return

            for _, row in df.iterrows():
                sid = int(row["student_id"])
                name = str(row["full_name"])
                cur_star = int(row.get("current_star", 1))
                icon_url = row.get("icon_url")
                icon_url = str(icon_url) if icon_url and str(icon_url) != "None" else None

                stars_str = "★" * cur_star

                def make_handler(student_id, student_name):
                    def handler(e):
                        on_student_select(student_id, student_name)
                    return handler

                btn = ft.ElevatedButton(
                    content=ft.Column([
                        ft.Image(
                            src=icon_url or "https://schaledb.com/images/common/default.webp",
                            width=44,
                            height=44,
                            fit=ft.ImageFit.COVER,
                            border_radius=22,
                            error_content=ft.Icon(ft.icons.PERSON, size=24),
                        ),
                        ft.Text(name, size=11, text_align=ft.TextAlign.CENTER),
                        ft.Text(stars_str, size=10, color=ft.colors.AMBER_700,
                                text_align=ft.TextAlign.CENTER),
                    ], alignment=ft.MainAxisAlignment.CENTER,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=2),
                    width=80,
                    height=90,
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(4),
                        bgcolor=ft.colors.SURFACE_VARIANT,
                    ),
                    on_click=make_handler(sid, name),
                )
                owned_row.controls.append(btn)

            owned_row.update()

        # ── 학생 선택 시 폼 자동 입력 ────────────────────────────────────────

        def on_student_select(student_id: int, name: str) -> None:
            """보유 학생 선택 → 현재/목표 수치 자동 입력"""
            state["student_id"] = student_id
            state["student_name"] = name
            selected_name.value = name
            selected_name.update()

            # 현재 수치 로드
            cultivation = service.get_cultivation(student_id)
            if cultivation is not None:
                for key, _, _, _ in FIELDS:
                    v = cultivation.get(key)
                    current_fields[key].value = str(int(v)) if v is not None else "1"
                    current_fields[key].update()

            # 목표 수치 로드 (미설정이면 현재 값으로 초기화)
            goal = service.get_goal(student_id)
            if goal is not None:
                for key, _, _, _ in FIELDS:
                    v = goal.get(key)
                    goal_fields[key].value = str(int(v)) if v is not None else "1"
                    goal_fields[key].update()
            else:
                # 목표 미설정: 현재 값 그대로 복사
                for key, _, _, _ in FIELDS:
                    goal_fields[key].value = current_fields[key].value
                    goal_fields[key].update()

            # 결과 초기화
            cost_result.controls = [ft.Text("[비용 계산하기] 버튼을 클릭하세요",
                                            color=ft.colors.GREY_500, size=13)]
            cost_result.update()

        # ── 비용 계산 버튼 핸들러 ────────────────────────────────────────────

        def on_calculate(e) -> None:
            """비용 계산하기 버튼 클릭"""
            sid = state["student_id"]
            if sid is None:
                return

            # 현재/목표 수치 수집
            cur_dict = {}
            goal_dict = {}
            for key, _, _, _ in FIELDS:
                try:
                    cur_dict[key] = int(current_fields[key].value or 1)
                    goal_dict[key] = int(goal_fields[key].value or 1)
                except ValueError:
                    cur_dict[key] = 1
                    goal_dict[key] = 1

            # 서비스 호출: DB 저장 + 비용 계산
            summary = service.calculate_and_save(sid, cur_dict, goal_dict)

            # 결과 표시
            cost_result.controls = _build_cost_rows(summary, cur_dict, goal_dict)
            cost_result.update()

        def _build_cost_rows(
            summary: CostSummary,
            cur: dict,
            goal: dict,
        ) -> list[ft.Control]:
            """비용 계산 결과를 Flet 위젯 목록으로 변환"""
            rows = []

            # 크레딧
            rows.append(ft.Text("── 필요 재화 ──", weight=ft.FontWeight.BOLD, size=14))

            if summary.credit > 0:
                rows.append(_cost_row("크레딧", f"{summary.credit:,}"))

            # 스킬 재료
            if summary.skill_items:
                rows.append(ft.Text("· 스킬 강화 재료", size=12, color=ft.colors.GREY_700))
                for item_name, amount in summary.skill_items.items():
                    rows.append(_cost_row(f"  {item_name}", f"{amount:,}개"))

            # 성급 상승 엘레프
            if summary.eleph_needed > 0:
                rows.append(ft.Text("── 성급 상승 ──", weight=ft.FontWeight.BOLD, size=14))
                rows.append(_cost_row("필요 엘레프", f"{summary.eleph_needed}개"))
                rows.append(_cost_row(
                    "보유 엘레프",
                    f"{summary.eleph_current}개 "
                    f"({'부족' if summary.eleph_current < summary.eleph_needed else '충분'})"
                ))

            # 인연 선물
            if summary.bond_gifts:
                rows.append(ft.Text("── 인연 랭크 선물 ──", weight=ft.FontWeight.BOLD, size=14))
                for gift_name, amount in summary.bond_gifts.items():
                    rows.append(_cost_row(gift_name, f"{amount}개"))

            if not rows:
                rows.append(ft.Text("계산할 육성 내용이 없습니다.", color=ft.colors.GREY_500))

            return rows

        def _cost_row(label: str, value: str) -> ft.Control:
            """비용 항목 1행 위젯"""
            return ft.Row([
                ft.Text(label, size=12, expand=True),
                ft.Text(value, size=12, weight=ft.FontWeight.W_500, color=ft.colors.BLUE_700),
            ])

        # 초기 보유 학생 목록 로드
        refresh_owned()

        # 보유 학생 없으면 안내
        cost_result.controls = [ft.Text("학생을 선택하면 육성 목표를 설정할 수 있습니다.",
                                         color=ft.colors.GREY_500, size=13)]

        # ── 레이아웃 조립 ────────────────────────────────────────────────────
        return ft.Column([
            # 보유 학생 버튼 목록
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("보유 학생", size=14, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=owned_row,
                            height=110,
                        ),
                    ], spacing=6),
                    padding=12,
                ),
            ),

            # 선택된 학생명
            ft.Row([
                selected_name,
                ft.ElevatedButton(
                    text="목록 새로고침",
                    icon=ft.icons.REFRESH,
                    on_click=lambda e: refresh_owned(),
                    height=32,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            # 입력 폼 + 결과 패널
            ft.Row([
                # 좌측: 현재/목표 수치 입력 폼
                ft.Container(
                    content=ft.Column([
                        ft.Text("현재  →  목표 수치 설정",
                                size=13, weight=ft.FontWeight.BOLD),
                        form_rows,
                        ft.ElevatedButton(
                            text="비용 계산하기",
                            icon=ft.icons.CALCULATE,
                            on_click=on_calculate,
                            style=ft.ButtonStyle(
                                bgcolor=ft.colors.GREEN_700,
                                color=ft.colors.WHITE,
                                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                            ),
                        ),
                    ], spacing=8),
                    width=320,
                    border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=12,
                ),

                # 우측: 비용 계산 결과
                ft.Container(
                    content=ft.Column([
                        ft.Text("필요 재화", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=cost_result,
                            expand=True,
                        ),
                    ], spacing=8, expand=True),
                    expand=True,
                    border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=12,
                ),
            ], spacing=12, expand=True),
        ], spacing=8, expand=True)

    return build
