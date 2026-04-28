"""
占いモンスター 手相SVG ダイアグラム生成

Round 7（くろたん指令: 手のひらイラスト実装指令書 2026-04-28）
- 手のひら輪郭 + 5本指 のSVG
- 検出された主要線をカラーでハイライト
- 検出されなかった線はグレー破線
- 発達した丘をゴールド半透明円で強調
- 特殊マークをアイコン表示
- 凡例HTMLも生成
- 左右の手を transform で反転対応
"""
from typing import Optional

# ============================================================
# 定数
# ============================================================

# 線の日本語名と色
LINE_DEFS = {
    "life_line":  {"name": "生命線",  "active": "#E74C3C", "label_x": 50,  "label_y": 360},
    "head_line":  {"name": "頭脳線",  "active": "#2ECC71", "label_x": 50,  "label_y": 250},
    "heart_line": {"name": "感情線",  "active": "#3498DB", "label_x": 60,  "label_y": 200},
    "fate_line":  {"name": "運命線",  "active": "#9B59B6", "label_x": 305, "label_y": 360},
    "sun_line":   {"name": "太陽線",  "active": "#F1C40F", "label_x": 305, "label_y": 290},
}

# 主要線のSVGパス（viewBox 360x480、左手前提）
LINE_PATHS = {
    # 生命線: 親指と人差し指の間 → 手首
    "life_line":  "M 138,210 C 120,260 95,330 90,400 Q 88,420 105,425",
    # 頭脳線: 生命線起点付近 → 手の中央横へ
    "head_line":  "M 138,235 C 165,250 200,255 240,250 Q 260,248 275,253",
    # 感情線: 小指側 → 人差し指方向
    "heart_line": "M 270,205 C 240,200 200,202 160,210 Q 140,213 122,220",
    # 運命線: 手首中央 → 中指の付け根
    "fate_line":  "M 180,425 C 178,375 176,320 174,275 Q 173,250 173,225",
    # 太陽線: 中央下 → 薬指の付け根
    "sun_line":   "M 222,340 C 220,310 218,275 216,240 Q 215,225 215,215",
}

# 線の表示スタイル（detected/length/depth による分岐）
def line_style(detected: bool, length: str, depth: str) -> dict:
    """線の表示スタイルを返す"""
    if not detected:
        return {"stroke_width": 1.5, "opacity": 0.4, "dasharray": "4,4"}
    # 検出された場合、深さで太さを変える
    if depth == "deep":
        return {"stroke_width": 4, "opacity": 1.0, "dasharray": "none"}
    elif depth == "shallow":
        return {"stroke_width": 2, "opacity": 0.7, "dasharray": "none"}
    else:  # normal or unknown
        return {"stroke_width": 3, "opacity": 0.9, "dasharray": "none"}


# 丘の位置と日本語名
MOUNT_DEFS = {
    "jupiter":       {"name": "木星丘",   "cx": 138, "cy": 200, "r": 22, "label_dy": 4},
    "saturn":        {"name": "土星丘",   "cx": 178, "cy": 195, "r": 20, "label_dy": 4},
    "apollo":        {"name": "太陽丘",   "cx": 220, "cy": 200, "r": 20, "label_dy": 4},
    "mercury":       {"name": "水星丘",   "cx": 262, "cy": 215, "r": 20, "label_dy": 4},
    "venus":         {"name": "金星丘",   "cx": 110, "cy": 320, "r": 32, "label_dy": 4},
    "luna":          {"name": "月丘",     "cx": 270, "cy": 360, "r": 30, "label_dy": 4},
    "mars_positive": {"name": "第一火星丘", "cx": 110, "cy": 245, "r": 16, "label_dy": 4},
    "mars_negative": {"name": "第二火星丘", "cx": 270, "cy": 290, "r": 16, "label_dy": 4},
}


def mount_style(level: str) -> Optional[dict]:
    """丘の表示スタイル。普通・不明 は表示しない（描画なし）"""
    if level == "developed":
        return {"fill": "#FFD700", "opacity": 0.32}
    elif level == "weak":
        return {"fill": "#7F8C8D", "opacity": 0.15}
    return None


# 特殊マーク
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

# マークの表示位置（おおよそ）。実際の location が来ない場合のフォールバック
MARK_DEFAULT_POS = {
    "simian_line":    (180, 220),
    "mystic_cross":   (200, 280),
    "ring_of_solomon":(138, 175),
    "haoh_line":      (180, 270),
    "buddha_eye":     (60, 240),  # 親指
    "star":           (220, 215),
    "great_triangle": (180, 290),
    "square":         (240, 290),
}


# ============================================================
# 手のひら輪郭の SVG（左手前提、右手は transform で反転）
# ============================================================

