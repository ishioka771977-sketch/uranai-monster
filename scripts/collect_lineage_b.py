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
MAX_HOPS = 6  # 1県あたりの最大ページ取得数(4では区別・支部別インデックスの県で不足=京都で実測)

INDEX_PATH = _root / "data" / "kojindo" / "shrines" / "_jinjacho_index.json"
RAW_A_PATH = _root / "data" / "kojindo" / "shrines" / "_pilot_konohanasakuya_raw.json"
HTML_CACHE = _root / "data" / "kojindo" / "_html_cache"  # gitignore対象(検品用生HTML)
REPORT_MD = _root / "docs" / f"P2パイロット報告_浅間系_方式B_{date.today().strftime('%Y%m%d')}.md"

# 10系列の定義(系統ラベルは sohonsha_v3.json 準拠・祭神パターンは採用判定に使用)
LINEAGES = {
    "konohanasakuya": {
        "label": "浅間系", "target": "浅間神社",
        "keywords": ["浅間"],
        "deity_desc": "木花咲耶姫命/木花之佐久夜毘売命/浅間大神",
        "deity_patterns": ["木花", "咲耶", "サクヤ", "さくや", "浅間大神", "此花", "佐久夜", "咲夜"],
    },
    "oyamatsumi": {
        "label": "三島・山祇系", "target": "大山祇神社・三島神社・山祇神社",
        "keywords": ["大山祇", "三島", "山祇"],
        "deity_desc": "大山祇神/大山積大神/大山津見神",
        "deity_patterns": ["大山祇", "大山積", "大山津見", "大山つみ"],
    },
    "amaterasu": {
        "label": "神明系", "target": "神明社・神明宮・皇大神社・天祖神社",
        "keywords": ["神明", "皇大神", "天祖"],
        "deity_desc": "天照大御神/天照大神/天照皇大神",
        "deity_patterns": ["天照"],
    },
    "tsukuyomi": {
        "label": "月読系", "target": "月読神社・月讀神社・月夜見神社・月山神社",
        "keywords": ["月読", "月讀", "月夜見", "月山"],
        "deity_desc": "月読命/月讀尊/月夜見尊",
        "deity_patterns": ["月読", "月讀", "月夜見", "月弓"],
    },
    "izanagi": {
        "label": "伊弉諾・多賀系", "target": "多賀神社・伊弉諾神社",
        "keywords": ["多賀", "伊弉諾", "伊邪那岐"],
        "deity_desc": "伊弉諾尊/伊邪那岐命",
        "deity_patterns": ["伊弉諾", "伊邪那岐", "伊耶那岐", "伊奘諾", "イザナギ", "いざなぎ"],
    },
    "okuninushi": {
        "label": "出雲系", "target": "出雲神社・大国主神社・大己貴神社・大國魂神社",
        "keywords": ["出雲", "大国主", "大己貴", "大國魂"],
        "deity_desc": "大国主命/大國主大神/大己貴命/大穴牟遅神",
        "deity_patterns": ["大国主", "大國主", "大己貴", "大穴牟遅", "大穴持", "オオクニヌシ"],
    },
    "susanoo": {
        "label": "祇園・八坂/氷川/須佐系", "target": "八坂神社・祇園神社・氷川神社・須賀神社・津島神社・素盞嗚神社",
        "keywords": ["八坂", "氷川", "須賀", "津島", "素盞", "素戔", "祇園"],
        "deity_desc": "素戔嗚尊/素盞嗚命/須佐之男命",
        "deity_patterns": ["素戔", "素盞", "須佐之男", "須佐能", "すさのお", "スサノオ"],
    },
    "ninigi": {
        "label": "霧島系", "target": "霧島神社・瓊瓊杵尊を祀る神社(新田神社等)",
        "keywords": ["霧島", "瓊瓊杵", "邇邇芸"],
        "deity_desc": "瓊瓊杵尊/邇邇芸命/天津日高彦火瓊瓊杵尊",
        "deity_patterns": ["瓊瓊杵", "瓊々杵", "邇邇芸", "邇々芸", "ニニギ", "瓊杵"],
    },
    "watatsumi": {
        "label": "綿津見系", "target": "海神社・綿津見神社・志賀神社・和多都美神社",
        "keywords": ["綿津見", "海神", "志賀", "和多都美"],
        "deity_desc": "綿津見神(底津・仲津・上津綿津見神)/少童命",
        "deity_patterns": ["綿津見", "少童", "和多都美", "海神", "わたつみ", "ワタツミ"],
    },
    "seoritsuhime": {
        "label": "祓戸系", "target": "祓戸神社・瀬織津姫を祀る神社",
        "keywords": ["祓戸", "瀬織津"],
        "deity_desc": "瀬織津姫命/祓戸大神",
        "deity_patterns": ["瀬織津", "祓戸"],
    },
}


