# 데이터베이스 과제02 - Term Project 설계서

## 과제 개요
좋아하는 주제에 대한 DB 설계서 + Flet 애플리케이션 설계서 작성

## 제출 방법
- hwp (또는 word) 파일로 LMS에 제출
- 첨부된 설계서 양식(`설계서양식(2026-05-12)01.hwp`) 사용

## 제한 요소
- **테이블 수**: 3개 이상 (Entity 2개 + Relationship 1개 이상)
- **JOIN**: 필수, 세 개 이상의 테이블 join (left join 권장)
- **기술 스택**: Flet (GUI) + DuckDB (DB)
- **ERD**: ERD Editor 사용, Crow's Feet Diagram 작성 (수업 시간 강의 방식)
- 수업 시간에 배운 내용 활용
- 동일한 스키마 → 모두 0점 처리 (반드시 직접 수정할 것)

## 설계서 구성 (샘플 기준)
1. 개요 (주제 설명, 목적)
2. 전체 구성도 (시스템 아키텍처)
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
8. 설계 구성 요소 및 제한 요소 충족 여부
9. 결론 및 자체 평가

## 샘플 참조 사항 (설계서샘플-데이터베이스.pdf)
- 샘플 주제: 헤븐 번즈 레드 게임 (캐릭터/스타일/부대 편성 관리)
- 샘플은 Spring Boot + MySQL 사용 → 이번 과제는 **Flet + DuckDB** 사용
- 샘플은 MySQL Workbench ERD → 이번 과제는 **ERD Editor (Crow's Feet)**
- 샘플의 구성(개요, Use Case, UI Design, ERD, SQL 스키마, Sequence Diagram) 참고

## 기술 스택
- GUI: **Flet** (Python)
- DB: **DuckDB**
- ERD Tool: **ERD Editor** (Crow's Feet 표기법)

## 스키마 핵심 결정 사항
- 스킬 컬럼명은 **한국어 인게임 명칭 기준**: `ex_skill`, `normal_skill`, `enhance_skill`, `sub_skill` (EX→기본→강화→서브 순)
- `cultivation` (현재 육성) / `cultivation_goal` (목표 육성) 분리 → LEFT JOIN으로 3테이블 JOIN 충족
- `gacha_pull`의 `is_pickup`은 저장하지 않음 (banner JOIN으로 도출 가능)
- `bond_rank` 범위: 1~100

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
