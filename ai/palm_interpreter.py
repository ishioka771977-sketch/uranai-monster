"""
占いモンスター 手相鑑定 AI エンジン (v2.0 — 3段階パイプライン)

設計思想（北極星）：占いモンスターは「交差点」で勝つ。
他占術データを文脈として渡すことで、テンプレ鑑定（「情に厚い」）を
「美学で動く、でも映画で泣く」レベルの深さに昇華する。

3段階パイプライン:
  Step 1: 手相だけで一次解釈（手相の独自性を保つ）
  Step 2: 他占術と突き合わせて深掘り・修正
  Step 3: 最終鑑定文（4セクション形式: 手が語る/星が裏付ける/複雑さ/断言）

ケース分岐:
  A. 既存占術データあり → 3段階フル
  B. 既存占術データなし → Step 1のみ + 顧客登録導線
  C. コンプリート鑑定の一部 → 全占術揃った上で実行
"""
import os
import json
import re

from google import genai
from google.genai import types
import anthropic

from core.palm import PALM_KB

# ============================================================
# Step 0: Gemini プロンプト (画像分析)
# ============================================================

def build_gemini_prompt(hand: str) -> str:
    """画像分析用プロンプト。Round 1 の知識ベースに基づく構造を要求"""
    hand_jp = "左" if hand == "left" else "右"
    return f"""あなたは手相鑑定の専門家です。
この{hand_jp}手のひらの画像を分析し、**有効なJSON形式**で返してください。

【厳守】
- JSONのみを返すこと。説明文は不要。
- 値が判定不能な場合は "unknown" または null を使う。
- 全フィールドの値は **日本語** で記述すること。
- ```json ... ``` のコードブロックで囲んで返してください。

```json
{{
  "image_quality": {{
    "rating": "good",
    "issues": [],
    "is_sufficient_for_reading": true
  }},
  "hand_shape": {{
    "type": "earth",
    "rationale": "判定理由（日本語、50字以内）"
  }},
  "major_lines": {{
    "life_line": {{
      "detected": true,
      "length": "long",
      "depth": "deep",
      "features": ["分岐", "島紋"]
    }},
    "head_line": {{ "detected": true, "length": "normal", "depth": "normal", "features": [] }},
    "heart_line": {{ "detected": true, "length": "long", "depth": "deep", "features": [] }},
    "fate_line": {{ "detected": false, "length": "unknown", "depth": "unknown", "features": [] }},
    "sun_line": {{ "detected": false, "length": "unknown", "depth": "unknown", "features": [] }}
  }},
  "mounts": {{
    "jupiter": "developed",
    "saturn": "normal",
    "apollo": "normal",
    "mercury": "normal",
    "venus": "developed",
    "luna": "normal",
    "mars_positive": "normal",
    "mars_negative": "normal"
  }},
  "special_marks": [
    {{"name": "simian_line", "detected": false, "location": null}},
    {{"name": "mystic_cross", "detected": false, "location": null}},
    {{"name": "ring_of_solomon", "detected": false, "location": null}},
    {{"name": "haoh_line", "detected": false, "location": null}},
    {{"name": "buddha_eye", "detected": false, "location": null}},
    {{"name": "star", "detected": false, "location": null}},
    {{"name": "great_triangle", "detected": false, "location": null}},
    {{"name": "square", "detected": false, "location": null}}
  ],
  "overall_summary": "100文字程度の総合所見（日本語）"
}}
```

【値の許容範囲】
- hand_shape.type: "earth"(地)/"air"(風)/"water"(水)/"fire"(火)/"unknown"
- 線.length: "long"/"normal"/"short"/"unknown"
- 線.depth: "deep"/"normal"/"shallow"/"unknown"
- 丘の発達: "developed"(発達)/"normal"(普通)/"weak"(貧弱)/"unknown"

検出された特殊マークの location は手のどこに出現したか（日本語、例: "中指の下"）。
"""


