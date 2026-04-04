"""
再利用UIコンポーネント（ui/components.py）
裏メニュー・コース別鑑定表示・タロットカード
くろたん完全改良版対応
"""
import os
from datetime import date
import streamlit as st
from core.models import DivinationBundle

TAROT_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tarot_images")


def render_css(css: str):
    st.markdown(css, unsafe_allow_html=True)


def render_gold_divider():
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)


def render_star_deco(text: str = "✦ ☽ ✦"):
    st.markdown(f'<div class="star-deco">{text}</div>', unsafe_allow_html=True)


# ============================================================
# 裏メニュー（ひでさん専用画面）
# ============================================================
def render_ura_menu(bundle: DivinationBundle, recommendation: dict):
    """裏メニュー: 命式ハイライト + おすすめコース"""
    s = bundle.sanmei
    w = bundle.western
    k = bundle.kyusei
    n = bundle.numerology
    current_year = date.today().year

    # 天中殺チェック
    tenchusatsu_status = "⚠ 該当" if current_year in s.tenchusatsu_years else "✓ 非該当"

    render_star_deco("✦")
    st.markdown("""
<div style="text-align:center; margin-bottom:5px;">
  <span style="color:#BFA350; font-size:1.3em; font-weight:bold;">✦ 鑑定準備完了 ✦</span><br>
  <span style="color:#8A8478; font-size:0.85em;">（この画面はあなただけに見えています）</span>
</div>
""", unsafe_allow_html=True)

    # 命式ハイライト（拡張版）
    # ASC/MC表示（出生時刻ありの場合）
    asc_mc_row = ""
    if w.asc_sign:
        asc_mc_row = f'<div>♈ ASC: <span style="color:#D4B96A">{w.asc_sign}</span></div><div>♑ MC: <span style="color:#D4B96A">{w.mc_sign or "不明"}</span></div>'

    st.markdown(f"""<div class="divination-card">
<div class="card-header">── 命式ハイライト ──</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:0.92em;">
<div>🔥 日干: <span style="color:#D4B96A">{s.nichikan}（{s.nichikan_gogyo}性）</span></div>
<div>⭐ 中央星: <span style="color:#D4B96A">{s.chuo_sei}</span></div>
<div>{w.sun_sign_symbol} 太陽星座: <span style="color:#D4B96A">{w.sun_sign}</span></div>
<div>★ 本命星: <span style="color:#D4B96A">{k.honmei_sei}</span></div>
<div>🔢 LP: <span style="color:#D4B96A">{n.life_path}（{n.life_path_title}）</span></div>
<div>🌀 天中殺: <span style="color:#D4B96A">{s.tenchusatsu} {tenchusatsu_status}</span></div>
{asc_mc_row}
</div>
</div>""", unsafe_allow_html=True)

    # 人体図表示（算命学拡張）— 別のmarkdownブロックで表示
    if s.kita_sei:
        st.markdown(f"""<div class="divination-card" style="margin-top:8px;">
<div style="color:#8A8478; font-size:0.8em; margin-bottom:4px; text-align:center;">── 人体図 ──</div>
<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:2px; text-align:center; font-size:0.9em; max-width:280px; margin:0 auto;">
<div></div><div style="color:#D4B96A;">{s.kita_sei}<br><span style="color:#8A8478;font-size:0.8em">北</span></div><div></div>
<div style="color:#D4B96A;">{s.nishi_sei}<br><span style="color:#8A8478;font-size:0.8em">西</span></div>
<div style="color:#BFA350; font-weight:bold;">{s.chuo_sei}<br><span style="color:#8A8478;font-size:0.8em">中央</span></div>
<div style="color:#D4B96A;">{s.higashi_sei}<br><span style="color:#8A8478;font-size:0.8em">東</span></div>
<div></div><div style="color:#D4B96A;">{s.minami_sei}<br><span style="color:#8A8478;font-size:0.8em">南</span></div><div></div>
</div>
</div>""", unsafe_allow_html=True)

    # おすすめコース
    recs = recommendation.get("recommendations", [])
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    st.markdown('<div class="divination-card"><div class="card-header">── おすすめコース ──</div>', unsafe_allow_html=True)

    for rec in recs:
        rank = rec.get("rank", 0)
        medal = medals.get(rank, "")
        course = rec.get("course", "")
        reason = rec.get("reason", "")
        opening = rec.get("opening_line", "")

        st.markdown(f"""
<div style="margin-bottom:12px; padding:8px; border-left:3px solid #BFA350;">
  <div style="font-size:1.05em; color:#D4B96A; font-weight:bold;">{medal} {course}コース</div>
  <div style="font-size:0.88em; color:#A39E93; margin:4px 0;">→ {reason}</div>
  <div style="font-size:0.85em; color:#8A8478; font-style:italic;">💬「{opening}」</div>
</div>
""", unsafe_allow_html=True)

    # フルコースコメント
    full_note = recommendation.get("full_course_note", "")
    if full_note:
        st.markdown(f"""
<div style="margin-top:8px; padding:6px; border:1px dashed #BFA350; border-radius:6px; text-align:center;">
  <span style="color:#BFA350; font-size:0.85em;">✧ フルコース: {full_note}</span>
</div>
""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 共通鑑定結果表示（headline / reading / closing 構造）
# ============================================================
def _render_course_card(title: str, headline: str, reading: str, closing: str,
                        data_tags: str = "", extra_html: str = ""):
    """全コース共通のカード表示。新JSON構造（headline/reading/closing）対応。"""
    st.markdown(f"""
<div class="divination-card">
  <div class="card-header">✦ {title} ✦</div>

  <div style="text-align:center; margin:12px 0;">
    <span style="font-size:1.2em; color:#BFA350; font-weight:bold;">「{headline}」</span>
  </div>

  {data_tags}

  {extra_html}

  <div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{reading}</div>

  <div class="gold-divider"></div>

  <div style="text-align:center; margin-top:14px; font-size:1.05em; color:#D4B96A; font-style:italic; line-height:1.8;">
    ✦ {closing} ✦
  </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# 算命学コース結果（改良版）
# ============================================================
def render_sanmei_course(bundle: DivinationBundle, data: dict):
    """算命学コースの鑑定結果表示"""
    s = bundle.sanmei

    # 命式サマリータグ
    tags = f"""
  <div style="margin:8px 0; display:flex; flex-wrap:wrap; gap:6px; justify-content:center;">
    <span class="uranai-tag-gold">日干: {s.nichikan}（{s.nichikan_gogyo}性・{s.nichikan_inyo}）</span>
    <span class="uranai-tag-gold">中央星: {s.chuo_sei}（{s.chuo_honno}）</span>
    <span class="uranai-tag">{s.tenchusatsu}</span>
  </div>"""

    # 人体図（拡張データがあれば表示）
    jintaizu = ""
    if s.kita_sei:
        jintaizu = f"""
  <div style="margin:10px auto; max-width:280px; padding:8px; border:1px solid #2A2A2A; border-radius:6px;">
    <div style="text-align:center; color:#8A8478; font-size:0.8em; margin-bottom:6px;">── 人体図 ──</div>
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:4px; text-align:center; font-size:0.9em;">
      <div></div><div style="color:#D4B96A;">{s.kita_sei}<br><span style="color:#5A5A5A;font-size:0.75em">北（頭）</span></div><div></div>
      <div style="color:#D4B96A;">{s.nishi_sei}<br><span style="color:#5A5A5A;font-size:0.75em">西（左手）</span></div>
      <div style="color:#BFA350; font-weight:bold;">{s.chuo_sei}<br><span style="color:#5A5A5A;font-size:0.75em">中央（胸）</span></div>
      <div style="color:#D4B96A;">{s.higashi_sei}<br><span style="color:#5A5A5A;font-size:0.75em">東（右手）</span></div>
      <div></div><div style="color:#D4B96A;">{s.minami_sei}<br><span style="color:#5A5A5A;font-size:0.75em">南（腹）</span></div><div></div>
    </div>
  </div>
  <div class="gold-divider"></div>"""

    # 五行バランス表示
    gogyo = s.gogyo_balance
    gogyo_html = ""
    if any(v > 0 for v in gogyo.values()):
        bars = []
        max_val = max(gogyo.values()) or 1
        for element, count in gogyo.items():
            colors = {"木": "#7CB87C", "火": "#C47A6A", "土": "#C49860", "金": "#D4B96A", "水": "#7CA3B8"}
            width = int(count / max_val * 100) if max_val > 0 else 0
            bars.append(f'<div style="display:flex;align-items:center;gap:4px;margin:2px 0;">'
                       f'<span style="width:20px;color:{colors.get(element, "#aaa")}">{element}</span>'
                       f'<div style="background:{colors.get(element, "#555")};height:12px;width:{width}%;border-radius:3px;min-width:4px;"></div>'
                       f'<span style="color:#8A8478;font-size:0.8em;">{count}</span></div>')
        gogyo_html = f"""
  <div style="margin:8px 0; padding:6px; border:1px solid #2A2A2A; border-radius:4px;">
    <div style="color:#8A8478; font-size:0.8em; margin-bottom:4px;">五行バランス:</div>
    {"".join(bars)}
  </div>"""

    # 格局表示
    kakkyoku_html = ""
    if s.kakkyoku:
        kakkyoku_html = f'<div style="text-align:center; margin:6px 0;"><span class="uranai-tag-gold">特殊格局: {s.kakkyoku}</span></div>'

    _render_course_card(
        title="算命学が読み解く、あなたの魂",
        headline=data.get("headline", ""),
        reading=data.get("reading", data.get("nichikan_reading", "")),
        closing=data.get("closing", data.get("one_line", "")),
        data_tags=tags,
        extra_html=jintaizu + gogyo_html + kakkyoku_html,
    )


# ============================================================
# 西洋占星術コース結果（改良版）
# ============================================================
def render_western_course(bundle: DivinationBundle, data: dict):
    """西洋占星術コースの鑑定結果表示"""
    w = bundle.western

    # 天体一覧テーブル
    planet_html = ""
    if w.planets:
        rows = []
        for p in w.planets:
            deg_in_sign = p.degree % 30
            deg_str = f"{int(deg_in_sign)}°{int((deg_in_sign % 1) * 60):02d}'"
            retro = " <span style='color:#C47A6A;'>R</span>" if p.is_retrograde else ""
            house = f"{p.house}H" if p.house else "-"
            rows.append(f"<tr><td>{p.name}</td><td>{p.sign}{retro}</td><td>{deg_str}</td><td>{house}</td></tr>")
        planet_html = f"""
  <details style="margin:8px 0;">
    <summary style="color:#8A8478; cursor:pointer; font-size:0.85em;">📋 天体データ一覧</summary>
    <table style="width:100%; font-size:0.82em; margin-top:4px; border-collapse:collapse;">
      <tr style="color:#BFA350; border-bottom:1px solid #2A2A2A;">
        <th style="text-align:left;padding:2px 4px;">天体</th><th>星座</th><th>度数</th><th>ハウス</th>
      </tr>
      {"".join(rows)}
    </table>
  </details>"""

    # ASC/MC タグ
    asc_mc_tags = ""
    if w.asc_sign:
        asc_mc_tags = f"""
  <div style="margin:6px 0; display:flex; flex-wrap:wrap; gap:6px; justify-content:center;">
    <span class="uranai-tag-gold">ASC: {w.asc_sign}</span>
    <span class="uranai-tag-gold">MC: {w.mc_sign or '不明'}</span>
    <span class="uranai-tag-gold">{w.sun_sign_symbol} 太陽: {w.sun_sign}</span>
    <span class="uranai-tag">月: {w.moon_sign or '不明'}</span>
  </div>"""
    else:
        asc_mc_tags = f"""
  <div style="margin:6px 0; display:flex; flex-wrap:wrap; gap:6px; justify-content:center;">
    <span class="uranai-tag-gold">{w.sun_sign_symbol} 太陽: {w.sun_sign}（{w.sun_element}）</span>
  </div>"""

    # アスペクト一覧
    aspect_html = ""
    if w.aspects:
        aspect_items = []
        for a in w.aspects:
            if a.orb <= 5.0:
                aspect_items.append(f"<span style='color:#A39E93;font-size:0.82em;'>{a.planet1}{a.aspect_type}{a.planet2}({a.orb}°)</span>")
        if aspect_items:
            aspect_html = f"""
  <div style="margin:6px 0; padding:4px; border:1px solid #2A2A2A; border-radius:4px;">
    <div style="color:#8A8478; font-size:0.78em;">主要アスペクト: {" / ".join(aspect_items)}</div>
  </div>"""

    _render_course_card(
        title="西洋占星術が描く、あなたの星図",
        headline=data.get("headline", ""),
        reading=data.get("reading", data.get("sun_reading", "")),
        closing=data.get("closing", data.get("one_line", "")),
        data_tags=asc_mc_tags,
        extra_html=planet_html + aspect_html,
    )


# ============================================================
# 九星気学コース結果（改良版）
# ============================================================
def render_kyusei_course(bundle: DivinationBundle, data: dict):
    """九星気学コースの鑑定結果表示"""
    k = bundle.kyusei

    tags = f"""
  <div style="margin:6px 0; display:flex; flex-wrap:wrap; gap:6px; justify-content:center;">
    <span class="uranai-tag-gold">本命星: {k.honmei_sei}</span>
    <span class="uranai-tag-gold">月命星: {k.getsu_mei_sei}</span>
    <span class="uranai-tag">吉方位: {k.lucky_direction}</span>
    <span class="uranai-tag">凶方位: {k.bad_direction}</span>
  </div>"""

    _render_course_card(
        title="九星気学が示す、あなたの運命",
        headline=data.get("headline", ""),
        reading=data.get("reading", data.get("honmei_reading", "")),
        closing=data.get("closing", data.get("one_line", "")),
        data_tags=tags,
    )


# ============================================================
# 数秘術コース結果（改良版）
# ============================================================
def render_numerology_course(bundle: DivinationBundle, data: dict):
    """数秘術コースの鑑定結果表示"""
    n = bundle.numerology

    tags = f"""
  <div style="margin:6px 0; display:flex; flex-wrap:wrap; gap:6px; justify-content:center;">
    <span class="uranai-tag-gold">ライフパス: {n.life_path}「{n.life_path_title}」</span>
    <span class="uranai-tag-gold">誕生日数: {n.birthday_number}</span>
    <span class="uranai-tag">2026年 個人年: {n.personal_year}「{n.personal_year_title}」</span>
  </div>"""

    _render_course_card(
        title="数秘術が解き明かす、あなたの数字",
        headline=data.get("headline", ""),
        reading=data.get("reading", data.get("life_path_reading", "")),
        closing=data.get("closing", data.get("one_line", "")),
        data_tags=tags,
    )


# ============================================================
# タロットコース結果（改良版）
# ============================================================
def render_tarot_course(bundle: DivinationBundle, data: dict):
    """タロットコースの鑑定結果表示"""
    t = bundle.tarot
    pos_text = "逆位置" if t.is_reversed else "正位置"
    pos_symbol = "🔃" if t.is_reversed else "✨"

    keywords_html = "".join(
        f'<span class="uranai-tag">{kw}</span>' for kw in t.keywords
    )

    headline = data.get("headline", data.get("one_line", ""))

    st.markdown(f"""
<div class="divination-card">
  <div class="card-header">✦ 今のあなたへ ── タロットカード ✦</div>

  <div style="text-align:center; margin:12px 0;">
    <span style="font-size:1.2em; color:#BFA350; font-weight:bold;">「{headline}」</span>
  </div>

  <div style="text-align:center; margin-bottom:6px;">
    <span style="font-size:0.9em; color:#8A8478;">No.{t.card_number} &nbsp;</span>
    <span class="tarot-name-jp" style="font-size:1.2em;">{t.card_name}</span>
    <span style="font-size:0.85em; color:#BFA350;"> {t.card_name_en}</span>
  </div>
  <div style="text-align:center; margin-bottom:8px;">
    <span class="tarot-position">{pos_symbol} {pos_text}</span>
  </div>
""", unsafe_allow_html=True)

    # タロット画像表示
    img_path = os.path.join(TAROT_IMAGES_DIR, f"major_{t.card_number:02d}.jpg")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(img_path):
            from PIL import Image as PILImage
            img = PILImage.open(img_path)
            if t.is_reversed:
                img = img.rotate(180)
            st.image(img, width="stretch")
        else:
            st.markdown("""
<div class="tarot-card-face" style="height:200px; display:flex; align-items:center; justify-content:center;">
  <div style="font-size:3em;">✦</div>
</div>""", unsafe_allow_html=True)

    closing = data.get("closing", "")

    st.markdown(f"""
  <div style="text-align:center; margin:10px 0;">
    {keywords_html}
  </div>
  <div class="gold-divider"></div>
  <div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{data.get('reading', '')}</div>

  <div class="gold-divider"></div>

  <div style="text-align:center; margin-top:14px; font-size:1.05em; color:#D4B96A; font-style:italic; line-height:1.8;">
    ✦ {closing} ✦
  </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# 総合タブ（フルコース時のみ・改良版）
# ============================================================
def render_synthesis_tab(bundle: DivinationBundle, data: dict):
    """総合鑑定タブ: 料理の感想であって料理そのものではない"""
    headline = data.get("headline", "")
    story = data.get("story", data.get("summary", ""))
    message = data.get("message", "")

    st.markdown(f"""
<div class="divination-card">
  <div style="text-align:center; margin-bottom:16px;">
    <div style="font-size:1.4em; color:#BFA350; font-weight:bold; line-height:1.6;">
      ✦ {headline} ✦
    </div>
  </div>

  <div class="reading-text" style="font-size:1.05em; line-height:2.0; white-space:pre-wrap;">
    {story}
  </div>

  <div class="gold-divider"></div>

  <div style="text-align:center; margin-top:14px; font-size:1.1em; color:#D4B96A; font-style:italic; line-height:1.8;">
    {message}
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center; color:#8A8478; font-size:0.85em; margin-top:10px;">
  ↑ もっと深く知りたい占術をタブでタップ ↑
</div>
""", unsafe_allow_html=True)


# ============================================================
# タロットカード裏面（旧互換用）
# ============================================================
def render_tarot_card_back(waiting=False):
    """タロットカード裏面。waiting=Trueならまだ順番が来てないカード"""
    opacity = "0.5" if waiting else "1.0"
    st.markdown(f"""
<div style="text-align:center; opacity:{opacity};">
  <div style="background:linear-gradient(135deg, #1A1A1A 0%, #222222 50%, #1A1A1A 100%);
       border:2px solid #BFA350; border-radius:8px; padding:40px 15px;
       display:inline-block; min-width:120px; min-height:170px;
       display:flex; align-items:center; justify-content:center;">
    <span style="color:#BFA350; font-size:1.5em; letter-spacing:4px;">✦☽✦</span>
  </div>
</div>
""", unsafe_allow_html=True)


SUIT_SYMBOLS = {
    "wands": "🪄", "cups": "🏆", "swords": "⚔️", "pentacles": "💰",
}

def render_tarot_card_simple(card):
    """タロットカード1枚の表面をシンプルに表示（対話型タロット用）"""
    import os
    from PIL import Image

    pos_text = "逆位置" if card.is_reversed else "正位置"
    pos_color = "#D4837A" if card.is_reversed else "#BFA350"

    # カード画像を探す
    img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tarot_images")
    img_found = False

    # image_keyから画像を探す
    if card.image_key:
        img_path = os.path.join(img_dir, f"{card.image_key}.jpg")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            if card.is_reversed:
                img = img.rotate(180)
            st.image(img, width="stretch")
            img_found = True

    # 画像がない場合（小アルカナ等）→ スートシンボルで表示
    if not img_found:
        # image_keyからスートを推測
        suit = ""
        if card.image_key:
            for s in ["wands", "cups", "swords", "pentacles"]:
                if s in card.image_key:
                    suit = s
                    break
        symbol = SUIT_SYMBOLS.get(suit, "🃏")
        rotation = "transform:rotate(180deg);" if card.is_reversed else ""
        st.markdown(f"""
<div style="background:linear-gradient(135deg, #f5f0e0, #e8dcc8); border:2px solid #BFA350;
     border-radius:8px; padding:20px; text-align:center; min-height:140px;
     display:flex; align-items:center; justify-content:center; {rotation}">
  <span style="font-size:3em;">{symbol}</span>
</div>
""", unsafe_allow_html=True)

    # カード名 + ポジション
    st.markdown(f"""
<div style="text-align:center;">
<div style="color:#BFA350; font-weight:bold; font-size:0.95em;">{card.card_name}</div>
<div style="color:#8A8478; font-size:0.75em;">{card.card_name_en}</div>
<div style="color:{pos_color}; font-size:0.8em; margin-top:3px;">{pos_text}</div>
</div>
""", unsafe_allow_html=True)


def render_tarot_card_face(bundle: DivinationBundle, reading: str):
    """旧互換用"""
    render_tarot_course(bundle, {"reading": reading, "headline": "", "closing": ""})


# ============================================================
# テーマ別深掘り鑑定結果
# ============================================================
THEME_DISPLAY = {
    "love": {"icon": "💕", "title": "恋愛運", "color": "#D4837A"},
    "marriage": {"icon": "💍", "title": "結婚運", "color": "#D4B96A"},
    "career": {"icon": "💼", "title": "仕事運", "color": "#7CA3B8"},
    "future10": {"icon": "🔮", "title": "10年後の自分", "color": "#A08B99"},
    "shine": {"icon": "✨", "title": "最大限に輝く生き方", "color": "#D4B96A"},
}


def render_ziwei_course(bundle, data: dict):
    """紫微斗数コースの鑑定結果表示"""
    z = bundle.ziwei
    if z is None:
        st.warning("紫微斗数のデータがありません")
        return

    headline = data.get("headline", "")

    # 命宮の主星
    ming_palace = next((p for p in z.palaces if p.palace_name == '命宮'), None)
    ming_stars_text = '・'.join(ming_palace.main_stars) if ming_palace and ming_palace.main_stars else '空宮（対宮の星が影響）'

    # 四化テキスト
    sihua_text = '　'.join(f'{star}({hua})' for star, hua in z.sihua_assignments.items())

    st.markdown(f"""
<div class="divination-card">
<div class="card-header">✦ 紫微斗数 ── 命盤鑑定 ✦</div>

<div style="text-align:center; margin:12px 0;">
<span style="font-size:1.2em; color:#BFA350; font-weight:bold;">「{headline}」</span>
</div>

<div style="text-align:center; margin-bottom:8px;">
<span style="font-size:0.85em; color:#8A8478;">農暦 {z.lunar_year}年{z.lunar_month}月{z.lunar_day}日 {z.birth_hour_name}生まれ</span>
</div>

<table style="width:100%; border-collapse:collapse; margin:10px 0;">
<tr>
<td style="padding:6px; border:1px solid #2A2A2A; color:#BFA350; width:30%;">命宮</td>
<td style="padding:6px; border:1px solid #2A2A2A; color:#F0EBE0;">{z.ming_gong_branch}宮 ── {ming_stars_text}</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #2A2A2A; color:#BFA350;">身宮</td>
<td style="padding:6px; border:1px solid #2A2A2A; color:#F0EBE0;">{z.shen_gong_branch}宮</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #2A2A2A; color:#BFA350;">五行局</td>
<td style="padding:6px; border:1px solid #2A2A2A; color:#F0EBE0;">{z.five_element_name}</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #2A2A2A; color:#BFA350;">年干支</td>
<td style="padding:6px; border:1px solid #2A2A2A; color:#F0EBE0;">{z.year_stem}{z.year_branch}年</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #2A2A2A; color:#BFA350;">四化</td>
<td style="padding:6px; border:1px solid #2A2A2A; color:#F0EBE0; font-size:0.85em;">{sihua_text}</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #2A2A2A; color:#BFA350;">大限方向</td>
<td style="padding:6px; border:1px solid #2A2A2A; color:#F0EBE0;">{z.da_xian_direction}</td>
</tr>
</table>
""", unsafe_allow_html=True)

    # 命盤グリッド（4x4の宮配置）
    # 巳午未申 / 辰__酉 / 卯__戌 / 寅丑子亥
    GRID_ORDER = [
        [5, 6, 7, 8],     # 巳午未申
        [4, -1, -1, 9],   # 辰__酉
        [3, -1, -1, 10],  # 卯__戌
        [2, 1, 0, 11],    # 寅丑子亥
    ]

    # 地支→宮情報のマッピング
    branch_to_palace = {p.branch_idx: p for p in z.palaces}

    grid_html = '<table style="width:100%; border-collapse:collapse; margin:10px 0; table-layout:fixed;">'
    for row in GRID_ORDER:
        grid_html += '<tr>'
        for branch_idx in row:
            if branch_idx == -1:
                grid_html += '<td style="border:1px solid #2A2A2A; padding:4px; background:#1A1A1A;"></td>'
            else:
                palace = branch_to_palace.get(branch_idx)
                if palace:
                    stars = '<br>'.join(palace.main_stars) if palace.main_stars else ''
                    aux = ' '.join(palace.aux_stars[:3]) if palace.aux_stars else ''
                    sihua_badges = ''.join(f'<span style="color:#D4B96A;font-size:0.7em;">{s}</span>' for s in palace.sihua)
                    is_ming = palace.palace_name == '命宮'
                    bg = '#222222' if is_ming else '#1A1A1A'
                    border_color = '#BFA350' if is_ming else '#2A2A2A'
                    grid_html += f'''<td style="border:1px solid {border_color}; padding:4px; background:{bg}; vertical-align:top; font-size:0.75em; color:#F0EBE0;">
<div style="color:#8A8478;font-size:0.85em;">{palace.palace_name}</div>
<div style="color:#BFA350;font-weight:bold;">{stars}</div>
<div style="color:#8A8478;font-size:0.8em;">{aux}</div>
{sihua_badges}
</td>'''
                else:
                    grid_html += '<td style="border:1px solid #2A2A2A; padding:4px; background:#1A1A1A;"></td>'
        grid_html += '</tr>'
    grid_html += '</table>'

    st.markdown(grid_html, unsafe_allow_html=True)

    # 大限表示
    da_xian_html = '<div style="margin:10px 0;"><span style="color:#BFA350; font-weight:bold;">大限（10年運）</span> ' + z.da_xian_direction + '<br>'
    for i, (s, e) in enumerate(z.da_xian_ages[:8]):
        palace = z.palaces[i] if i < len(z.palaces) else None
        pname = palace.palace_name if palace else ''
        da_xian_html += f'<span style="color:#8A8478; font-size:0.85em;">第{i+1}限 {s}〜{e}歳（{pname}）</span><br>'
    da_xian_html += '</div>'
    st.markdown(da_xian_html, unsafe_allow_html=True)

    # AI鑑定文
    reading = data.get("reading", "")
    if reading:
        st.markdown(f'<div style="color:#F0EBE0; line-height:1.8; margin:15px 0;">{reading}</div>', unsafe_allow_html=True)

    closing = data.get("closing", "")
    if closing:
        st.markdown(f"""
<div style="text-align:center; margin:15px 0; padding:10px; border:1px solid #3A6EA5; border-radius:8px;">
<span style="color:#6EB5FF;">✦ {closing} ✦</span>
</div>
""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_aisho_result(bundle1, bundle2, data: dict):
    """相性占い結果を表示"""
    s1 = bundle1.sanmei
    s2 = bundle2.sanmei
    w1 = bundle1.western
    w2 = bundle2.western
    n1 = bundle1.person.name or "1人目"
    n2 = bundle2.person.name or "2人目"

    headline = data.get("headline", "")
    score = data.get("score", "")
    reading = data.get("reading", "")
    closing = data.get("closing", "")

    # スコア表示
    score_html = ""
    if score:
        try:
            score_int = int(score)
            color = "#D4837A" if score_int >= 80 else "#D4B96A" if score_int >= 60 else "#7CA3B8"
            score_html = f"""
<div style="text-align:center; margin:12px 0;">
<span style="font-size:2.5em; color:{color}; font-weight:bold;">{score_int}</span>
<span style="color:#8A8478; font-size:0.9em;"> / 100</span>
</div>"""
        except ValueError:
            pass

    # 2人のデータ比較タグ
    tags = f"""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:10px 0; font-size:0.88em;">
<div style="text-align:center; padding:8px; border:1px solid #BFA350; border-radius:6px;">
<div style="color:#BFA350; font-weight:bold; margin-bottom:4px;">{n1}</div>
<div>日干: <span style="color:#D4B96A">{s1.nichikan}（{s1.nichikan_gogyo}）</span></div>
<div>{w1.sun_sign_symbol} <span style="color:#D4B96A">{w1.sun_sign}</span></div>
<div>中央星: <span style="color:#D4B96A">{s1.chuo_sei}</span></div>
</div>
<div style="text-align:center; padding:8px; border:1px solid #D4837A; border-radius:6px;">
<div style="color:#D4837A; font-weight:bold; margin-bottom:4px;">{n2}</div>
<div>日干: <span style="color:#D4B96A">{s2.nichikan}（{s2.nichikan_gogyo}）</span></div>
<div>{w2.sun_sign_symbol} <span style="color:#D4B96A">{w2.sun_sign}</span></div>
<div>中央星: <span style="color:#D4B96A">{s2.chuo_sei}</span></div>
</div>
</div>"""

    st.markdown(f"""<div class="divination-card" style="border-color:#D4837A;">
<div class="card-header" style="color:#D4837A;">💕 相性鑑定 💕</div>
<div style="text-align:center; margin:12px 0;">
<span style="font-size:1.2em; color:#D4837A; font-weight:bold;">「{headline}」</span>
</div>
{score_html}
{tags}
<div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{reading}</div>
<div class="gold-divider"></div>
<div style="text-align:center; margin-top:14px; font-size:1.05em; color:#D4837A; font-style:italic; line-height:1.8;">
💕 {closing} 💕
</div>
</div>""", unsafe_allow_html=True)


def render_bansho_course(bundle: DivinationBundle, data: dict = None):
    """万象学コース: 宿命エネルギー指数の結果表示 + AI鑑定文"""
    from core.bansho_energy import get_energy_percent, HONNOU_DETAIL, HONNOU_MAP

    s = bundle.sanmei
    e = s.bansho_energy
    if e is None:
        st.warning("万象学のデータがありません")
        return

    pct = get_energy_percent(e.total_energy)
    bar_filled = int(pct / 5)  # 20文字幅
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    # ── エネルギースペクトル（全体の中での位置） ──
    spectrum_markers = [
        (89, "89"), (160, "160"), (180, "180"), (200, "200"),
        (230, "230"), (300, "300"), (401, "401"),
    ]
    spectrum_pos = max(0, min(100, int((e.total_energy - 89) / (401 - 89) * 100)))
    spectrum_zones = """
<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin:4px 0;">
  <div style="flex:23;background:#7CA3B8;" title="集中特化型(〜160)"></div>
  <div style="flex:6;background:#7CB87C;" title="自営業向き(161〜180)"></div>
  <div style="flex:16;background:#BFA350;" title="組織適応型(181〜230)"></div>
  <div style="flex:22;background:#C49860;" title="超活動型(231〜300)"></div>
  <div style="flex:33;background:#C47A6A;" title="規格外型(301〜)"></div>
</div>"""

    # ── 五本能ランキング行 ──
    medals = ["🥇", "🥈", "🥉", "　", "　"]
    ranking_rows = ""
    for i, (honnou, score) in enumerate(e.honnou_ranking):
        detail = HONNOU_DETAIL.get(honnou, {})
        kw = detail.get("keyword", "")
        pct_of_total = int(score / e.total_energy * 100) if e.total_energy > 0 else 0
        bar_w = int(score / max(e.honnou_ranking[0][1], 1) * 100)
        colors = {"守備": "#7CB87C", "表現": "#C47A6A", "魅力": "#C49860", "攻撃": "#D4B96A", "学習": "#7CA3B8"}
        color = colors.get(honnou, "#BFA350")
        zero_mark = ' <span style="color:#C47A6A;font-size:0.75em;">（未開発）</span>' if score == 0 else ""
        ranking_rows += f"""
<div style="margin:8px 0;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
    <span style="width:24px;font-size:1.1em;">{medals[i]}</span>
    <span style="color:{color};font-weight:bold;width:50px;font-size:1.05em;">{honnou}</span>
    <span style="color:#8A8478;font-size:0.82em;flex:1;">{kw}</span>
    <span style="color:#D4B96A;font-weight:bold;font-size:1.1em;">{score}点</span>
    <span style="color:#5A5A5A;font-size:0.75em;">({pct_of_total}%){zero_mark}</span>
  </div>
  <div style="background:#1A1A1A;border-radius:4px;height:10px;overflow:hidden;">
    <div style="background:{color};height:100%;width:{bar_w}%;border-radius:4px;"></div>
  </div>
</div>"""

    # ── 第1本能の詳細 ──
    top_detail = HONNOU_DETAIL.get(e.top_honnou, {})
    second_detail = HONNOU_DETAIL.get(e.second_honnou, {})

    # 陰陽キャラクター
    yinyang_char = e.top1_yang_detail or e.top1_yin_detail
    yinyang_html = ""
    if yinyang_char and e.dominant_yinyang:
        yinyang_html = f"""
  <div style="margin-top:6px; padding:6px 10px; background:#141414; border-radius:4px;">
    <span style="color:#C49860;font-size:0.8em;">【{e.dominant_yinyang}の{e.top_honnou}】</span>
    <span style="color:#F0EBE0;font-size:0.82em;">{yinyang_char}</span>
  </div>"""

    # ── コンボ才能セクション ──
    combo_html = ""
    if e.combo_talent:
        combo_html = f"""
<div style="margin:12px 0; padding:12px; background:linear-gradient(135deg, #1A1A1A, #222222); border:1px solid #BFA350; border-radius:8px;">
  <div style="color:#D4B96A; font-size:0.95em; font-weight:bold; text-align:center; margin-bottom:6px;">🎯 あなたの才能タイプ: {e.combo_talent}</div>
  <div style="color:#F0EBE0; font-size:0.85em; text-align:center; line-height:1.6;">
    {e.combo_description}<br>
    <span style="color:#8A8478;font-size:0.8em;">（{e.top_honnou}{e.top_score} × {e.second_honnou}{e.second_score} の掛け算）</span>
  </div>
</div>"""

    # ── 五行バランス ──
    gogyo_balance_html = ""
    if e.gogyo_balance:
        gb_rows = ""
        gogyo_colors = {"木": "#7CB87C", "火": "#C47A6A", "土": "#C49860", "金": "#D4B96A", "水": "#7CA3B8"}
        max_score = max((gb.get("score", 0) if isinstance(gb, dict) else 0) for gb in e.gogyo_balance.values()) or 1
        for gname in ["木", "火", "土", "金", "水"]:
            gb = e.gogyo_balance.get(gname, {})
            gscore = gb.get("score", 0) if isinstance(gb, dict) else 0
            gpct = gb.get("percent", 0) if isinstance(gb, dict) else 0
            ghonnou = gb.get("honnou", HONNOU_MAP.get(gname, "")) if isinstance(gb, dict) else ""
            gbar_w = int(gscore / max_score * 100)
            gc = gogyo_colors.get(gname, "#BFA350")
            gb_rows += f"""
<div style="display:flex;align-items:center;gap:6px;margin:4px 0;">
  <span style="color:{gc};width:20px;font-weight:bold;font-size:0.9em;">{gname}</span>
  <span style="color:#8A8478;width:30px;font-size:0.75em;">{ghonnou}</span>
  <div style="flex:1;background:#1A1A1A;border-radius:3px;height:8px;overflow:hidden;">
    <div style="background:{gc};height:100%;width:{gbar_w}%;border-radius:3px;"></div>
  </div>
  <span style="color:#D4B96A;font-size:0.82em;width:40px;text-align:right;">{gscore}</span>
  <span style="color:#5A5A5A;font-size:0.72em;width:35px;">({gpct}%)</span>
</div>"""
        gogyo_balance_html = f"""
<div style="margin:12px 0; padding:10px; border:1px solid #2A2A2A; border-radius:6px;">
  <div style="color:#BFA350; font-size:0.85em; font-weight:bold; margin-bottom:8px;">五行バランス</div>
  {gb_rows}
</div>"""

    # ── 0点本能セクション（詳細版） ──
    zero_html = ""
    if e.zero_honnou_details:
        zero_items = ""
        for zd in e.zero_honnou_details:
            zero_items += f"""
<div style="margin:8px 0; padding:8px; border-left:2px solid #C47A6A; padding-left:12px;">
  <div style="color:#C49860; font-size:0.88em; font-weight:bold;">{zd.get('name','')}</div>
  <div style="color:#F0EBE0; font-size:0.82em; line-height:1.6; margin-top:2px;">
    {zd.get('meaning','')}<br>
    {zd.get('advice','')}<br>
    <span style="color:#7CB87C;">✦ {zd.get('alternative','')}</span>
  </div>
</div>"""
        zero_html = f"""
<div style="margin:12px 0; padding:10px; border:1px dashed #C47A6A44; border-radius:6px; background:#1A1A1A;">
  <div style="color:#C49860; font-size:0.9em; font-weight:bold; margin-bottom:6px;">🔮 0点の本能 ── 未開発の領域</div>
  {zero_items}
</div>"""
    elif e.zero_honnou:
        zero_names = "・".join(e.zero_honnou)
        zero_html = f"""
<div style="margin:12px 0; padding:10px; border:1px dashed #C47A6A44; border-radius:6px; background:#1A1A1A;">
  <div style="color:#C49860; font-size:0.88em; font-weight:bold; margin-bottom:4px;">🔮 0点の本能: {zero_names}</div>
  <div style="color:#F0EBE0; font-size:0.82em; line-height:1.6;">
    生まれ持った才能ではないが「できない」わけではない。<b style="color:#C49860;">意識的に努力が必要な領域。</b>
  </div>
</div>"""

    # ── 陽転・陰転セクション ──
    bd = e.band_detail if isinstance(e.band_detail, dict) else {}
    youten_actions = bd.get("youten_actions", [])
    inten_signs = bd.get("inten_signs", [])
    energy_life_html = ""
    if youten_actions or inten_signs:
        youten_items = ""
        for a in youten_actions:
            youten_items += f'<div style="color:#F0EBE0;font-size:0.82em;line-height:1.6;margin:3px 0;padding-left:14px;text-indent:-14px;">✦ {a}</div>'
        inten_items = ""
        for s_item in inten_signs:
            inten_items += f'<div style="color:#F0EBE0;font-size:0.82em;line-height:1.6;margin:3px 0;padding-left:14px;text-indent:-14px;">⚠ {s_item}</div>'
        correct_life = bd.get("correct_life", "")
        correct_html = f'<div style="color:#F0EBE0;font-size:0.85em;line-height:1.6;margin-bottom:10px;padding:6px 10px;background:#141414;border-radius:4px;">{correct_life}</div>' if correct_life else ""
        energy_life_html = f"""
<div style="margin:12px 0; padding:12px; border:1px solid #2A2A2A; border-radius:6px;">
  <div style="color:#BFA350; font-size:0.9em; font-weight:bold; margin-bottom:8px;">⚡ エネルギーの正しい使い方</div>
  {correct_html}
  <div style="color:#7CB87C; font-size:0.85em; font-weight:bold; margin:8px 0 4px;">陽転（健全にエネルギーを使う）</div>
  {youten_items}
  <div style="color:#C47A6A; font-size:0.85em; font-weight:bold; margin:10px 0 4px;">陰転サイン（こうなったら要注意）</div>
  {inten_items}
</div>"""

    # ── drink_talk セクション ──
    drink_html = ""
    if e.drink_talk:
        drink_html = f"""
<div style="margin:12px 0; padding:10px; background:#141414; border-radius:6px; border-left:3px solid #BFA350;">
  <div style="color:#BFA350; font-size:0.8em; font-weight:bold; margin-bottom:4px;">🍺 くろちゃんの即答</div>
  <div style="color:#F0EBE0; font-size:0.85em; line-height:1.7; font-style:italic;">{e.drink_talk}</div>
</div>"""

    # ── AI鑑定文セクション ──
    ai_reading_html = ""
    if data and data.get("reading"):
        headline = data.get("headline", "")
        reading = data.get("reading", "")
        closing = data.get("closing", "")
        ai_reading_html = f"""
<div class="gold-divider"></div>
<div style="color:#BFA350; font-size:0.9em; font-weight:bold; margin:12px 0 6px; text-align:center;">── くろちゃんの鑑定 ──</div>
<div style="text-align:center; margin:8px 0 12px;">
  <span style="font-size:1.1em; color:#D4B96A; font-weight:bold;">「{headline}」</span>
</div>
<div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{reading}</div>
<div style="text-align:center; margin-top:14px; font-size:1.0em; color:#BFA350; font-style:italic; line-height:1.8;">
  ✦ {closing} ✦
</div>"""

    # ── メインレンダリング ──
    st.markdown(f"""
<div class="divination-card" style="border-color:#BFA350;">
<div class="card-header">⚡ 万象学 ── 宿命エネルギー診断 ⚡</div>

<div style="text-align:center; margin:16px 0 8px;">
  <div style="font-size:3em; font-weight:bold; color:#D4B96A; line-height:1;">{e.total_energy}</div>
  <div style="font-size:0.9em; color:#BFA350; margin-top:4px;">宿命エネルギー指数</div>
</div>

<div style="text-align:center; margin:8px 0;">
  <span class="uranai-tag-gold" style="font-size:1em; padding:4px 16px;">{e.energy_type}</span>
</div>

<div style="margin:12px 20px;">
  <div style="position:relative;">
    {spectrum_zones}
    <div style="position:relative;height:20px;">
      <div style="position:absolute;left:{spectrum_pos}%;transform:translateX(-50%);text-align:center;">
        <div style="color:#D4B96A;font-size:1.2em;line-height:1;">▼</div>
        <div style="color:#D4B96A;font-size:0.72em;font-weight:bold;">{e.total_energy}</div>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;color:#5A5A5A;font-size:0.65em;margin-top:2px;">
      <span>89</span><span>160</span><span>200</span><span>300</span><span>401</span>
    </div>
  </div>
</div>

<div style="text-align:center; color:#8A8478; font-size:0.88em; margin:6px 0 16px; line-height:1.6;">
  {e.energy_description}
</div>

{drink_html}

<div class="gold-divider"></div>

<div style="color:#BFA350; font-size:0.9em; font-weight:bold; margin:12px 0 6px; text-align:center;">── 五本能ランキング ──</div>
{ranking_rows}

{combo_html}

{gogyo_balance_html}

<div class="gold-divider"></div>

<div style="margin:12px 0; padding:10px; border:1px solid #2A2A2A; border-radius:6px;">
  <div style="color:#BFA350; font-size:0.88em; font-weight:bold; margin-bottom:6px;">💡 第1本能: {e.top_honnou}（{top_detail.get('gogyo','')}/{e.top_score}点）</div>
  <div style="color:#F0EBE0; font-size:0.85em; line-height:1.7;">
    {top_detail.get('personality','')}<br>
    <span style="color:#8A8478;">向いてる仕事:</span> {top_detail.get('career','')}<br>
    <span style="color:#7CB87C;">強み:</span> {top_detail.get('strong','')}
    <span style="color:#C47A6A;"> 弱み:</span> {top_detail.get('weak','')}
  </div>
  {yinyang_html}
</div>

<div style="margin:12px 0; padding:10px; border:1px solid #2A2A2A; border-radius:6px;">
  <div style="color:#BFA350; font-size:0.88em; font-weight:bold; margin-bottom:6px;">💡 第2本能: {e.second_honnou}（{second_detail.get('gogyo','')}/{e.second_score}点）</div>
  <div style="color:#F0EBE0; font-size:0.85em; line-height:1.7;">
    {second_detail.get('personality','')}<br>
    <span style="color:#8A8478;">向いてる仕事:</span> {second_detail.get('career','')}
  </div>
</div>

{zero_html}

{energy_life_html}

{ai_reading_html}

<div style="text-align:center; margin:16px 0 8px; color:#8A8478; font-size:0.78em; line-height:1.6;">
  ※エネルギーの高低に良し悪しはありません。<br>
  自分のエネルギー量に合った生き方をすることが最も重要です。
</div>

<div style="text-align:center; margin-top:12px; color:#BFA350; font-size:0.88em; font-weight:bold;">
  {e.energy_advice}
</div>

</div>""", unsafe_allow_html=True)


def render_theme_result(theme_key: str, data: dict):
    """テーマ別鑑定結果を表示"""
    theme = THEME_DISPLAY.get(theme_key, {"icon": "✦", "title": theme_key, "color": "#BFA350"})

    headline = data.get("headline", "")
    reading = data.get("reading", "")
    closing = data.get("closing", "")

    st.markdown(f"""<div class="divination-card" style="border-color:{theme['color']}; margin-top:16px;">
<div class="card-header" style="color:{theme['color']};">{theme['icon']} {theme['title']} {theme['icon']}</div>
<div style="text-align:center; margin:12px 0;">
<span style="font-size:1.2em; color:{theme['color']}; font-weight:bold;">「{headline}」</span>
</div>
<div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{reading}</div>
<div class="gold-divider"></div>
<div style="text-align:center; margin-top:14px; font-size:1.05em; color:{theme['color']}; font-style:italic; line-height:1.8;">
✦ {closing} ✦
</div>
</div>""", unsafe_allow_html=True)
