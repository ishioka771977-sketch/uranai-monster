# -*- coding: utf-8 -*-
"""読み比べmd → 評価用HTMLページ(Artifact用)。正解は含めない。

  .venv/bin/python scripts/build_blind_page.py docs/読み比べ本人版_Fable51vsOpus55_YYYYMMDD.md out.html
"""
import html
import json
import re
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
md = src.read_text(encoding="utf-8")

courses = []  # [{name, A:{headline, body}, B:{...}}]
for block in re.split(r"^# 【", md, flags=re.M)[1:]:
    name = block.split("】", 1)[0]
    c = {"name": name}
    for label in "AB":
        m = re.search(rf"^## {re.escape(name)}−{label}\n\n(.*?)(?=^## |\Z|^---)", block, flags=re.M | re.S)
        body = m.group(1).strip() if m else ""
        hm = re.match(r"\*\*「(.*?)」\*\*\n\n", body)
        c[label] = {"headline": hm.group(1) if hm else "", "body": body[hm.end():] if hm else body}
    courses.append(c)


def paras(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    return "".join(f"<p>{html.escape(p.strip())}</p>" for p in re.split(r"\n\s*\n", t) if p.strip())


tabs, panes = [], []
for i, c in enumerate(courses):
    tabs.append(f'<button class="tab" role="tab" id="tab-{i}" data-i="{i}" aria-selected="{str(i==0).lower()}">'
                f'<span>{html.escape(c["name"])}</span><b class="pick" id="pick-{i}"></b></button>')
    cols = ""
    for L in "AB":
        n = len(re.sub(r"\s", "", c[L]["body"]))
        cols += (f'<article class="reading"><header><span class="lbl">{L}</span>'
                 f'<span class="len">{n:,}字</span></header>'
                 f'<h3>「{html.escape(c[L]["headline"])}」</h3>{paras(c[L]["body"])}</article>')
    panes.append(
        f'<section class="pane" id="pane-{i}" role="tabpanel" aria-labelledby="tab-{i}"{"" if i==0 else " hidden"}>'
        f'<div class="pair">{cols}</div>'
        f'<div class="vote" role="group" aria-label="{html.escape(c["name"])}の判定">'
        f'<span class="q">{html.escape(c["name"])}はどっちが良い？</span>'
        f'<button id="v-{i}-A" data-i="{i}" data-v="A">Aが良い</button>'
        f'<button id="v-{i}-=" data-i="{i}" data-v="=">引き分け</button>'
        f'<button id="v-{i}-B" data-i="{i}" data-v="B">Bが良い</button></div></section>')

names = json.dumps([c["name"] for c in courses], ensure_ascii=False)
page = (Path(__file__).with_name("blind_page_template.html").read_text(encoding="utf-8")
        .replace("{{TABS}}", "".join(tabs)).replace("{{PANES}}", "".join(panes))
        .replace("{{NAMES}}", names).replace("{{N}}", str(len(courses))))
out.write_text(page, encoding="utf-8")
print(f"{out} ({len(courses)}占術)")
