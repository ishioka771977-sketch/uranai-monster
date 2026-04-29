"""
占いモンスター 手相SVG ダイアグラム生成 v3.0 — ハイブリッド方式

くろたん指令「手のひらイラスト実装指令書」に基づく実装。
v3.0: SVG手描きから AI生成画像 + SVG オーバーレイ方式へ移行
- 背景: Imagen 4.0 で生成した手のひらテンプレート画像（data/palm_template_left.jpg、
        base64 エンコードして SVG image 要素で埋込）
- オーバーレイ: 検出された主要線をカラー強調、丘をゴールド円、特殊マークをアイコン

【座標系】
- viewBox: 360 × 660（テンプレート画像 480×880 にあわせた 9:16.5 アスペクト）
- 画像はそのまま 360×660 にフィット
"""
import base64
import os
from pathlib import Path
from typing import Optional

# ============================================================
# テンプレート画像の base64 を1度だけ読み込む
# ============================================================

_DATA_DIR = Path(__file__).parent.parent / "data"
_TEMPLATE_B64_PATH = _DATA_DIR / "palm_template_left_b64.txt"

try:
    with open(_TEMPLATE_B64_PATH, "r", encoding="utf-8") as _f:
        _PALM_TEMPLATE_B64 = _f.read().strip()
except FileNotFoundError:
    _PALM_TEMPLATE_B64 = ""


# ============================================================
# 線の定義（v1テンプレートに合わせた座標）
# ============================================================

LINE_DEFS = {
    "life_line":  {"name": "生命線",  "active": "#E74C3C", "label_x": 50,  "label_y": 460},
    "head_line":  {"name": "頭脳線",  "active": "#2ECC71", "label_x": 50,  "label_y": 360},
    "heart_line": {"name": "感情線",  "active": "#3498DB", "label_x": 50,  "label_y": 295},
    "fate_line":  {"name": "運命線",  "active": "#9B59B6", "label_x": 320, "label_y": 460},
    "sun_line":   {"name": "太陽線",  "active": "#F1C40F", "label_x": 320, "label_y": 380},
}

# v1 テンプレート (viewBox 360x660) に合わせた線パス
LINE_PATHS = {
    # 生命線: 人差し指と親指の間 (155, 305) → 親指の付け根を回り込む → 手首 (155, 580)
    "life_line":  "M 155,305 C 138,335 122,375 120,420 Q 122,490 145,560 Q 150,575 158,582",
    # 頭脳線: 生命線起点 (155, 330) → 手のひらの中央を横切って → 小指側 (275, 360)
    "head_line":  "M 155,330 C 185,345 220,355 250,358 Q 265,360 275,360",
    # 感情線: 小指側 (280, 295) → 人差し指側 (140, 290)
    "heart_line": "M 280,295 C 245,278 200,278 165,288 Q 150,290 140,290",
    # 運命線: 手首中央 (200, 580) → 中指の付け根 (190, 270)
    "fate_line":  "M 200,580 C 198,500 195,400 192,330 Q 191,290 190,270",
    # 太陽線: 中央下 (235, 460) → 薬指の付け根 (235, 280)
    "sun_line":   "M 235,460 C 232,400 230,340 233,295 Q 234,285 235,280",
}


def line_style(detected: bool, length: str, depth: str) -> dict:
    """検出/未検出 + 深さで線スタイルを返す"""
    if not detected:
        # 未検出は描画しない（背景画像に既存の薄い線が見えるので）
        return None
    if depth == "deep":
        return {"stroke_width": 4, "opacity": 0.95, "dasharray": "none"}
    elif depth == "shallow":
        return {"stroke_width": 2.5, "opacity": 0.8, "dasharray": "none"}
    else:
        return {"stroke_width": 3, "opacity": 0.9, "dasharray": "none"}


# ============================================================
# 丘の定義（v1テンプレートに合わせて位置調整）
# ============================================================

MOUNT_DEFS = {
    "jupiter":       {"name": "木星丘",     "cx": 152, "cy": 285, "r": 22},
    "saturn":        {"name": "土星丘",     "cx": 188, "cy": 280, "r": 22},
    "apollo":        {"name": "太陽丘",     "cx": 222, "cy": 285, "r": 22},
    "mercury":       {"name": "水星丘",     "cx": 258, "cy": 295, "r": 20},
    "venus":         {"name": "金星丘",     "cx": 130, "cy": 450, "r": 36},
    "luna":          {"name": "月丘",       "cx": 270, "cy": 480, "r": 32},
    "mars_positive": {"name": "第一火星丘", "cx": 138, "cy": 360, "r": 16},
    "mars_negative": {"name": "第二火星丘", "cx": 268, "cy": 410, "r": 16},
}


