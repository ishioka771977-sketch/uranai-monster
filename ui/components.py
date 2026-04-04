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
  <span style="color:#C9A84C; font-size:1.3em; font-weight:bold;">✦ 鑑定準備完了 ✦</span><br>
  <span style="color:#9B8FC4; font-size:0.85em;">（この画面はあなただけに見えています）</span>
</div>
""", unsafe_allow_html=True)

    # 命式ハイライト（拡張版）
    # ASC/MC表示（出生時刻ありの場合）
    asc_mc_row = ""
    if w.asc_sign:
        asc_mc_row = f'<div>♈ ASC: <span style="color:#F5D78E">{w.asc_sign}</span></div><div>♑ MC: <span style="color:#F5D78E">{w.mc_sign or "不明"}</span></div>'

    st.markdown(f"""<div class="divination-card">
<div class="card-header">── 命式ハイライト ──</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:0.92em;">
<div>🔥 日干: <span style="color:#F5D78E">{s.nichikan}（{s.nichikan_gogyo}性）</span></div>
<div>⭐ 中央星: <span style="color:#F5D78E">{s.chuo_sei}</span></div>
<div>{w.sun_sign_symbol} 太陽星座: <span style="color:#F5D78E">{w.sun_sign}</span></div>
<div>★ 本命星: <span style="color:#F5D78E">{k.honmei_sei}</span></div>
<div>🔢 LP: <span style="color:#F5D78E">{n.life_path}（{n.life_path_title}）</span></div>
<div>🌀 天中殺: <span style="color:#F5D78E">{s.tenchusatsu} {tenchusatsu_status}</span></div>
{asc_mc_row}
</div>
</div>""", unsafe_allow_html=True)

    # 人体図表示（算命学拡張）— 別のmarkdownブロックで表示
    if s.kita_sei:
        st.markdown(f"""<div class="divination-card" style="margin-top:8px;">
<div style="color:#9B8FC4; font-size:0.8em; margin-bottom:4px; text-align:center;">── 人体図 ──</div>
<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:2px; text-align:center; font-size:0.9em; max-width:280px; margin:0 auto;">
<div></div><div style="color:#F5D78E;">{s.kita_sei}<br><span style="color:#9B8FC4;font-size:0.8em">北</span></div><div></div>
<div style="color:#F5D78E;">{s.nishi_sei}<br><span style="color:#9B8FC4;font-size:0.8em">西</span></div>
<div style="color:#C9A84C; font-weight:bold;">{s.chuo_sei}<br><span style="color:#9B8FC4;font-size:0.8em">中央</span></div>
<div style="color:#F5D78E;">{s.higashi_sei}<br><span style="color:#9B8FC4;font-size:0.8em">東</span></div>
<div></div><div style="color:#F5D78E;">{s.minami_sei}<br><span style="color:#9B8FC4;font-size:0.8em">南</span></div><div></div>
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
<div style="margin-bottom:12px; padding:8px; border-left:3px solid #C9A84C;">
  <div style="font-size:1.05em; color:#F5D78E; font-weight:bold;">{medal} {course}コース</div>
  <div style="font-size:0.88em; color:#d4d0e0; margin:4px 0;">→ {reason}</div>
  <div style="font-size:0.85em; color:#9B8FC4; font-style:italic;">💬「{opening}」</div>
</div>
""", unsafe_allow_html=True)

    # フルコースコメント
    full_note = recommendation.get("full_course_note", "")
    if full_note:
        st.markdown(f"""
