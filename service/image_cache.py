"""
service/image_cache.py
SchaleDB 이미지 로컬 캐시 모듈

- 이미지를 data/images/{subdir}/{filename} 에 로컬 저장
- Flet Image 위젯용 경로 반환:
    - 캐시 있음  → file:///절대경로.webp  (Flet가 로컬 파일 로드)
    - 캐시 없음  → 원래 원격 URL 그대로   (Flet가 네트워크 로드)

[현재 상태]
실제 화면(views/*.py)에서는 ft.Image(src=원격 URL)을 직접 사용 중이며,
Flet/Flutter의 이미지 로더는 Referer 헤더 없이도 SchaleDB 이미지를 정상적으로
받아오는 것이 확인되어(Playwright로 직접 캡처해 검증함) 이 모듈은 아직 호출되지
않는다. urllib 같은 일반 HTTP 클라이언트로 직접 다운로드할 때는 Referer가
없으면 SchaleDB가 차단하므로, 추후 "이미지를 서버에서 미리 받아 로컬에
캐시해 두고 싶다"는 요구가 생기면(예: 오프라인 사용, 트래픽 절감) 그대로
꺼내 쓸 수 있도록 남겨 둔 유틸리티이다.
"""

import os
import urllib.request

CACHE_ROOT = os.path.join("data", "images")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://schaledb.com/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

# WebP 파일인지 확인하는 헤더 bytes
_VALID_IMAGE_HEADERS = [
    b"RIFF",    # WebP
    b"\x89PNG", # PNG
    b"\xff\xd8", # JPEG
    b"GIF8",    # GIF
]


def _is_valid_image(path: str) -> bool:
    """저장된 파일이 실제 이미지인지 확인 (HTML 에러 페이지 제외)"""
    if not os.path.exists(path) or os.path.getsize(path) < 100:
        return False
    with open(path, "rb") as f:
        header = f.read(4)
    return any(header.startswith(h) for h in _VALID_IMAGE_HEADERS)


def get_src(url: str | None) -> str | None:
    """
    Flet Image src 값 반환.
    - 로컬 캐시 유효: file:///절대경로
    - 캐시 없음/다운로드 실패: 원격 URL (Flet가 직접 로드)
    - URL None: None
    """
    if not url or not url.startswith("http"):
        return url

    parts = url.rstrip("/").split("/")
    filename = parts[-1]
    subdir = parts[-2]
    cache_dir = os.path.join(CACHE_ROOT, subdir)
    os.makedirs(cache_dir, exist_ok=True)
    local_path = os.path.join(cache_dir, filename)
    abs_path = os.path.abspath(local_path)

    # 유효한 이미지 캐시가 있으면 file:// URI 반환
    if _is_valid_image(abs_path):
        return f"file://{abs_path}"

    # 캐시 없으면 다운로드 시도
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        # 받은 데이터가 이미지인지 확인 (HTML 차단)
        if not any(data[:4].startswith(h) for h in _VALID_IMAGE_HEADERS):
            return url  # 이미지가 아님 → 원격 URL로 폴백
        with open(local_path, "wb") as f:
            f.write(data)
        return f"file://{abs_path}"
    except Exception:
        return url  # 실패 → 원격 URL로 폴백


# 하위 호환성 유지
def get_cached(url: str | None) -> str | None:
    return get_src(url)


def preload_icons(student_ids: list[int]) -> None:
    """학생 아이콘 일괄 사전 다운로드"""
    downloaded = 0
    for sid in student_ids:
        if not sid:
            continue
        url = f"https://schaledb.com/images/student/icon/{sid}.webp"
        result = get_src(url)
        if result and result.startswith("file://"):
            downloaded += 1
    print(f"[ImageCache] 아이콘 캐시 완료: {downloaded}개")