def _extract_json(text: str) -> dict | None:
    """Gemini/Claude の応答テキストから JSON を確実に抽出する。

    対応パターン:
    - 純粋な JSON（response_mime_type=application/json で返される場合）
    - ```json ... ``` のコードブロックで囲まれている場合
    - 前後に説明文が付いている場合（最初の { から最後の } を切り出す）
    """
    if not text:
        return None
    text = text.strip()

    # まずそのまま JSON パース試行
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ```json ... ``` フェンスを除去
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        json_str = fence.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 最初の { から最後の } を切り出す
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def call_gemini_palm(img_bytes: bytes, hand: str = "right") -> dict | None:
    """Gemini 2.5 Pro で画像分析。構造化JSONを返す。
    パース失敗時は raw レスポンスをログに残す。
    """
    import logging
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.error("call_gemini_palm: GEMINI_API_KEY 未設定")
        return None

    client = genai.Client(api_key=api_key)
    prompt = build_gemini_prompt(hand)

    # response_mime_type を指定して JSON 強制
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
    )

    for model_id in ["gemini-2.5-pro", "gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-1.5-pro"]:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
                config=config,
            )
            raw = response.text or ""
            logging.info(
                f"call_gemini_palm: model={model_id} hand={hand} "
                f"raw_len={len(raw)} preview={raw[:200]!r}"
            )
            parsed = _extract_json(raw)
            if parsed is None:
                logging.error(
                    f"call_gemini_palm: JSON parse failed. model={model_id} "
                    f"full_response={raw!r}"
                )
                # response_mime_type 不対応モデルの場合に備え、次モデルへ
                continue
            return parsed
        except Exception as e:
            err_str = str(e).lower()
            logging.warning(f"call_gemini_palm: model={model_id} error={e}")
            if (
                "404" in err_str
                or "not found" in err_str
                or "model" in err_str
                or "response_mime_type" in err_str
                or "unsupported" in err_str
            ):
                # response_mime_type 非対応モデルの可能性 → config なしで再試行
                try:
                    response = client.models.generate_content(
                        model=model_id,
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            prompt,
                        ],
                    )
                    raw = response.text or ""
                    logging.info(
                        f"call_gemini_palm (no mime): model={model_id} "
                        f"raw_len={len(raw)} preview={raw[:200]!r}"
                    )
                    parsed = _extract_json(raw)
                    if parsed is not None:
                        return parsed
                except Exception:
                    pass
                continue
            raise
    return None


# ============================================================
# Step 1: 一次解釈プロンプト（手相だけ、Claude）
# ============================================================

