"""
보조 데이터 수집 스크립트
저장 파일:
  data/items.json       - 아이템 ID → 이름/카테고리
  data/gacha_config.json - 가챠 확률 설정
  data/costs.json       - 하드코딩 육성 비용 테이블
"""

import json, os, urllib.request

BASE = "https://schaledb.com/data/kr"

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

# ── 1. 아이템 데이터 ─────────────────────────────────────────
def build_items():
    print("  GET items.min.json")
    raw = fetch_json(f"{BASE}/items.min.json")
    print("  GET equipment.min.json")
    equip = fetch_json(f"{BASE}/equipment.min.json")

    # 아이템 (items.min.json)
    items = {}
    for iid, item in raw.items():
        items[int(iid)] = {
            "id":       int(iid),
            "name":     item.get("Name", ""),
            "category": item.get("Category", ""),
            "rarity":   item.get("Rarity", ""),
            "exp_value": item.get("ExpValue", 0),   # 활동 보고서·선물 경험치
        }

    # 장비 (equipment.min.json) — 고유 무기 강화 재료 포함
    equip_items = {}
    for eid, eq in equip.items():
        equip_items[int(eid)] = {
            "id":             int(eid),
            "name":           eq.get("Name", ""),
            "category":       eq.get("Category", ""),
            "rarity":         eq.get("Rarity", ""),
            "level_up_feed_exp": eq.get("LevelUpFeedExp", 0),
        }

    return {"items": items, "equipment": equip_items}

# ── 2. 가챠 확률 설정 ────────────────────────────────────────
def build_gacha_config(students):
    """
    실제 블루아카이브 가챠 확률 구조 (Nexon 공식 확률표 기준)
    풀 구성: is_limited == '통상' 학생만

    ※ 확률은 매 뽑기 고정 (소프트 파티 없음).
      여기 적힌 per_student 값은 service/gacha_service.py의
      _gacha_algorithm() 하드코딩 상수와 반드시 일치시킬 것.
      (과거 소프트 파티 설계의 잔재인 tenth_pull/soft_pity 확률표는
       실제 알고리즘에서 사용하지 않으므로 제거함 — 횟수가 늘어도
       확률이 올라가지 않는다.)
    """
    pool = {1: [], 2: [], 3: []}
    for s in students:
        if s["is_limited"] == "통상":
            pool[s["star_grade"]].append(s["id"])

    n3 = len(pool[3])   # 106명
    n2 = len(pool[2])   # 23명
    n1 = len(pool[1])   # 11명

    return {
        "pickup_rate": 0.7,                    # 픽업 학생 고정 확률 (%)
        "non_pickup_3star_per_student": 0.022772,  # Nexon 공식 확률표 (고정값)
        "2star_per_student": 0.804348,             # Nexon 공식 확률표 (고정값)

        "hard_pity": 200,             # 200회 → 픽업 학생 확정
        "tenth_pull_guarantee": "2성 이상 확정 (별도 확률표 없음, 매 뽑기 확률 고정)",

        "pool_sizes": {
            "3성_통상": n3,
            "2성_통상": n2,
            "1성_통상": n1,
        },
        "pool_ids": {
            "3성": pool[3],
            "2성": pool[2],
            "1성": pool[1],
        },

        "note": (
            "확률은 매 뽑기 고정이며 누적 뽑기 횟수에 따라 변하지 않음(소프트 파티 없음). "
            "한정/페스/아카이브 학생은 배너 픽업 시에만 등장. "
            "배포 학생은 가챠 풀 미포함."
        ),
    }

