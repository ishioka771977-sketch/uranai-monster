"""ひでさんの部屋(別アプリ)用の固定資産をエクスポートする。

  python scripts/export_hidesan_room.py static    # 命式・日運表・タロット・プロンプト(API不要)
  python scripts/export_hidesan_room.py readings  # 8コース+5テーマの鑑定文(Claude API・約30分)

出力先: ~/ishioka/hidesan-room/data/
"""
from __future__ import annotations
import json, os, sys, time
from datetime import date, timedelta
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
from dotenv import load_dotenv
load_dotenv(_root / ".env")
os.environ.setdefault("AI_PROVIDER", "claude")

OUT = Path.home() / "ishioka" / "hidesan-room" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def build_bundle():
    from core.models import PersonInput, DivinationBundle
    from core.sanmei import calculate_sanmei
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.western import calculate_western
    from core.ziwei import calculate_ziwei
    from core.shichusuimei import calculate_shichusuimei
    from core.kojindo import calculate_kojindo
    from core.tarot import draw_tarot
    h = json.loads((_root / "data" / "hidesan.json").read_text(encoding="utf-8"))
    p = PersonInput(birth_date=date.fromisoformat(h["birth_date"]), birth_time=h["birth_time"],
                    birth_place=h.get("birth_place"), blood_type=h.get("blood_type"),
                    name="ひでさん", gender=h.get("gender", "男性"), current_pref="北海道")
    sanmei = calculate_sanmei(p)
    shichu = calculate_shichusuimei(p)
    try:
        kojindo = calculate_kojindo(sanmei, p, shichu)
    except Exception as e:
        print("kojindo skip:", e); kojindo = None
    return DivinationBundle(person=p, sanmei=sanmei, western=calculate_western(p),
                            kyusei=calculate_kyusei(p), numerology=calculate_numerology(p),
                            tarot=draw_tarot(1, major_only=True)[0], ziwei=calculate_ziwei(p),
                            shichusuimei=shichu, kojindo=kojindo, has_birth_time=True,
                            has_blood_type=True)


def export_static():
    import ai.interpreter as I
    from core.kaiyun import (calc_lucky_score, generate_monthly_advice, generate_yearly_advice,
                             calc_taiun, get_current_taiun)
    from core.aisho_scoring import TENCHUSATSU_JUNISHI
    from core.tarot import _load_all_cards
    b = build_bundle()
    s = b.sanmei
    profile = {
        "name": "ひでさん", "birth_date": str(b.person.birth_date), "birth_time": b.person.birth_time,
        "birth_place": b.person.birth_place, "gender": b.person.gender,
        "summary": I._format_all_data_summary(b),
        "person_context": I._person_context_block(b),
        "highlights": {
            "nichikan": s.nichikan, "chuo_sei": s.chuo_sei, "tenchusatsu": s.tenchusatsu,
            "sun_sign": b.western.sun_sign, "moon_sign": b.western.moon_sign,
            "asc": getattr(b.western, "asc_sign", None), "honmei": b.kyusei.honmei_sei,
            "life_path": b.numerology.life_path,
        },
    }
    (OUT / "profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=1), encoding="utf-8")

    pd = {"day_kan": s.hi_kan, "year_kan": s.nen_kan, "month_kan": s.tsuki_kan, "month_shi": s.tsuki_shi,
          "tenchusatsu": TENCHUSATSU_JUNISHI.get(s.tenchusatsu, []), "special_kaku": s.kakkyoku or ""}
    days = {}
    d = date(2026, 9, 1)
    while d <= date(2027, 12, 31):
        r = calc_lucky_score(d, pd)
        r["reasons"] = [list(x) for x in r.get("reasons", [])]
        days[d.isoformat()] = r
        d += timedelta(days=1)
    months = {f"{y}-{m:02d}": generate_monthly_advice(pd, y, m) for y in (2026, 2027) for m in range(1, 13)}
    years = {str(y): generate_yearly_advice(pd, y) for y in (2026, 2027, 2028)}
    taiun = calc_taiun(pd, b.person.birth_date, b.person.gender)
    cur = get_current_taiun(taiun, b.person.birth_date.year, date.today().year)
    (OUT / "fortune.json").write_text(json.dumps({"person_data": pd, "days": days, "months": months,
                                                  "years": years, "taiun": taiun, "current_taiun": cur},
                                                 ensure_ascii=False, default=str), encoding="utf-8")

    cards = []
    for c in _load_all_cards():
        cards.append({k: c.get(k) for k in ("number", "name", "name_en", "image_key", "suit", "suit_name",
                                            "upright", "reversed", "_arcana")})
    (OUT / "tarot_deck.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")

    prompts = {"system_base": I.SYSTEM_PROMPT_BASE, "tarot_interactive": I.TAROT_INTERACTIVE_PROMPT,
               "v3_polish": I._v3_polish_directive(), "spreads": I.SPREAD_DEFAULTS}
    (OUT / "prompts.json").write_text(json.dumps(prompts, ensure_ascii=False, indent=1), encoding="utf-8")
    print("static done:", [p.name for p in OUT.iterdir()])


def export_readings():
    import ai.interpreter as I
    b = build_bundle()
    path = OUT / "readings.json"
    out = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    jobs = [("course", c) for c in ("算命学", "星座", "九星気学", "数秘術", "紫微斗数", "万象学", "四柱推命", "古神道")]
    jobs += [("theme", t) for t in ("love", "marriage", "career", "future10", "shine")]
    for kind, key in jobs:
        k = f"{kind}:{key}"
        if k in out and out[k].get("reading"):
            print("skip", k); continue
        t0 = time.time()
        try:
            r = I.generate_single_course(b, key) if kind == "course" else I.generate_theme_reading(b, key)
            out[k] = {"headline": r.get("headline", ""), "reading": r.get("reading", ""),
                      "closing": r.get("closing", ""), "generated_at": date.today().isoformat()}
            print(f"[{k}] {time.time()-t0:.0f}s {len(out[k]['reading'])}chars", flush=True)
        except Exception as e:
            print(f"[{k}] FAILED {e}", flush=True)
        path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("readings done:", len(out))


if __name__ == "__main__":
    {"static": export_static, "readings": export_readings}[sys.argv[1]]()