def mount_style(level: str) -> Optional[dict]:
    """発達 → ゴールド、貧弱 → グレー、その他 → 描画なし"""
    if level == "developed":
        return {"fill": "#FFD700", "opacity": 0.32}
    elif level == "weak":
        return {"fill": "#7F8C8D", "opacity": 0.15}
    return None


# ============================================================
# 特殊マーク
# ============================================================

MARK_DEFS = {
    "simian_line":    {"symbol": "⚡", "color": "#FF4500", "label": "マスカケ線"},
    "mystic_cross":   {"symbol": "✦",  "color": "#9B59B6", "label": "神秘十字"},
    "ring_of_solomon":{"symbol": "◎",  "color": "#3498DB", "label": "ソロモンの環"},
    "haoh_line":      {"symbol": "👑", "color": "#FFD700", "label": "覇王線"},
    "buddha_eye":     {"symbol": "◉",  "color": "#27AE60", "label": "仏眼"},
    "star":           {"symbol": "★",  "color": "#F1C40F", "label": "スター"},
    "great_triangle": {"symbol": "△",  "color": "#1ABC9C", "label": "大三角形"},
    "square":         {"symbol": "□",  "color": "#3498DB", "label": "四角紋"},
}

MARK_DEFAULT_POS = {
    "simian_line":    (200, 320),
    "mystic_cross":   (210, 380),
    "ring_of_solomon":(155, 250),
    "haoh_line":      (215, 360),
    "buddha_eye":     (95, 440),
    "star":           (225, 290),
    "great_triangle": (200, 410),
    "square":         (250, 400),
}


# ============================================================
# SVG パーツ生成
# ============================================================

def _draw_lines(major_lines: dict) -> str:
    """検出された主要線だけを描画（未検出はテンプレ画像の薄い線がそのまま見える）"""
    svg = ""
    for line_key, defs in LINE_DEFS.items():
        line_data = major_lines.get(line_key, {}) or {}
        detected = bool(line_data.get("detected"))
        if not detected:
            continue
        length = line_data.get("length", "unknown") or "unknown"
        depth = line_data.get("depth", "unknown") or "unknown"
        style = line_style(detected, length, depth)
        if not style:
            continue
        path = LINE_PATHS[line_key]
        color = defs["active"]
        svg += (
            f'<path d="{path}" fill="none" '
            f'stroke="{color}" stroke-width="{style["stroke_width"]}" '
            f'opacity="{style["opacity"]}" stroke-linecap="round"/>\n'
        )
    return svg


def _draw_mounts(mounts: dict) -> str:
    """発達した丘をハイライト"""
    svg = ""
    for mount_key, defs in MOUNT_DEFS.items():
        level = mounts.get(mount_key, "unknown")
        style = mount_style(level)
        if not style:
            continue
        svg += (
            f'<circle cx="{defs["cx"]}" cy="{defs["cy"]}" r="{defs["r"]}" '
            f'fill="{style["fill"]}" opacity="{style["opacity"]}"/>\n'
        )
    return svg


def _draw_special_marks(special_marks: list) -> str:
    """検出された特殊マークをアイコン表示"""
    svg = ""
    for mark in (special_marks or []):
        if not mark.get("detected"):
            continue
        name = mark.get("name", "")
        defs = MARK_DEFS.get(name)
        if not defs:
            continue
        cx, cy = MARK_DEFAULT_POS.get(name, (200, 380))
        svg += (
            f'<text x="{cx}" y="{cy}" font-size="24" '
            f'text-anchor="middle" fill="{defs["color"]}" '
            f'style="filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3));">{defs["symbol"]}</text>\n'
        )
    return svg


def _draw_labels(major_lines: dict, hand: str = "left") -> str:
    """検出された線のラベル（外側）を描画。右手の場合はX反転を考慮"""
    svg = ""
    is_right = hand == "right"
    for line_key, defs in LINE_DEFS.items():
        line_data = major_lines.get(line_key, {}) or {}
        if not line_data.get("detected"):
            continue
        x = defs["label_x"]
        y = defs["label_y"]
        if is_right:
            x = 360 - x
        anchor = "end" if x < 180 else "start"
        if is_right:
            anchor = "start" if x < 180 else "end"
        svg += (
            f'<text x="{x}" y="{y}" font-size="11" '
            f'fill="{defs["active"]}" font-weight="bold" '
            f'text-anchor="{anchor}">{defs["name"]}</text>\n'
        )
    return svg


