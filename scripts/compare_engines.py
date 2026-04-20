"""鑑定エンジン比較テスト — Gemini 2.5 Pro vs Claude Opus 4.7

使い方:
  cd uranai_monster
  python scripts/compare_engines.py

5パターン × 2エンジン = 10鑑定文を生成し、
Markdownファイルに並べて docs/ 配下に出力する。

発行: 2026-04-20 くろたん指令書 統合指令書 タスク1
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional

# プロジェクトルートを path に追加
_here = Path(__file__).resolve().parent
_root = _here.parent
sys.path.insert(0, str(_root))

# stdout utf-8 化（Windows cp932 対策）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Streamlit secrets → 環境変数
import streamlit as st
for _key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
    try:
        if _key in st.secrets and not os.environ.get(_key):
            os.environ[_key] = st.secrets[_key]
    except Exception:
        pass

from core.models import PersonInput, DivinationBundle
from core.sanmei import calculate_sanmei
from core.western import calculate_western
from core.kyusei import calculate_kyusei
from core.numerology import calculate_numerology
from core.ziwei import calculate_ziwei
from core.tarot import draw_tarot
try:
    from core.shichusuimei import calculate_shichusuimei
except Exception:
    calculate_shichusuimei = None  # type: ignore

from ai import interpreter as _ai

import anthropic


CLAUDE_MODEL = "claude-opus-4-7"
OUTPUT_PATH = _root / "docs" / f"鑑定エンジン比較テスト_Gemini_vs_Opus_{date.today().strftime('%Y%m%d')}.md"


# ============================================================
# Claude 呼び出し（Gemini _call_api / _call_api_text の Claude 版）
# ============================================================
_claude_client = anthropic.Anthropic()


def _claude_call_api(prompt: str, max_tokens: int = 2500) -> dict:
    """Claude Opus で JSON 応答生成（_call_api の Claude 版）

    Claude Opus 4.7 は temperature パラメータが deprecated のため指定しない。
    """
    # Claude の出力上限は 8192〜16384 程度。thinking と output 合わせて 16K くらい
    effective_max = min(max_tokens + 4096, 16000)
    response = _claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=effective_max,
        system=_ai.SYSTEM_PROMPT_BASE,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(getattr(b, "text", "") for b in response.content)
    return _ai._parse_json_response(text)


def _claude_call_api_text(system: str, prompt: str, max_tokens: int = 1000) -> str:
    """Claude Opus でテキスト応答（_call_api_text の Claude 版）"""
    effective_max = min(max_tokens + 4096, 16000)
    response = _claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=effective_max,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(getattr(b, "text", "") for b in response.content)


# ============================================================
# bundle ビルダー（ui/pages.py L1540-1587 のロジックを抜粋）
# ============================================================
def build_bundle(person: PersonInput) -> DivinationBundle:
    sanmei = calculate_sanmei(person)
    western = calculate_western(person)
    kyusei = calculate_kyusei(person)
    numerology = calculate_numerology(person)
    ziwei = calculate_ziwei(person)
    shichu = None
    if calculate_shichusuimei is not None:
        try:
            shichu = calculate_shichusuimei(person)
        except Exception as e:
            print(f"  (四柱推命 スキップ: {e})")
    tarot = draw_tarot(1, major_only=True)[0]
    return DivinationBundle(
        person=person,
        sanmei=sanmei,
        western=western,
        kyusei=kyusei,
        numerology=numerology,
        tarot=tarot,
        ziwei=ziwei,
        shichusuimei=shichu,
        has_birth_time=person.birth_time is not None,
        has_blood_type=person.blood_type is not None,
    )


# ============================================================
# provider 切替（モンキーパッチ）
# ============================================================
_orig_call_api = _ai._call_api
_orig_call_api_text = _ai._call_api_text


def _set_provider(provider: str):
    if provider == "claude":
        _ai._call_api = _claude_call_api
        _ai._call_api_text = _claude_call_api_text
    else:
        _ai._call_api = _orig_call_api
        _ai._call_api_text = _orig_call_api_text


def run_with_provider(provider: str, func: Callable, *args, **kwargs):
    """指定 provider で func を呼び、(result, elapsed_sec) を返す"""
    _set_provider(provider)
    t0 = time.time()
    err: Optional[str] = None
    result = None
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    finally:
        _set_provider("gemini")  # 必ず戻す
    elapsed = time.time() - t0
    return result, elapsed, err


# ============================================================
# 出力ヘルパー
# ============================================================
def _format_result(result) -> str:
    """dict or str の鑑定結果を Markdown 本文に整形"""
    if result is None:
        return "_（生成失敗）_"
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        lines = []
        if result.get("headline"):
            lines.append(f"**{result['headline']}**\n")
        if result.get("reading"):
            lines.append(result["reading"])
        if result.get("closing"):
            lines.append(f"\n— {result['closing']}")
        # その他のフィールド（fields があれば）
        other_keys = [k for k in result.keys() if k not in ("headline", "reading", "closing")]
        if other_keys:
            lines.append("\n<details><summary>その他のフィールド</summary>\n")
            for k in other_keys:
                v = result.get(k)
                if isinstance(v, (dict, list)):
                    import json as _json
                    v = _json.dumps(v, ensure_ascii=False, indent=2)
                lines.append(f"- **{k}**: {v}")
            lines.append("\n</details>")
        return "\n".join(lines)
    return str(result)


def _char_count(result) -> int:
    if result is None:
        return 0
    if isinstance(result, str):
        return len(result)
    if isinstance(result, dict):
        return sum(len(str(v)) for v in result.values() if isinstance(v, (str, int, float)))
    return len(str(result))


# ============================================================
# メイン：5パターン実行
# ============================================================
def main():
    print("=" * 60)
    print("鑑定エンジン比較テスト — Gemini 2.5 Pro vs Claude Opus 4.7")
    print("=" * 60)

    # 人物データ
    hideki = PersonInput(
        birth_date=date(1977, 5, 24),
        birth_time="1:34",
        birth_place="函館市",
        blood_type="A",
        name="ひでさん",
        gender="男性",
    )
    kazuya = PersonInput(
        birth_date=date(1994, 8, 25),
        name="一也",
        gender="男性",
    )

    print("\n[1/3] bundle 構築中…")
    hideki_bundle = build_bundle(hideki)
    kazuya_bundle = build_bundle(kazuya)
    print(f"  ✓ ひでさん: {hideki_bundle.sanmei.hi_kanshi} / {hideki_bundle.western.sun_sign}")
    print(f"  ✓ 一也: {kazuya_bundle.sanmei.hi_kanshi} / {kazuya_bundle.western.sun_sign}")

    # ── パターン3 用: 統合鑑定には先に個別コース結果（headline）が必要 ──
    print("\n[2/3] 統合鑑定用の course_results を Gemini で事前生成…")
    _set_provider("gemini")
    course_results: dict = {}
    # sanmei
    r = _ai.generate_sanmei_reading(hideki_bundle)
    course_results["sanmei"] = {"headline": r.get("headline", "")}
    print(f"  sanmei headline: {course_results['sanmei']['headline']}")
    # western
    r = _ai.generate_western_reading(hideki_bundle)
    course_results["western"] = {"headline": r.get("headline", "")}
    print(f"  western headline: {course_results['western']['headline']}")
    # kyusei
    try:
        r = _ai.generate_kyusei_reading(hideki_bundle)
        course_results["kyusei"] = {"headline": r.get("headline", "")}
    except Exception:
        course_results["kyusei"] = {"headline": ""}
    print(f"  kyusei headline: {course_results['kyusei']['headline']}")
    # numerology
    try:
        r = _ai.generate_numerology_reading(hideki_bundle)
        course_results["numerology"] = {"headline": r.get("headline", "")}
    except Exception:
        course_results["numerology"] = {"headline": ""}
    print(f"  numerology headline: {course_results['numerology']['headline']}")
    # tarot
    try:
        r = _ai.generate_tarot_reading(hideki_bundle)
        course_results["tarot"] = {"headline": r.get("headline", "")}
    except Exception:
        course_results["tarot"] = {"headline": ""}
    print(f"  tarot headline: {course_results['tarot']['headline']}")

    # ── パターン定義 ──
    patterns = [
        {
            "name": "算命学 単体鑑定（ひでさん）",
            "course": "sanmei",
            "func": lambda: _ai.generate_sanmei_reading(hideki_bundle),
        },
        {
            "name": "西洋占星術 単体鑑定（ひでさん）",
            "course": "western",
            "func": lambda: _ai.generate_western_reading(hideki_bundle),
        },
        {
            "name": "統合鑑定（ひでさん / 6占術まとめ）",
            "course": "synthesis",
            "func": lambda: _ai.generate_synthesis(hideki_bundle, course_results),
        },
        {
            "name": "テーマ別深掘り『仕事運』（ひでさん）",
            "course": "theme_career",
            "func": lambda: _ai.generate_theme_reading(hideki_bundle, "career"),
        },
        {
            "name": "相性鑑定（ひでさん × 一也 / 親子）",
            "course": "aisho",
            "func": lambda: _ai.generate_aisho_reading(hideki_bundle, kazuya_bundle, "parent_child"),
        },
    ]

    # ── 各パターンを両エンジンで実行 ──
    print(f"\n[3/3] 各パターンを両エンジンで生成…")
    comparison_data = []
    for i, pat in enumerate(patterns, 1):
        print(f"\n--- パターン{i}: {pat['name']} ---")
        # Gemini
        print(f"  [Gemini 2.5 Pro] 生成中…", flush=True)
        g_result, g_elapsed, g_err = run_with_provider("gemini", pat["func"])
        print(f"  [Gemini 2.5 Pro] 完了 {g_elapsed:.1f}秒" + (f" (エラー: {g_err})" if g_err else ""))
        # Claude
        print(f"  [Claude Opus 4.7] 生成中…", flush=True)
        c_result, c_elapsed, c_err = run_with_provider("claude", pat["func"])
        print(f"  [Claude Opus 4.7] 完了 {c_elapsed:.1f}秒" + (f" (エラー: {c_err})" if c_err else ""))

        comparison_data.append({
            "name": pat["name"],
            "course": pat["course"],
            "gemini": {"result": g_result, "elapsed": g_elapsed, "error": g_err},
            "claude": {"result": c_result, "elapsed": c_elapsed, "error": c_err},
        })

    # ── Markdown 出力 ──
    print(f"\n[完了] 結果を Markdown に書き出し: {OUTPUT_PATH}")
    lines = []
    lines.append(f"# 鑑定エンジン比較テスト — Gemini 2.5 Pro vs Claude Opus 4.7")
    lines.append("")
    lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"条件: 同一プロンプト・同一入力データ / temperature=0.9")
    lines.append(f"モデル: `gemini-2.5-pro` / `{CLAUDE_MODEL}`")
    lines.append("")
    lines.append("## 【評価観点】")
    lines.append("ひでさん、以下の観点で読み比べてください：")
    lines.append("")
    lines.append("1. **断定力** — 言い切っているか、曖昧に逃げていないか")
    lines.append("2. **刺さり度** — 読んだ人が「おお」と思うか")
    lines.append("3. **くろたんキャラクター** — 断定口調・ポジティブ転換ができているか")
    lines.append("4. **専門用語の扱い** — 難しい用語を平易に言い換えているか")
    lines.append("5. **統合力**（統合鑑定のみ） — 複数占術の結果を矛盾なく統合できているか")
    lines.append("6. **文章の自然さ** — 機械的でなく、人間が書いたように読めるか")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, c in enumerate(comparison_data, 1):
        lines.append(f"## パターン{i}：{c['name']}")
        lines.append("")
        # Gemini
        lines.append(f"### 【A】Gemini 2.5 Pro")
        if c["gemini"]["error"]:
            lines.append(f"_エラー: {c['gemini']['error']}_")
        else:
            lines.append(_format_result(c["gemini"]["result"]))
        lines.append("")
        # Claude
        lines.append(f"### 【B】Claude Opus 4.7")
        if c["claude"]["error"]:
            lines.append(f"_エラー: {c['claude']['error']}_")
        else:
            lines.append(_format_result(c["claude"]["result"]))
        lines.append("")
        # 比較メタ
        lines.append(f"### 比較メモ")
        lines.append(f"| | Gemini 2.5 Pro | Claude Opus 4.7 |")
        lines.append(f"|---|---|---|")
        lines.append(f"| 生成時間 | {c['gemini']['elapsed']:.1f}秒 | {c['claude']['elapsed']:.1f}秒 |")
        lines.append(f"| 文字数 | {_char_count(c['gemini']['result'])} 文字 | {_char_count(c['claude']['result'])} 文字 |")
        lines.append(f"| エラー | {c['gemini']['error'] or '—'} | {c['claude']['error'] or '—'} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✨ 完了！ファイル: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
