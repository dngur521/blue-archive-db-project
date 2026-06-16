"""
views/_helpers.py
Flet 뷰 3개(student_view, gacha_view, cultivation_view)가 공통으로 쓰는 유틸리티

[배경]
Flet 컨트롤은 아직 페이지(또는 부모 컨트롤)에 추가되기 전 상태에서 .update()를
호출하면 RuntimeError를 던진다. 이 프로젝트는 화면을 만들면서 동시에 초기 상태를
채워 넣는 패턴(예: build() 안에서 refresh_xxx()를 먼저 한 번 호출해 둠)을 쓰기
때문에, 컨트롤 갱신 직후 매번 "혹시 아직 마운트 전이면 무시" 처리가 필요하다.

리팩토링 전에는 student_view.py / gacha_view.py / cultivation_view.py 세 파일이
각자 똑같은 try/except RuntimeError 블록을 함수마다 반복해서 작성하고 있었다
(gacha_view.py만 해도 6곳, cultivation_view.py는 자체적으로 같은 기능의
_safe_update()를 따로 만들어 쓰고 있었음). 같은 로직이 세 군데에 흩어져 있으면
동작을 바꿀 때 세 곳을 다 고쳐야 하므로, 이 모듈 하나로 모았다.
"""

import flet as ft


def safe_update(*controls: ft.Control) -> None:
    """
    전달된 컨트롤들을 차례로 update() 시도한다.
    - None 이거나 아직 페이지에 마운트되지 않아 RuntimeError가 나는 컨트롤은
      조용히 무시하고 다음 컨트롤로 넘어간다.
    - 여러 컨트롤을 한 번에 넘길 수 있어 호출부가 짧아진다.
      예) safe_update(stat_total, stat_star3, progress_bar)
    """
    for ctrl in controls:
        if ctrl is None:
            continue
        try:
            ctrl.update()
        except RuntimeError:
            pass


def show_confirm_dialog(
    page: ft.Page,
    title: str,
    message: str,
    on_confirm,
    confirm_label: str = "확인",
) -> None:
    """
    "취소 / 확인" 2버튼 확인 모달(AlertDialog)을 띄운다.

    뽑기 기록 초기화, 육성 수치 초기화, 보유 학생 전체 초기화처럼 되돌릴 수 없는
    작업을 실행하기 전에 사용자 확인을 받는 용도. gacha_view.py와
    cultivation_view.py에서 거의 동일한 모달 코드가 3번 중복되어 있던 것을
    이 함수 하나로 모았다.

    Args:
        page: 다이얼로그를 띄울 Flet Page (page.overlay에 추가됨)
        title: 모달 제목
        message: 모달 본문 설명
        on_confirm: 확인 버튼 클릭 시 실행할 콜백 (인자 없이 호출됨).
            다이얼로그를 닫는 처리는 이 함수가 먼저 해주므로, on_confirm
            내부에서는 실제 처리(DB 삭제, 상태 초기화 등)만 작성하면 된다.
        confirm_label: 확인 버튼 텍스트 (기본값 "확인", 보통 "초기화" 등으로 지정)
    """

    def _confirm(e) -> None:
        dlg.open = False
        page.update()
        on_confirm()

    def _cancel(e) -> None:
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, weight=ft.FontWeight.BOLD),
        content=ft.Text(message, size=13),
        actions=[
            ft.TextButton("취소", on_click=_cancel),
            ft.ElevatedButton(
                confirm_label,
                on_click=_confirm,
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()
