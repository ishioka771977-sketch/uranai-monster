# -*- coding: utf-8 -*-
"""Fable 5.1 vs Opus 5.5 ブラインド読み比べ(本人版・7占術)

使い方:
  .venv/bin/python scripts/blind_fable_vs_opus55.py

アプリの実プロンプトを同一投入(blind_engine_test.py の捕獲器を流用)。
Opus 5.5 は既定effortがmediumなので、本番Fableと揃えて high を明示。
出力:
  docs/読み比べ本人版_Fable51vsOpus55_<日付>.md … 評価用(正解なし)
  data/_blind_fable_vs_opus55_answers.json     … 正解表+トークン実測(封印)
"""
from __future__ import annotations

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "scripts"))

from blind_engine_test import COURSES, build_bundle, capture_prompt  # noqa: E402
import anthropic  # noqa: E402

NAME, BIRTH, BIRTH_TIME = "ひでさん", date(1977, 5, 24), "01:34"
ENGINES = {
    "Claude Fable 5.1": {"model": "claude-fable-5-1"},
    "Claude Opus 5.5 (effort high)": {"model": "claude-opus-5-5", "output_config": {"effort": "high"}},
}
PRICE = {"claude-fable-5-1": (10.0, 50.0), "claude-opus-5-5": (4.0, 20.0)}  # $/1M in,out
ANSWERS = _root / "data" / "_blind_fable_vs_opus55_answers.json"


def gen(engine: str, system: str, prompt: str) -> dict:
    cfg = ENGINES[engine]
    c = anthropic.Anthropic(timeout=900.0, max_retries=3)
    extra = {"output_config": cfg["output_config"]} if "output_config" in cfg else None
    t0 = time.time()
    with c.messages.stream(model=cfg["model"], max_tokens=16000, system=system,
                           messages=[{"role": "user", "content": prompt}],
                           extra_body=extra) as st:
        r = st.get_final_message()
    pin, pout = PRICE[cfg["model"]]
    u = r.usage
    return {
        "text": "".join(getattr(b, "text", "") for b in r.content),
        "served": r.model, "stop": r.stop_reason, "sec": round(time.time() - t0),
        "in": u.input_tokens, "out": u.output_tokens,
        "usd": round(u.input_tokens / 1e6 * pin + u.output_tokens / 1e6 * pout, 4),
    }


def main():
    from ai.interpreter import _parse_json_response
    bundle = build_bundle(BIRTH, NAME, BIRTH_TIME)
    prompts = {k: capture_prompt(bundle, k) for k in COURSES}
    print("プロンプト捕獲完了: " + " / ".join(COURSES[k][0] for k in COURSES), flush=True)

    jobs = [(k, e) for k in COURSES for e in ENGINES]
    with ThreadPoolExecutor(max_workers=7) as ex:
        futs = {(k, e): ex.submit(gen, e, *prompts[k]) for k, e in jobs}
        res = {}
        for (k, e), f in futs.items():
            res[(k, e)] = f.result()
            print(f"  done {COURSES[k][0]} ({len(res)}/{len(jobs)})", flush=True)

    rng = random.Random(datetime.now().isoformat())
    today = date.today().strftime("%Y%m%d")
    out_md = _root / "docs" / f"読み比べ本人版_Fable51vsOpus55_{today}.md"
    L = [f"# 読み比べ本人版: 7占術×2エンジン ({date.today().isoformat()})", "",
         f"- 対象: {NAME}本人の命式({BIRTH.isoformat()} {BIRTH_TIME}生)",
         "- 各占術で A・B のどちらが良いかを選ぶ(引き分け可)。並び順は占術ごとにランダム", ""]
    key = {}
    for k in COURSES:
        jp = COURSES[k][0]
        order = list(ENGINES)
        rng.shuffle(order)
        key[jp] = dict(zip("AB", order))
        L += [f"# 【{jp}】", ""]
        for label, e in zip("AB", order):
            r = _parse_json_response(res[(k, e)]["text"]) or {}
            L += [f"## {jp}−{label}", "", f"**「{r.get('headline', '')}」**", "",
                  r.get("reading", "") or res[(k, e)]["text"], ""]
    L += ["---", "", "回答: " + " / ".join(f"{COURSES[k][0]}=" for k in COURSES)]
    out_md.write_text("\n".join(L), encoding="utf-8")

    stats = {f"{COURSES[k][0]}|{e}": {kk: v for kk, v in res[(k, e)].items() if kk != "text"}
             for k, e in jobs}
    ANSWERS.write_text(json.dumps({"created_at": datetime.now().isoformat(timespec="seconds"),
                                   "file": out_md.name, "key": key, "stats": stats},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    for e in ENGINES:
        rows = [res[(k, e)] for k in COURSES]
        print(f"[{e}] 合計${sum(r['usd'] for r in rows):.2f} / 平均{sum(r['sec'] for r in rows)//len(rows)}秒 "
              f"/ stop={set(r['stop'] for r in rows)} / served={set(r['served'] for r in rows)}")
    print(f"評価用 -> {out_md}\n正解表 -> {ANSWERS}(封印)")


if __name__ == "__main__":
    main()