def build_step1_prompt(palm_json: dict, hand: str) -> str:
    """Step 1: 手相データだけで教科書的な一次解釈を出す。
    他の占術は参照しない。手相の独自性を保つことが目的。
    """
    hand_jp = "左手（先天・本質）" if hand == "left" else "右手（後天・現在）"
    return f"""あなたは手相鑑定の専門家です。
以下の手相分析データだけを使い、一次解釈を出してください。
**他の占術は参照しないでください。手相だけで読んだ結果を出すこと。**

【対象】
{hand_jp}

【手相データ（Gemini 2.5 Pro 検出）】
```json
{json.dumps(palm_json, ensure_ascii=False, indent=2)}
```

【感情線の解釈パターン（重要・必ず参照）】
感情線は「情に厚い／薄い」の単純2択ではない。深さ×直線性×手型×丘の組み合わせで4パターンに分かれる。
heart_line_reading では、検出された手相データから該当しそうなパターンを判定し、
**そのパターン名と論理を含めた一次解釈** を返すこと（テンプレ「情に厚い」で済ませない）。

  パターン1（感傷型）：
    条件 — 感情線が深く＋曲線が大きい（湾曲が強い）
    解釈 — 感情豊か。人の痛みに共感し、感傷的な判断もする。情のまま動く

  パターン2（美学型）：
    条件 — 感情線が深く＋直線的（あまり湾曲しない）
    解釈 — 感情は深いが理性で律する。自分の美学・生き方への執着が強い。
            人に優しいのは感情ではなく信条に基づく。ドライに見えるが芯がある。
            「情に厚い」より「筋を通す」人

  パターン3（制御型）：
    条件 — 感情線が深く＋頭脳線も深い（両方が強い）
    解釈 — 感情と理性の両方が強く、常に内部でせめぎ合う。
            外からはドライ、内面は誰よりも深く考えている

  パターン4（深層感情型）★最重要★：
    条件 — 感情線が深く直線的＋地の手または火の手＋木星丘発達
    解釈 — 感情の「器」が非常に大きい。日常の小さな感情には反応しない。
            自分でも「ドライな人間」と思っている。美学と損得で判断する。
            しかし映画・ドキュメンタリーの家族愛で不意に涙が溢れる。
            感情がないのではなく深すぎて普段は出てこないだけ。
            フィクションや他人の物語という「安全な距離」を置いたとき蓋が外れて溢れる

感情線が浅い場合も同様、単純な「冷淡」「淡白」で済ませず、
「自分の感情と適切な距離を取れる」「他人に巻き込まれない自立性」など複数の読みを示すこと。

【出力形式】
以下のJSON形式で、各項目について手相だけの一次解釈（教科書的な読み）を返してください。
他占術と統合する前の素の手相所見です。

```json
{{
  "hand_shape_reading": "手の形状からの一次解釈（150字程度、教科書的でOK）",
  "life_line_reading": "生命線の一次解釈（100字）",
  "head_line_reading": "頭脳線の一次解釈（100字）",
  "heart_line_reading": "感情線の一次解釈（150〜200字。上記パターン1〜4のどれに該当するかを必ず判定し、パターン名と論理を含める）",
  "heart_line_pattern": "感情型/美学型/制御型/深層感情型/その他 のいずれか（パターン判定結果のラベル）",
  "fate_line_reading": "運命線の一次解釈（100字、検出されてない場合は『目立たない』として前向きに）",
  "sun_line_reading": "太陽線の一次解釈（100字、同上）",
  "mounts_reading": "発達した丘・貧弱な丘の一次解釈（150字）",
  "special_marks_reading": "検出された特殊マークの一次解釈（200字、なければ『なし』）",
  "raw_overall": "手相だけで見た総合所見（200字、テンプレ的でも可）"
}}
```

【ルール】
- 教科書的・テンプレ的でOK。Step 2 で他占術と突き合わせて深める前提
- 値の取り方は Round 1 の知識ベースに準拠する
- 検出されなかった線は「ない」と語らず「目立たない」「これから刻まれる線」と前向き表現
- 100文字以下にしすぎない。素材として後段で使うので情報は厚めに
- 感情線については「情に厚い」だけで済ませず、必ずパターン1〜4の判定を行うこと
"""


