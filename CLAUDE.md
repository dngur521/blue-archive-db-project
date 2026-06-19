# 데이터베이스 과제02 - Term Project 설계서

## 과제 개요
좋아하는 주제에 대한 DB 설계서 + Flet 애플리케이션 설계서 작성

## 제출 파일
1. **설계서** (`설계서.md`) → `설계서양식(2026-05-12)01.hwp` 양식으로 제출 완료
2. **최종 결과 보고서** (`최종보고서.md`) → `최종보고서양식(2026-06-03).pdf` 양식으로 제출 완료

## 제한 요소
- **테이블 수**: 3개 이상 (Entity 2개 + Relationship 1개 이상) → 현재 8개 테이블 충족
- **JOIN**: 필수, 세 개 이상의 테이블 join (left join 권장) → 4테이블 JOIN 충족
- **기술 스택**: Flet 0.85.3 (GUI) + DuckDB 1.5.3 (DB)
- **ERD**: ERD Editor 사용, Crow's Feet Diagram 작성 (수업 시간 강의 방식)
- 수업 시간에 배운 내용 활용
- 동일한 스키마 → 모두 0점 처리 (반드시 직접 수정할 것)

## 설계서 구성 (설계서양식 기준, 섹션 1~10)
1. 개요
2. 전체 구성도
3. Use Case / 요구사항 분석
4. UI Design (화면 설계)
5. Conceptual Design (ERD - Crow's Feet 방식)
6. Logical Design (DuckDB 스키마 SQL)
7. Sequence Diagram — Use Case와 1:1 대응
   - 7.1 (3.1) 학생 목록 조회 및 필터링
   - 7.2 (3.1.1) 학생 상세 정보 및 스킬 조회
   - 7.3 (3.2 / 3.2.1) 가챠 뽑기 실행 및 결과 저장
   - 7.4 (3.3) 보유 학생 현황 조회
   - 7.5 (3.3.1 / 3.3.2) 육성 목표 설정 및 비용 계산
8. Repository Interface 설계
9. 설계 구성 요소 및 제한 요소 충족 여부
10. 결론 및 자체 평가

## 최종 결과 보고서 구성 (최종보고서양식 기준)
0. 결과 요약 (SQL 3+ 테이블, JOIN, Flet GUI, Image 저장/출력, GitHub)
1. 서론
2. 작품 개요 (2.1 전체 구성도, 2.2 설계구성요소/제한요소)
3. 설계 (3.1 Use Case ~ 3.6 Repository Interface)
4. 구현 (각 Use Case별 핵심 코드 + 실행 화면 캡처)
5. 결론
6. 자체 분석과 평가
7. 부록 (전체 소스 코드 텍스트 형태로 첨부)

## 기술 스택
- GUI: **Flet 0.85.3** (Python)
- DB: **DuckDB 1.5.3**
- ERD Tool: **ERD Editor** (Crow's Feet 표기법)
- 패키지 매니저: **uv**

## 테이블 구성 (총 8개)

| 테이블 | 유형 |
|---|---|
| student | Entity 1 |
| student_image | 약한 엔티티 (student 종속) |
| student_stat | 약한 엔티티 (student 종속, 1:1, PK=FK) |
| skill | 약한 엔티티 (student 종속) |
| banner | Entity 2 |
| gacha_pull | Relationship 1 (banner↔student) |
| cultivation | Relationship 2 (student 1:0..1) |
| cultivation_goal | Relationship 3 (student 1:0..1) |

## 스키마 핵심 결정 사항
- 스킬 컬럼명은 **한국어 인게임 명칭 기준**: `ex_skill`, `normal_skill`, `enhance_skill`, `sub_skill` (EX→기본→강화→서브 순)
- `cultivation` (현재 육성) / `cultivation_goal` (목표 육성) 분리 → LEFT JOIN으로 4테이블 JOIN 충족
- `gacha_pull`의 `is_pickup`은 저장하지 않음 (banner JOIN으로 도출 가능)
- `bond_rank` 범위: **1~50** (costs.json 실제 데이터 기준; 설계 시 100으로 설계했으나 수정)
- `weapon_name`, `gear_name`에 **UNIQUE 제약 없음** (코스튬 학생이 원본과 동일 무기명 공유)
- `student_stat`: SchaleDB `student_extras.json`에서 수집, FK=PK 구조로 student와 1:1
- `skill` 테이블: `params_lv1`, `params_max` 컬럼에 `<?N>` 플레이스홀더 수치 JSON 저장
- DB 파일 경로: `data/bluearchive.db`

## 가챠 확률 (Nexon 공개 확률표 기준)
- **픽업 3성**: 0.700000%
- **비픽업 3성**: 캐릭터당 0.022772% × 풀 크기 (동적 계산)
- **2성**: 캐릭터당 0.804348% × 풀 크기 (동적 계산)
- **소프트 파티**: **없음** (블루아카이브는 소프트 파티 미적용)
- **10회 보장**: 2성 이상 확정
- **200회 하드 파티**: 픽업 학생 확정

## 샘플 참조 사항 (설계서샘플-데이터베이스.pdf)
- 샘플 주제: 헤븐 번즈 레드 게임 (캐릭터/스타일/부대 편성 관리)
- 샘플은 Spring Boot + MySQL → 이번 과제는 **Flet + DuckDB**
- 샘플은 MySQL Workbench ERD → 이번 과제는 **ERD Editor (Crow's Feet)**

## 커밋 메시지 규칙
이모지 + Conventional Commit 형식 사용:

| 이모지 | 타입 | 용도 |
|---|---|---|
| ✨ | feat | 새 기능 |
| 🐛 | fix | 버그 수정 |
| 📝 | docs | 문서 수정 |
| 🗃️ | db | DB 스키마/ERD 변경 |
| ♻️ | refactor | 리팩토링 |
| 🔧 | chore | 설정/기타 |

예시: `✨ feat: 가챠 시뮬레이터 서비스 레이어 구현`

## 주의사항
- AI로 생성한 스키마를 그대로 사용하지 말 것 (반드시 수정)
- 다른 학생과 동일한 스키마 → 0점
