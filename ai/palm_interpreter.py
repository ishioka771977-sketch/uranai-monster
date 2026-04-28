"""
占いモンスター 手相鑑定 AI エンジン

2段階パイプライン:
  Step 1: Gemini 2.5 Pro で画像分析 → 構造化JSON
  Step 2: Claude Opus 4.7 で鑑定文生成（既存8占術データ＋くろたんキャラ）
"""
import os
import json
import re

from google import genai
from google.genai import types
import anthropic

from core.palm import PALM_KB

# ============================================================
# Gemini プロンプト (Step 1: 画像分析)
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
    """``` json ... ``` のコードブロックを抽出して dict に変換"""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    json_str = m.group(1).strip() if m else text.strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def call_gemini_palm(img_bytes: bytes, hand: str = "right") -> dict | None:
    """
    Gemini 2.5 Pro で画像分析。構造化JSONを返す。

    Args:
        img_bytes: 1600px以下にリサイズ済みのJPEGバイト
        hand: "left" | "right"
    Returns:
        Geminiの分析JSON、または None（パース失敗時）
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)
    prompt = build_gemini_prompt(hand)

    # Gemini 2.5 Pro → fallback to 2.0 flash if not available
    for model_id in ["gemini-2.5-pro", "gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-1.5-pro"]:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            )
            return _extract_json(response.text)
        except Exception as e:
            err_str = str(e).lower()
            if "404" in err_str or "not found" in err_str or "model" in err_str:
                continue
            raise
    return None

# ============================================================
# Claude プロンプト (Step 2: 鑑定文生成)
# ============================================================

def _summarize_existing_uranai(existing: dict) -> list[str]:
    """既存8占術の鑑定結果を文字列リストにまとめる"""
    summary = []
    if not existing:
        return summary
    if "sanmei" in existing:
        s = existing["sanmei"]
        chuou = s.get("chuoseiboshi") or s.get("center_star") or s.get("中央星")
        if chuou:
            summary.append(f"算命学: 中央星 = {chuou}")
    if "shichusuimei" in existing:
        s = existing["shichusuimei"]
        kan = s.get("day_kan") or s.get("日干")
        if kan:
            summary.append(f"四柱推命: 日干 = {kan}")
    if "western" in existing:
        s = existing["western"]
        sun = s.get("sun_sign") or s.get("太陽")
        asc = s.get("asc_sign") or s.get("ASC")
        if sun:
            summary.append(f"西洋占星術: 太陽 = {sun}" + (f"、ASC = {asc}" if asc else ""))
    if "kyusei" in existing:
        s = existing["kyusei"]
        hon = s.get("honmeiboshi") or s.get("本命星")
        if hon:
            summary.append(f"九星気学: 本命星 = {hon}")
    if "numerology" in existing:
        s = existing["numerology"]
        lp = s.get("lifepath") or s.get("life_path") or s.get("ライフパス")
        if lp:
            summary.append(f"数秘術: ライフパス = {lp}")
    if "tarot" in existing:
        s = existing["tarot"]
        card = s.get("main_arcana") or s.get("メインカード")
        if card:
            summary.append(f"タロット: メインカード = {card}")
    if "ziwei" in existing:
        s = existing["ziwei"]
        m = s.get("meigung_main") or s.get("命宮主星")
        if m:
            summary.append(f"紫微斗数: 命宮主星 = {m}")
    if "bansho" in existing:
        s = existing["bansho"]
        g = s.get("gogyo_balance") or s.get("五行")
        if g:
            summary.append(f"万象学: 五行 = {g}")
    return summary


def build_claude_palm_prompt(palm_json: dict, hand: str, existing: dict) -> str:
    """くろたんキャラ + 8占術連携 + 演出ルール込みのプロンプト"""
    hand_jp = "左手（先天・本質）" if hand == "left" else "右手（後天・現在）"
    presentation = PALM_KB.get("presentation_guidance", {})
    integration = PALM_KB.get("integration_with_uranai_monster", {})

    existing_summary = _summarize_existing_uranai(existing)

    # 検出された特殊マーク
    detected_marks = [
        m["name"] for m in palm_json.get("special_marks", []) if m.get("detected")
    ]

    # 演出ルールを抜粋
    rule_lines = []
    rule_map = {
        "simian_line": ("masakake", "マスカケ線"),
        "mystic_cross": (None, "神秘十字"),
        "ring_of_solomon": (None, "ソロモンの環"),
        "haoh_line": ("haoh_line", "覇王線"),
        "buddha_eye": ("buddha_eye", "仏眼"),
        "star": (None, "スター"),
        "great_triangle": ("great_triangle", "大三角形"),
        "square": ("square", "四角紋"),
    }
    for mark_name in detected_marks:
        if mark_name in rule_map:
            key, jp = rule_map[mark_name]
            rule = presentation.get(key, {}) if key else None
            if rule:
                rule_lines.append(
                    f"- 検出された **{jp}** の演出: {rule.get('level')} レベル — "
                    + " / ".join(rule.get("rules", []))
                )

    integration_lines = [f"- {k}: {v}" for k, v in integration.items()]

    return f"""あなたは「くろたん」という名前の女性占い師です。
