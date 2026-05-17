# 블루아카이브 가챠 & 육성 시뮬레이터

> 데이터베이스 Term Project (2026-1 / 오병우 교수 / 2분반)

블루아카이브 학생 도감 조회, 가챠 시뮬레이션, 육성 비용 계산 기능을 제공하는 데스크탑 앱 설계서 및 구현 프로젝트.

## 기술 스택

| 역할 | 기술 |
|---|---|
| GUI | Python + Flet |
| DB | DuckDB |
| ERD | ERD Editor (Crow's Feet) |
| 데이터 수집 | SchaleDB API |

## 주요 기능

1. **학생 도감** — 260명 학생 정보 조회, 스킬·고유 무기·애용품 상세 팝업
2. **가챠 시뮬레이터** — 실제 게임 확률(3성 3%, 200회 천장) 기반 뽑기, 결과 DB 저장
3. **육성 시뮬레이터** — 현재/목표 수치 입력 시 필요 재화(크레딧·보고서·스킬 재료 등) 자동 계산

## DB 스키마 (7개 테이블)

```
student ──< student_image
student ──< skill
student ──< banner ──< gacha_pull >── student
student ──< cultivation
student ──< cultivation_goal
```

| 테이블 | 설명 |
|---|---|
| student | 학생 기본 정보 (SchaleDB에서 수집) |
| student_image | 학생 이미지 URL (초상화/아이콘/무기) |
| skill | 학생별 스킬 목록 |
| banner | 가챠 배너 (3성 학생 1명당 1개) |
| gacha_pull | 가챠 뽑기 기록 |
| cultivation | 보유 학생 현재 육성 현황 |
| cultivation_goal | 목표 육성 현황 |

## 파일 구조

```
.
├── 설계서_초안.md          # 설계서 마크다운 원본
├── BlueArchive.erd         # ERD Editor 다이어그램
├── fetch_students.py       # SchaleDB 학생 데이터 수집
├── fetch_config.py         # 가챠 설정·육성 비용 데이터 생성
└── data/
    ├── students.json       # 학생 데이터 (260명)
    ├── gacha_config.json   # 가챠 확률 설정
    ├── items.json          # 아이템/장비 데이터
    └── costs.json          # 육성 비용 테이블
```

## 데이터 수집

```bash
python fetch_students.py   # data/students.json 생성
python fetch_config.py     # data/gacha_config.json, items.json, costs.json 생성
```
