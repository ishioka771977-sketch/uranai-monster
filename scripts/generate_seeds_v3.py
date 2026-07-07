# -*- coding: utf-8 -*-
"""古神道v3 P3: 意識の種120本バッチ生成(十干10×月支12)

設計: docs/古神道v3_P3プロンプト設計案_20260704.md(くろたん承認 2026-07-05)
月支定義: docs/古神道v3_月支定義表草案_20260704.md(くろたん確定 2026-07-05)
モデル: claude-fable-5 / Batches API(50%オフ) / 構造化出力(strict)

使い方:
  python scripts/generate_seeds_v3.py submit   # バッチ投入(batch_idを保存)
  python scripts/generate_seeds_v3.py collect  # 結果回収+検品+格納+官能評価md生成
  python scripts/generate_seeds_v3.py retry 甲_子 乙_午 ...  # NGセルのみ再生成(通常API)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from core.kojindo import JIKKAN_GUARDIAN_TABLE

MODEL = "claude-fable-5"
BATCH_ID_FILE = _root / "data" / "kojindo" / "_seeds_v3_batch_id.txt"
OUT_JSON = _root / "data" / "kojindo" / "seeds_v3.json"
OUT_MD = _root / "docs" / f"意識の種120本_官能評価用_{date.today().strftime('%Y%m%d')}.md"

# ============================================================
# 母体: 骨格版の意識の種10本(丙のみくろたん改訂版 2026-07-05)
# ============================================================
SEEDS_BASE = {
    "甲": "「大樹のように、動かず・急がず・根を張る」——参拝前に、いま自分が根を張るべき場所を一つ言葉にしてから鳥居をくぐる",
    "乙": "「散ることを恐れず、いま咲く」——完璧を待たずに始めたいことを一つ胸に置いて参拝する",
    "丙": "「願う前に、照らされていることに気づく」——正宮では日々への感謝だけを述べる。特別な願いがあるなら、神楽殿でのご祈祷という正式な作法へ。",
    "丁": "「語らぬものの声を聴く」——参拝前に3分、スマホを閉じて無言の時間を作ってから拝殿へ",
    "戊": "「創る前に、区切る」——新しく始める前に終わらせるべきことを一つ決めて参拝する",
    "己": "「願うのではなく、育てたい縁を名乗る」——結びたい縁(人・仕事・土地)を具体的に一つ、心中で名乗ってから四拍手する",
    "庚": "「断つものを決めてから、くぐる」——切り捨てたい習慣・関係・迷いを一つ決めてから鳥居をくぐる",
    "辛": "「磨かれるために、降りる」——安全圏から一段降りて挑む場面を一つ思い描いて参拝する",
    "壬": "「流れに逆らわず、潮目を読む」——いま自分が満ち潮か引き潮かを一言で言い切ってから参拝する",
    "癸": "「流してから、入れる」——手水を「洗う」でなく「流し去る」意識で行い、手放したいものを水に託してから拝殿へ",
}

# ============================================================
# 月支12種の顕れ方(くろたん確定 2026-07-05・出典: 月支定義表)
# ============================================================
GETSU_SHI_APPEARANCE = {
    "子": "誰も見ていない夜のうちに、最初の一滴が動き出す。静かな始動——顕れは水面下から",
    "丑": "凍った土の下の貯蔵庫。溜めてから動く——顕れは満ちるまで出てこない",
    "寅": "夜明けと同時に踏み出す。火種ごと進む——顕れは最初の一歩の勢いに出る",
    "卯": "硬い幹ではなく、枝葉として四方へ。しなやかに広がる——顕れは柔らかさと数",
    "辰": "異質なものを腹に呑んで、うねりにする。混ざりを束ねる——顕れは編集力",
    "巳": "表に出る前に、内側で先に燃えている。内燃から外へ——顕れは温度差の一撃",
    "午": "真昼の道に影はない。直進して照らす——顕れは隠さないこと・即答",
    "未": "火を止めたあと、味がしみていく時間。熟成させる——顕れは引き際のあとに残る",
    "申": "使う道具を素早く持ち替える。切り替えの速さ——顕れは手数と実務",
    "酉": "九割できたものを、最後の一磨きで別物にする。仕上げの純度——顕れは削ぎ落とし",
    "戌": "消えかけの火種を懐で守る番人。締めて守る——顕れは戸締まりと継続",
    "亥": "深く潜って、次の春の仕込みをする。潜って仕込む——顕れは見えない準備",
}

SYSTEM_PROMPT = """あなたは「占いモンスターくろたん」の古神道v3・意識の種ライター。

