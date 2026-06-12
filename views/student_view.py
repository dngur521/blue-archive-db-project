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

from service.student_service import StudentService

SCHALEDB = "https://schaledb.com/images/student"


def create_student_view(service: StudentService) -> ft.Control:
    """
    학생 도감 탭 컨트롤 생성
    - service를 통해 학생 목록 및 상세 정보 조회
    """

    # ── 필터 상태 ────────────────────────────────────────────────────────────
    filter_state = {
        "star": None,  # 성급 필터 (None = 전체)
        "school": None,  # 학교 필터
        "role": None,  # 역할 필터
        "keyword": "",  # 검색어
    }

    # ── 학생 목록 ListView ───────────────────────────────────────────────────
    student_list = ft.ListView(
        expand=True,
        spacing=4,
        padding=ft.Padding(right=8),
    )

    # ── 상세 정보 패널 (우측) ────────────────────────────────────────────────
    detail_image = ft.Image(
        src="https://schaledb.com/images/common/default.webp",
        width=180,
        height=180,
        fit="contain",
        border_radius=8,
        error_content=ft.Icon(ft.Icons.PERSON, size=80, color=ft.Colors.GREY_400),
    )

    detail_name = ft.Text("학생을 선택하세요", size=20, weight=ft.FontWeight.BOLD)
    detail_school = ft.Text("", size=13, color=ft.Colors.GREY_600)
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
        import json as _json
        import re as _re

        df = service.get_student_detail(student_id)
        if df.empty:
            return

        s = df.iloc[0]
        sid = s.get("id")

        # 초상화 이미지: DB의 student_image 테이블에서 URL 조회
        collection_url = service.get_collection_image_url(int(sid)) if sid else None
        if collection_url:
            detail_image.src = collection_url
        detail_image.update()

        detail_name.value = str(s.get("full_name", ""))
        detail_school.value = (
            f"{s.get('school', '')}  ·  {s.get('club', '')}  ·  "
            f"{s.get('school_year', '')}"
        )

        # ── 능력치 (student_stat 테이블) ────────────────────────────────────
        st = service.get_student_stat(int(sid)) if sid else None
        stat_row = ft.Column([], spacing=4)

        if st is not None:
            # 스탯 텍스트 컨트롤 (토글 시 값 갱신)
            hp_val   = ft.Text(f"{int(st['max_hp_1']):,}", size=12, weight=ft.FontWeight.W_500)
            atk_val  = ft.Text(f"{int(st['atk_1']):,}",   size=12, weight=ft.FontWeight.W_500)
            def_val  = ft.Text(f"{int(st['def_1']):,}",   size=12, weight=ft.FontWeight.W_500)
            heal_val = ft.Text(f"{int(st['heal_1']):,}",  size=12, weight=ft.FontWeight.W_500)

            btn_st_lv1 = ft.TextButton(
                "Lv.1", style=ft.ButtonStyle(color=ft.Colors.BLUE_700)
            )
            btn_st_max = ft.TextButton(
                "MAX", style=ft.ButtonStyle(color=ft.Colors.GREY_400)
            )

            def _update_stat(mode: int):
                hp_val.value   = f"{int(st['max_hp_1' if mode == 0 else 'max_hp_max']):,}"
                atk_val.value  = f"{int(st['atk_1'   if mode == 0 else 'atk_max']):,}"
                def_val.value  = f"{int(st['def_1'   if mode == 0 else 'def_max']):,}"
                heal_val.value = f"{int(st['heal_1'  if mode == 0 else 'heal_max']):,}"
                btn_st_lv1.style = ft.ButtonStyle(
                    color=ft.Colors.BLUE_700 if mode == 0 else ft.Colors.GREY_400
                )
                btn_st_max.style = ft.ButtonStyle(
                    color=ft.Colors.AMBER_800 if mode == 1 else ft.Colors.GREY_400
                )
                try:
                    hp_val.update(); atk_val.update()
                    def_val.update(); heal_val.update()
                    btn_st_lv1.update(); btn_st_max.update()
                except RuntimeError:
                    pass

            btn_st_lv1.on_click = lambda e: _update_stat(0)
            btn_st_max.on_click = lambda e: _update_stat(1)

            def _sc(label, val_ctrl):
                return ft.Column(
                    [ft.Text(label, size=10, color=ft.Colors.GREY_600), val_ctrl],
                    spacing=0,
                )

            stat_row.controls = [
                ft.Row([btn_st_lv1, btn_st_max], spacing=0),
                ft.Row(
                    [
                        _sc("최대체력", hp_val),
                        _sc("공격력",   atk_val),
                        _sc("방어력",   def_val),
                        _sc("치유력",   heal_val),
                    ],
                    spacing=20,
                    wrap=True,
                ),
            ]

        # ── 기본 정보 ────────────────────────────────────────────────────────
        detail_info.controls = [
            stat_row,
            ft.Divider(height=1),
            _info_row("무기", str(s.get("weapon_type_code", ""))),
            _info_row("장갑", str(s.get("armor_type", ""))),
            _info_row("역할", str(s.get("tactic_role", ""))),
            _info_row("위치", str(s.get("position", ""))),
            _info_row("속성", str(s.get("bullet_type", ""))),
            _info_row(
                "지형",
                (
                    f"시가지 {s.get('terrain_street', '?')}  "
                    f"야외 {s.get('terrain_outdoor', '?')}  "
                    f"실내 {s.get('terrain_indoor', '?')}"
                ),
            ),
            ft.Divider(height=1),
            _info_row("고유무기", str(s.get("weapon_name", ""))),
            _info_row("애용품", str(s.get("gear_name", "-") or "-")),
            ft.Divider(height=1),
            _info_row("성우", str(s.get("voice", ""))),
            _info_row("생일", str(s.get("birthday", ""))),
            _info_row("나이", str(s.get("age", ""))),
            _info_row("키", str(s.get("height", ""))),
            _info_row("취미", str(s.get("hobby", ""))),
        ]

        # ── 스킬 버튼 ────────────────────────────────────────────────────────
        skill_buttons.controls = []

        # DB 타입 → 인게임 표시명 (normal_skill 자동공격은 숨김)
        skill_type_labels = {
            "ex_skill":      "EX",
            "enhance_skill": "기본",   # Public = 인게임 기본 스킬
            "sub_skill":     "강화",   # Passive = 인게임 강화 스킬
            "extra_skill":   "서브",   # ExtraPassive = 인게임 서브 스킬
        }

        # 영문 게임 태그 → 한국어 번역
        _STAT_TAG_KR = {
            "CriticalDamage":      "치명 대미지",
            "CriticalChance":      "치명률",
            "CriticalPoint":       "치명률",
            "DamagedRatio":        "받는 피해량",
            "AttackPower":         "공격력",
            "MaxHP":               "최대 체력",
            "DefensePower":        "방어력",
            "HealPower":           "치유력",
            "BlockRate":           "방어 관통",
            "Evasion":             "회피",
            "StabilityPoint":      "안정감",
            "AttackSpeed":         "공격 속도",
            "NormalAttackSpeed":   "기본 공격 속도",
            "Range":               "사거리",
            "Speed":               "이동 속도",
            "AmmoCount":           "탄약 수",
            "AccumulationDamage":  "누적 대미지",
            "CostChange":          "코스트",
            "EnhanceSonicRate":    "강화 비율",
            "DefensePenetration":  "방어 무시",
            "ReloadTime":          "재장전 시간",
            "SkillDamage":         "스킬 대미지",
        }

        def _resolve_params(desc: str, params_json: str | None) -> str:
            """영문 태그 번역 + <?N> 수치 치환
            순서: ①<?N> 치환 → ②<b:Tag> 번역 → ③나머지 태그 제거
            <?N>을 먼저 치환해야 <[^>]+> 정리 시 사라지지 않음
            """
            if not desc:
                return desc
            # ① <?N> 수치 치환 (params 있을 때만)
            if params_json:
                try:
                    params = _json.loads(params_json)
                    for i, val in enumerate(params):
                        desc = desc.replace(f"<?{i + 1}>", str(val))
                except Exception:
                    pass
            # ② <b:TagName> → 한국어
            desc = _re.sub(
                r"<b:([^>]+)>",
                lambda m: _STAT_TAG_KR.get(m.group(1), m.group(1)),
                desc,
            )
            # ③ 나머지 <...> 태그 제거
            desc = _re.sub(r"<[^>]+>", "", desc)
            return desc

        for _, row in df.iterrows():
            sk_type = str(row.get("skill_type", ""))
            if sk_type not in skill_type_labels:
                continue  # normal_skill(자동공격) 숨김

            sk_label = skill_type_labels[sk_type]
            sk_name  = str(row.get("skill_name", "") or "")
            sk_desc  = str(row.get("skill_desc", "") or "")
            p_lv1    = row.get("params_lv1")
            p_max    = row.get("params_max")

            p_lv1_str = p_lv1 if isinstance(p_lv1, str) else None
            p_max_str = p_max if isinstance(p_max, str) else None

            desc_lv1 = _resolve_params(sk_desc, p_lv1_str)
            desc_max = _resolve_params(sk_desc, p_max_str)

            def make_skill_handler(label, name, d1, dm):
                def handler(e):
                    state_mode = {"v": 0}  # 0=Lv.1, 1=MAX

                    content_text = ft.Text(
                        d1 if d1 else "(설명 없음)", size=12,
                    )
                    has_toggle = bool(d1 and dm and d1 != dm)

                    btn_lv1 = ft.TextButton(
                        "Lv.1",
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_700),
                    )
                    btn_max = ft.TextButton(
                        "MAX",
                        style=ft.ButtonStyle(color=ft.Colors.GREY_400),
                    )

                    def _switch(mode: int):
                        state_mode["v"] = mode
                        content_text.value = (d1 if mode == 0 else dm) or "(설명 없음)"
                        btn_lv1.style = ft.ButtonStyle(
                            color=ft.Colors.BLUE_700 if mode == 0 else ft.Colors.GREY_400
                        )
                        btn_max.style = ft.ButtonStyle(
                            color=ft.Colors.AMBER_800 if mode == 1 else ft.Colors.GREY_400
                        )
                        try:
                            content_text.update()
                            btn_lv1.update()
                            btn_max.update()
                        except RuntimeError:
                            pass

                    btn_lv1.on_click = lambda e: _switch(0)
                    btn_max.on_click = lambda e: _switch(1)

                    toggle_row = (
                        ft.Row([btn_lv1, btn_max], spacing=0)
                        if has_toggle
                        else ft.Row([ft.Text(
                            "Lv.1", size=11, color=ft.Colors.GREY_700,
                            weight=ft.FontWeight.BOLD,
                        )])
                    )

                    dlg = ft.AlertDialog(
                        title=ft.Text(
                            f"[{label}] {name}", weight=ft.FontWeight.BOLD,
                        ),
                        content=ft.Container(
                            content=ft.Column(
                                [toggle_row, ft.Divider(height=6), content_text],
                                spacing=4,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            width=320,
                            height=160,
                        ),
                        actions=[
                            ft.TextButton(
                                "닫기",
                                on_click=lambda e: close_dlg(e, dlg, page),
                            )
                        ],
                    )
                    page.overlay.append(dlg)
                    dlg.open = True
                    page.update()

                return handler

            btn_color = {
                "EX":   ft.Colors.DEEP_PURPLE_700,
                "기본": ft.Colors.BLUE_700,
                "강화": ft.Colors.GREEN_700,
                "서브": ft.Colors.ORANGE_700,
            }.get(sk_label, ft.Colors.BLUE_700)

            skill_buttons.controls.append(
                ft.ElevatedButton(
                    sk_label,
                    on_click=make_skill_handler(sk_label, sk_name, desc_lv1, desc_max),
                    style=ft.ButtonStyle(
                        bgcolor=btn_color,
                        color=ft.Colors.WHITE,
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                    ),
                )
            )

        detail_name.update()
        detail_school.update()
        skill_buttons.update()
        detail_info.update()

    def _info_row(label: str, value: str) -> ft.Control:
        """라벨-값 쌍을 표시하는 Row 위젯"""
        return ft.Row(
            [
                ft.Text(label, size=12, color=ft.Colors.GREY_600, width=60),
                ft.Text(value, size=12, expand=True),
            ],
            spacing=8,
        )

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
            # 아이콘 이미지: DB에 저장된 ID 기반 URL 직접 사용
            icon_url = str(row.get("icon_url", "")) or None
            stars_str = "★" * star

            # 성급별 색상
            star_color = {3: ft.Colors.YELLOW_700, 2: ft.Colors.ORANGE_400}.get(
                star, ft.Colors.ORANGE_300
            )

            def make_card_handler(student_id):
                def handler(e):
                    update_detail(student_id, page)

                return handler

            card = ft.Container(
                content=ft.Row(
                    [
                        # 아이콘 이미지
                        ft.Image(
                            src=icon_url
                            or "https://schaledb.com/images/common/default.webp",
                            width=40,
                            height=40,
                            fit="cover",
                            border_radius=20,
                            error_content=ft.Icon(ft.Icons.PERSON, size=24),
                        ),
                        # 이름 + 성급
                        ft.Column(
                            [
                                ft.Text(name, size=13, weight=ft.FontWeight.W_500),
                                ft.Text(
                                    stars_str + f"  {role}",
                                    size=11,
                                    color=star_color,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                border_radius=6,
                ink=True,
                on_click=make_card_handler(sid),
                bgcolor=ft.Colors.SURFACE_CONTAINER,
            )
            student_list.controls.append(card)

        try:
            student_list.update()
        except RuntimeError:
            pass

    # ── 필터 컨트롤 생성 ─────────────────────────────────────────────────────

    def build_filters(page: ft.Page) -> ft.Row:
        """검색 바 + 필터 드롭다운 Row 생성"""
        schools = ["전체"] + service.get_schools()
        roles = ["전체"] + service.get_roles()
        stars = ["전체", "3성", "2성", "1성"]

        search = ft.TextField(
            hint_text="이름 검색...",
            expand=True,
            height=38,
            content_padding=ft.Padding(left=10, right=10, top=4, bottom=4),
            on_change=lambda e: (
                filter_state.update(keyword=e.control.value),
                refresh_list(page),
            ),
        )

        def make_dropdown(options: list[str], key: str, none_val):
            def on_change(e):
                v = e.control.value
                filter_state[key] = (
                    None if v == "전체" else (int(v[0]) if key == "star" else v)
                )
                refresh_list(page)

            return ft.Dropdown(
                options=[ft.dropdown.Option(o) for o in options],
                value="전체",
                width=110,
                height=38,
                content_padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                on_select=on_change,
            )

        return ft.Row(
            [
                search,
                make_dropdown(schools, "school", None),
                make_dropdown(roles, "role", None),
                make_dropdown(stars, "star", None),
            ],
            spacing=8,
        )

    # ── 탭 전체 레이아웃 조립 ───────────────────────────────────────────────

    def build(page: ft.Page) -> ft.Control:
        filters = build_filters(page)
        refresh_list(page)

        return ft.Column(
            [
                filters,
                ft.Row(
                    [
                        # 좌측: 학생 목록
                        ft.Container(
                            content=student_list,
                            width=240,
                            expand=False,
                            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                            border_radius=8,
                            padding=4,
                        ),
                        # 우측: 상세 정보
                        ft.Container(
                            content=detail_panel,
                            expand=True,
                            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                            border_radius=8,
                            padding=12,
                        ),
                    ],
                    expand=True,
                    spacing=8,
                ),
            ],
            expand=True,
            spacing=8,
        )

    # build 함수를 호출하는 래퍼 (Page 접근이 필요해서 지연 생성)
    # main.py에서 page를 넘겨서 생성
    return build
