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
"""

import flet as ft
from service.gacha_service import GachaService, PullResult

# 성급별 배경색
STAR_COLORS = {
    3: ft.colors.AMBER_100,
    2: ft.colors.ORANGE_100,
    1: ft.colors.GREY_100,
}

# 성급별 텍스트 색상
STAR_TEXT_COLORS = {
    3: ft.colors.AMBER_900,
    2: ft.colors.ORANGE_900,
    1: ft.colors.GREY_700,
}


def create_gacha_view(service: GachaService) -> callable:
    """가챠 시뮬레이터 탭 컨트롤 생성기 반환"""

    def build(page: ft.Page) -> ft.Control:
        # ── 배너 목록 로드 ───────────────────────────────────────────────────
        banners_df = service.get_banners()
        if banners_df.empty:
            return ft.Column([ft.Text("배너 정보 없음. 앱을 재시작하세요.")])

        # 배너 ID → 이름 매핑
        banner_map = {
            int(row["id"]): str(row["pickup_name"])
            for _, row in banners_df.iterrows()
        }
        first_banner_id = int(banners_df.iloc[0]["id"])

        # ── 상태 ────────────────────────────────────────────────────────────
        state = {"banner_id": first_banner_id}

        # ── 컨트롤 ──────────────────────────────────────────────────────────
        # 배너 드롭다운
        banner_dropdown = ft.Dropdown(
            label="배너 선택",
            options=[
                ft.dropdown.Option(key=str(bid), text=name)
                for bid, name in banner_map.items()
            ],
            value=str(first_banner_id),
            width=280,
        )

        # 진행도 바
        progress_bar = ft.ProgressBar(
            value=0,
            width=400,
            color=ft.colors.BLUE_400,
            bgcolor=ft.colors.GREY_200,
        )
        progress_text = ft.Text("0 / 200", size=14)

        # 통계 텍스트
        stat_total = ft.Text("총 뽑기: 0회", size=13)
        stat_star3 = ft.Text("3성 획득: 0명", size=13)
        stat_to_pity = ft.Text("파티까지: 200회", size=13, color=ft.colors.BLUE_700)

        # 픽업 확정 수령 버튼 (200회 달성 시 활성화)
        claim_btn = ft.ElevatedButton(
            text="픽업 학생 확정 수령",
            icon=ft.icons.STAR,
            bgcolor=ft.colors.AMBER_600,
            color=ft.colors.WHITE,
            disabled=True,
        )

        # 최근 뽑기 결과 목록
        result_list = ft.ListView(
            expand=True,
            spacing=4,
            padding=4,
        )

        # ── 상태 갱신 함수 ───────────────────────────────────────────────────

        def refresh_stats() -> None:
            """통계 및 진행도 바 갱신"""
            bid = state["banner_id"]
            stats = service.get_stats(bid)
            total = stats["total_pulls"]
            star3 = stats["star3_count"]
            current = stats["current_pull_count"]

            stat_total.value = f"총 뽑기: {total}회"
            stat_star3.value = f"3성 획득: {star3}명"
            stat_to_pity.value = f"파티까지: {200 - current}회"
            progress_bar.value = min(current / 200, 1.0)
            progress_text.value = f"{current} / 200"
            claim_btn.disabled = (current < 200)

            stat_total.update()
            stat_star3.update()
            stat_to_pity.update()
            progress_bar.update()
            progress_text.update()
            claim_btn.update()

        def refresh_results(new_results: list[PullResult] | None = None) -> None:
            """최근 뽑기 결과 목록 갱신"""
            result_list.controls = []

            # 새로운 결과가 있으면 상단에 추가 표시
            if new_results:
                result_list.controls.append(
                    ft.Text("─── 이번 뽑기 결과 ───", size=12, color=ft.colors.GREY_600)
                )
                for r in new_results:
                    result_list.controls.append(_make_result_card(r))
                result_list.controls.append(ft.Divider(height=1))

            # DB에서 최근 기록 로드
            bid = state["banner_id"]
            recent_df = service.get_recent_pulls(bid, limit=20)
            if not recent_df.empty:
                result_list.controls.append(
                    ft.Text("─── 최근 기록 ───", size=12, color=ft.colors.GREY_600)
                )
                for _, row in recent_df.iterrows():
                    star = int(row["star_grade"])
                    name = str(row["full_name"])
                    is_pickup = bool(row["is_pickup"])
                    stars_str = "★" * star
                    label = f"{stars_str} {name}" + (" 🎯픽업" if is_pickup else "")
                    result_list.controls.append(
                        ft.Container(
                            content=ft.Text(label, size=12, color=STAR_TEXT_COLORS.get(star, ft.colors.BLACK)),
                            bgcolor=STAR_COLORS.get(star, ft.colors.GREY_100),
                            border_radius=4,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        )
                    )

            result_list.update()

        def _make_result_card(r: PullResult) -> ft.Control:
            """뽑기 결과 1건 카드 위젯"""
            stars_str = "★" * r.star_grade
            label = f"{stars_str} {r.student_name}"
            if r.is_pickup:
                label += " 🎯픽업"
            if r.is_new:
                label += " ✨NEW"
            if r.eleph_gained > 0:
                label += f" (엘레프 +{r.eleph_gained})"

            return ft.Container(
                content=ft.Text(label, size=13, weight=ft.FontWeight.W_500,
                                color=STAR_TEXT_COLORS.get(r.star_grade, ft.colors.BLACK)),
                bgcolor=STAR_COLORS.get(r.star_grade, ft.colors.GREY_100),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border=ft.border.all(
                    2, ft.colors.AMBER_400
                ) if r.star_grade == 3 else None,
            )

        # ── 이벤트 핸들러 ────────────────────────────────────────────────────

        def on_banner_change(e) -> None:
            """배너 선택 변경"""
            state["banner_id"] = int(e.control.value)
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

        # 이벤트 연결
        banner_dropdown.on_change = on_banner_change
        claim_btn.on_click = on_claim

        # 초기 상태 로드
        refresh_stats()
        refresh_results()

        # ── 레이아웃 조립 ────────────────────────────────────────────────────
        return ft.Column([
            # 배너 선택
            ft.Row([banner_dropdown], alignment=ft.MainAxisAlignment.START),

            # 진행도 바
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("모집 진행도", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([progress_bar, progress_text], spacing=12),
                        ft.Row([stat_total, stat_star3, stat_to_pity], spacing=24),
                    ], spacing=8),
                    padding=16,
                )
            ),

            # 뽑기 버튼
            ft.Row([
                ft.ElevatedButton(
                    text="1회 뽑기",
                    icon=ft.icons.CASINO,
                    on_click=lambda e: on_pull(1),
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.BLUE_700,
                        color=ft.colors.WHITE,
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                ),
                ft.ElevatedButton(
                    text="10회 뽑기",
                    icon=ft.icons.CASINO,
                    on_click=lambda e: on_pull(10),
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.INDIGO_700,
                        color=ft.colors.WHITE,
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                ),
                claim_btn,
            ], spacing=12),

            ft.Divider(height=1),

            # 뽑기 결과 목록
            ft.Text("뽑기 결과", size=14, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=result_list,
                expand=True,
                border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                border_radius=8,
                padding=8,
            ),
        ], spacing=12, expand=True)

    return build