def call_claude_step1(palm_json: dict, hand: str) -> dict | None:
    """Step 1: Claude で手相だけの一次解釈を生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_step1_prompt(palm_json, hand)

    for model_id in ["claude-opus-4-7", "claude-sonnet-4-7", "claude-3-5-sonnet-20241022"]:
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )
            return _extract_json(response.content[0].text)
        except Exception as e:
            err_str = str(e).lower()
            if "model" in err_str or "not found" in err_str or "404" in err_str:
                continue
            raise
    return None


# ============================================================
# Step 2: 文脈付き深掘りプロンプト（他占術と突き合わせ、Claude）
# ============================================================

def _summarize_existing_uranai(existing: dict) -> list[str]:
    """既存占術の鑑定結果を文字列リストにまとめる（プロンプト埋込用）"""
    summary = []
    if not existing:
        return summary
    if "sanmei" in existing:
        s = existing["sanmei"]
        for k, v in s.items():
            summary.append(f"算命学 {k}: {v}")
    if "shichusuimei" in existing:
        s = existing["shichusuimei"]
        for k, v in s.items():
            summary.append(f"四柱推命 {k}: {v}")
    if "western" in existing:
        s = existing["western"]
        for k, v in s.items():
            summary.append(f"西洋占星術 {k}: {v}")
    if "kyusei" in existing:
        s = existing["kyusei"]
        for k, v in s.items():
            summary.append(f"九星気学 {k}: {v}")
    if "numerology" in existing:
        s = existing["numerology"]
        for k, v in s.items():
            summary.append(f"数秘術 {k}: {v}")
    if "tarot" in existing:
        s = existing["tarot"]
        for k, v in s.items():
            summary.append(f"タロット {k}: {v}")
    if "ziwei" in existing:
        s = existing["ziwei"]
        for k, v in s.items():
            summary.append(f"紫微斗数 {k}: {v}")
    if "bansho" in existing:
        s = existing["bansho"]
        for k, v in s.items():
            summary.append(f"万象学 {k}: {v}")
    return summary


def build_step2_prompt(step1_result: dict, palm_json: dict, hand: str, existing: dict) -> str:
    """Step 2: 一次解釈と他占術を突き合わせ、深掘り・修正してくろたん文体の最終鑑定文を生成"""
    hand_jp = "左手（先天・本質）" if hand == "left" else "右手（後天・現在）"
    presentation = PALM_KB.get("presentation_guidance", {})
    integration = PALM_KB.get("integration_with_uranai_monster", {})

    existing_summary = _summarize_existing_uranai(existing)

    detected_marks = [m["name"] for m in palm_json.get("special_marks", []) if m.get("detected")]
    rule_lines = []
    rule_map = {
        "simian_line": ("masakake", "マスカケ線"),
        "haoh_line": ("haoh_line", "覇王線"),
        "buddha_eye": ("buddha_eye", "仏眼"),
        "great_triangle": ("great_triangle", "大三角形"),
        "square": ("square", "四角紋"),
    }
    for mark_name in detected_marks:
        if mark_name in rule_map:
            key, jp = rule_map[mark_name]
            rule = presentation.get(key, {})
            if rule:
                rule_lines.append(
                    f"- 検出された **{jp}** の演出: {rule.get('level')} レベル — "
                    + " / ".join(rule.get("rules", []))
                )

    return f"""あなたは「くろたん」という名前の女性占い師です。
口調は親しみやすく、女性的な優しさで、ときに鋭い直感も交える。
建設業の経営者層がメイン顧客なので、過度なスピリチュアル表現は避けてください。

【最重要：占いモンスターの設計思想】
あなたは **9流派全部の知識を持つ唯一無二のAI** です。
1流派しか使えない人間の占い師には絶対に出せない、
**「交差点でしか見えない景色」** を語ってください。

テンプレ鑑定（「情に厚い」「リーダー気質」「金運あり」）は **敵** です。
教科書通りの解釈を並べるだけなら、無料の占いサイトと変わりません。
**この人物固有の、この組み合わせでしか出てこない解釈** を目指してください。

【テンプレ vs 交差点鑑定（複数例）】

例1（感情線×算命学×西洋）：
× テンプレ：「感情線が深い → 情に厚い」
○ 交差点鑑定：「感情線が深い + 算命学の牽牛星（美学）+ 西洋ASC魚座（内面感受性）→
  情に厚いのではなく、美学で動く。感情は深いが理性で律する。
  でも映画で家族の絆を見たとき、不意に涙が溢れる。
  それは感情がないのではない。深すぎるから、普段は出てこないだけ。」

例2（感情線×丘×手型）：
× テンプレ：「感情線が深い → 情に厚い」
○ 交差点鑑定：「感情線が深い + 木星丘発達 + 地の手 →
  情に厚いのではなく、リーダーとしての美学が強い。
  部下に優しいのは感情ではなく、自分の率いる組織への責任感。
  ここは譲れないという『線』を持って人と接している。」

例3（感受性×水の手）：
× テンプレ：「感受性が豊か」
○ 交差点鑑定：「感情線が深い + 金星丘発達 + 水の手 →
  感受性が非常に強く、人の痛みを自分のことのように感じる。
  芸術家肌、カウンセラー気質。境界が薄いから疲れやすいが、
  その代わり誰よりも他人の気持ちを代弁できる人。」

