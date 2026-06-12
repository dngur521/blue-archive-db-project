"""
fetch_extras.py
SchaleDB에서 누락된 데이터 추가 수집
- student_extras.json: 학생 스탯 (Lv.1 / MAX) + 스킬 파라미터 (Lv.1 / MAX)
"""
import json, urllib.request

BASE = "https://schaledb.com/data/kr"

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

SKILL_KEY = {
    "Ex":           "ex_skill",
    "Normal":       "normal_skill",
    "Public":       "enhance_skill",
    "Passive":      "sub_skill",
    "ExtraPassive": "extra_skill",
}

def main():
    print("SchaleDB API 요청 중...")
    raw = fetch_json(f"{BASE}/students.min.json")
    print(f"  {len(raw)}명 데이터 수신")

    extras = {}
    for sid_str, s in raw.items():
        sid = int(sid_str)

        # ── 스탯 ──────────────────────────────────────────────────────────────
        stats = {
            "max_hp_1":   s.get("MaxHP1", 0),
            "max_hp_max": s.get("MaxHP100", 0),
            "atk_1":      s.get("AttackPower1", 0),
            "atk_max":    s.get("AttackPower100", 0),
            "def_1":      s.get("DefensePower1", 0),
            "def_max":    s.get("DefensePower100", 0),
            "heal_1":     s.get("HealPower1", 0),
            "heal_max":   s.get("HealPower100", 0),
        }

        # ── 스킬 파라미터 ──────────────────────────────────────────────────────
        # Parameters[param_idx][level_idx]
        # params_lv1 = [Parameters[i][0] for i in range(N)]  (Lv.1 수치)
        # params_max = [Parameters[i][-1] for i in range(N)] (MAX 수치)
        skill_params = {}
        for raw_type, db_type in SKILL_KEY.items():
            sk = s.get("Skills", {}).get(raw_type, {})
            params = sk.get("Parameters", [])
            if params:
                skill_params[db_type] = {
                    "lv1": [row[0] if row else "" for row in params],
                    "max": [row[-1] if row else "" for row in params],
                }

        extras[sid] = {"stats": stats, "skill_params": skill_params}

    out = "data/student_extras.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(extras, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {out} ({len(extras)}명)")

if __name__ == "__main__":
    main()