HAND_OUTLINE_SVG = """
  <!-- 背景 -->
  <rect x="0" y="0" width="360" height="480" fill="#FFF8F0" rx="20"/>

  <!-- 手のひら本体 -->
  <path d="M 88 220
           Q 78 280 78 340
           Q 78 410 130 435
           Q 180 450 230 435
           Q 285 410 285 340
           Q 285 280 275 220
           Q 250 210 220 210
           L 220 200
           Q 195 205 178 205
           Q 160 205 138 200
           Q 115 205 100 210
           Q 90 213 88 220 Z"
        fill="#FDEBD0" stroke="#D4A574" stroke-width="2"/>

  <!-- 親指（左下から外へ） -->
  <path d="M 88 230
           Q 60 235 45 260
           Q 35 290 50 320
           Q 70 340 95 325
           Q 105 310 102 270
           Q 100 245 88 230 Z"
        fill="#FDEBD0" stroke="#D4A574" stroke-width="2"/>

  <!-- 人差し指 -->
  <path d="M 120 205
           Q 118 130 122 65
           Q 124 35 138 35
           Q 152 35 152 65
           Q 150 130 152 205 Z"
        fill="#FDEBD0" stroke="#D4A574" stroke-width="2"/>

  <!-- 中指 -->
  <path d="M 162 205
           Q 160 120 164 45
           Q 166 18 180 18
           Q 194 18 195 45
           Q 192 120 196 205 Z"
        fill="#FDEBD0" stroke="#D4A574" stroke-width="2"/>

  <!-- 薬指 -->
  <path d="M 205 205
           Q 203 130 208 60
           Q 210 32 222 32
           Q 234 32 235 60
           Q 232 130 237 205 Z"
        fill="#FDEBD0" stroke="#D4A574" stroke-width="2"/>

  <!-- 小指 -->
  <path d="M 247 215
           Q 245 165 250 110
           Q 252 80 263 80
           Q 274 80 275 110
           Q 272 165 277 215 Z"
        fill="#FDEBD0" stroke="#D4A574" stroke-width="2"/>

  <!-- 手首（下） -->
  <path d="M 130 435 Q 180 450 230 435 L 240 470 Q 180 480 120 470 Z"
        fill="#FDEBD0" stroke="#D4A574" stroke-width="2"/>
"""


# ============================================================
# SVG 生成
# ============================================================

def _draw_lines(major_lines: dict) -> str:
    """主要線をSVGで描画"""
    svg = ""
    for line_key, defs in LINE_DEFS.items():
        line_data = major_lines.get(line_key, {}) or {}
        detected = bool(line_data.get("detected"))
        length = line_data.get("length", "unknown") or "unknown"
        depth = line_data.get("depth", "unknown") or "unknown"
        style = line_style(detected, length, depth)
        path = LINE_PATHS[line_key]
        color = defs["active"] if detected else "#BDC3C7"
        dash = f' stroke-dasharray="{style["dasharray"]}"' if style["dasharray"] != "none" else ""
        svg += (
            f'<path d="{path}" fill="none" '
            f'stroke="{color}" stroke-width="{style["stroke_width"]}" '
            f'opacity="{style["opacity"]}" stroke-linecap="round"{dash}/>\n'
        )
    return svg


def _draw_mounts(mounts: dict) -> str:
    """丘をSVGで描画"""
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


def _draw_special_marks(special_marks: list, hand: str = "left") -> str:
    """検出された特殊マークをアイコン表示"""
    svg = ""
    for mark in (special_marks or []):
        if not mark.get("detected"):
            continue
        name = mark.get("name", "")
        defs = MARK_DEFS.get(name)
        if not defs:
            continue
        cx, cy = MARK_DEFAULT_POS.get(name, (180, 250))
        svg += (
            f'<text x="{cx}" y="{cy}" font-size="22" '
            f'text-anchor="middle" fill="{defs["color"]}">{defs["symbol"]}</text>\n'
        )
    return svg


def _draw_labels(major_lines: dict, hand: str = "left") -> str:
    """検出された線のラベルを描画。右手の場合は座標を反転調整。"""
    svg = ""
    is_right = hand == "right"
    for line_key, defs in LINE_DEFS.items():
        line_data = major_lines.get(line_key, {}) or {}
        if not line_data.get("detected"):
            continue
        x = defs["label_x"]
        y = defs["label_y"]
        if is_right:
            # 右手は SVG が反転するので、ラベルだけ手動で位置調整
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


def generate_palm_diagram(analysis: dict, hand: str = "left", width: int = 360, height: int = 480) -> str:
    """
    画像認識の分析結果に基づいた手のひらSVGを返す。

    Args:
        analysis: Gemini が返した構造化JSON
                  {
                    "hand_shape": {"type": ...},
                    "major_lines": {"life_line": {...}, "head_line": {...}, ...},
                    "mounts": {"jupiter": "developed", ...},
                    "special_marks": [{"name": "buddha_eye", "detected": true, ...}, ...]
                  }
        hand: "left" | "right"
        width, height: SVG サイズ

    Returns:
        SVG 文字列（HTML として safe に埋め込める）
    """
    if not analysis:
        analysis = {}
    major_lines = analysis.get("major_lines", {}) or {}
    mounts = analysis.get("mounts", {}) or {}
    special_marks = analysis.get("special_marks", []) or []

    # 左手はそのまま、右手は X 軸で反転
    if hand == "right":
        transform = f' transform="translate({width}, 0) scale(-1, 1)"'
    else:
        transform = ""

    inner = HAND_OUTLINE_SVG
    inner += _draw_lines(major_lines)
    inner += _draw_mounts(mounts)
    inner += _draw_special_marks(special_marks, hand)

    # ラベルは反転させない
    labels = _draw_labels(major_lines, hand)

    svg = f"""
<div style="text-align:center; margin: 8px 0;">
  <svg viewBox="0 0 {width} {height}" width="{width}" height="{height}"
       xmlns="http://www.w3.org/2000/svg"
       style="max-width:100%; height:auto; background:#FFF8F0; border-radius:20px; box-shadow:0 2px 8px rgba(150,120,80,0.15);">
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

    # 主要線
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

    # 発達した丘
    developed_mounts = [k for k, v in mounts.items() if v == "developed"]
    if developed_mounts:
        html += '<div style="color:#BFA350; font-weight:bold; margin:10px 0 4px;">発達した丘</div>'
        for m in developed_mounts:
            name = MOUNT_DEFS.get(m, {}).get("name", m)
            html += f'<div><span style="color:#FFD700; font-size:14px;">●</span> {name}</div>'

    # 検出された特殊マーク
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