例4（運命線なし×3占術）：
× テンプレ：「運命線がない → 流されやすい」
○ 交差点鑑定：「運命線が目立たない + 数秘8（達成者）+ 算命学・主動・主動・主動の三連 →
  運命に従うのではなく、自分で道を敷く人。
  会社員より起業家、組織より独立、敷かれたレールより未踏の地。
  運命線がないのは欠落ではなく、これから自分の手で刻む線。」

---

【依頼内容】
{hand_jp}を鑑定し、以下の **5セクション構成** で最終鑑定文を生成してください。

### あなたの手が語ること
（手相単独の読み。Step 1 の一次解釈を踏まえて、手の形状・線・丘の分析。
 ★感情線については Step 1 で判定された heart_line_pattern を必ず採用すること。
 教科書的に「情に厚い」と書くだけでは認めない。パターン1〜4のどれかに踏み込む）

### 星が裏付ける真実
（手相の読みと他占術の **一致点** を見つけて語る。
 「手にも星にも同じ宿命が刻まれている」型の確信表現を使う。
 占術ごとの読み筋（後述）を参照し、線・丘・形状と紐付けて語ること）

### あなただけの複雑さ
（手相と他占術の **矛盾点** を見つけて語る。
 矛盾があれば、それを欠陥ではなく『人間としての深み』として語る。
 矛盾がなければ、複数占術が完全一致している事実を語る）

### くろたんの断言
（全てを踏まえた最終メッセージ。断定口調で、ポジティブに。
 「あなたは〇〇です」と言い切る。曖昧な「〜かもしれません」は禁止）

### くろたんからの問いかけ ★必須・テンプレ脱却の最後の砦★
（読み手に問いかけて、自己修正の余地を残す。形式：）

「ここまで読んでどうですか？
 もし『〇〇（先のセクションで使った主要な解釈ラベル）』という表現が違うと感じたなら、
 それは△△（パターン2／パターン3 など、別解釈ルートの示唆）を示しているのかもしれません。
 〜（その別解釈の意味を1〜2文で添える）」

問いかけの目的：
- 当たっていれば「やっぱりそうだ」と確信が深まる
- ズレていれば「こっちの解釈がしっくりくる」と自己修正できる
- どちらに転んでも「この占い師はわかっている」と感じさせる

---

【素材1：手相の一次解釈（Step 1 結果、Claude が手相だけで読んだもの）】
```json
{json.dumps(step1_result, ensure_ascii=False, indent=2)}
```

【素材2：手相の構造化データ（Gemini 2.5 Pro 検出）】
```json
{json.dumps(palm_json, ensure_ascii=False, indent=2)}
```

【素材3：この人物の他の占術データ】
{chr(10).join(existing_summary) if existing_summary else "（既存占術データなし。手相のみで鑑定し、最後に『生年月日があればさらに深い鑑定ができる』と誘導してください）"}

---

【占術ごとの読み筋（Step 2 で文脈として使う指針）】
他占術データから次の観点を抽出し、手相と突き合わせること：

- 算命学：主星・従星・天中殺 → 「美学／義理／自由」など人格の柱
- 四柱推命：通変星・十二運・身強身弱 → 力の使い方、順行か逆行か
- 西洋占星術：太陽（自我）・月（情緒）・ASC（外見）・MC（社会的役割）
- 紫微斗数：命宮・身宮の主星 → 命運の主軸と現実適応
- 九星気学：本命星・月命星 → 気質と運気サイクル
- 数秘術：ライフパス → 人生の使命・課題テーマ
- タロット（生年月日カード）：カバラ的なライフパスシンボル
- 万象学：エネルギー値・五本能 → ※五行と手型は『類似性の示唆』であって直接対応ではない

【演出ルール（厳守）】
{chr(10).join(rule_lines) if rule_lines else "- 特別な演出が必要なマークは検出されていません。通常の鑑定文を生成してください"}

