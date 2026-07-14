# -*- coding: utf-8 -*-
"""4エンジン・ブラインドテスト生成器(第三者テスター用)

使い方:
  .venv/bin/python scripts/blind_engine_test.py <名前> <YYYY-MM-DD> <占術> [HH:MM]
  占術: sanmei | western | kyusei | numerology | ziwei | shichu | bansho
  例: .venv/bin/python scripts/blind_engine_test.py 華子 1985-03-12 sanmei

出力:
  docs/ブラインドテスト_<名前>_<占術>_<日付>.md  … テスター配布用(正解なし)
  data/_blind_test_answers.json                 … 正解表(gitignore・封印)

エンジン: Claude Fable 5 / Claude Opus 4.8 / GPT-5.6 Sol(codex CLI) / Gemini 2.5 Pro(gemini CLI)
アプリの実プロンプトを同一投入。並び順はテストごとにランダム。
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

import anthropic

ANSWERS_PATH = _root / "data" / "_blind_test_answers.json"
GEMINI_ENV_FALLBACK = Path.home() / "hoshino-consult" / ".env"

COURSES = {
    "sanmei": ("算命学", "generate_sanmei_reading"),
    "western": ("占星術", "generate_western_reading"),
    "kyusei": ("九星気学", "generate_kyusei_reading"),
    "numerology": ("数秘術", "generate_numerology_reading"),
    "ziwei": ("紫微斗数", "generate_ziwei_reading"),
    "shichu": ("四柱推命", "generate_shichusuimei_reading"),
    "bansho": ("万象学", "generate_bansho_reading"),
}


def build_bundle(birth: date, name: str, birth_time: str | None):
    from core.models import PersonInput, DivinationBundle
    from core.sanmei import calculate_sanmei
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.western import calculate_western
    from core.tarot import draw_tarot
    p = PersonInput(birth_date=birth, name=name, gender="その他", birth_time=birth_time)
    kw = {}
    if birth_time:
        from core.ziwei import calculate_ziwei
        from core.shichusuimei import calculate_shichusuimei
        kw = {"ziwei": calculate_ziwei(p), "shichusuimei": calculate_shichusuimei(p),
              "has_birth_time": True}
    return DivinationBundle(person=p, sanmei=calculate_sanmei(p), western=calculate_western(p),
                            kyusei=calculate_kyusei(p), numerology=calculate_numerology(p),
                            tarot=draw_tarot(1, major_only=True)[0], **kw)


def capture_prompt(bundle, course_key: str) -> tuple[str, str]:
    """アプリが本番で組むsystem+promptを横取り"""
    import ai.interpreter as I
    _, fn_name = COURSES[course_key]
    gen = getattr(I, fn_name)
    cap = {}
    if course_key == "bansho":
        def spy(system, prompt, max_tokens=1000):
            cap["system"], cap["prompt"] = system, prompt
            raise RuntimeError("captured")
        orig = I._call_api_text
        I._call_api_text = spy
        try:
            gen(bundle)
        except Exception:
            pass
        I._call_api_text = orig
        system = I._current_time_context() + "\n" + cap["system"]
    else:
        def spy(prompt, max_tokens=2500):
            cap["prompt"] = prompt
            raise RuntimeError("captured")
        orig = I._call_api
        I._call_api = spy
        try:
            gen(bundle)
        except Exception:
            pass
        I._call_api = orig
        system = I._current_time_context() + "\n" + I.SYSTEM_PROMPT_BASE
    return system, cap["prompt"]


def gen_claude(model: str, system: str, prompt: str) -> str:
    c = anthropic.Anthropic(timeout=600.0, max_retries=2)
    with c.messages.stream(model=model, max_tokens=9000, system=system,
                           messages=[{"role": "user", "content": prompt}]) as st:
        r = st.get_final_message()
    return "".join(getattr(b, "text", "") for b in r.content)


def _combined(system: str, prompt: str) -> str:
    return ("以下のシステム指示に厳密に従い、続くユーザープロンプトに回答してください。"
            "ツールやファイル操作は不要です。指定されたJSONのみを出力してください。\n\n"
            f"===システム指示===\n{system}\n\n===ユーザープロンプト===\n{prompt}")


def gen_gpt56(system: str, prompt: str) -> str:
    p = subprocess.run(
        ["codex", "exec", "-m", "gpt-5.6-sol", "--skip-git-repo-check", "-s", "read-only", "-"],
        input=_combined(system, prompt).encode(), capture_output=True, timeout=600)
    return p.stdout.decode()


def gen_gemini(system: str, prompt: str) -> str:
    import os
    env = dict(os.environ)
    if not env.get("GEMINI_API_KEY") and GEMINI_ENV_FALLBACK.exists():
        for line in GEMINI_ENV_FALLBACK.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                env["GEMINI_API_KEY"] = line.split("=", 1)[1].strip()
    env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"
    p = subprocess.run(["gemini", "-m", "gemini-2.5-pro", "-p", _combined(system, prompt)],
                       capture_output=True, timeout=600, env=env)
    return p.stdout.decode()


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    name, birth_s, course_key = sys.argv[1], sys.argv[2], sys.argv[3]
    birth_time = sys.argv[4] if len(sys.argv) > 4 else None
    if course_key not in COURSES:
        print(f"占術は {'/'.join(COURSES)} から選んでください")
        sys.exit(1)
    if course_key in ("ziwei", "shichu") and not birth_time:
        print("紫微斗数・四柱推命は出生時刻(HH:MM)が必要です")
        sys.exit(1)
    birth = date.fromisoformat(birth_s)
    course_jp, _ = COURSES[course_key]

    print(f"[1/4] 命式計算+プロンプト捕獲: {name} {birth_s} {course_jp}", flush=True)
    bundle = build_bundle(birth, name, birth_time)
    system, prompt = capture_prompt(bundle, course_key)

    from ai.interpreter import _parse_json_response
    engines = {
        "Claude Fable 5": lambda: gen_claude("claude-fable-5", system, prompt),
        "Claude Opus 4.8": lambda: gen_claude("claude-opus-4-8", system, prompt),
        "GPT-5.6 Sol": lambda: gen_gpt56(system, prompt),
        "Gemini 2.5 Pro": lambda: gen_gemini(system, prompt),
    }
    results = {}
    for i, (ename, fn) in enumerate(engines.items(), 2):
        print(f"[{i}/5] 生成中: (エンジン{i-1}/4)", flush=True)  # 端末にもエンジン名を出さない
        results[ename] = _parse_json_response(fn())

    # 並び順はテスト固有シードでシャッフル(名前+日付+時刻から決定)
    seed = hashlib.sha256(f"{name}{birth_s}{course_key}{datetime.now().isoformat()}".encode()).hexdigest()
    order = list(engines.keys())
    random.Random(seed).shuffle(order)

    today = date.today().strftime("%Y%m%d")
    out_md = _root / "docs" / f"ブラインドテスト_{name}_{course_jp}_{today}.md"
    L = [f"# {name}さんの{course_jp}鑑定 読み比べ(A〜D)", "",
         f"- 生年月日: {birth_s}" + (f" {birth_time}" if birth_time else ""),
         "- 4本は同じ生年月日から作った鑑定文です。読みやすさ・当たってる感・心に残るかで",
         "  **1位と最下位**を選んでください。理由も一言もらえると嬉しいです。", ""]
    for label, ename in zip("ABCD", order):
        r = results[ename] or {}
        L += [f"## 鑑定{label}", "", f"**「{r.get('headline','')}」**", "", r.get("reading", ""), ""]
    L += ["---", "", "回答: 1位=　　最下位=　　ひとこと:"]
    out_md.write_text("\n".join(L), encoding="utf-8")

    # 正解表は封印ファイルへ(配布物・チャットに出さない)
    answers = json.loads(ANSWERS_PATH.read_text()) if ANSWERS_PATH.exists() else []
    answers.append({
        "test_id": f"{name}_{course_jp}_{today}",
        "file": out_md.name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "key": {label: ename for label, ename in zip("ABCD", order)},
    })
    ANSWERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANSWERS_PATH.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n配布用 -> {out_md}")
    print(f"正解表 -> {ANSWERS_PATH}(封印・開けないこと)")


if __name__ == "__main__":
    main()