口調は親しみやすく、女性的な優しさで、ときに鋭い直感も交える。
建設業の経営者層がメイン顧客なので、過度なスピリチュアル表現は避けてください。

【依頼】
依頼者の{hand_jp}を鑑定し、500〜1000字の鑑定文を生成してください。

【手相分析データ（Gemini 2.5 Pro 検出）】
```json
{json.dumps(palm_json, ensure_ascii=False, indent=2)}
```

【既存占術の鑑定結果（参考、ある分だけ）】
{chr(10).join(existing_summary) if existing_summary else "（既存占術データ未提供。手相のみで鑑定してください）"}

【演出ルール（厳守）】
{chr(10).join(rule_lines) if rule_lines else "- 特別な演出が必要なマークは検出されていません。通常の鑑定文を生成してください"}

【既存占術との連携指針】
{chr(10).join(integration_lines)}

【重要な注意】
- 万象学の五行と手の形状の関係は『直接対応』ではなく『類似性の示唆』として語る
- 検出されなかった線は「ない」と語らず「目立たない」「これからの線」と前向きに表現
- 既存占術と手相が同じ方向を指している場合は『偶然ではない一致』として強調する
- 検出されたマーク以外（特に覇王線・マスカケ線等の希少なもの）について「ある」と語ってはならない

【出力形式】
そのまま鑑定文（500〜1000字）。マークダウンの見出しは「### 〜」レベルまで使用可。
冒頭に「ひでさん、」など名前呼びはしない（依頼者の名前は不明なため）。
"""


def call_claude_palm(palm_json: dict, hand: str = "right", existing: dict | None = None) -> str:
    """
    Claude Opus 4.7 で鑑定文を生成する。

    Args:
        palm_json: Gemini が返した手相分析 JSON
        hand: "left" | "right"
        existing: 既存8占術の鑑定結果dict（任意）
    Returns:
        生成された鑑定文（日本語、500〜1000字）
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "（鑑定文の生成に失敗しました。ANTHROPIC_API_KEY が未設定です）"

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_claude_palm_prompt(palm_json, hand, existing or {})

    # claude-opus-4-7 → fallback chain
    for model_id in [
        "claude-opus-4-7",
        "claude-sonnet-4-7",
        "claude-3-5-sonnet-20241022",
    ]:
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
    return "（鑑定文の生成に失敗しました。Claude モデルにアクセスできません）"


# ============================================================
# 統合フロー (上位から呼ぶ便利関数)
# ============================================================

def run_palm_pipeline(
    img_bytes: bytes,
    hand: str = "right",
    existing: dict | None = None,
) -> dict:
    """
    画像 → Gemini 分析 → Claude 鑑定文生成 のパイプライン

    Returns:
        {
            "ok": bool,
            "palm_json": dict | None,
            "rationale": str | None,
            "error": str | None,
        }
    """
    # Step 1: Gemini 画像分析
    try:
        palm_json = call_gemini_palm(img_bytes, hand)
    except Exception as e:
        return {"ok": False, "palm_json": None, "rationale": None, "error": f"Gemini分析エラー: {e}"}

    if not palm_json:
        return {"ok": False, "palm_json": None, "rationale": None, "error": "Geminiから有効なJSONが返却されませんでした"}

    iq = palm_json.get("image_quality", {})
    if iq.get("rating") == "poor" or iq.get("is_sufficient_for_reading") is False:
        return {
            "ok": False,
            "palm_json": palm_json,
            "rationale": None,
            "error": "画像の品質が鑑定に不十分です: " + ", ".join(iq.get("issues", [])),
        }

    # Step 2: Claude 鑑定文生成
    try:
        rationale = call_claude_palm(palm_json, hand, existing)
    except Exception as e:
        return {"ok": False, "palm_json": palm_json, "rationale": None, "error": f"Claude鑑定文エラー: {e}"}

    return {
        "ok": True,
        "palm_json": palm_json,
        "rationale": rationale,
        "error": None,
    }