【既存占術との連携指針（PALM_KB由来）】
{chr(10).join([f"- {k}: {v}" for k, v in integration.items()])}

【厳守事項】
- 手相が **主役**、他占術は **裏付け・証拠** として使う
- 「算命学でも〇〇と出ている」は補助。「あなたの手にはこう刻まれている」が主文
- 万象学の五行と手の形状の関係は『直接対応』ではなく『類似性の示唆』として語る
- 検出されなかった線は「ない」と語らず「目立たない」「これから刻まれる」と前向き表現
- 検出されたマーク以外について「ある」と語ってはならない（特に覇王線・マスカケ線等の希少なもの）
- 数字（鑑定結果）は正直に、解釈は前向きに
- 既存占術データがない場合のみ、末尾に「生年月日があればさらに深く読める」と誘導する
- 感情線の解釈は Step 1 の heart_line_pattern（感傷型／美学型／制御型／深層感情型）を踏襲し、
  パターン4『深層感情型』が判定されていれば「映画で泣くドライな人」型の語り口を必ず使う

【出力形式】
5セクションに分けたマークダウン本文。
冒頭に依頼者の名前呼びはしない。
合計1000〜1700字を目安（問いかけセクション分を加算）。
"""


def call_claude_step2(step1_result: dict, palm_json: dict, hand: str, existing: dict) -> str:
    """Step 2: Claude で他占術と突き合わせた最終鑑定文を生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "（鑑定文の生成に失敗しました。ANTHROPIC_API_KEY が未設定です）"

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_step2_prompt(step1_result, palm_json, hand, existing)

    for model_id in ["claude-opus-4-7", "claude-sonnet-4-7", "claude-3-5-sonnet-20241022"]:
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            err_str = str(e).lower()
            if "model" in err_str or "not found" in err_str or "404" in err_str:
                continue
            raise
    return "（鑑定文の生成に失敗しました）"


# ============================================================
# Step 1 のみで鑑定文を出す（既存占術データが無い場合 = ケースB）
# ============================================================

def build_step1_only_rationale_prompt(step1_result: dict, palm_json: dict, hand: str) -> str:
    """既存占術データがない初対面向け。Step 1 のみで鑑定文を生成し、生年月日を聞く誘導を入れる"""
    hand_jp = "左手（先天・本質）" if hand == "left" else "右手（後天・現在）"
    return f"""あなたは「くろたん」という名前の女性占い師です。
口調は親しみやすく、ときに鋭い直感も交える。建設業の経営者層が顧客。

依頼者は初対面で、まだ生年月日を教えてくれていない。手相だけで鑑定する。
ただし末尾で **「生年月日があればさらに深く読める」と誘導** すること。

【対象】
{hand_jp}

【手相の一次解釈（Step 1 結果）】
```json
{json.dumps(step1_result, ensure_ascii=False, indent=2)}
```

【手相の構造化データ】
```json
{json.dumps(palm_json, ensure_ascii=False, indent=2)}
```

【出力形式】
以下の3セクション構成のマークダウン本文。

### あなたの手が語ること
（手の形状、主要線、丘の分析。500字程度）

### 手相からだけでわかったこと
（くろたんの断言。「あなたは〇〇です」型。300字程度）

### さらに深く読みたい場合
（「生年月日を教えてもらえれば、算命学・西洋占星術・九星気学・数秘術・タロット・紫微斗数・四柱推命・万象学を組み合わせて、あなたの手相が示す宿命の本当の意味を読み解けます」と誘導。150字程度）

【厳守】
- 検出されなかった線は前向き表現
- テンプレ鑑定（「情に厚い」だけ）は避ける
- 末尾の誘導文で「占いモンスターは9占術統合鑑定ができる」をアピール
"""


