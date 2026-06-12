# 블루아카이브 가챠 & 육성 시뮬레이터

> 데이터베이스 Term Project (2026-1 / 오병우 교수 / 2분반)  
> 20210262 김우혁

블루아카이브 학생 도감 조회, 가챠 시뮬레이션, 육성 비용 계산 기능을 제공하는 데스크탑 앱.

## 기술 스택

| 역할 | 기술 |
|---|---|
| GUI | Python + Flet 0.85.3 |
| DB | DuckDB 1.5.3 |
| ERD | ERD Editor (Crow's Feet) |
| 데이터 수집 | SchaleDB API |
| 패키지 매니저 | uv |

## 주요 기능

1. **학생 도감** — 260명 학생 정보 조회, 스킬·고유 무기·애용품 상세 팝업
2. **가챠 시뮬레이터** — Nexon 공개 확률 기반(픽업 0.7%, 비픽업 캐릭터당 0.022772%, 200회 하드 파티) 뽑기, 결과 DB 저장
3. **육성 시뮬레이터** — 현재/목표 수치 입력 시 필요 재화(크레딧·스킬 재료·인연 선물) 자동 계산

## DB 스키마 (8개 테이블)

```
student ──< student_image
student ──  student_stat   (1:1, PK=FK)
student ──< skill
student ──< banner ──< gacha_pull >── student
student ──< cultivation
student ──< cultivation_goal
```

| 테이블 | 유형 | 설명 |
|---|---|---|
| student | Entity 1 | 학생 기본 정보 (SchaleDB에서 수집) |
| student_image | 약한 엔티티 | 학생 이미지 URL (초상화/아이콘/무기) |
| student_stat | 약한 엔티티 | 학생 기본 능력치 Lv.1/MAX |
| skill | 약한 엔티티 | 학생별 스킬 목록 (수치 파라미터 포함) |
| banner | Entity 2 | 가챠 배너 (3성 학생 1명당 1개) |
| gacha_pull | Relationship 1 | 가챠 뽑기 기록 |
| cultivation | Relationship 2 | 보유 학생 현재 육성 현황 |
| cultivation_goal | Relationship 3 | 목표 육성 현황 |

## 파일 구조

```
.
├── main.py                 # Entry Point
├── service/
│   ├── student_service.py
│   ├── gacha_service.py
│   └── cultivation_service.py
├── repository/
│   ├── interfaces.py
│   └── duckdb/
│       ├── connection.py
│       ├── student.py
│       ├── student_image.py
│       ├── student_stat.py
│       ├── skill.py
│       ├── banner.py
│       ├── gacha_pull.py
│       ├── cultivation.py
│       ├── cultivation_goal.py
│       └── join.py         # JOIN 전용 쿼리 (3+ 테이블)
├── views/
│   ├── student_view.py
│   ├── gacha_view.py
│   └── cultivation_view.py
├── data/
│   ├── students.json        # 학생 데이터 (260명)
│   ├── student_extras.json  # 학생 능력치·스킬 파라미터
│   ├── gacha_config.json    # 가챠 확률 설정
│   ├── items.json           # 아이템/장비 데이터
│   ├── costs.json           # 육성 비용 테이블
│   └── bluearchive.db       # DuckDB 데이터베이스
├── 설계서_초안.md            # 설계서 마크다운 원본
├── 최종보고서_초안.md         # 최종 결과 보고서 마크다운 원본
└── BlueArchive.erd          # ERD Editor 다이어그램
```

## 실행 방법

```bash
# 데이터 수집 (최초 1회)
uv run python fetch_students.py
uv run python fetch_extras.py
uv run python fetch_config.py

# 앱 실행
uv run flet run main.py
```

## 데이터 수집 스크립트

| 스크립트 | 생성 파일 | 내용 |
|---|---|---|
| `fetch_students.py` | `students.json` | SchaleDB 260명 학생 기본 정보·스킬·이미지 |
| `fetch_extras.py` | `student_extras.json` | 학생 능력치·스킬 파라미터 |
| `fetch_config.py` | `gacha_config.json`, `items.json`, `costs.json` | 가챠 설정·비용 테이블 |