def raw_b_path(god_id: str) -> Path:
    """系列ごとの方式B生データファイル(浅間はパイロットのファイルを継続使用)"""
    if god_id == "konohanasakuya":
        return _root / "data" / "kojindo" / "shrines" / "_pilot_b_konohanasakuya_raw.json"
    return _root / "data" / "kojindo" / "shrines" / f"_run_b_{god_id}_raw.json"


RAW_B_PATH = raw_b_path("konohanasakuya")  # 後方互換(report()は浅間パイロット用)


def build_system(lin: dict) -> str:
    kws = "・".join(lin["keywords"])
    return f"""あなたは神社データベースの調査員。県神社庁の公式サイト内から「{lin['target']}」
({lin['deity_desc']} を祀る{lin['label']}の神社)を探す。厳守事項:

- 推測禁止。ページに実際に書かれている情報のみを出力。確認できなければ0件でよい
- source_quoteはページ本文からの逐語引用(要約・言い換え禁止)
- 祭神がページ上で確認できない神社は出力しない(社名だけの一覧は不可)
- 対象の情報がなく、神社検索・神社一覧・「あ行」索引等の
  より適切なページへのリンクがあれば action=follow でそのURLを指定
- 検索フォームがある場合、GETパラメータ形式が推測できるなら follow 先URLとして
  組み立ててよい(例: ?q={lin['keywords'][0]})。日本語はそのまま書いてよい(取得側でエンコードする)。
  POSTしか無ければ諦めて索引リンク(「あ行」「さ行」等)を辿る
- 検索キーワードは「{kws}」のような短い形を優先する(「〜神社」まで付けると
  完全一致検索で別表記が漏れる。新潟で実測)。複数キーワードは順に試してよい
- 神社を発見してもaction=followで探索を続けてよい(発見分は蓄積される)。
  同じ県内に対象の神社がまだありそうなら索引・検索を続ける(目安: 県ごとに1〜3社確保できれば十分)
- 祭神は詳細ページにしか無いことが多い。一覧で対象らしき社名を見つけたら
  その詳細ページへfollowして祭神を確認する"""

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
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(3_000_000)  # 500KBでは<head>肥大サイトで本文に届かない(山梨で実測)
                for enc in ("utf-8", "shift_jis", "euc-jp", "cp932"):
                    try:
                        return r.status, raw.decode(enc)
                    except Exception:
                        continue
                return r.status, raw.decode("utf-8", errors="replace")
        except Exception as e:
            # TLSバージョン不一致対策(山形で実測: PythonのLibreSSLがTLS1.3を話せず
            # サーバー側がTLS1.3必須)。SSL系の失敗はcurlで1回だけ再試行
            if "SSL" in str(e) or "TLS" in str(e):
                return _fetch_via_curl(url, timeout)
            raise
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _fetch_via_curl(url: str, timeout: int = 15) -> tuple[int, str]:
    import subprocess
    try:
        p = subprocess.run(
            ["curl", "-sL", "-m", str(timeout), "-A", UA,
             "-w", "\n__HTTP_STATUS__%{http_code}", url],
            capture_output=True, timeout=timeout + 5,
        )
        raw = p.stdout[:3_000_000]
        m = re.search(rb"__HTTP_STATUS__(\d+)\s*$", raw)
        status = int(m.group(1)) if m else 0
        body_raw = re.sub(rb"\n__HTTP_STATUS__\d+\s*$", b"", raw)
        for enc in ("utf-8", "shift_jis", "euc-jp", "cp932"):
            try:
                return status, body_raw.decode(enc)
            except Exception:
                continue
        return status, body_raw.decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"curl-fallback {type(e).__name__}: {e}"


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
    seen = set()
    # 引用符はダブル/シングル両対応(山梨・三重の取りこぼし対策)
    for m in re.finditer(r'''<a[^>]*?href=["']([^"'#]+)["'][^>]*>(.*?)</a>''', html, re.S | re.I):
        href, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        absu = urllib.parse.urljoin(base_url, href)
        if absu in seen:
            continue
        seen.add(absu)
        links.append(f"{label[:30]} => {absu}")
    # 神社検索・一覧・索引に関わるリンクを優先して上限内に残す
    KEY = ("検索", "一覧", "索引", "神社", "浅間", "さ行", "あ行", "search", "list", "jinja", "shrine", "map")
    links.sort(key=lambda s: 0 if any(k in s.lower() for k in KEY) else 1)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:40_000], links[:200]