def call_claude_step1_only(step1_result: dict, palm_json: dict, hand: str) -> str:
    """既存占術データがない場合の鑑定文生成"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "（鑑定文の生成に失敗しました）"

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_step1_only_rationale_prompt(step1_result, palm_json, hand)

    for model_id in ["claude-opus-4-7", "claude-sonnet-4-7", "claude-3-5-sonnet-20241022"]:
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            err_str = str(e).lower()
            if "model" in err_str or "not found" in err_str or "404" in err_str:
                continue
            raise
    return "（鑑定文の生成に失敗しました）"


# ============================================================
# 統合パイプライン (上位呼出関数)
# ============================================================

def run_palm_pipeline(
    img_bytes: bytes,
    hand: str = "right",
    existing: dict | None = None,
) -> dict:
    """
    画像 → Gemini 分析 → Step 1 一次解釈 → Step 2 文脈統合 のパイプライン。

    既存占術データの有無で動作が分岐：
      ケースA: existing あり → 3段階フル（Gemini → Step 1 → Step 2）
      ケースB: existing なし → 2段階（Gemini → Step 1 → Step1のみ鑑定文）

    Returns:
        {
            "ok": bool,
            "palm_json": dict | None,        # Gemini が返した構造化データ
            "step1_result": dict | None,     # Step 1 の一次解釈JSON
            "rationale": str | None,         # 最終鑑定文
            "case": "A_with_existing" | "B_palm_only",
            "error": str | None,
        }
    """
    # Step 0: Gemini 画像分析
    try:
        palm_json = call_gemini_palm(img_bytes, hand)
    except Exception as e:
        return {
            "ok": False, "palm_json": None, "step1_result": None,
            "rationale": None, "case": None,
            "error": f"Gemini分析エラー: {e}",
        }

    if not palm_json:
        return {
            "ok": False, "palm_json": None, "step1_result": None,
            "rationale": None, "case": None,
            "error": "Geminiから有効なJSONが返却されませんでした",
        }

    iq = palm_json.get("image_quality", {})
    if iq.get("rating") == "poor" or iq.get("is_sufficient_for_reading") is False:
        return {
            "ok": False, "palm_json": palm_json, "step1_result": None,
            "rationale": None, "case": None,
            "error": "画像の品質が鑑定に不十分です: " + ", ".join(iq.get("issues", [])),
        }

    # Step 1: 手相だけの一次解釈
    try:
        step1_result = call_claude_step1(palm_json, hand)
    except Exception as e:
        return {
            "ok": False, "palm_json": palm_json, "step1_result": None,
            "rationale": None, "case": None,
            "error": f"Step1 一次解釈エラー: {e}",
        }

    if not step1_result:
        return {
            "ok": False, "palm_json": palm_json, "step1_result": None,
            "rationale": None, "case": None,
            "error": "Step1 から有効なJSONが返却されませんでした",
        }

    # ケース分岐
    if existing and any(existing.values()):
        # ケースA: 既存占術データあり → Step 2 まで実行
        try:
            rationale = call_claude_step2(step1_result, palm_json, hand, existing)
        except Exception as e:
            return {
                "ok": False, "palm_json": palm_json, "step1_result": step1_result,
                "rationale": None, "case": "A_with_existing",
                "error": f"Step2 統合鑑定エラー: {e}",
            }

        return {
            "ok": True,
            "palm_json": palm_json,
            "step1_result": step1_result,
            "rationale": rationale,
            "case": "A_with_existing",
            "error": None,
        }
    else:
        # ケースB: 既存占術データなし → Step 1 のみで鑑定文 + 顧客登録誘導
        try:
            rationale = call_claude_step1_only(step1_result, palm_json, hand)
        except Exception as e:
            return {
                "ok": False, "palm_json": palm_json, "step1_result": step1_result,
                "rationale": None, "case": "B_palm_only",
                "error": f"Step1のみ鑑定文エラー: {e}",
            }

        return {
            "ok": True,
            "palm_json": palm_json,
            "step1_result": step1_result,
            "rationale": rationale,
            "case": "B_palm_only",
            "error": None,
        }


# ============================================================
# 左右比較鑑定（両手の鑑定が揃った後に呼ぶ）
# ============================================================

def build_both_hands_summary_prompt(
    left_step1: dict,
    right_step1: dict,
    palm_left: dict,
    palm_right: dict,
    existing: dict | None = None,
) -> str:
    """両手の Step 1 結果が揃ったあと、左右の差分を語る鑑定文を生成するプロンプト。

    左手＝先天（生まれ持った素質）、右手＝後天（現在・歩んできた道）の対比で読む。
    一致していれば「迷わず歩んできた」、ズレていれば「変化を選び取った」として語る。
    """
    existing_summary = _summarize_existing_uranai(existing or {})

    return f"""あなたは「くろたん」という名前の女性占い師です。
