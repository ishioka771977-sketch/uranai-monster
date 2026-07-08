# -*- coding: utf-8 -*-
"""古神道v3 P2パイロット: 浅間系(konohanasakuya)系列社収集

設計: docs/古神道v3_P2パイロット計画_20260704.md(くろたん承認 2026-07-05)
モデル: claude-sonnet-5 + web_search(機械抽出に最高級モデルは使わない・適材適所)
原則: 0件許容・推測禁止・許可リスト方式(デフォルト棄却)

使い方:
  python scripts/collect_lineage_pilot.py test   # 疎通テスト5県
  python scripts/collect_lineage_pilot.py run    # 全47都道府県
  python scripts/collect_lineage_pilot.py report # 検品+集計+サンプル20件md
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
from dotenv import load_dotenv
load_dotenv(_root / ".env")

import anthropic

MODEL = "claude-sonnet-5"
LINEAGE = "浅間"
GOD_ID = "konohanasakuya"
RAW_PATH = _root / "data" / "kojindo" / "shrines" / "_pilot_konohanasakuya_raw.json"
REPORT_MD = _root / "docs" / f"P2パイロット報告_浅間系_{date.today().strftime('%Y%m%d')}.md"

PREFS = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]
TEST_PREFS = ["北海道", "静岡県", "山梨県", "京都府", "沖縄県"]

# Tier1: 自動合格ドメインパターン(計画書準拠)
TIER1_PATTERNS = [
    r"jinjahoncho\.or\.jp$",
    r"jinj[ay]a?ch?o",                    # 都道府県神社庁(hokkaidojinjacho.jp等 .or.jp以外も実在・疎通テスト実測)
    r"\.lg\.jp$", r"^pref\..*\.jp$", r"^(www\.)?city\..*\.jp$",
    r"^town\..*\.jp$", r"^vill\..*\.jp$",
    r"\.go\.jp$", r"\.ac\.jp$",
]

# 祭神検証: 主祭神欄にこのいずれかが含まれないレコードは棄却(疎通テストで祭神未確認レコード混入を実測)
DEITY_PATTERNS = ["木花", "咲耶", "サクヤ", "さくや", "浅間大神"]
# Tier3: 自動棄却(明示ブロック。これ以外の未知ドメインは Tier2=神社公式候補として保留)
TIER3_PATTERNS = [
    r"ameblo\.jp", r"note\.com", r"hatenablog", r"fc2", r"livedoor",
    r"wikipedia\.org", r"hotokami\.jp", r"omairi\.club", r"goshuin",
    r"jalan\.net", r"tripadvisor", r"rurubu", r"gurutabi",
]

SYSTEM = """あなたは神社データベースの調査員。以下を厳守する。