## 血統ルール(最重要)
- 母体の「意識の種」の核概念を必ず保持する。別の人格・別の教えを創作しない
- 母体のフレーズの言い換えではなく、月支の顕れ方で「具体化」する

## トーン(宗教勧誘の回避)
- 「〜すべき」「必ず」「ご利益」「救われる」等の断定・利益保証は禁止
- 命令形ではなく「〜してから鳥居をくぐる」等の提案形
- 宗教の勧誘ではなく、文化的な所作の案内として書く

## 形式
- phrase: 20字以内の一行(「」で括れる強度)
- action: 参拝前に1分でできる具体的所作を1つ(数値・五感を含む)"""

OUTPUT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "phrase": {"type": "string", "description": "意識の種フレーズ(20字以内・一行)"},
            "action": {"type": "string", "description": "参拝前1分の具体的所作(数値・五感を含む)"},
            "note": {"type": "string", "description": "設計メモ(任意・ユーザー非表示)"},
        },
        "required": ["phrase", "action", "note"],
        "additionalProperties": False,
    },
}

NG_WORDS = ["すべき", "必ず", "ご利益", "救われる", "開運確実", "絶対に"]
JIKKAN = list(SEEDS_BASE.keys())
SHI = list(GETSU_SHI_APPEARANCE.keys())

# custom_idはASCII制約(^[a-zA-Z0-9_-]{1,64}$)のため支をローマ字化
SHI_ROMAJI = {
    "子": "ne", "丑": "ushi", "寅": "tora", "卯": "u",
    "辰": "tatsu", "巳": "mi", "午": "uma", "未": "hitsuji",
    "申": "saru", "酉": "tori", "戌": "inu", "亥": "i",
}
ROMAJI_SHI = {v: k for k, v in SHI_ROMAJI.items()}


def _user_prompt(jikkan: str, shi: str) -> str:
    god = JIKKAN_GUARDIAN_TABLE[jikkan]
    return (
        f"守護神: {god['god']}({jikkan}・{god['story_type']})\n"
        f"母体の意識の種: {SEEDS_BASE[jikkan]}\n"
        f"月支: {shi}——{GETSU_SHI_APPEARANCE[shi]}\n\n"
        f"この月支生まれの人向けに、母体の核概念を保ったまま、"
        f"顕れ方をこの月支に合わせて具体化した意識の種を1本。"
    )


def _params(jikkan: str, shi: str) -> MessageCreateParamsNonStreaming:
    return MessageCreateParamsNonStreaming(
        model=MODEL,
        max_tokens=2000,  # 思考(常時オン)+短文出力の余裕。設計案1,000から技術調整
        system=SYSTEM_PROMPT,
        output_config={"format": OUTPUT_SCHEMA},
        messages=[{"role": "user", "content": _user_prompt(jikkan, shi)}],
    )


def submit() -> None:
    client = anthropic.Anthropic()
    requests = [
        Request(custom_id=f"{JIKKAN_GUARDIAN_TABLE[j]['god_id']}_{SHI_ROMAJI[s]}", params=_params(j, s))
        for j in JIKKAN for s in SHI
    ]
    batch = client.messages.batches.create(requests=requests)
    BATCH_ID_FILE.write_text(batch.id)
    print(f"batch submitted: {batch.id} ({len(requests)} requests) -> {BATCH_ID_FILE}")


def _lint(entry: dict) -> list[str]:
    problems = []
    text = entry.get("phrase", "") + entry.get("action", "")
    for w in NG_WORDS:
        if w in text:
            problems.append(f"NGワード: {w}")
    if len(entry.get("phrase", "")) > 26:  # 「」込みの余裕を+6字
        problems.append(f"phrase長超過: {len(entry['phrase'])}字")
    if not entry.get("phrase") or not entry.get("action"):
        problems.append("必須フィールド空")
    return problems


def collect() -> None:
    client = anthropic.Anthropic()
    batch_id = BATCH_ID_FILE.read_text().strip()
    batch = client.messages.batches.retrieve(batch_id)
    print(f"batch {batch_id}: {batch.processing_status} {batch.request_counts}")
    if batch.processing_status != "ended":
        print("まだ処理中。後で collect を再実行してください。")
        return

    god_id_to_jikkan = {v["god_id"]: k for k, v in JIKKAN_GUARDIAN_TABLE.items()}
    entries, failures = {}, []
    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type != "succeeded":
            failures.append((cid, result.result.type))
            continue
        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            data = json.loads(text)
        except Exception as e:
            failures.append((cid, f"json_error: {e}"))
            continue
        problems = _lint(data)
        god_id, shi_r = cid.rsplit("_", 1)
        shi = ROMAJI_SHI.get(shi_r, shi_r)
        entries[cid] = {
            "god_id": god_id,
            "jikkan": god_id_to_jikkan.get(god_id, "?"),
            "shi": shi,
            "phrase": data.get("phrase", ""),
            "action": data.get("action", ""),
            "note": data.get("note", ""),
            "lint": problems,
            "model": msg.model,
            "stop_reason": msg.stop_reason,
        }

    ok = [e for e in entries.values() if not e["lint"]]
    ng = [e for e in entries.values() if e["lint"]]
    print(f"回収: {len(entries)}/120 / lint合格: {len(ok)} / lint要確認: {len(ng)} / API失敗: {len(failures)}")
    for cid, why in failures:
        print(f"  FAIL {cid}: {why}")
    for e in ng:
        print(f"  LINT {e['jikkan']}_{e['shi']}: {e['lint']}")

    OUT_JSON.write_text(json.dumps({
        "_comment": "古神道v3 意識の種120本(十干×月支)。生成: claude-fable-5 Batches。官能評価前の生データ+lint結果。",
        "_batch_id": batch_id,
        "_generated_at": date.today().isoformat(),
        "seeds": entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON -> {OUT_JSON}")

    lines = [
        f"# 意識の種120本 官能評価用一覧({date.today().isoformat()})",
        "",
        "- 生成: claude-fable-5(Batches・構造化出力) / 血統: 骨格版の母体10本(丙はくろたん改訂版)×月支定義表(確定版)",
        f"- 機械検品: 回収{len(entries)}/120・lint合格{len(ok)}・要確認{len(ng)}",
        "- 評価方法: 各行のチェック欄に ○(採用)/△(修正)/×(再生成) を記入。×はセル単位で再生成します",
        "",
    ]
    for j in JIKKAN:
        god = JIKKAN_GUARDIAN_TABLE[j]
        lines += [f"## {j} {god['god']}({god['god_id']})", "",
                  f"母体: {SEEDS_BASE[j]}", "",
                  "| 月支 | phrase | action | lint | 評価 |", "|---|---|---|---|---|"]
        for s in SHI:
            e = entries.get(f"{god['god_id']}_{SHI_ROMAJI[s]}")
            if e:
                lint = "⚠️" + ";".join(e["lint"]) if e["lint"] else "OK"
                lines.append(f"| {s} | {e['phrase']} | {e['action']} | {lint} |  |")
            else:
                lines.append(f"| {s} | (生成失敗) |  | FAIL |  |")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"官能評価md -> {OUT_MD}")


def retry(cids: list[str]) -> None:
    """NGセルのみ通常APIで再生成し、JSONを更新"""
    client = anthropic.Anthropic()
    data = json.loads(OUT_JSON.read_text())
    god_id_to_jikkan = {v["god_id"]: k for k, v in JIKKAN_GUARDIAN_TABLE.items()}
    still_refused = []
    for cid in cids:
        god_id, shi_r = cid.rsplit("_", 1)
        shi = ROMAJI_SHI.get(shi_r, shi_r)
        jikkan = god_id_to_jikkan[god_id]
        ok = False
        for attempt in range(3):  # refusalは確率的な偽陽性のため最大3回
            resp = client.messages.create(**_params(jikkan, shi))
            if resp.stop_reason == "refusal":
                cat = getattr(resp.stop_details, "category", None) if resp.stop_details else None
                print(f"  {cid}: refusal(category={cat}) attempt {attempt+1}/3")
                continue
            text = next((b.text for b in resp.content if b.type == "text"), "")
            d = json.loads(text)
            data["seeds"][cid] = {
                "god_id": god_id, "jikkan": jikkan, "shi": shi,
                "phrase": d.get("phrase", ""), "action": d.get("action", ""),
                "note": d.get("note", ""), "lint": _lint(d),
                "model": resp.model, "stop_reason": resp.stop_reason,
            }
            print(f"retried {cid}: {d.get('phrase','')}")
            ok = True
            break
        if not ok:
            still_refused.append(cid)
    if still_refused:
        print(f"3回とも拒否(要くろたん相談): {still_refused}")
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "submit"
    if cmd == "submit":
        submit()
    elif cmd == "collect":
        collect()
    elif cmd == "retry":
        retry(sys.argv[2:])
    else:
        print(__doc__)
