"""
views/gacha_view.py
가챠 시뮬레이터 탭 Flet UI

Use Case 3.2: 가챠 뽑기
Use Case 3.2.1: 가챠 결과 저장

구성:
- 배너 선택 드롭다운
- 모집 진행도 바 (0/200)
- 1회 / 10회 뽑기 버튼
- 최근 뽑기 결과 표시
- 통계 (총 뽑기 수, 3성 획득 수)

컨트롤 갱신(.update())과 확인 모달은 views/_helpers.py의
safe_update() / show_confirm_dialog() 공통 헬퍼를 사용한다
(student_view.py, cultivation_view.py와 동일한 헬퍼 공유).
"""

import flet as ft

from service.gacha_service import GachaService, PullResult
from views._helpers import safe_update, show_confirm_dialog

# 성급별 배경색
STAR_COLORS = {
    3: ft.Colors.AMBER_100,
    2: ft.Colors.ORANGE_100,
    1: ft.Colors.GREY_100,
}

# 성급별 텍스트 색상
STAR_TEXT_COLORS = {
    3: ft.Colors.AMBER_900,
    2: ft.Colors.ORANGE_900,
    1: ft.Colors.GREY_700,
}


def create_gacha_view(service: GachaService) -> callable:
    """가챠 시뮬레이터 탭 컨트롤 생성기 반환"""

    def build(page: ft.Page) -> ft.Control:
        # ── 배너 목록 로드 ───────────────────────────────────────────────────
        banners_df = service.get_banners()
        if banners_df.empty:
            return ft.Column([ft.Text("배너 정보 없음. 앱을 재시작하세요.")])

        # 배너 ID → (이름, student_id, star_grade) 매핑
        banner_map = {
            int(row["id"]): str(row["pickup_name"]) for _, row in banners_df.iterrows()
        }
        banner_info = {
            int(row["id"]): {
                "name":       str(row["pickup_name"]),
                "student_id": int(row["pickup_student_id"]),
                "star_grade": int(row["star_grade"]),
            }
            for _, row in banners_df.iterrows()
        }
        first_banner_id = int(banners_df.iloc[0]["id"])

        # ── 상태 ────────────────────────────────────────────────────────────
        state = {"banner_id": first_banner_id, "search": ""}
        # 전체 배너 옵션 (검색 필터링용)
        all_options = [
            ft.dropdown.Option(key=str(bid), text=name)
            for bid, name in banner_map.items()
        ]

        # ── 컨트롤 ──────────────────────────────────────────────────────────
        # 픽업 학생 이름 검색
        banner_search = ft.TextField(
            hint_text="픽업 학생 이름 검색...",
            expand=True,
            height=40,
            content_padding=ft.Padding(left=10, right=10, top=4, bottom=4),
        )

        # 배너 드롭다운
        banner_dropdown = ft.Dropdown(
            label="배너 선택 (검색 후 선택)",
            options=all_options,
            value=str(first_banner_id),
            width=350,
        )

        # 진행도 바
        progress_bar = ft.ProgressBar(
            value=0,
            width=400,
            color=ft.Colors.BLUE_400,
            bgcolor=ft.Colors.GREY_200,
        )
        progress_text = ft.Text("0 / 200", size=14)

        # 통계 텍스트
        stat_total = ft.Text("총 뽑기: 0회", size=13)
        stat_star3 = ft.Text("3성 획득: 0명", size=13)
        stat_to_pity = ft.Text("천장까지: 200회", size=13, color=ft.Colors.BLUE_700)

        # 픽업 확정 수령 버튼 (200회 달성 시 활성화)
        claim_btn = ft.ElevatedButton(
            "픽업 학생 확정 수령",
            icon=ft.Icons.STAR,
            bgcolor=ft.Colors.AMBER_600,
            color=ft.Colors.WHITE,
            disabled=True,
        )

        # 픽업 학생 카드 (진행도 카드 우측)
        pickup_card = ft.Container(width=90)

        # 최근 뽑기 결과 목록
        result_list = ft.ListView(
            expand=True,
            spacing=4,
            padding=4,
        )

        # ── 상태 갱신 함수 ───────────────────────────────────────────────────

        def refresh_pickup_card() -> None:
            """진행도 카드 우측 픽업 학생 사진·성급 갱신"""
            info = banner_info.get(state["banner_id"])
            if not info:
                pickup_card.content = None
                safe_update(pickup_card)
                return

            sid   = info["student_id"]
            star  = info["star_grade"]
            name  = info["name"]
            icon_url = f"https://schaledb.com/images/student/icon/{sid}.webp"
            star_color = STAR_TEXT_COLORS.get(star, ft.Colors.GREY_700)

            pickup_card.content = ft.Column(
                [
                    ft.Container(
                        content=ft.Image(
                            src=icon_url,
                            width=72, height=72,
                            fit="cover",
                            border_radius=8,
                            error_content=ft.Icon(ft.Icons.PERSON, size=32),
                        ),
                        border=ft.Border.all(2, ft.Colors.AMBER_400),
                        border_radius=8,
                    ),
                    ft.Text(
                        name,
                        size=10,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        width=80,
                    ),
                    ft.Text(
                        "★" * star,
                        size=11,
                        color=star_color,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            safe_update(pickup_card)

        def refresh_stats() -> None:
            """
            통계 및 진행도 바 갱신
            - get_stats()로 총 뽑기 수 / 3성 획득 수 / 현재 사이클 뽑기 수를 조회
            - 천장(200회)까지 남은 횟수를 계산해 진행도 바·텍스트에 반영
            - 200회 도달 시 [픽업 확정 수령] 버튼 활성화
            """
            bid = state["banner_id"]
            stats = service.get_stats(bid)
            total = stats["total_pulls"]
            star3 = stats["star3_count"]
            current = stats["current_pull_count"]

            remaining = max(0, 200 - current)
            stat_total.value = f"총 뽑기: {total}회"
            stat_star3.value = f"3성 획득: {star3}명"
            stat_to_pity.value = f"천장까지: {remaining}회"
            progress_bar.value = min(current / 200, 1.0)
            progress_text.value = f"{min(current, 200)} / 200"
            claim_btn.disabled = current < 200

            # 위 6개 컨트롤을 한 번에 갱신 (마운트 전이면 safe_update가 조용히 무시)
            safe_update(
                stat_total, stat_star3, stat_to_pity,
                progress_bar, progress_text, claim_btn,
            )

        def _make_pull_grid(results: list[PullResult]) -> ft.Control:
            """뽑기 결과 5×N 이미지 그리드"""
            cards = []
            for r in results:
                icon_url = f"https://schaledb.com/images/student/icon/{r.student_id}.webp"
                bg = STAR_COLORS.get(r.star_grade, ft.Colors.GREY_100)
                border = (
                    ft.Border.all(2, ft.Colors.AMBER_400)
                    if r.star_grade == 3
                    else ft.Border.all(1, ft.Colors.GREY_300)
                )
                badges = []
                if r.is_pickup:
                    badges.append("🎯")
                if r.is_new:
                    badges.append("NEW")
                badge_str = " ".join(badges)

                card = ft.Container(
                    content=ft.Column(
                        [
                            ft.Image(
                                src=icon_url,
                                width=58, height=58,
                                fit="cover",
                                border_radius=6,
                                error_content=ft.Icon(ft.Icons.PERSON, size=28),
                            ),
                            ft.Text(
                                r.student_name,
                                size=9,
                                text_align=ft.TextAlign.CENTER,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                "★" * r.star_grade
                                + (f"\n{badge_str}" if badge_str else ""),
                                size=9,
                                color=STAR_TEXT_COLORS.get(r.star_grade, ft.Colors.BLACK),
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=74, height=108,
                    bgcolor=bg,
                    border=border,
                    border_radius=8,
                    padding=4,
                )
                cards.append(card)

            rows = []
            for i in range(0, len(cards), 5):
                rows.append(ft.Row(
                    cards[i:i + 5],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                ))
            return ft.Column(
                rows, spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

        def refresh_results(new_results: list[PullResult] | None = None) -> None:
            """최근 뽑기 결과 목록 갱신"""
            result_list.controls = []

            # 새로운 결과: 이미지 그리드로 표시
            if new_results:
                result_list.controls.append(
                    ft.Text("─── 이번 뽑기 결과 ───", size=12, color=ft.Colors.GREY_600)
                )
                result_list.controls.append(_make_pull_grid(new_results))
                result_list.controls.append(ft.Divider(height=1))

            # DB에서 최근 기록 로드
            bid = state["banner_id"]
            recent_df = service.get_recent_pulls(bid, limit=20)
            if not recent_df.empty:
                result_list.controls.append(
                    ft.Text("─── 최근 기록 ───", size=12, color=ft.Colors.GREY_600)
                )
                for _, row in recent_df.iterrows():
                    star = int(row["star_grade"])
                    name = str(row["full_name"])
                    is_pickup = bool(row["is_pickup"])
                    stars_str = "★" * star
                    label = f"{stars_str} {name}" + (" 🎯픽업" if is_pickup else "")
                    result_list.controls.append(
                        ft.Container(
                            content=ft.Text(
                                label,
                                size=12,
                                color=STAR_TEXT_COLORS.get(star, ft.Colors.BLACK),
                            ),
                            bgcolor=STAR_COLORS.get(star, ft.Colors.GREY_100),
                            border_radius=4,
                            padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                        )
                    )

            safe_update(result_list)

        # ── 이벤트 핸들러 ────────────────────────────────────────────────────

        def on_banner_search(e) -> None:
            """픽업 학생 이름 검색 → 드롭다운 옵션 필터링"""
            keyword = e.control.value.strip().lower()
            state["search"] = keyword
            filtered = [
                opt
                for opt in all_options
                if keyword == "" or keyword in opt.text.lower()
            ]
            banner_dropdown.options = filtered
            # 현재 선택이 필터 밖이면 첫 번째로 변경
            valid_keys = {opt.key for opt in filtered}
            if str(state["banner_id"]) not in valid_keys and filtered:
                state["banner_id"] = int(filtered[0].key)
                banner_dropdown.value = filtered[0].key
                refresh_pickup_card()
                refresh_stats()
                refresh_results()
            safe_update(banner_dropdown)

        def on_banner_change(e) -> None:
            """배너 선택 변경"""
            if e.control.value:
                state["banner_id"] = int(e.control.value)
            refresh_pickup_card()
            refresh_stats()
            refresh_results()

        def on_pull(count: int) -> None:
            """뽑기 버튼 클릭 (1회 또는 10회)"""
            bid = state["banner_id"]
            results = service.pull(bid, count)
            refresh_stats()
            refresh_results(results)

        def on_claim(e) -> None:
            """픽업 확정 수령 버튼 클릭"""
            bid = state["banner_id"]
            result = service.claim_pickup(bid)
            if result:
                refresh_stats()
                refresh_results([result])

        def on_reset_banner(e) -> None:
            """뽑기 초기화 버튼 — 확인 모달을 띄운 뒤, 확인 시에만 실제 삭제 수행"""
            bid = state["banner_id"]
            banner_name = banner_map.get(bid, "")

            def do_reset() -> None:
                service.reset_banner(bid)
                refresh_stats()
                refresh_results()

            show_confirm_dialog(
                page,
                title="뽑기 기록 초기화",
                message=(
                    f"[{banner_name}] 배너의 모든 뽑기 기록이 삭제됩니다.\n"
                    "이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?"
                ),
                on_confirm=do_reset,
                confirm_label="초기화",
            )

        # 이벤트 연결
        banner_search.on_change = on_banner_search
        banner_dropdown.on_select = on_banner_change
        claim_btn.on_click = on_claim

        # 초기 상태 로드
        refresh_pickup_card()
        refresh_stats()
        refresh_results()

        # ── 레이아웃 조립 ────────────────────────────────────────────────────
        return ft.Column(
            [
                # 픽업 학생 이름 검색 + 배너 드롭다운
                ft.Row([banner_search, banner_dropdown], spacing=8),
                # 진행도 바
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                # 좌측: 진행도 정보
                                ft.Column(
                                    [
                                        ft.Text(
                                            "모집 진행도",
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Row([progress_bar, progress_text], spacing=12),
                                        ft.Row(
                                            [stat_total, stat_star3, stat_to_pity],
                                            spacing=24,
                                        ),
                                    ],
                                    spacing=8,
                                    expand=True,
                                ),
                                # 우측: 픽업 학생 사진
                                pickup_card,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=12,
                        ),
                        padding=16,
                    )
                ),
                # 뽑기 버튼
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "1회 뽑기",
                            icon=ft.Icons.CASINO,
                            on_click=lambda e: on_pull(1),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                padding=ft.Padding(
                                    left=20, right=20, top=12, bottom=12
                                ),
                            ),
                        ),
                        ft.ElevatedButton(
                            "10회 뽑기",
                            icon=ft.Icons.CASINO,
                            on_click=lambda e: on_pull(10),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.INDIGO_700,
                                color=ft.Colors.WHITE,
                                padding=ft.Padding(
                                    left=20, right=20, top=12, bottom=12
                                ),
                            ),
                        ),
                        claim_btn,
                        ft.ElevatedButton(
                            "초기화",
                            icon=ft.Icons.DELETE_SWEEP,
                            on_click=on_reset_banner,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE,
                                padding=ft.Padding(
                                    left=16, right=16, top=12, bottom=12
                                ),
                            ),
                        ),
                    ],
                    spacing=12,
                ),
                ft.Divider(height=1),
                # 뽑기 결과 목록
                ft.Text("뽑기 결과", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=result_list,
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=8,
                ),
            ],
            spacing=12,
            expand=True,
        )

    return build
