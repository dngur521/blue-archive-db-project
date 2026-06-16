"""
SchaleDB 블루아카이브 학생 데이터 수집 스크립트 (한국어)
- /data/kr/students.min.json : 이름/스킬/무기/애용품 등 한국어 텍스트
- /data/kr/localization.min.json : 학교/동아리/타입 코드 → 한국어 매핑
저장 형식: data/students.json
"""

import json
import os
import urllib.request

BASE = "https://schaledb.com/data/kr"

def fetch_json(url: str) -> dict:
    """주어진 URL에서 JSON을 GET으로 받아 dict로 반환.
    SchaleDB는 User-Agent 헤더가 없는 요청을 차단하므로 브라우저처럼 위장한다."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

# 스킬 타입 코드 → 한국어 레이블
SKILL_LABEL = {
    "Ex":            "EX스킬",
    "Normal":        "기본스킬",
    "Passive":       "서브스킬",
    "Public":        "강화스킬",
    "ExtraPassive":  "서브스킬2",
    "GearPublic":    "강화스킬(애용품)",
    "WeaponPassive": "서브스킬(무기)",
}

# 포지션 코드 → 한국어
POSITION_KR = {
    "Front":  "전열",
    "Middle": "중열",
    "Back":   "후열",
}

SKILL_ICON_BASE = "https://schaledb.com/images/skill"

def parse_skills(raw_skills: dict) -> dict:
    """
    스킬 정보 파싱 (이름/설명/아이콘 URL)
    - Icon 필드는 SchaleDB가 실제 게임에서 쓰는 스킬 효과 분류 아이콘 코드
      (예: COMMON_SKILLICON_CIRCLE, COMMON_SKILLICON_HEAL ...).
      캐릭터마다 고유한 그림은 아니지만 인게임과 동일한 실제 아이콘 자산이다.
    - URL: https://schaledb.com/images/skill/{Icon}.webp (대소문자 그대로 유지해야 함)
    """
    if not raw_skills or not isinstance(raw_skills, dict):
        return {}
    result = {}
    for sk_type, skill_data in raw_skills.items():
        label = SKILL_LABEL.get(sk_type, sk_type)
        if isinstance(skill_data, dict):
            icon = skill_data.get("Icon")
            result[label] = {
                "name": skill_data.get("Name", ""),
                "desc": skill_data.get("Desc", ""),
                "icon": f"{SKILL_ICON_BASE}/{icon}.webp" if icon else None,
            }
    return result

def parse_student(sid: str, raw: dict, loc: dict) -> dict:
    """
    SchaleDB 학생 원본 데이터(raw) 1명을 우리 스키마에 맞는 dict로 변환.

    Args:
        sid: 학생 고유 ID (문자열, students.min.json의 key)
        raw: students.min.json에서 해당 학생의 원본 JSON 객체
        loc: localization.min.json 전체 (학교/동아리/타입 코드 → 한국어 매핑)

    Returns: data/students.json에 그대로 저장될 학생 1명 dict
             (기본 정보 + 전투 정보 + 스킬 + 무기/애용품 + 프로필)
    """
    # ── 로컬라이즈 테이블 단축 참조 ────────────────────────────
    school_kr     = loc.get("School", {})
    school_long   = loc.get("SchoolLong", {})
    club_kr       = loc.get("Club", {})
    armor_kr      = loc.get("ArmorType", {})
    bullet_kr     = loc.get("BulletType", {})
    tactic_kr     = loc.get("TacticRole", {})
    adapt_kr      = loc.get("AdaptationType", {})
    weapon_type_kr = {
        "SG": "산탄총", "SMG": "기관단총", "AR": "돌격소총",
        "GL": "유탄발사기", "HG": "권총", "SR": "저격소총",
        "RG": "철도포", "MG": "기관총", "MT": "박격포", "FT": "화염방사기",
    }

    # ── 기본 정보 ────────────────────────────────────────────
    name        = raw.get("Name", "")
    family      = raw.get("FamilyName", "")
    full_name   = f"{family} {name}".strip() if family else name
    star_grade  = raw.get("StarGrade", 0)
    path_name   = raw.get("PathName", "")   # 영문 고유 ID용 (이미지 경로 등)

    # ── 전투 정보 ────────────────────────────────────────────
    weapon_code  = raw.get("WeaponType", "")
    armor_code   = raw.get("ArmorType", "")
    tactic_code  = raw.get("TacticRole", "")
    position_code = raw.get("Position", "")
    bullet_code  = raw.get("BulletType", "")

    weapon_type = weapon_type_kr.get(weapon_code, weapon_code)
    armor_type  = armor_kr.get(armor_code, armor_code)
    tactic_role = tactic_kr.get(tactic_code, tactic_code)
    position    = POSITION_KR.get(position_code, position_code)
    bullet_type = bullet_kr.get(bullet_code, bullet_code)   # 공격 속성

    # 지형 적응도
    adapt_street  = raw.get("StreetBattleAdaptation", 0)
    adapt_outdoor = raw.get("OutdoorBattleAdaptation", 0)
    adapt_indoor  = raw.get("IndoorBattleAdaptation", 0)
    adapt_label   = {0: "D", 1: "D", 2: "C", 3: "B", 4: "A", 5: "S", 6: "SS"}
    terrain = {
        "시가지": adapt_label.get(adapt_street, str(adapt_street)),
        "야외":   adapt_label.get(adapt_outdoor, str(adapt_outdoor)),
        "실내":   adapt_label.get(adapt_indoor, str(adapt_indoor)),
    }

    # ── 스킬 ────────────────────────────────────────────────
    skills = parse_skills(raw.get("Skills", {}))

    # ── 고유 무기 ────────────────────────────────────────────
    weapon_info = raw.get("Weapon", {}) or {}
    weapon_name = weapon_info.get("Name", "")
    weapon_desc = weapon_info.get("Desc", "")
    weapon_adapt_code = weapon_info.get("AdaptationType", "")
    weapon_adapt = adapt_kr.get(weapon_adapt_code, weapon_adapt_code)

    # ── 스킬 재료 (레벨 2~10, 8단계 / EX는 2~5, 4단계) ──────
    skill_mat      = raw.get("SkillMaterial", [])        # [[itemId,...], ...]
    skill_mat_amt  = raw.get("SkillMaterialAmount", [])
    skill_ex_mat   = raw.get("SkillExMaterial", [])
    skill_ex_amt   = raw.get("SkillExMaterialAmount", [])

    def zip_mat(ids_list, amt_list):
        """레벨별 [아이템ID 목록]과 [수량 목록]을 한 쌍으로 묶어
        [[{"item_id":.., "amount":..}, ...], ...] 형태로 변환.
        예: ids_list[0]=[1,2], amt_list[0]=[3,4] (Lv1→2 재료)
            → result[0]=[{"item_id":1,"amount":3}, {"item_id":2,"amount":4}]"""
        result = []
        for ids, amts in zip(ids_list, amt_list):
            result.append([{"item_id": i, "amount": a} for i, a in zip(ids, amts)])
        return result

    skill_upgrade_cost = zip_mat(skill_mat, skill_mat_amt)
    ex_upgrade_cost    = zip_mat(skill_ex_mat, skill_ex_amt)

    # ── 애용품 ──────────────────────────────────────────────
    gear_info     = raw.get("Gear", {}) or {}
    gear_name     = gear_info.get("Name", "")
    gear_desc     = gear_info.get("Desc", "")
    gear_released = gear_info.get("Released", [False])
    has_gear      = bool(gear_name and any(gear_released))
    gear_tier_mat = zip_mat(
        gear_info.get("TierUpMaterial", []),
        gear_info.get("TierUpMaterialAmount", [])
    )

    # ── 프로필 ──────────────────────────────────────────────
    school_code = raw.get("School", "")
    club_code   = raw.get("Club", "")

    school      = school_kr.get(school_code, school_code)
    school_full = school_long.get(school_code, school_code)
    club        = club_kr.get(club_code, club_code)
    school_year = raw.get("SchoolYear", "")
    voice       = raw.get("CharacterVoice", "")
    birthday    = raw.get("Birthday", "") or raw.get("BirthDay", "")
    age         = raw.get("CharacterAge", "")
    height      = raw.get("CharHeightMetric", "")
    hobby       = raw.get("Hobby", "")
    designer    = raw.get("Designer", "")
    illustrator = raw.get("Illustrator", "")
    # IsLimited는 [JP, Global, KR] 리스트. 첫 번째 값을 대표값으로 사용
    is_limited_raw = raw.get("IsLimited", 0)
    is_limited_val = is_limited_raw[0] if isinstance(is_limited_raw, list) else is_limited_raw
    limited_label_loc = loc.get("IsLimitedFilter", {})
    is_limited = limited_label_loc.get(str(is_limited_val), str(is_limited_val))

    return {
        "id":          int(sid),
        "path_name":   path_name,          # 영문 식별자 (이미지 URL 등에 사용)
        "name":        name,
        "family_name": family,
        "full_name":   full_name,
        "star_grade":  star_grade,
        "is_limited":  is_limited,

        "weapon_type": weapon_type,        # 무기 종류 (한국어)
        "weapon_type_code": weapon_code,   # 원본 코드 (SR/SG 등)
        "armor_type":  armor_type,         # 장갑 종류 (한국어)
        "tactic_role": tactic_role,        # 전술 역할 (한국어)
        "position":    position,           # 포지션 (한국어)
        "bullet_type": bullet_type,        # 공격 속성 (한국어)
        "terrain":     terrain,            # 지형 적응도

        "skills": skills,

        "weapon": {
            "name":           weapon_name,
            "desc":           weapon_desc,
            "adapt":          weapon_adapt,
            "stat_level_type": weapon_info.get("StatLevelUpType", "Standard"),
        },

        # 스킬 업그레이드 재료 (index 0 = Lv1→2)
        "skill_upgrade_cost": skill_upgrade_cost,   # 일반/강화/서브 공통, 8단계
        "ex_upgrade_cost":    ex_upgrade_cost,       # EX 스킬, 4단계

        "has_gear":       has_gear,
        "gear_name":      gear_name,
        "gear_desc":      gear_desc,
        "gear_tier_cost": gear_tier_mat,            # 애용품 티어업 재료 (최대 3단계)

        "profile": {
            "school":       school,
            "school_full":  school_full,
            "club":         club,
            "school_year":  school_year,
            "voice":        voice,
            "birthday":     birthday,
            "age":          age,
            "height":       height,
            "hobby":        hobby,
            "designer":     designer,
            "illustrator":  illustrator,
        },
    }

def main():
    """
    실행 흐름:
      1) SchaleDB에서 학생 원본 데이터 + 로컬라이즈 테이블을 받아온다
      2) 학생별로 parse_student()를 돌려 우리 스키마 dict로 변환
      3) ID 순으로 정렬 후 data/students.json에 저장
      4) 확인용으로 상위 3명 샘플을 콘솔에 출력
    """
    print("SchaleDB 한국어 학생 데이터 수집 시작...")

    print(f"  GET {BASE}/students.min.json")
    raw_data = fetch_json(f"{BASE}/students.min.json")
    print(f"  총 {len(raw_data)}명 학생 발견")

    print(f"  GET {BASE}/localization.min.json")
    loc = fetch_json(f"{BASE}/localization.min.json")

    students = []
    for sid, raw in raw_data.items():
        try:
            students.append(parse_student(sid, raw, loc))
        except Exception as e:
            print(f"  [경고] ID {sid} 파싱 오류: {e}")

    students.sort(key=lambda s: s["id"])

    output = {
        "meta": {
            "source":   "https://schaledb.com",
            "language": "한국어",
            "total":    len(students),
        },
        "students": students,
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/students.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {out_path}")
    print(f"총 {len(students)}명 수집됨")

    # 샘플 3명 출력
    for s in students[:3]:
        print(f"\n{'='*50}")
        print(f"[{s['id']}] {s['full_name']} ({s['star_grade']}성 / {s['is_limited']})")
        print(f"  무기: {s['weapon_type']}({s['weapon_type_code']})  장갑: {s['armor_type']}  역할: {s['tactic_role']}  포지션: {s['position']}")
        print(f"  공격속성: {s['bullet_type']}  지형: {s['terrain']}")
        print(f"  고유무기: {s['weapon']['name']}")
        print(f"  애용품: {'O - ' + s['gear_name'] if s['has_gear'] else 'X'}")
        p = s['profile']
        print(f"  소속: {p['school_full']} / {p['club']} / {p['school_year']}")
        print(f"  성우: {p['voice']}  생일: {p['birthday']}  나이: {p['age']}  키: {p['height']}")
        print(f"  취미: {p['hobby']}")
        print(f"  스킬: {list(s['skills'].keys())}")

if __name__ == "__main__":
    main()