- 推測禁止。webで確認できた情報のみを出力し、確認できなければ空リストを返す(0件は正しい結果)
- 出典は「神社公式サイト・神社本庁/都道府県神社庁・自治体公式」のみ採用。個人ブログ/まとめ/Wikipedia/観光商業サイトは出典にしない
- 各神社について、出典ページに実際に書かれている文言を source_quote に逐語で引用する(要約しない)
- 緯度経度は出典に無ければ null(住所から推測しない)"""

SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "shrines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "pref": {"type": "string"},
                        "city": {"type": "string"},
                        "address": {"type": "string"},
                        "main_deity": {"type": "string", "description": "主祭神(出典記載どおり)"},
                        "source_url": {"type": "string"},
                        "source_quote": {"type": "string", "description": "出典ページの逐語引用(祭神・由緒の該当箇所)"},
                        "lat": {"type": ["number", "null"]},
                        "lng": {"type": ["number", "null"]},
                    },
                    "required": ["name", "pref", "city", "address", "main_deity", "source_url", "source_quote", "lat", "lng"],
                    "additionalProperties": False,
                },
            },
            "search_note": {"type": "string", "description": "0件の場合の理由等"},
        },
        "required": ["shrines", "search_note"],
        "additionalProperties": False,
    },
}


def _user_prompt(pref: str) -> str:
    return (
        f"{pref}に鎮座する浅間神社(浅間系・木花咲耶姫/木花之佐久夜毘売命を祀る神社)を"
        f"web検索で調べ、公式情報源(神社公式サイト・神社庁・自治体公式)で祭神が確認できたものだけを"
        f"最大3社、JSONで返せ。地域の代表的な社(一宮・県社格・著名社)を優先。"
        f"公式情報源で確認できない場合は無理に埋めず0件でよい。"
    )


def _domain(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1).lower() if m else "").removeprefix("www.")


def classify(url: str) -> str:
    d = _domain(url)
    if not d:
        return "tier3_reject"
    for p in TIER3_PATTERNS:
        if re.search(p, d):
            return "tier3_reject"
    for p in TIER1_PATTERNS:
        if re.search(p, d):
            return "tier1_auto"
    return "tier2_shrine_official_pending"


def _collect_one(client: anthropic.Anthropic, pref: str) -> dict:
    """1都道府県分を収集して結果dictを返す(例外は呼び出し側で処理)"""
    resp = None
    for attempt in range(3):  # 529 overloaded / 一時エラーのリトライ(疎通テスト実測)
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=4000,
                system=SYSTEM,
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
                output_config={"format": SCHEMA},
                messages=[{"role": "user", "content": _user_prompt(pref)}],
            ) as stream:
                resp = stream.get_final_message()
            break
        except anthropic.APIStatusError as e:
            if e.status_code in (429, 529) and attempt < 2:
                print(f"  {pref}: {e.status_code} retry in 60s ({attempt+1}/3)")
                time.sleep(60)
                continue
            raise
    assert resp is not None
    text = next((b.text for b in resp.content if b.type == "text"), "")
    payload = json.loads(text)
    for s in payload.get("shrines", []):
        if not any(p in (s.get("main_deity") or "") for p in DEITY_PATTERNS):
            s["tier"] = "rejected_deity_unverified"
        else:
            s["tier"] = classify(s.get("source_url", ""))
        s["retrieved_at"] = date.today().isoformat()
    note = payload.get("search_note", "")
    # 劣化検知: 検索ツール上限で調べきれなかった0件は「結果」ではなく「エラー」として
    # 再キュー対象にする(2026-07-08パイロット実測: 劣化0件と正直な0件の混同を防ぐ)
    if not payload.get("shrines") and re.search(
        r"(上限|limit exceeded|max_uses|レート制限|利用回数|placeholder|検索を一切実行できま)", note
    ):
        raise RuntimeError(f"degraded: tool limit ({note[:60]})")
    return {
        "shrines": payload.get("shrines", []),
        "search_note": note,
        "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens},
        "stop_reason": resp.stop_reason,
    }


def run(prefs: list[str], workers: int = 1) -> None:
    # workers=1+間隔20s: web_searchサーバーツールのレート上限対策(3並列で上限踏みを実測)
    # web検索ラウンドが多い県は1クエリ2〜12分かかる(実測)ため、
    # ストリーミング+3並列で実行。増分保存はロックで直列化
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = anthropic.Anthropic(timeout=600.0, max_retries=1)
    data = json.loads(RAW_PATH.read_text()) if RAW_PATH.exists() else {"prefs": {}}
    todo = [p for p in prefs if not (p in data["prefs"] and "error" not in data["prefs"][p])]
    print(f"対象: {len(todo)}県(済{len(prefs) - len(todo)}県スキップ) / {workers}並列")
    lock = threading.Lock()
    done_count = 0

    def work(pref: str):
        nonlocal done_count
        t0 = time.time()
        try:
            time.sleep(20)  # 検索レートのペーシング
            rec = _collect_one(client, pref)
            n = len(rec["shrines"])
            msg = f"{pref}: {n}社 ({time.time()-t0:.0f}s)"
        except Exception as e:
            rec = {"error": f"{type(e).__name__}: {e}"}
            msg = f"{pref}: ERROR {e}"
        with lock:
            done_count += 1
            data["prefs"][pref] = rec
            RAW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{done_count}/{len(todo)}] {msg}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(as_completed([ex.submit(work, p) for p in todo]))
    print(f"raw -> {RAW_PATH}")


def report() -> None:
    data = json.loads(RAW_PATH.read_text())
    all_shrines, errors, zero = [], [], []
    for pref, rec in data["prefs"].items():
        if "error" in rec:
            errors.append((pref, rec["error"]))
            continue
        if not rec["shrines"]:
            zero.append(pref)
        for s in rec["shrines"]:
            s["_pref_query"] = pref
            all_shrines.append(s)
    tiers = {"tier1_auto": 0, "tier2_shrine_official_pending": 0, "tier3_reject": 0}
    for s in all_shrines:
        tiers[s["tier"]] += 1
    # 重複(同名同県)検出
    seen, dups = set(), 0
    for s in all_shrines:
        k = (s["pref"], s["name"])
        if k in seen: dups += 1
        seen.add(k)

    usable = [s for s in all_shrines if s["tier"] != "tier3_reject"]
    lines = [
        f"# P2パイロット報告: 浅間系({date.today().isoformat()})",
        "",
        f"- クエリ: {len(data['prefs'])}都道府県 / エラー: {len(errors)} / 0件県: {len(zero)}({'、'.join(zero) if zero else 'なし'})",
        f"- 収集: {len(all_shrines)}社(重複{dups}) → Tier1自動合格 {tiers['tier1_auto']} / Tier2神社公式(要QA) {tiers['tier2_shrine_official_pending']} / **Tier3棄却 {tiers['tier3_reject']}**",
        f"- 採用候補(Tier1+2): {len(usable)}社 / 棄却率: {tiers['tier3_reject']}/{len(all_shrines)}",
        "",
        "## サンプル20件(くろたんレビュー用)",
        "",
        "| # | 県 | 社名 | 主祭神(出典記載) | Tier | 出典 | 引用(冒頭60字) |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(usable[:20], 1):
        q = (s.get("source_quote") or "")[:60].replace("|", "｜").replace("\n", " ")
        lines.append(f"| {i} | {s['pref']} | {s['name']} | {s['main_deity'][:16]} | {s['tier'].split('_')[0]} | {s['source_url'][:48]} | {q} |")
    if errors:
        lines += ["", "## エラー", ""] + [f"- {p}: {e}" for p, e in errors]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {REPORT_MD}")
    print(f"収集{len(all_shrines)} / 採用候補{len(usable)} / 棄却{tiers['tier3_reject']} / 0件県{len(zero)} / エラー{len(errors)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        run(TEST_PREFS)
    elif cmd == "run":
        run(PREFS)
    elif cmd == "report":
        report()
    else:
        print(__doc__)