<div style="margin-top:8px; padding:6px; border:1px dashed #C9A84C; border-radius:6px; text-align:center;">
  <span style="color:#C9A84C; font-size:0.85em;">✧ フルコース: {full_note}</span>
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
    <span style="font-size:1.2em; color:#C9A84C; font-weight:bold;">「{headline}」</span>
  </div>

  {data_tags}

  {extra_html}

  <div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{reading}</div>

  <div class="gold-divider"></div>

  <div style="text-align:center; margin-top:14px; font-size:1.05em; color:#F5D78E; font-style:italic; line-height:1.8;">
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
  <div style="margin:10px auto; max-width:280px; padding:8px; border:1px solid #3a3652; border-radius:6px;">
    <div style="text-align:center; color:#9B8FC4; font-size:0.8em; margin-bottom:6px;">── 人体図 ──</div>
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:4px; text-align:center; font-size:0.9em;">
      <div></div><div style="color:#F5D78E;">{s.kita_sei}<br><span style="color:#666;font-size:0.75em">北（頭）</span></div><div></div>
      <div style="color:#F5D78E;">{s.nishi_sei}<br><span style="color:#666;font-size:0.75em">西（左手）</span></div>
      <div style="color:#C9A84C; font-weight:bold;">{s.chuo_sei}<br><span style="color:#666;font-size:0.75em">中央（胸）</span></div>
      <div style="color:#F5D78E;">{s.higashi_sei}<br><span style="color:#666;font-size:0.75em">東（右手）</span></div>
      <div></div><div style="color:#F5D78E;">{s.minami_sei}<br><span style="color:#666;font-size:0.75em">南（腹）</span></div><div></div>
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
            colors = {"木": "#4CAF50", "火": "#FF5722", "土": "#FF9800", "金": "#FFD700", "水": "#2196F3"}
            width = int(count / max_val * 100) if max_val > 0 else 0
            bars.append(f'<div style="display:flex;align-items:center;gap:4px;margin:2px 0;">'
                       f'<span style="width:20px;color:{colors.get(element, "#aaa")}">{element}</span>'
                       f'<div style="background:{colors.get(element, "#555")};height:12px;width:{width}%;border-radius:3px;min-width:4px;"></div>'
                       f'<span style="color:#9B8FC4;font-size:0.8em;">{count}</span></div>')
        gogyo_html = f"""
  <div style="margin:8px 0; padding:6px; border:1px solid #3a3652; border-radius:4px;">
    <div style="color:#9B8FC4; font-size:0.8em; margin-bottom:4px;">五行バランス:</div>
    {"".join(bars)}
  </div>"""

    # 格局表示
    kakkyoku_html = ""
    if s.kakkyoku:
        kakkyoku_html = f'<div style="text-align:center; margin:6px 0;"><span class="uranai-tag-gold">特殊格局: {s.kakkyoku}</span></div>'

    # 万象学エネルギー表示
    energy_html = ""
    if s.bansho_energy:
        from core.bansho_energy import get_energy_percent, HONNOU_DETAIL
        e = s.bansho_energy
        pct = get_energy_percent(e.total_energy)
        bar_filled = int(pct / 4)  # 25文字幅
        bar = "█" * bar_filled + "░" * (25 - bar_filled)
        medals = ["🥇", "🥈", "🥉", "　", "　"]
        ranking_rows = ""
        for i, (honnou, score) in enumerate(e.honnou_ranking):
            detail = HONNOU_DETAIL.get(honnou, {})
            kw = detail.get("keyword", "")
            ranking_rows += (
                f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">'
                f'<span style="width:22px;">{medals[i]}</span>'
                f'<span style="color:#F5D78E;width:40px;">{honnou}</span>'
                f'<span style="color:#9B8FC4;font-size:0.85em;flex:1;">{kw}</span>'
                f'<span style="color:#C9A84C;font-weight:bold;">{score}点</span>'
                f'</div>'
            )
        energy_html = f"""
  <div style="margin:12px 0; padding:10px; border:1px solid #C9A84C; border-radius:6px; background:rgba(201,168,76,0.05);">
    <div style="text-align:center; color:#C9A84C; font-size:0.9em; font-weight:bold; margin-bottom:8px;">═══ 宿命エネルギー ═══</div>
    <div style="text-align:center; margin:6px 0;">
      <span style="color:#F5D78E; font-size:1.4em; font-weight:bold;">{e.total_energy}</span>
      <span style="color:#9B8FC4; font-size:0.85em; margin-left:6px;">{e.energy_type}</span>
    </div>
    <div style="text-align:center; font-family:monospace; color:#C9A84C; font-size:0.85em; margin:4px 0;">
      {bar} {pct}%<span style="color:#666;font-size:0.8em;">（範囲: 89〜401）</span>
    </div>
    <div style="margin:8px 0 4px; padding-top:6px; border-top:1px solid #3a3652;">
      {ranking_rows}
    </div>
    <div style="color:#9B8FC4; font-size:0.78em; margin-top:6px; text-align:center;">{e.energy_description}</div>
  </div>"""

    _render_course_card(
        title="算命学が読み解く、あなたの魂",
        headline=data.get("headline", ""),
        reading=data.get("reading", data.get("nichikan_reading", "")),
        closing=data.get("closing", data.get("one_line", "")),
        data_tags=tags,
        extra_html=jintaizu + gogyo_html + kakkyoku_html + energy_html,
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
            retro = " <span style='color:#FF6B6B;'>R</span>" if p.is_retrograde else ""
            house = f"{p.house}H" if p.house else "-"
            rows.append(f"<tr><td>{p.name}</td><td>{p.sign}{retro}</td><td>{deg_str}</td><td>{house}</td></tr>")
        planet_html = f"""
  <details style="margin:8px 0;">
    <summary style="color:#9B8FC4; cursor:pointer; font-size:0.85em;">📋 天体データ一覧</summary>
    <table style="width:100%; font-size:0.82em; margin-top:4px; border-collapse:collapse;">
      <tr style="color:#C9A84C; border-bottom:1px solid #3a3652;">
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
                aspect_items.append(f"<span style='color:#d4d0e0;font-size:0.82em;'>{a.planet1}{a.aspect_type}{a.planet2}({a.orb}°)</span>")
        if aspect_items:
            aspect_html = f"""
  <div style="margin:6px 0; padding:4px; border:1px solid #3a3652; border-radius:4px;">
    <div style="color:#9B8FC4; font-size:0.78em;">主要アスペクト: {" / ".join(aspect_items)}</div>
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
    <span style="font-size:1.2em; color:#C9A84C; font-weight:bold;">「{headline}」</span>
  </div>

  <div style="text-align:center; margin-bottom:6px;">
    <span style="font-size:0.9em; color:#9B8FC4;">No.{t.card_number} &nbsp;</span>
    <span class="tarot-name-jp" style="font-size:1.2em;">{t.card_name}</span>
    <span style="font-size:0.85em; color:#C9A84C;"> {t.card_name_en}</span>
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

  <div style="text-align:center; margin-top:14px; font-size:1.05em; color:#F5D78E; font-style:italic; line-height:1.8;">
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
    <div style="font-size:1.4em; color:#C9A84C; font-weight:bold; line-height:1.6;">
      ✦ {headline} ✦
    </div>
  </div>

  <div class="reading-text" style="font-size:1.05em; line-height:2.0; white-space:pre-wrap;">
    {story}
  </div>

  <div class="gold-divider"></div>

  <div style="text-align:center; margin-top:14px; font-size:1.1em; color:#F5D78E; font-style:italic; line-height:1.8;">
    {message}
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center; color:#9B8FC4; font-size:0.85em; margin-top:10px;">
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
  <div style="background:linear-gradient(135deg, #1a1040 0%, #2d1b69 50%, #1a1040 100%);
       border:2px solid #C9A84C; border-radius:8px; padding:40px 15px;
       display:inline-block; min-width:120px; min-height:170px;
       display:flex; align-items:center; justify-content:center;">
    <span style="color:#C9A84C; font-size:1.5em; letter-spacing:4px;">✦☽✦</span>
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
    pos_color = "#FF6B9D" if card.is_reversed else "#C9A84C"

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
<div style="background:linear-gradient(135deg, #f5f0e0, #e8dcc8); border:2px solid #C9A84C;
     border-radius:8px; padding:20px; text-align:center; min-height:140px;
     display:flex; align-items:center; justify-content:center; {rotation}">
  <span style="font-size:3em;">{symbol}</span>
</div>
""", unsafe_allow_html=True)

    # カード名 + ポジション
    st.markdown(f"""
<div style="text-align:center;">
<div style="color:#C9A84C; font-weight:bold; font-size:0.95em;">{card.card_name}</div>
<div style="color:#9B8FC4; font-size:0.75em;">{card.card_name_en}</div>
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
    "love": {"icon": "💕", "title": "恋愛運", "color": "#FF6B9D"},
    "marriage": {"icon": "💍", "title": "結婚運", "color": "#FFD700"},
    "career": {"icon": "💼", "title": "仕事運", "color": "#4FC3F7"},
    "future10": {"icon": "🔮", "title": "10年後の自分", "color": "#CE93D8"},
    "shine": {"icon": "✨", "title": "最大限に輝く生き方", "color": "#FFE082"},
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
<span style="font-size:1.2em; color:#C9A84C; font-weight:bold;">「{headline}」</span>
</div>

<div style="text-align:center; margin-bottom:8px;">
<span style="font-size:0.85em; color:#9B8FC4;">農暦 {z.lunar_year}年{z.lunar_month}月{z.lunar_day}日 {z.birth_hour_name}生まれ</span>
</div>

<table style="width:100%; border-collapse:collapse; margin:10px 0;">
<tr>
<td style="padding:6px; border:1px solid #3A2E6E; color:#C9A84C; width:30%;">命宮</td>
<td style="padding:6px; border:1px solid #3A2E6E; color:#E8E0F0;">{z.ming_gong_branch}宮 ── {ming_stars_text}</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #3A2E6E; color:#C9A84C;">身宮</td>
<td style="padding:6px; border:1px solid #3A2E6E; color:#E8E0F0;">{z.shen_gong_branch}宮</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #3A2E6E; color:#C9A84C;">五行局</td>
<td style="padding:6px; border:1px solid #3A2E6E; color:#E8E0F0;">{z.five_element_name}</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #3A2E6E; color:#C9A84C;">年干支</td>
<td style="padding:6px; border:1px solid #3A2E6E; color:#E8E0F0;">{z.year_stem}{z.year_branch}年</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #3A2E6E; color:#C9A84C;">四化</td>
<td style="padding:6px; border:1px solid #3A2E6E; color:#E8E0F0; font-size:0.85em;">{sihua_text}</td>
</tr>
<tr>
<td style="padding:6px; border:1px solid #3A2E6E; color:#C9A84C;">大限方向</td>
<td style="padding:6px; border:1px solid #3A2E6E; color:#E8E0F0;">{z.da_xian_direction}</td>
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
                grid_html += '<td style="border:1px solid #2A1F4E; padding:4px; background:#1A1535;"></td>'
            else:
                palace = branch_to_palace.get(branch_idx)
                if palace:
                    stars = '<br>'.join(palace.main_stars) if palace.main_stars else ''
                    aux = ' '.join(palace.aux_stars[:3]) if palace.aux_stars else ''
                    sihua_badges = ''.join(f'<span style="color:#FFD700;font-size:0.7em;">{s}</span>' for s in palace.sihua)
                    is_ming = palace.palace_name == '命宮'
                    bg = '#2A1F5E' if is_ming else '#1A1535'
                    border_color = '#C9A84C' if is_ming else '#3A2E6E'
                    grid_html += f'''<td style="border:1px solid {border_color}; padding:4px; background:{bg}; vertical-align:top; font-size:0.75em; color:#E8E0F0;">
<div style="color:#9B8FC4;font-size:0.85em;">{palace.palace_name}</div>
<div style="color:#C9A84C;font-weight:bold;">{stars}</div>
<div style="color:#7A6FA0;font-size:0.8em;">{aux}</div>
{sihua_badges}
</td>'''
                else:
                    grid_html += '<td style="border:1px solid #2A1F4E; padding:4px; background:#1A1535;"></td>'
        grid_html += '</tr>'
    grid_html += '</table>'

    st.markdown(grid_html, unsafe_allow_html=True)

    # 大限表示
    da_xian_html = '<div style="margin:10px 0;"><span style="color:#C9A84C; font-weight:bold;">大限（10年運）</span> ' + z.da_xian_direction + '<br>'
    for i, (s, e) in enumerate(z.da_xian_ages[:8]):
        palace = z.palaces[i] if i < len(z.palaces) else None
        pname = palace.palace_name if palace else ''
        da_xian_html += f'<span style="color:#9B8FC4; font-size:0.85em;">第{i+1}限 {s}〜{e}歳（{pname}）</span><br>'
    da_xian_html += '</div>'
    st.markdown(da_xian_html, unsafe_allow_html=True)

    # AI鑑定文
    reading = data.get("reading", "")
    if reading:
        st.markdown(f'<div style="color:#E8E0F0; line-height:1.8; margin:15px 0;">{reading}</div>', unsafe_allow_html=True)

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
            color = "#FF6B9D" if score_int >= 80 else "#FFD700" if score_int >= 60 else "#4FC3F7"
            score_html = f"""
<div style="text-align:center; margin:12px 0;">
<span style="font-size:2.5em; color:{color}; font-weight:bold;">{score_int}</span>
<span style="color:#9B8FC4; font-size:0.9em;"> / 100</span>
</div>"""
        except ValueError:
            pass

    # 2人のデータ比較タグ
    tags = f"""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:10px 0; font-size:0.88em;">
<div style="text-align:center; padding:8px; border:1px solid #C9A84C; border-radius:6px;">
<div style="color:#C9A84C; font-weight:bold; margin-bottom:4px;">{n1}</div>
<div>日干: <span style="color:#F5D78E">{s1.nichikan}（{s1.nichikan_gogyo}）</span></div>
<div>{w1.sun_sign_symbol} <span style="color:#F5D78E">{w1.sun_sign}</span></div>
<div>中央星: <span style="color:#F5D78E">{s1.chuo_sei}</span></div>
</div>
<div style="text-align:center; padding:8px; border:1px solid #FF6B9D; border-radius:6px;">
<div style="color:#FF6B9D; font-weight:bold; margin-bottom:4px;">{n2}</div>
<div>日干: <span style="color:#F5D78E">{s2.nichikan}（{s2.nichikan_gogyo}）</span></div>
<div>{w2.sun_sign_symbol} <span style="color:#F5D78E">{w2.sun_sign}</span></div>
<div>中央星: <span style="color:#F5D78E">{s2.chuo_sei}</span></div>
</div>
</div>"""

    st.markdown(f"""<div class="divination-card" style="border-color:#FF6B9D;">
<div class="card-header" style="color:#FF6B9D;">💕 相性鑑定 💕</div>
<div style="text-align:center; margin:12px 0;">
<span style="font-size:1.2em; color:#FF6B9D; font-weight:bold;">「{headline}」</span>
</div>
{score_html}
{tags}
<div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{reading}</div>
<div class="gold-divider"></div>
<div style="text-align:center; margin-top:14px; font-size:1.05em; color:#FF6B9D; font-style:italic; line-height:1.8;">
💕 {closing} 💕
</div>
</div>""", unsafe_allow_html=True)


def render_theme_result(theme_key: str, data: dict):
    """テーマ別鑑定結果を表示"""
    theme = THEME_DISPLAY.get(theme_key, {"icon": "✦", "title": theme_key, "color": "#C9A84C"})

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