def extract_forms(html: str, base_url: str) -> list[str]:
    """検索フォームのaction/method/入力欄名を抽出(山梨で実測:
    パラメータ名がjinjaNameでモデルの推測keyword=では検索不能だった)"""
    forms = []
    for fm in re.finditer(r"<form\b[^>]*>(.*?)</form>", html, re.S | re.I):
        tag = fm.group(0)[: fm.group(0).find(">") + 1]
        action_m = re.search(r'''action=["']([^"']*)["']''', tag, re.I)
        method_m = re.search(r'''method=["']([^"']*)["']''', tag, re.I)
        action = urllib.parse.urljoin(base_url, action_m.group(1)) if action_m else base_url
        method = (method_m.group(1) if method_m else "GET").upper()
        names = re.findall(r'''<(?:input|select|textarea)[^>]*?name=["']([^"']+)["']''', fm.group(1), re.I)
        if names:
            forms.append(f"action={action} method={method} fields={sorted(set(names))}")
    return forms[:10]


def collect_pref(client: anthropic.Anthropic, pref: str, entry_url: str,
                 lin: dict | None = None) -> dict:
    lin = lin or LINEAGES["konohanasakuya"]
    if not robots_allows(entry_url):
        return {"shrines": [], "search_note": "robots.txtによりクロール不可", "hops": 0}
    url = entry_url
    visited = []
    pages_cache = []
    found = []
    notes = []
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
        forms = extract_forms(html, url)
        forms_sec = ("\n\n## 検索フォーム(action/method/入力欄名。GETならこのフィールド名でURLを組み立てられる)\n"
                     + "\n".join(forms)) if forms else ""
        resp = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system=build_system(lin),
            output_config={"format": SCHEMA},
            messages=[{"role": "user", "content": (
                f"対象県: {pref}\n現在のページ: {url}(残り探索回数: {MAX_HOPS - hop - 1})\n"
                f"訪問済み: {visited}\n\n## ページ本文(タグ除去済み)\n{text}\n\n"
                f"## ページ内リンク\n" + "\n".join(links) + forms_sec
            )}],
        )
        payload = json.loads(next(b.text for b in resp.content if b.type == "text"))
        for s in payload["shrines"]:
            s["source_url"] = url
            s["tier"] = "tier1_auto"  # 県神社庁DB由来
            s["retrieved_at"] = date.today().isoformat()
            s["html_cache"] = cache_name
            if not any(p in (s.get("main_deity") or "") for p in lin["deity_patterns"]):
                s["tier"] = "rejected_deity_unverified"
            # 発見分は蓄積し、探索は action に従い継続(初版は発見即終了で途中打ち切りだった)
            if not any(f.get("name") == s.get("name") for f in found):
                found.append(s)
        notes.append(payload["note"])
        next_url = payload.get("next_url")
        if payload["action"] == "done" or not next_url or next_url in visited:
            return {"shrines": found, "search_note": " / ".join(n for n in notes if n),
                    "hops": hop + 1, "visited": visited, "html_cache": pages_cache}
        url = next_url
    return {"shrines": found, "search_note": "最大探索回数到達: " + " / ".join(n for n in notes if n),
            "hops": MAX_HOPS, "visited": visited, "html_cache": pages_cache}