# ── 3. 하드코딩 육성 비용 테이블 ─────────────────────────────
def build_costs():
    """
    SchaleDB API에 없는 비용 데이터.
    블루아카이브 공식 인게임 수치 기반.
    """

    # 캐릭터 레벨업 누적 경험치 (Lv1 기준 0, Lv2까지 필요 EXP...)
    # 활동 보고서 EXP: 초급 50 / 일반 500 / 상급 2000 / 최상급 10000
    # 레벨당 필요 EXP (인게임 실제 값, Lv1→2부터 Lv89→90까지)
    char_level_exp = [
        # Lv 1~10
        63, 144, 237, 342, 459, 594, 741, 900, 1071,
        # Lv 11~20
        1392, 1653, 1926, 2214, 2517, 2835, 3168, 3519, 3888, 4275,
        # Lv 21~30
        4815, 5376, 5958, 6564, 7194, 7848, 8526, 9228, 9954, 10695,
        # Lv 31~40
        11700, 12726, 13782, 14868, 15984, 17130, 18306, 19512, 20748, 22014,
        # Lv 41~50
        23490, 24996, 26538, 28116, 29730, 31380, 33066, 34788, 36546, 38340,
        # Lv 51~60
        40500, 42702, 44946, 47232, 49560, 51930, 54342, 56796, 59292, 61830,
        # Lv 61~70
        65340, 68904, 72522, 76194, 79920, 83700, 87534, 91422, 95364, 99360,
        # Lv 71~80
        105336, 111384, 117504, 123696, 129960, 136296, 142704, 149184, 155736, 162360,
        # Lv 81~90
        172440, 182592, 192816, 203112, 213480, 223920, 234432, 245016, 255672, 266400,
    ]
    # 레벨 구간별 크레딧 (1레벨당)
    char_level_credit = []
    for lv in range(1, 91):
        if lv <= 20:   credit = 200
        elif lv <= 40: credit = 500
        elif lv <= 60: credit = 1_000
        elif lv <= 80: credit = 3_000
        else:          credit = 5_000
        char_level_credit.append(credit)

    # 일반/강화/서브 스킬 레벨업 크레딧 (Lv1→2 부터 Lv9→10까지, 8단계)
    normal_skill_credit = [
        5_000, 7_500, 10_000, 20_000, 40_000, 60_000, 90_000, 150_000
    ]

    # EX 스킬 레벨업 크레딧 (Lv1→2 부터 Lv4→5까지, 4단계)
    ex_skill_credit = [
        100_000, 200_000, 400_000, 800_000
    ]

    # 고유 무기 레벨별 누적 필요 EXP (Lv1 기준 0)
    # StatLevelUpType: Standard / Premature(빠른성장) / LateBloom(느린성장)
    # 무기 강화 재료: N=10EXP / R=50EXP / SR=200EXP / SSR=1000EXP
    weapon_level_exp = {
        "Standard": [
            200, 400, 700, 1100, 1600, 2200, 2900, 3700, 4600,         # 1~9
            5700, 7000, 8500, 10200, 12100, 14200, 16500, 19000, 21700, 24600, 27800,  # 10~19
            31500, 35500, 39900, 44700, 49900, 55500, 61500, 67900, 74700, 81900,      # 20~29
            89700, 98000, 106900, 116300, 126200, 136600, 147500, 158900, 170800, 183200, # 30~39
            196400, 210100, 224300, 239000, 254200, 269900, 286100, 302800, 320000, 337700, # 40~49
        ],
        "Premature": [   # 초반 성장 빠름
            150, 300, 525, 825, 1200, 1650, 2175, 2775, 3450,
            4275, 5250, 6375, 7650, 9075, 10650, 12375, 14250, 16275, 18450, 20850,
            23625, 26625, 29925, 33525, 37425, 41625, 46125, 50925, 56025, 61425,
            67350, 73650, 80325, 87225, 94350, 101700, 109275, 117075, 125100, 133350,
            142050, 151050, 160350, 169950, 179850, 190050, 200550, 211350, 222450, 233850,
        ],
        "LateBloom": [   # 후반 성장 빠름
            250, 500, 875, 1375, 2000, 2750, 3625, 4625, 5750,
            7125, 8750, 10625, 12750, 15125, 17750, 20625, 23750, 27125, 30750, 34750,
            39375, 44375, 49875, 55875, 62375, 69375, 76875, 84875, 93375, 102375,
            112050, 122300, 133125, 144525, 156500, 169050, 182175, 195875, 210150, 225000,
            240750, 257150, 274200, 291900, 310250, 329250, 348900, 369200, 390150, 411750,
        ],
    }

    # 인연 랭크 누적 필요 Favor EXP (랭크 1 기준 0, 랭크 2까지 필요량...)
    # 선물 1개 기본 ExpValue: N=1, R=5, SR=20
    bond_rank_exp = [
        0,
        100, 200, 400, 700, 1100, 1600, 2200, 2900, 3700, 4600,  # 1~10
        5700, 7000, 8500, 10200, 12100, 14200, 16500, 19000, 21700, 24600,  # 11~20
        27800, 31200, 34800, 38600, 42600, 46800, 51200, 55800, 60600, 65600,  # 21~30
        71000, 76700, 82600, 88700, 95000, 101500, 108200, 115100, 122200, 129500,  # 31~40
        137200, 145200, 153400, 161800, 170400, 179200, 188200, 197400, 206800, 216400,  # 41~50
    ]

    return {
        "char_level": {
            "max_level": 90,
            "exp_per_level": char_level_exp,    # index 0 = Lv1→2 필요 EXP
            "credit_per_level": char_level_credit,
            "exp_items": {
                "초급 활동 보고서": {"item_id": 10, "exp": 50},
                "일반 활동 보고서": {"item_id": 11, "exp": 500},
                "상급 활동 보고서": {"item_id": 12, "exp": 2000},
                "최상급 활동 보고서": {"item_id": 13, "exp": 10000},
            },
        },
        "skill": {
            "max_normal_level": 10,
            "max_ex_level": 5,
            "normal_credit_per_level": normal_skill_credit,
            "ex_credit_per_level": ex_skill_credit,
        },
        "weapon": {
            "max_level": 50,
            "exp_by_type": weapon_level_exp,
            "exp_items": {
                "A": {"N": {"id": 10, "exp": 10}, "R": {"id": 11, "exp": 50},
                      "SR": {"id": 12, "exp": 200}, "SSR": {"id": 13, "exp": 1000}},
                "B": {"N": {"id": 20, "exp": 10}, "R": {"id": 21, "exp": 50},
                      "SR": {"id": 22, "exp": 200}, "SSR": {"id": 23, "exp": 1000}},
                "C": {"N": {"id": 30, "exp": 10}, "R": {"id": 31, "exp": 50},
                      "SR": {"id": 32, "exp": 200}, "SSR": {"id": 33, "exp": 1000}},
                "Z": {"N": {"id": 40, "exp": 10}, "R": {"id": 41, "exp": 50},
                      "SR": {"id": 42, "exp": 200}, "SSR": {"id": 43, "exp": 1000}},
            },
            "weapon_type_to_exp_type": {
                "SR": "A", "RG": "A",
                "SG": "B", "HG": "B", "GL": "B", "MT": "B",
                "SMG": "C", "AR": "C", "MG": "C",
                "FT": "Z",
            },
        },
        "bond_rank": {
            "max_rank": 50,
            "exp_thresholds": bond_rank_exp,    # index 0 = 랭크1 진입 시, index N = 랭크N→N+1
            "gift_exp_values": {
                "N급 선물": 1, "R급 선물": 5, "SR급 선물": 20,
            },
            "note": "SR 선물(ExpValue 20) 기준 필요 개수 = 필요EXP / 20 (올림)",
        },
    }