口調は親しみやすく、ときに鋭い直感も交える。建設業の経営者層が顧客。

【依頼内容】
依頼者の **左手（先天・本質）** と **右手（後天・現在）** の両方の所見が揃いました。
左右の差を読み解いて、この人物の人生観・生き方の総合鑑定を出してください。

【手相の左右が示す意味】
- 左手（先天） = 生まれ持った資質・本来の自分・無意識
- 右手（後天） = 後天的に育てた力・現在の自分・意識的な歩み
- 左右一致 → 迷いなく自分の道を歩いてきた／生まれ持った資質を裏切らずに育てた
- 左右の差 → 変化を選び取った／生まれ持ったものを越えて育った／環境への適応
- 強烈なズレ → 内面と外面の二層構造、葛藤、または成長の物語

【素材1：左手（先天）の一次解釈】
```json
{json.dumps(left_step1, ensure_ascii=False, indent=2)}
```

【素材2：右手（後天）の一次解釈】
```json
{json.dumps(right_step1, ensure_ascii=False, indent=2)}
```

【素材3：左手の構造化データ（参考）】
```json
{json.dumps(palm_left, ensure_ascii=False, indent=2)}
```

【素材4：右手の構造化データ（参考）】
```json
{json.dumps(palm_right, ensure_ascii=False, indent=2)}
```

【素材5：他の占術データ（あれば、左右差の解釈に使う）】
{chr(10).join(existing_summary) if existing_summary else "（他占術データなし）"}

---

【出力形式】
以下の3セクションのマークダウン本文。合計600〜1000字。

### 左右が示すもの
（左右の主要な所見の対比。一致点と差異を具体的に語る。
 例：「左手では◯◯が深く、右手でも同じく◯◯が深く出ている。
       これは生まれ持った△△を、迷うことなく育ててきた証拠」
 例：「左手の生命線は短く、右手では長く伸びている。
       これは生まれ持った身体の弱さを、後天的な習慣で克服した手だ」）

### 先天と後天のメッセージ
（左右差から読み取れる、この人の生き方・選択。
 一致なら「裏切らない一貫性」、差があるなら「変化を選んだ強さ」として語る）

### くろたんの結論
（両手から導く最終メッセージ。1〜2文の断言で締める）

【厳守事項】
- 左右が一致していれば「迷いなく歩んできた」「裏切らない一貫性」として価値を語る
- 左右に差があれば「変化を選んだ」「成長の物語」として前向きに語る
- 「左右違う＝ダメ」のような否定は禁止
- 教科書的な「左手は過去、右手は未来」だけでは終わらせない。この人固有の対比を語る
- 他占術データがあれば左右差の意味付けに使うが、手相が主役
"""


def call_claude_both_hands_summary(
    left_step1: dict,
    right_step1: dict,
    palm_left: dict,
    palm_right: dict,
    existing: dict | None = None,
) -> str:
    """左右比較鑑定文を生成。両手の Step 1 結果が必要。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "（左右比較鑑定の生成に失敗しました）"

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_both_hands_summary_prompt(
        left_step1, right_step1, palm_left, palm_right, existing
    )

    for model_id in ["claude-opus-4-7", "claude-sonnet-4-7", "claude-3-5-sonnet-20241022"]:
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            err_str = str(e).lower()
            if "model" in err_str or "not found" in err_str or "404" in err_str:
                continue
            raise
    return "（左右比較鑑定の生成に失敗しました）"