def run(prefs: list[str] | None = None, god_id: str = "konohanasakuya",
        offset: int = 0) -> None:
    """1系列×県リストの収集走行。

    offset: 県リストの回転開始位置。並列ワーカーが同一ドメインに
    同時アクセスしないよう、ワーカーごとにずらす(クローリングマナー)。
    """
    lin = LINEAGES[god_id]
    out_path = raw_b_path(god_id)
    index = json.loads(INDEX_PATH.read_text())
    raw_a = json.loads(RAW_A_PATH.read_text()) if RAW_A_PATH.exists() else {"prefs": {}}
    data = json.loads(out_path.read_text()) if out_path.exists() else {"prefs": {}}
    client = anthropic.Anthropic(timeout=240.0, max_retries=1)

    all_prefs = list(index.keys())
    if prefs is None:
        if god_id == "konohanasakuya":
            # パイロット互換: 方式A未確定 + 偽ゼロ疑い5県の再検証
            FALSE_ZERO = ["秋田県", "北海道", "新潟県", "山梨県", "兵庫県"]
            a_ok = {k for k, v in raw_a["prefs"].items() if "error" not in v and v.get("shrines")}
            prefs = [p for p in all_prefs if p not in a_ok or p in FALSE_ZERO]
        else:
            prefs = all_prefs
    prefs = prefs[offset:] + prefs[:offset]

    for i, pref in enumerate(prefs, 1):
        if pref in data["prefs"] and "error" not in data["prefs"][pref]:
            print(f"[{god_id} {i}/{len(prefs)}] {pref}: 済", flush=True)
            continue
        entry = index.get(pref, {})
        if not entry.get("url"):
            data["prefs"][pref] = {
                "shrines": [], "search_note": entry.get("note", "神社庁サイトなし"),
                "source_type_note": "県神社庁DB不存在につき代替(本走行で神社公式・自治体ソース収集)",
            }
            print(f"[{god_id} {i}/{len(prefs)}] {pref}: 代替扱い(庁サイトなし)", flush=True)
        else:
            t0 = time.time()
            try:
                # search_url(検索結果URL雛形・実在確認済み)があれば入口として優先。
                # {kw} プレースホルダに系列の第一キーワードを差し込む
                su = entry.get("search_url")
                start = su.replace("{kw}", lin["keywords"][0]) if su else entry["url"]
                rec = collect_pref(client, pref, start, lin)
                print(f"[{god_id} {i}/{len(prefs)}] {pref}: {len(rec['shrines'])}社 hops={rec['hops']} ({time.time()-t0:.0f}s)", flush=True)
            except Exception as e:
                rec = {"error": f"{type(e).__name__}: {e}"}
                print(f"[{god_id} {i}/{len(prefs)}] {pref}: ERROR {str(e)[:70]}", flush=True)
            data["prefs"][pref] = rec
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"raw(B) -> {out_path}")


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
    all_prefs = set(list(raw_a["prefs"]) + list(raw_b["prefs"]))
    zero_prefs = sorted(p for p in all_prefs if not any(s["_pref"] == p for s in usable))
    errors = [(p, r["error"][:60]) for p, r in raw_b["prefs"].items() if "error" in r]
    reject_rate = (len(merged) - len(usable)) / len(merged) * 100 if merged else 0.0
    lines = [
        f"# P2パイロット報告: 浅間系(方式A+B統合・{date.today().isoformat()})",
        "",
        f"- 収集: {len(merged)}社(方式A {sum(1 for s in merged if s['_method']=='A')} / 方式B {sum(1 for s in merged if s['_method']=='B')})",
        f"- 採用候補: {len(usable)}社 / 祭神未確認棄却: {len(merged)-len(usable)}社(棄却率 {reject_rate:.0f}%)",
        f"- 有社県: {len(all_prefs)-len(zero_prefs)} / 0社県: {len(zero_prefs)} / エラー: {len(errors)}",
        "",
        "## サンプル20件(くろたんレビュー用・県ラウンドロビンで多様化)",
        "",
        "| # | 県 | 社名 | 主祭神(出典記載) | 方式 | 出典 | 引用(冒頭60字) |",
        "|---|---|---|---|---|---|---|",
    ]
    # 県ごとに巡回で1件ずつ取り20件に(特定県の大量ヒットで埋まるのを防ぐ)
    by_pref: dict[str, list] = {}
    for s in usable:
        by_pref.setdefault(s["_pref"], []).append(s)
    sample = []
    while len(sample) < 20 and any(by_pref.values()):
        for p in sorted(by_pref):
            if by_pref[p] and len(sample) < 20:
                sample.append(by_pref[p].pop(0))
    for i, s in enumerate(sample, 1):
        q = (s.get("source_quote") or "")[:60].replace("|", "｜").replace("\n", " ")
        lines.append(f"| {i} | {s['_pref']} | {s['name']} | {s['main_deity'][:16]} | {s['_method']} | {s['source_url'][:44]} | {q} |")
    lines += ["", "## 0社県と理由", "", "| 県 | 分類 | 備考(調査ノートより) |", "|---|---|---|"]
    for p in zero_prefs:
        rec = raw_b["prefs"].get(p) or raw_a["prefs"].get(p) or {}
        note = (rec.get("source_type_note") or rec.get("search_note") or "")[:70].replace("|", "｜").replace("\n", " ")
        if rec.get("source_type_note"):
            cat = "代替扱い(庁DB不存在)"
        elif "error" in rec:
            cat = "エラー"
        else:
            cat = "庁DB上で未確認"
        lines.append(f"| {p} | {cat} | {note} |")
    if errors:
        lines += ["", "## エラー", ""] + [f"- {p}: {e}" for p, e in errors]
    lines += [
        "",
        "## 県別収量(採用候補)",
        "",
        "| 県 | 社数 | 方式 |",
        "|---|---|---|",
    ]
    counts: dict[str, list] = {}
    for s in usable:
        counts.setdefault(s["_pref"], []).append(s["_method"])
    for p in sorted(counts):
        lines.append(f"| {p} | {len(counts[p])} | {'/'.join(sorted(set(counts[p])))} |")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {REPORT_MD} / 採用候補{len(usable)}社 / 0社県{len(zero_prefs)}")