# ============================================================
# メイン: SVG 生成
# ============================================================

def generate_palm_diagram(
    analysis: dict, hand: str = "left", width: int = 360, height: int = 660
) -> str:
    """
    手相の構造化分析結果から、SVG ダイアグラムを生成する。

    背景: Imagen 4.0 生成のテンプレート画像（base64 埋込）
    オーバーレイ: 検出線・発達した丘・特殊マークを SVG で描画

    Args:
        analysis: Gemini の構造化JSON
        hand: "left" | "right"
        width, height: SVG 出力サイズ（推奨 360×660、9:16.5）

    Returns:
        SVG 文字列（HTML 埋込可、自己完結）
    """
    if not analysis:
        analysis = {}
    major_lines = analysis.get("major_lines", {}) or {}
    mounts = analysis.get("mounts", {}) or {}
    special_marks = analysis.get("special_marks", []) or []

    # 右手は image + line/mount/mark を含む g を X軸で反転
    if hand == "right":
        transform = f' transform="translate({width}, 0) scale(-1, 1)"'
    else:
        transform = ""

    # 背景画像（base64 埋込）
    if _PALM_TEMPLATE_B64:
        bg_image = (
            f'<image href="data:image/jpeg;base64,{_PALM_TEMPLATE_B64}" '
            f'x="0" y="0" width="{width}" height="{height}" '
            f'preserveAspectRatio="xMidYMid meet"/>'
        )
    else:
        # base64 が無ければ単色背景
        bg_image = f'<rect width="{width}" height="{height}" fill="#FFF8F0"/>'

    inner = bg_image
    inner += _draw_lines(major_lines)
    inner += _draw_mounts(mounts)
    inner += _draw_special_marks(special_marks)

    # ラベルは反転させない（読みやすさ優先）
    labels = _draw_labels(major_lines, hand)

    svg = f"""
<div style="text-align:center; margin: 8px 0;">
  <svg viewBox="0 0 {width} {height}" width="{width}" height="{height}"
       xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
       style="max-width:100%; height:auto; background:#FFF8F0; border-radius:20px; box-shadow:0 4px 16px rgba(150,120,80,0.22);">
    <g{transform}>
      {inner}
    </g>
    {labels}
  </svg>
</div>
"""
    return svg


# ============================================================
# 凡例HTML
# ============================================================

def generate_legend_html(analysis: dict) -> str:
    """検出された線・丘・マークの凡例HTML"""
    if not analysis:
        analysis = {}
    major_lines = analysis.get("major_lines", {}) or {}
    mounts = analysis.get("mounts", {}) or {}
    special_marks = analysis.get("special_marks", []) or []

    html = '<div style="font-size:13px; line-height:1.9; color:#5D4E37; padding:8px 4px;">'

    html += '<div style="color:#BFA350; font-weight:bold; margin-bottom:4px;">線の読み方</div>'
    for line_key, defs in LINE_DEFS.items():
        line_data = major_lines.get(line_key, {}) or {}
        if line_data.get("detected"):
            html += (
                f'<div><span style="color:{defs["active"]}; font-weight:bold; font-size:14px;">━</span> '
                f'{defs["name"]}</div>'
            )
        else:
            html += (
                f'<div style="opacity:0.5;"><span style="color:#BDC3C7;">┄┄</span> '
                f'<span style="color:#999;">{defs["name"]}（目立たない）</span></div>'
            )

    developed_mounts = [k for k, v in mounts.items() if v == "developed"]
    if developed_mounts:
        html += '<div style="color:#BFA350; font-weight:bold; margin:10px 0 4px;">発達した丘</div>'
        for m in developed_mounts:
            name = MOUNT_DEFS.get(m, {}).get("name", m)
            html += f'<div><span style="color:#FFD700; font-size:14px;">●</span> {name}</div>'

    detected_marks = [m for m in special_marks if m.get("detected")]
    if detected_marks:
        html += '<div style="color:#BFA350; font-weight:bold; margin:10px 0 4px;">特殊マーク</div>'
        for mark in detected_marks:
            name = mark.get("name", "")
            defs = MARK_DEFS.get(name)
            if not defs:
                continue
            html += (
                f'<div><span style="color:{defs["color"]}; font-size:16px;">{defs["symbol"]}</span> '
                f'{defs["label"]}</div>'
            )

    html += '</div>'
    return html
