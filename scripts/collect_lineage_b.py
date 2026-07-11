# -*- coding: utf-8 -*-
"""古神道v3 P2方式B: 系列社収集(直接取得+抽出分離)——浅間系パイロット

設計: docs/古神道v3_P2方式B提案_20260711.md(くろたん承認+3条件 2026-07-11)
  Stage1: 県神社庁サイトをローカル取得(web検索ゼロ)。Sonnetは「次にどのリンクを
          辿るか」のナビゲーションと抽出のみ担当(ツール不使用=クォータ非依存)
  Stage2: 取得済みページから祭神・所在地・逐語引用を構造化抽出
  マナー: UA明示(連絡先付き)・3.5秒間隔・1県あたり最大4ページ・robots"Disallow: /"尊重

使い方:
  python scripts/collect_lineage_b.py test  # 3県疎通(秋田・富山・鹿児島)
  python scripts/collect_lineage_b.py run   # 方式A未確定の全県
  python scripts/collect_lineage_b.py report
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
from dotenv import load_dotenv
load_dotenv(_root / ".env")

import anthropic

MODEL = "claude-sonnet-5"
UA = "uranai-monster-shrine-research/1.0 (data verification; contact: ishioka771977@gmail.com)"
INTERVAL = 3.5
MAX_HOPS = 4  # 1県あたりの最大ページ取得数

INDEX_PATH = _root / "data" / "kojindo" / "shrines" / "_jinjacho_index.json"
RAW_A_PATH = _root / "data" / "kojindo" / "shrines" / "_pilot_konohanasakuya_raw.json"
RAW_B_PATH = _root / "data" / "kojindo" / "shrines" / "_pilot_b_konohanasakuya_raw.json"
HTML_CACHE = _root / "data" / "kojindo" / "_html_cache"  # gitignore対象(検品用生HTML)
REPORT_MD = _root / "docs" / f"P2パイロット報告_浅間系_方式B_{date.today().strftime('%Y%m%d')}.md"

DEITY_PATTERNS = ["木花", "咲耶", "サクヤ", "さくや", "浅間大神", "此花"]

SYSTEM = """あなたは神社データベースの調査員。県神社庁の公式サイト内から「浅間神社」
(木花咲耶姫/木花之佐久夜毘売命/浅間大神を祀る神社)を探す。厳守事項:

- 推測禁止。ページに実際に書かれている情報のみを出力。確認できなければ0件でよい
- source_quoteはページ本文からの逐語引用(要約・言い換え禁止)
- 祭神がページ上で確認できない神社は出力しない(社名だけの一覧は不可)
- ページ内に浅間神社の情報がなく、神社検索・神社一覧・「あ行」索引等の
  より適切なページへのリンクがあれば action=follow でそのURLを指定
