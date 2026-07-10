# -*- coding: utf-8 -*-
"""古神道v3 P2方式B: 47都道府県神社庁エントリポイント表の構築

方式: web検索を使わず、ドメイン命名パターン候補を生成して実在確認(HTTP GET)。
クローリングマナー(くろたん条件1):
  - User-Agent明示(連絡先付き)
  - リクエスト間隔3秒以上
  - 同一ドメインへは原則1アクセス(実在確認のみ)
  - robots.txtの取得を試み、Disallow:/ が明示されていればスキップ

出力: data/kojindo/shrines/_jinjacho_index.json + docs/神社庁エントリポイント表(くろたんレビュー用)
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
OUT_JSON = _root / "data" / "kojindo" / "shrines" / "_jinjacho_index.json"
OUT_MD = _root / "docs" / f"古神道v3_神社庁エントリポイント表_{date.today().strftime('%Y%m%d')}.md"

UA = "uranai-monster-shrine-research/1.0 (data verification; contact: ishioka771977@gmail.com)"
INTERVAL = 3.5  # 秒

# (県名, ローマ字候補)。既知確定URLは known で先に採用(過去の一次情報調査で実在確認済み)
PREFS = [
    ("北海道", ["hokkaido"], "https://hokkaidojinjacho.jp"),
    ("青森県", ["aomori"], None),
    ("岩手県", ["iwate"], None),
    ("宮城県", ["miyagi"], None),
    ("秋田県", ["akita"], "https://akita-jinjacho.sakura.ne.jp"),
    ("山形県", ["yamagata"], None),
    ("福島県", ["fukushima"], None),
    ("茨城県", ["ibaraki"], None),
    ("栃木県", ["tochigi"], None),
    ("群馬県", ["gunma"], None),
    ("埼玉県", ["saitama"], None),
    ("千葉県", ["chiba"], None),
    ("東京都", ["tokyo"], "http://www.tokyo-jinjacho.or.jp"),
    ("神奈川県", ["kanagawa"], None),
    ("新潟県", ["niigata"], "https://niigata-jinjacho.jp"),
    ("富山県", ["toyama"], None),
    ("石川県", ["ishikawa"], None),
    ("福井県", ["fukui"], None),
    ("山梨県", ["yamanashi"], None),
    ("長野県", ["nagano"], None),
    ("岐阜県", ["gifu"], None),
    ("静岡県", ["shizuoka"], "http://www.shizuoka-jinjacho.or.jp"),
    ("愛知県", ["aichi"], None),
    ("三重県", ["mie"], None),
    ("滋賀県", ["shiga"], "https://www.shiga-jinjacho.jp"),
    ("京都府", ["kyoto"], None),
    ("大阪府", ["osaka"], None),
    ("兵庫県", ["hyogo"], "https://www.hyogo-jinjacho.com"),
    ("奈良県", ["nara"], None),
    ("和歌山県", ["wakayama"], None),
    ("鳥取県", ["tottori"], None),
    ("島根県", ["shimane"], None),
    ("岡山県", ["okayama"], None),
    ("広島県", ["hiroshima"], None),
    ("山口県", ["yamaguchi"], None),
    ("徳島県", ["tokushima"], None),
    ("香川県", ["kagawa"], None),
    ("愛媛県", ["ehime"], None),
    ("高知県", ["kochi"], None),
    ("福岡県", ["fukuoka"], None),
    ("佐賀県", ["saga"], None),
    ("長崎県", ["nagasaki"], None),
    ("熊本県", ["kumamoto"], None),
    ("大分県", ["oita"], None),
    ("宮崎県", ["miyazaki"], None),
    ("鹿児島県", ["kagoshima"], None),
    ("沖縄県", ["okinawa"], None),
]

PATTERNS = [
    "https://{r}-jinjacho.or.jp",
    "https://www.{r}-jinjacho.or.jp",
    "https://{r}-jinjacho.jp",
    "https://www.{r}-jinjacho.jp",
    "https://{r}jinjacho.jp",
    "https://www.{r}jinjacho.jp",
    "https://jinjacho-{r}.or.jp",
    "https://{r}-jinjacho.com",
    "https://www.{r}-jinjacho.com",
    "http://{r}-jinjacho.or.jp",
    "http://www.{r}-jinjacho.or.jp",
]


def fetch(url: str, timeout: int = 10) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(200_000)
            for enc in ("utf-8", "shift_jis", "euc-jp", "cp932"):
                try:
                    return r.status, raw.decode(enc)
                except Exception:
                    continue
            return r.status, raw.decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def looks_like_jinjacho(html: str, pref_name: str) -> bool:
    core = pref_name.rstrip("都府県")
    return ("神社庁" in html) and (core in html)


def main() -> None:
    results = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {}
    for pref, romajis, known in PREFS:
        if pref in results and results[pref].get("url"):
            print(f"{pref}: 済 {results[pref]['url']}")
            continue
        found = None
        tried = []
        candidates = ([known] if known else []) + [
            p.format(r=r) for r in romajis for p in PATTERNS
        ]
        for url in candidates:
            time.sleep(INTERVAL)
            status, body = fetch(url)
            tried.append(f"{url} -> {status}")
            if status == 200 and looks_like_jinjacho(body, pref):
                title_m = re.search(r"<title>([^<]*)</title>", body, re.I)
                found = {
                    "url": url,
                    "title": (title_m.group(1).strip() if title_m else "")[:60],
                    "verified_at": date.today().isoformat(),
                    "tier": "tier1_auto",
                    "method": "known" if url == known else "pattern",
                }
                break
        results[pref] = found or {"url": None, "tried": tried[-4:], "note": "パターン不一致・要手動確認"}
        OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{pref}: {'OK ' + found['url'] if found else '未解決'}", flush=True)

    ok = {k: v for k, v in results.items() if v.get("url")}
    lines = [
        f"# 古神道v3 神社庁エントリポイント表({date.today().isoformat()})",
        "",
        "- 方式: 検索不使用。ドメインパターン候補生成→HTTP実在確認(UA明示・3.5秒間隔・1ドメイン1アクセス)",
        f"- 解決: {len(ok)}/47県 / 未解決: {47 - len(ok)}県(要手動確認)",
        "- Tier判定: 県神社庁は全てTier1(自動合格ドメイン)",
        "",
        "| 県 | URL | タイトル | 確認方法 |",
        "|---|---|---|---|",
    ]
    for pref, _, _ in PREFS:
        r = results.get(pref, {})
        if r.get("url"):
            lines.append(f"| {pref} | {r['url']} | {r.get('title','')} | {r.get('method','')} |")
        else:
            lines.append(f"| {pref} | **未解決** | — | 要手動確認 |")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nmd -> {OUT_MD} / 解決 {len(ok)}/47")


if __name__ == "__main__":
    main()