def main():
    os.makedirs("data", exist_ok=True)

    # 학생 데이터 로드 (gacha_config 생성에 필요)
    print("data/students.json 로드...")
    with open("data/students.json", encoding="utf-8") as f:
        students = json.load(f)["students"]

    # 1. 아이템 데이터
    print("아이템 데이터 수집...")
    item_data = build_items()
    with open("data/items.json", "w", encoding="utf-8") as f:
        json.dump(item_data, f, ensure_ascii=False, indent=2)
    print(f"  저장: data/items.json ({len(item_data['items'])}개 아이템, {len(item_data['equipment'])}개 장비)")

    # 2. 가챠 설정
    print("가챠 설정 생성...")
    gacha = build_gacha_config(students)
    with open("data/gacha_config.json", "w", encoding="utf-8") as f:
        json.dump(gacha, f, ensure_ascii=False, indent=2)
    print(f"  저장: data/gacha_config.json")
    print(f"  3성풀: {gacha['pool_sizes']['3성_통상']}명 / 비픽업 개별: {gacha['non_pickup_3star_per_student']}%")
    print(f"  2성풀: {gacha['pool_sizes']['2성_통상']}명 / 개별: {gacha['2star_per_student']}%")
    print(f"  1성풀: {gacha['pool_sizes']['1성_통상']}명 / 개별: {gacha['1star_per_student']}%")

    # 3. 육성 비용 테이블
    print("육성 비용 테이블 생성...")
    costs = build_costs()
    with open("data/costs.json", "w", encoding="utf-8") as f:
        json.dump(costs, f, ensure_ascii=False, indent=2)
    print(f"  저장: data/costs.json")

    print("\n모든 보조 데이터 저장 완료.")

if __name__ == "__main__":
    main()