- 検索フォームがある場合、GETパラメータ形式が推測できるなら follow 先URLとして
  組み立ててよい(例: ?q=浅間神社)。日本語はそのまま書いてよい(取得側でエンコードする)。
  POSTしか無ければ諦めて索引リンク(「あ行」「さ行」等)を辿る"""

SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["follow", "done"]},
            "next_url": {"type": ["string", "null"], "description": "action=followのとき辿るURL(絶対URL)"},
            "shrines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "city": {"type": "string"},
                        "address": {"type": "string"},
                        "main_deity": {"type": "string"},
                        "source_quote": {"type": "string"},
                    },
                    "required": ["name", "city", "address", "main_deity", "source_quote"],
                    "additionalProperties": False,
                },
            },
            "note": {"type": "string"},
        },
        "required": ["action", "next_url", "shrines", "note"],
        "additionalProperties": False,
    },
}


def _encode_url(url: str) -> str:
    """URL中の非ASCII文字をUTF-8パーセントエンコード(鹿児島で文字化け実測 2026-07-11)"""
    return urllib.parse.quote(url, safe=":/?&=%#+~@,;")


def fetch(url: str, timeout: int = 15) -> tuple[int, str]:
    url = _encode_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(500_000)
            for enc in ("utf-8", "shift_jis", "euc-jp", "cp932"):
                try:
                    return r.status, raw.decode(enc)
                except Exception:
                    continue
            return r.status, raw.decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def robots_allows(base_url: str) -> bool:
    """robots.txtで全面Disallowされていないか(くろたん条件1)"""
    m = re.match(r"(https?://[^/]+)", base_url)
    if not m:
        return True
    status, body = fetch(m.group(1) + "/robots.txt", timeout=8)
    if status != 200:
        return True
    ua_all = re.split(r"(?i)user-agent:\s*\*", body)
    if len(ua_all) < 2:
        return True
    section = ua_all[1].split("User-agent:")[0]
    return not re.search(r"(?i)disallow:\s*/\s*$", section, re.M)


def html_to_text_and_links(html: str, base_url: str) -> tuple[str, list[str]]:
    links = []
    for m in re.finditer(r'<a[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        href, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        absu = urllib.parse.urljoin(base_url, href)
        links.append(f"{label[:30]} => {absu}")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:40_000], links[:150]


def collect_pref(client: anthropic.Anthropic, pref: str, entry_url: str) -> dict:
    if not robots_allows(entry_url):
        return {"shrines": [], "search_note": "robots.txtによりクロール不可", "hops": 0}
    url = entry_url
    visited = []
    pages_cache = []
    for hop in range(MAX_HOPS):
        time.sleep(INTERVAL)
        status, html = fetch(url)
        visited.append(url)
        if status != 200:
            return {"shrines": [], "search_note": f"取得失敗 {url} ({status}: {html[:60]})", "hops": hop + 1,
                    "visited": visited}
        cache_name = re.sub(r"[^a-zA-Z0-9]", "_", url)[:80] + ".html"
        HTML_CACHE.mkdir(parents=True, exist_ok=True)
        (HTML_CACHE / cache_name).write_text(html, encoding="utf-8")
        pages_cache.append(cache_name)
        text, links = html_to_text_and_links(html, url)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system=SYSTEM,
            output_config={"format": SCHEMA},
            messages=[{"role": "user", "content": (
                f"対象県: {pref}\n現在のページ: {url}(残り探索回数: {MAX_HOPS - hop - 1})\n"
                f"訪問済み: {visited}\n\n## ページ本文(タグ除去済み)\n{text}\n\n"
                f"## ページ内リンク\n" + "\n".join(links)
            )}],
        )
        payload = json.loads(next(b.text for b in resp.content if b.type == "text"))
        if payload["shrines"] or payload["action"] == "done" or not payload.get("next_url"):
            for s in payload["shrines"]:
                s["source_url"] = url
                s["tier"] = "tier1_auto"  # 県神社庁DB由来
                s["retrieved_at"] = date.today().isoformat()
                s["html_cache"] = cache_name
                if not any(p in (s.get("main_deity") or "") for p in DEITY_PATTERNS):
                    s["tier"] = "rejected_deity_unverified"
            return {"shrines": payload["shrines"], "search_note": payload["note"],
                    "hops": hop + 1, "visited": visited, "html_cache": pages_cache}
        url = payload["next_url"]
    return {"shrines": [], "search_note": "最大探索回数で未到達", "hops": MAX_HOPS, "visited": visited,
            "html_cache": pages_cache}


def run(prefs: list[str] | None = None) -> None:
    index = json.loads(INDEX_PATH.read_text())
    raw_a = json.loads(RAW_A_PATH.read_text()) if RAW_A_PATH.exists() else {"prefs": {}}
    data = json.loads(RAW_B_PATH.read_text()) if RAW_B_PATH.exists() else {"prefs": {}}
    client = anthropic.Anthropic(timeout=240.0, max_retries=1)

    # 対象 = 指定 or (方式A未確定 + 偽ゼロ疑い5県の再検証)
    FALSE_ZERO = ["秋田県", "北海道", "新潟県", "山梨県", "兵庫県"]
    all_prefs = list(index.keys())
    if prefs is None:
        a_ok = {k for k, v in raw_a["prefs"].items() if "error" not in v and v.get("shrines")}
        prefs = [p for p in all_prefs if p not in a_ok or p in FALSE_ZERO]

    for i, pref in enumerate(prefs, 1):
        if pref in data["prefs"] and "error" not in data["prefs"][pref]:
            print(f"[{i}/{len(prefs)}] {pref}: 済", flush=True)
            continue
        entry = index.get(pref, {})
        if not entry.get("url"):
            data["prefs"][pref] = {
                "shrines": [], "search_note": entry.get("note", "神社庁サイトなし"),
                "source_type_note": "県神社庁DB不存在につき代替(本走行で神社公式・自治体ソース収集)",
            }
            print(f"[{i}/{len(prefs)}] {pref}: 代替扱い(庁サイトなし)", flush=True)
        else:
            t0 = time.time()
            try:
                rec = collect_pref(client, pref, entry["url"])
                print(f"[{i}/{len(prefs)}] {pref}: {len(rec['shrines'])}社 hops={rec['hops']} ({time.time()-t0:.0f}s)", flush=True)
            except Exception as e:
                rec = {"error": f"{type(e).__name__}: {e}"}
                print(f"[{i}/{len(prefs)}] {pref}: ERROR {str(e)[:70]}", flush=True)
            data["prefs"][pref] = rec
        RAW_B_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"raw(B) -> {RAW_B_PATH}")


def report() -> None:
    raw_a = json.loads(RAW_A_PATH.read_text()) if RAW_A_PATH.exists() else {"prefs": {}}
    raw_b = json.loads(RAW_B_PATH.read_text()) if RAW_B_PATH.exists() else {"prefs": {}}
    merged, seen = [], set()
    for src, raw in (("A", raw_a), ("B", raw_b)):
        for pref, rec in raw["prefs"].items():
            if "error" in rec:
                continue
            for s in rec.get("shrines", []):
                key = (pref, s["name"])
                if key in seen:
                    continue
                seen.add(key)
                s["_pref"] = pref
                s["_method"] = src
                merged.append(s)
    usable = [s for s in merged if not s["tier"].startswith("rejected")]
    zero_prefs = [p for p in set(list(raw_a["prefs"]) + list(raw_b["prefs"]))
                  if not any(s["_pref"] == p for s in usable)]
    errors = [(p, r["error"][:60]) for p, r in raw_b["prefs"].items() if "error" in r]
    lines = [
        f"# P2パイロット報告: 浅間系(方式A+B統合・{date.today().isoformat()})",
        "",
        f"- 収集: {len(merged)}社(方式A {sum(1 for s in merged if s['_method']=='A')} / 方式B {sum(1 for s in merged if s['_method']=='B')})",
        f"- 採用候補: {len(usable)}社 / 祭神未確認棄却: {len(merged)-len(usable)}",
        f"- 0社県: {len(zero_prefs)} / エラー: {len(errors)}",
        "",
        "## サンプル20件(くろたんレビュー用)",
        "",
        "| # | 県 | 社名 | 主祭神(出典記載) | 方式 | 出典 | 引用(冒頭60字) |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(usable[:20], 1):
        q = (s.get("source_quote") or "")[:60].replace("|", "｜").replace("\n", " ")
        lines.append(f"| {i} | {s['_pref']} | {s['name']} | {s['main_deity'][:16]} | {s['_method']} | {s['source_url'][:44]} | {q} |")
    if errors:
        lines += ["", "## エラー", ""] + [f"- {p}: {e}" for p, e in errors]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {REPORT_MD} / 採用候補{len(usable)}社")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        run(["秋田県", "富山県", "鹿児島県"])
    elif cmd == "run":
        run()
    elif cmd == "report":
        report()
    else:
        print(__doc__)