def export_lineage() -> None:
    """全系列の採用候補をアプリ用 data/kojindo/shrines/lineage_v3.json に書き出す
    (core/kojindo.get_shrine_recommendation の二段目データソース)"""
    out = []
    for god_id, lin in LINEAGES.items():
        raws = []
        if god_id == "konohanasakuya" and RAW_A_PATH.exists():
            raws.append(("A", json.loads(RAW_A_PATH.read_text())))
        bp = raw_b_path(god_id)
        if bp.exists():
            raws.append(("B", json.loads(bp.read_text())))
        seen = set()
        n0 = len(out)
        for src, raw in raws:
            for pref, rec in raw["prefs"].items():
                if "error" in rec:
                    continue
                for s in rec.get("shrines", []):
                    if s.get("tier", "").startswith("rejected"):
                        continue
                    key = (pref, s["name"])
                    if key in seen:
                        continue
                    seen.add(key)
                    deity = s.get("main_deity")
                    out.append({
                        "lineage": lin["label"],
                        "god_id": god_id,
                        "pref": pref,
                        "name": s["name"],
                        "city": s.get("address") or s.get("city") or "",
                        "main_deity": deity if isinstance(deity, list) else [deity or ""],
                        "sources": [{
                            "url": s.get("source_url", ""),
                            "quote": s.get("source_quote", ""),
                            "retrieved_at": s.get("retrieved_at", ""),
                            "source_type": "県神社庁DB" if src != "A" else "神社公式等(方式A検証済み)",
                        }],
                    })
        print(f"  {god_id}: {len(out) - n0}社")
    p = _root / "data" / "kojindo" / "shrines" / "lineage_v3.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"lineage -> {p} / {len(out)}社")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        run(["秋田県", "富山県", "鹿児島県"])
    elif cmd == "run":
        # run [god_id] [offset] — 本走行は系列単位で実行(並列ワーカーはoffsetをずらす)
        gid = sys.argv[2] if len(sys.argv) > 2 else "konohanasakuya"
        off = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        run(god_id=gid, offset=off)
    elif cmd == "report":
        report()
    elif cmd == "export":
        export_lineage()
    else:
        print(__doc__)
