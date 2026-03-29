"""
各画面の描画ロジック（ui/pages.py）
TOP → 入力 → ローディング → 裏メニュー → 結果（5ステップ）

設計思想: アプリの主役はAIじゃない。ひでさん。
アプリはひでさんの耳元でささやく軍師。
"""
import streamlit as st
from datetime import date

from ui.components import (
    render_star_deco, render_gold_divider,
    render_ura_menu,
    render_sanmei_course, render_western_course,
    render_kyusei_course, render_numerology_course,
    render_tarot_course, render_ziwei_course, render_synthesis_tab,
    render_tarot_card_back, render_tarot_card_face,
    render_tarot_card_simple,
    render_theme_result,
)
from core.models import PersonInput


# ============================================================
# TOP画面
# ============================================================
def render_top_page():
    """TOP画面: アプリ名 + 鑑定スタートボタン"""
    render_star_deco("✦ ☽ ✦")

    st.markdown(
        '<div class="uranai-title">占いモンスターマシーン</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uranai-subtitle">～ あなたの星を読む ～</div>',
        unsafe_allow_html=True
    )

    render_gold_divider()

    st.markdown("""
<div style="text-align:center; color:#9B8FC4; font-size:0.9em; margin:20px 0 30px;">
  生年月日を入れるだけで<br>
  算命学・西洋占星術・九星気学・数秘術・タロットで<br>
  <span style="color:#C9A84C">あなたの本質と今年の運命を鑑定します</span>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✧ 鑑定をはじめる ✧", key="btn_start"):
            st.session_state.page = "input"
            # widgetキーのバージョンを上げて新規widgetとして扱う
            st.session_state._input_key_ver = st.session_state.get("_input_key_ver", 0) + 1
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🃏 タロット占い 🃏", key="btn_tarot"):
            st.session_state.page = "tarot_input"
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💕 相性占い 💕", key="btn_aisho"):
            st.session_state.page = "aisho_input"
            st.rerun()


# ============================================================
# 入力データ記憶（JSONファイル永続化 + session_state）
# ============================================================
import json as _json
import os as _os

_PEOPLE_DB_PATH = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "people_db.json")


def _load_people_db() -> dict:
    """保存済みの人物データをファイルから読み込み、session_stateにも反映"""
    if "_people_db" in st.session_state and st.session_state._people_db:
        return st.session_state._people_db
    try:
        if _os.path.exists(_PEOPLE_DB_PATH):
            with open(_PEOPLE_DB_PATH, encoding="utf-8") as f:
                db = _json.load(f)
            st.session_state._people_db = db
            return db
    except Exception:
        pass
    st.session_state._people_db = {}
    return {}


def _persist_people_db(db: dict):
    """人物データをJSONファイルに保存"""
    try:
        with open(_PEOPLE_DB_PATH, "w", encoding="utf-8") as f:
            _json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _save_person(name, year, month, day, time_str="", place="", blood="不明"):
    """鑑定した人のデータをsession_state + ファイルに記憶"""
    st.session_state._saved_name = name
    st.session_state._saved_year = year
    st.session_state._saved_month = month
    st.session_state._saved_day = day
    st.session_state._saved_time = time_str
    st.session_state._saved_place = place
    st.session_state._saved_blood = blood

    db = _load_people_db()
    if name:
        db[name] = {
            "name": name, "year": year, "month": month, "day": day,
            "time": time_str, "place": place, "blood": blood,
        }
        st.session_state._people_db = db
        _persist_people_db(db)


def _render_people_quick_select():
    """登録済みの人をクイック選択するボタンを表示"""
    people_db = _load_people_db()
    if not people_db:
        return

    names = list(people_db.keys())
    st.markdown("""
<div style="color:#9B8FC4; font-size:0.85em; text-align:center; margin-bottom:5px;">
前回の人をタップで選択
</div>
""", unsafe_allow_html=True)
    cols = st.columns(min(len(names), 4))
    for idx, name in enumerate(names[:4]):
        p = people_db[name]
        with cols[idx]:
            label = f"👤 {name}\n{p.get('year','')}/{p.get('month','')}/{p.get('day','')}"
            if st.button(label, key=f"btn_quick_{idx}"):
                st.session_state._saved_name = name
                st.session_state._saved_year = int(p.get("year", 1990))
                st.session_state._saved_month = int(p.get("month", 5))
                st.session_state._saved_day = int(p.get("day", 15))
                st.session_state._saved_time = p.get("time", "")
                st.session_state._saved_place = p.get("place", "")
                st.session_state._saved_blood = p.get("blood", "不明")
                st.session_state._input_key_ver = st.session_state.get("_input_key_ver", 0) + 1
                st.rerun()
    render_gold_divider()


# ============================================================
# 入力画面
# ============================================================
def render_input_page():
    """生年月日入力画面"""

    # ファイルから保存済みデータを復元
    _load_people_db()

    # デフォルト値（復元済みなら復元値、なければ初期値）
    saved_name = st.session_state.get("_saved_name", "")
    saved_year = st.session_state.get("_saved_year", 1990)
    saved_month = st.session_state.get("_saved_month", 5)
    saved_day = st.session_state.get("_saved_day", 15)
    saved_time = st.session_state.get("_saved_time", "")
    saved_place = st.session_state.get("_saved_place", "")
    saved_blood = st.session_state.get("_saved_blood", "不明")

    years = list(range(1930, date.today().year))
    blood_options = ["不明", "A", "B", "O", "AB"]

    render_star_deco("✦")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.6em;">生年月日を教えてください</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    # 登録済みの人がいたらクイック選択
    _render_people_quick_select()

    # widgetキーにバージョン番号を付けて、復元時に新規widgetとして扱わせる
    kv = st.session_state.get("_input_key_ver", 0)

    # 名前（任意）
    st.text_input(
        "お名前（ニックネームでもOK）",
        value=saved_name,
        placeholder="例: ゆうこ",
        key=f"input_name_{kv}"
    )

    year_idx = years.index(saved_year) if saved_year in years else years.index(1990)
    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.selectbox("年", options=years, index=year_idx, key=f"input_year_{kv}")
    with col2:
        month = st.selectbox("月", options=list(range(1, 13)), index=max(0, saved_month - 1), key=f"input_month_{kv}")
    with col3:
        day = st.selectbox("日", options=list(range(1, 32)), index=max(0, saved_day - 1), key=f"input_day_{kv}")

    # 任意項目（折りたたみ）
    has_detail = bool(saved_time or saved_place or saved_blood != "不明")
    with st.expander("▼ もっと詳しく（任意・より正確な鑑定に）", expanded=has_detail):
        st.text_input(
            "出生時刻（例: 01:34）",
            value=saved_time,
            placeholder="HH:MM",
            key=f"input_time_{kv}"
        )
        st.text_input(
            "出生地（例: 函館市、東京、大阪）",
            value=saved_place,
            placeholder="都市名",
            key=f"input_place_{kv}"
        )
        blood_idx = blood_options.index(saved_blood) if saved_blood in blood_options else 0
        st.radio(
            "血液型",
            options=blood_options,
            index=blood_idx,
            horizontal=True,
            key=f"input_blood_{kv}"
        )

    render_gold_divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✧ 鑑定する ✧", key="btn_divine"):
            # 日付バリデーション
            try:
                birth_date = date(year, month, day)
            except ValueError:
                st.error("⚠ 無効な日付です。正しい生年月日を入力してください。")
                return

            # session_stateから任意項目を取得（バージョン付きキー）
            input_name = st.session_state.get(f"input_name_{kv}", "").strip()
            input_time = st.session_state.get(f"input_time_{kv}", "").strip()
            input_place = st.session_state.get(f"input_place_{kv}", "").strip()
            input_blood = st.session_state.get(f"input_blood_{kv}", "不明")

            # セッションステートに保存
            st.session_state.person = PersonInput(
                birth_date=birth_date,
                name=input_name if input_name else None,
                birth_time=input_time if input_time else None,
                birth_place=input_place if input_place else None,
                blood_type=input_blood if input_blood != "不明" else None,
            )

            # 名前をキーにデータを記憶
            _save_person(
                input_name, year, month, day, input_time, input_place, input_blood
            )

            st.session_state.page = "loading"
            st.session_state.bundle = None
            st.session_state.recommendation = None
            st.session_state.course_results = {}
            st.session_state.selected_course = None
            st.rerun()

    # 戻るボタン
    if st.button("← 戻る", key="btn_back_input"):
        st.session_state.page = "top"
        st.rerun()


# ============================================================
# ローディング画面（計算 + おすすめコース生成）
# ============================================================
def render_loading_page():
    """計算・おすすめコース生成中の演出画面"""
    from core.sanmei import calculate_sanmei
    from core.western import calculate_western
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.tarot import draw_tarot
    from core.ziwei import calculate_ziwei
    from core.models import DivinationBundle
    from ai.interpreter import generate_recommendation

    # localStorageに保存

    render_star_deco("✦")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">✦ 星を読んでいます…</div>',
        unsafe_allow_html=True
    )

    person = st.session_state.person

    with st.status("✦ 占術エンジン起動中…", expanded=True) as status:
        st.write("✧ 算命学エンジン起動…")
        sanmei = calculate_sanmei(person)
        st.write(f"✧ 算命学 ── 完了（{sanmei.hi_kanshi} / {sanmei.chuo_sei}）")

        st.write("✧ 九星気学計算中…")
        kyusei = calculate_kyusei(person)
        st.write(f"✧ 九星気学 ── 完了（{kyusei.honmei_sei}）")

        st.write("✧ 数秘術を紐解いています…")
        numerology = calculate_numerology(person)
        st.write(f"✧ 数秘術 ── 完了（LP:{numerology.life_path} / 個人年:{numerology.personal_year}）")

        st.write("✧ 西洋占星術…星の配置を確認中…")
        western = calculate_western(person)
        st.write(f"✧ 西洋占星術 ── 完了（{western.sun_sign} {western.sun_sign_symbol}）")

        st.write("✧ 紫微斗数…命盤を作成中…")
        ziwei = calculate_ziwei(person)
        st.write(f"✧ 紫微斗数 ── 完了（{ziwei.five_element_name} / 命宮:{ziwei.ming_gong_branch}）")

        st.write("✧ タロットカードをシャッフル中…")
        tarot = draw_tarot(1, major_only=True)[0]
        st.write(f"✧ タロット ── 完了（{tarot.card_name}）")

        bundle = DivinationBundle(
            person=person,
            sanmei=sanmei,
            western=western,
            kyusei=kyusei,
            numerology=numerology,
            tarot=tarot,
            ziwei=ziwei,
            has_birth_time=person.birth_time is not None,
            has_blood_type=person.blood_type is not None,
        )

        st.write("✦ あなたに最適なコースを分析中…")
        recommendation = generate_recommendation(bundle)

        status.update(label="✦ 鑑定準備完了 ✦", state="complete")

    # セッションに保存して裏メニューへ
    st.session_state.bundle = bundle
    st.session_state.recommendation = recommendation
    st.session_state.page = "ura_menu"
    st.rerun()


# ============================================================
# 裏メニュー画面（ひでさん専用・相手に見せない）
# ============================================================
def render_ura_menu_page():
    """ひでさん専用画面: 命式ハイライト + おすすめコース + コース選択"""
    bundle = st.session_state.bundle
    recommendation = st.session_state.recommendation

    render_ura_menu(bundle, recommendation)

    render_gold_divider()

    # コース選択ボタン
    st.markdown("""
<div style="text-align:center; color:#9B8FC4; font-size:0.85em; margin-bottom:10px;">
  ↓ コースを選んでタップ ↓
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✦ 算命学", key="btn_sanmei"):
            _start_course("算命学")
    with col2:
        if st.button("✦ 星座", key="btn_western"):
            _start_course("星座")
    with col3:
        if st.button("✦ 九星気学", key="btn_kyusei"):
            _start_course("九星気学")

    col4, col5, col6 = st.columns(3)
    with col4:
        if st.button("✦ 数秘術", key="btn_numerology"):
            _start_course("数秘術")
    with col5:
        if st.button("✦ 紫微斗数", key="btn_ziwei"):
            _start_course("紫微斗数")
    with col6:
        if st.button("✧ フルコース ✧", key="btn_full"):
            _start_course("フルコース")

    render_gold_divider()

    # テーマ別深掘り鑑定セクション（コース選択と並列）
    st.markdown("""
<div style="text-align:center; margin:20px 0 10px;">
<span style="color:#C9A84C; font-size:1.15em; font-weight:bold;">✦ テーマで深掘り ✦</span><br>
<span style="color:#9B8FC4; font-size:0.85em;">全占術を横断した深掘り鑑定</span>
</div>
""", unsafe_allow_html=True)

    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        if st.button("💕 恋愛運", key="btn_ura_theme_love"):
            _start_theme("love")
    with tc2:
        if st.button("💍 結婚運", key="btn_ura_theme_marriage"):
            _start_theme("marriage")
    with tc3:
        if st.button("💼 仕事運", key="btn_ura_theme_career"):
            _start_theme("career")

    tc4, tc5 = st.columns(2)
    with tc4:
        if st.button("🔮 10年後の自分", key="btn_ura_theme_future10"):
            _start_theme("future10")
    with tc5:
        if st.button("✨ 最大限に輝く生き方", key="btn_ura_theme_shine"):
            _start_theme("shine")

    render_gold_divider()

    # くろちゃんに自由質問（裏メニュー）
    _render_ura_chat(bundle)

    # 戻るボタン
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← 入力に戻る", key="btn_back_ura"):
        st.session_state.page = "input"
        st.rerun()


def _start_theme(theme_key: str):
    """テーマ鑑定を生成して結果画面へ遷移"""
    st.session_state.selected_course = f"theme_{theme_key}"
    st.session_state.page = "generating_theme"
    st.rerun()


def _start_course(course: str):
    """コース選択後、鑑定生成画面へ遷移"""
    st.session_state.selected_course = course
    st.session_state.page = "generating"
    st.rerun()


# ============================================================
# 鑑定文生成画面（コース選択後のローディング）
# ============================================================
def render_generating_page():
    """選択されたコースの鑑定文を生成"""
    from ai.interpreter import generate_single_course, generate_full_course

    bundle = st.session_state.bundle
    course = st.session_state.selected_course

    render_star_deco("✦")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">✦ あなただけの言葉を紡いでいます…</div>',
        unsafe_allow_html=True
    )

    if course == "フルコース":
        with st.status("✦ フルコース鑑定生成中…", expanded=True) as status:
            st.write("✧ 5占術を同時に鑑定中…")
            results = generate_full_course(bundle)
            status.update(label="✦ 全コース鑑定完了 ✦", state="complete")
        st.session_state.course_results = results
    else:
        with st.status(f"✦ {course}コース鑑定生成中…", expanded=True) as status:
            st.write(f"✧ {course}の鑑定文を生成中…")
            result = generate_single_course(bundle, course)
            status.update(label=f"✦ {course}コース鑑定完了 ✦", state="complete")

        # コース名をキーに保存
        course_key_map = {
            "算命学": "sanmei", "星座": "western", "九星気学": "kyusei",
            "数秘術": "numerology", "タロット": "tarot", "紫微斗数": "ziwei",
        }
        key = course_key_map.get(course, course)
        st.session_state.course_results[key] = result

    st.session_state.page = "result"
    st.rerun()


# ============================================================
# テーマ別鑑定生成画面（裏メニューからの直接遷移用）
# ============================================================
def render_generating_theme_page():
    """テーマ別深掘り鑑定を生成"""
    from ai.interpreter import generate_theme_reading, THEME_NAMES

    bundle = st.session_state.bundle
    selected = st.session_state.selected_course  # "theme_love" 等
    theme_key = selected.replace("theme_", "")
    theme_name = THEME_NAMES.get(theme_key, theme_key)

    render_star_deco("✦")
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.5em;">✦ {theme_name}を深く読んでいます…</div>',
        unsafe_allow_html=True
    )

    with st.status(f"✦ {theme_name}を鑑定中…", expanded=True) as status:
        st.write(f"✧ 全占術データを横断して{theme_name}を分析中…")
        result = generate_theme_reading(bundle, theme_key)
        status.update(label=f"✦ {theme_name}鑑定完了 ✦", state="complete")

    if "theme_results" not in st.session_state:
        st.session_state.theme_results = {}
    st.session_state.theme_results[theme_key] = result
    st.session_state.page = "theme_result"
    st.session_state._current_theme = theme_key
    st.rerun()


# ============================================================
# テーマ別鑑定結果画面
# ============================================================
def render_theme_result_page():
    """テーマ別鑑定の結果画面"""
    bundle = st.session_state.bundle
    theme_key = st.session_state.get("_current_theme", "love")
    theme_data = st.session_state.get("theme_results", {}).get(theme_key, {})

    d = bundle.person.birth_date
    name = bundle.person.name
    render_star_deco("✦")
    title_text = f"{name}さん — " if name else ""
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.4em;">{title_text}{d.year}年{d.month}月{d.day}日生まれの星</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    render_theme_result(theme_key, theme_data)

    render_gold_divider()

    # くろちゃんにテーマ関連の質問
    _render_theme_chat(bundle, theme_key, theme_data)

    render_gold_divider()

    # 他のテーマも見る
    st.markdown("""
<div style="text-align:center; margin:20px 0 10px;">
<span style="color:#C9A84C; font-size:1.0em;">✦ 他のテーマも深掘り ✦</span>
</div>
""", unsafe_allow_html=True)

    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        if st.button("💕 恋愛運", key="btn_tr_love"):
            _start_theme("love")
    with tc2:
        if st.button("💍 結婚運", key="btn_tr_marriage"):
            _start_theme("marriage")
    with tc3:
        if st.button("💼 仕事運", key="btn_tr_career"):
            _start_theme("career")

    tc4, tc5 = st.columns(2)
    with tc4:
        if st.button("🔮 10年後の自分", key="btn_tr_future10"):
            _start_theme("future10")
    with tc5:
        if st.button("✨ 最大限に輝く生き方", key="btn_tr_shine"):
            _start_theme("shine")

    render_gold_divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✦ コース鑑定へ", key="btn_theme_to_course"):
            st.session_state.page = "ura_menu"
            st.rerun()
    with col2:
        if st.button("✧ もう一度鑑定する ✧", key="btn_theme_restart"):
            st.session_state.page = "input"
            st.session_state.bundle = None
            st.session_state.recommendation = None
            st.session_state.course_results = {}
            st.session_state.selected_course = None
            st.session_state.theme_results = {}
            st.rerun()


# ============================================================
# 結果画面
# ============================================================
def render_result_page():
    """結果画面: 単一コースまたはフルコースのタブ表示"""
    bundle = st.session_state.bundle
    course = st.session_state.selected_course
    results = st.session_state.course_results

    d = bundle.person.birth_date
    name = bundle.person.name
    render_star_deco("✦")
    title_text = f"{name}さん — " if name else ""
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.4em;">{title_text}{d.year}年{d.month}月{d.day}日生まれの星</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    if course == "フルコース":
        _render_full_course_result(bundle, results)
    else:
        _render_single_course_result(bundle, course, results)

    render_gold_divider()

    # テーマ別深掘り鑑定セクション
    _render_theme_section(bundle)

    render_gold_divider()

    # くろちゃんに個別質問チャット
    _render_general_chat(bundle, course, results)

    # フッターボタン群
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✦ 他のコースも見る", key="btn_other_course"):
            st.session_state.page = "ura_menu"
            st.rerun()
    with col2:
        if st.button("✧ もう一度鑑定する ✧", key="btn_restart"):
            st.session_state.page = "input"
            st.session_state.bundle = None
            st.session_state.recommendation = None
            st.session_state.course_results = {}
            st.session_state.selected_course = None
            st.session_state.theme_results = {}
            st.rerun()


def _render_single_course_result(bundle, course, results):
    """単一コース選択時: 1画面スクロールで深い鑑定"""
    course_key_map = {
        "算命学": "sanmei", "星座": "western", "九星気学": "kyusei",
        "数秘術": "numerology", "タロット": "tarot", "紫微斗数": "ziwei",
    }
    key = course_key_map.get(course, course)
    data = results.get(key, {})

    if course == "算命学":
        render_sanmei_course(bundle, data)
    elif course == "星座":
        render_western_course(bundle, data)
    elif course == "九星気学":
        render_kyusei_course(bundle, data)
    elif course == "数秘術":
        render_numerology_course(bundle, data)
    elif course == "タロット":
        render_tarot_course(bundle, data)
    elif course == "紫微斗数":
        render_ziwei_course(bundle, data)


def _render_full_course_result(bundle, results):
    """フルコース選択時: タブ構造で全コース表示"""
    tab_names = ["✦ 総合", "算命学", "星座", "九星気学", "数秘術", "紫微斗数", "タロット"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        synthesis = results.get("synthesis", {})
        render_synthesis_tab(bundle, synthesis)

    with tabs[1]:
        render_sanmei_course(bundle, results.get("sanmei", {}))

    with tabs[2]:
        render_western_course(bundle, results.get("western", {}))

    with tabs[3]:
        render_kyusei_course(bundle, results.get("kyusei", {}))

    with tabs[4]:
        render_numerology_course(bundle, results.get("numerology", {}))

    with tabs[5]:
        render_ziwei_course(bundle, results.get("ziwei", {}))

    with tabs[6]:
        render_tarot_course(bundle, results.get("tarot", {}))


# ============================================================
# テーマ別深掘り鑑定セクション
# ============================================================
THEME_BUTTONS = [
    ("love", "💕 恋愛運"),
    ("marriage", "💍 結婚運"),
    ("career", "💼 仕事運"),
    ("future10", "🔮 10年後の自分"),
    ("shine", "✨ 最大限に輝く生き方"),
]


def _render_theme_section(bundle):
    """結果画面下部のテーマ別深掘り鑑定セクション"""
    # テーマ結果の初期化
    if "theme_results" not in st.session_state:
        st.session_state.theme_results = {}

    st.markdown("""
<div style="text-align:center; margin:20px 0 10px;">
<span style="color:#C9A84C; font-size:1.15em; font-weight:bold;">✦ もっと深く見る ✦</span><br>
<span style="color:#9B8FC4; font-size:0.85em;">テーマを選ぶと、全占術を横断した深掘り鑑定が生成されます</span>
</div>
""", unsafe_allow_html=True)

    # テーマ選択ボタン（2行）
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(THEME_BUTTONS[0][1], key="btn_theme_love"):
            _generate_theme(bundle, "love")
    with col2:
        if st.button(THEME_BUTTONS[1][1], key="btn_theme_marriage"):
            _generate_theme(bundle, "marriage")
    with col3:
        if st.button(THEME_BUTTONS[2][1], key="btn_theme_career"):
            _generate_theme(bundle, "career")

    col4, col5 = st.columns(2)
    with col4:
        if st.button(THEME_BUTTONS[3][1], key="btn_theme_future10"):
            _generate_theme(bundle, "future10")
    with col5:
        if st.button(THEME_BUTTONS[4][1], key="btn_theme_shine"):
            _generate_theme(bundle, "shine")

    # 生成済みテーマ結果を表示
    theme_results = st.session_state.theme_results
    if theme_results:
        for theme_key, theme_data in theme_results.items():
            render_theme_result(theme_key, theme_data)


def _generate_theme(bundle, theme_key: str):
    """テーマ別鑑定を生成してセッションに保存"""
    from ai.interpreter import generate_theme_reading, THEME_NAMES

    theme_name = THEME_NAMES.get(theme_key, theme_key)

    # 既に生成済みなら何もしない
    if theme_key in st.session_state.get("theme_results", {}):
        return

    with st.status(f"✦ {theme_name}を鑑定中…", expanded=True) as status:
        st.write(f"✧ 全占術データを横断して{theme_name}を分析中…")
        result = generate_theme_reading(bundle, theme_key)
        status.update(label=f"✦ {theme_name}鑑定完了 ✦", state="complete")

    if "theme_results" not in st.session_state:
        st.session_state.theme_results = {}
    st.session_state.theme_results[theme_key] = result
    st.rerun()


# ============================================================
# 相性占い: 入力画面
# ============================================================
def render_aisho_input_page():
    """相性占い: 2人分の生年月日入力画面"""
    render_star_deco("💕")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">相性占い</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uranai-subtitle">～ ふたりの星を読む ～</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    # --- 1人目 ---
    st.markdown('<div style="color:#C9A84C; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">✦ 1人目</div>', unsafe_allow_html=True)
    name1 = st.text_input("お名前", value="", placeholder="例: ひでさん", key="aisho_name1")

    c1a, c1b, c1c = st.columns(3)
    with c1a:
        y1 = st.selectbox("年", options=list(range(1930, date.today().year)), index=list(range(1930, date.today().year)).index(1990), key="aisho_y1")
    with c1b:
        m1 = st.selectbox("月", options=list(range(1, 13)), index=4, key="aisho_m1")
    with c1c:
        d1 = st.selectbox("日", options=list(range(1, 32)), index=14, key="aisho_d1")

    with st.expander("▼ もっと詳しく（任意）", expanded=False):
        t1 = st.text_input("出生時刻", value="", placeholder="HH:MM", key="aisho_t1")
        p1 = st.text_input("出生地", value="", placeholder="都市名", key="aisho_p1")
        b1 = st.radio("血液型", options=["不明", "A", "B", "O", "AB"], index=0, horizontal=True, key="aisho_b1")

    render_gold_divider()

    # --- 2人目 ---
    st.markdown('<div style="color:#FF6B9D; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">✦ 2人目</div>', unsafe_allow_html=True)
    name2 = st.text_input("お名前", value="", placeholder="例: ゆうこ", key="aisho_name2")

    c2a, c2b, c2c = st.columns(3)
    with c2a:
        y2 = st.selectbox("年", options=list(range(1930, date.today().year)), index=list(range(1930, date.today().year)).index(1990), key="aisho_y2")
    with c2b:
        m2 = st.selectbox("月", options=list(range(1, 13)), index=4, key="aisho_m2")
    with c2c:
        d2 = st.selectbox("日", options=list(range(1, 32)), index=14, key="aisho_d2")

    with st.expander("▼ もっと詳しく（任意）", expanded=False):
        t2 = st.text_input("出生時刻", value="", placeholder="HH:MM", key="aisho_t2")
        p2 = st.text_input("出生地", value="", placeholder="都市名", key="aisho_p2")
        b2 = st.radio("血液型", options=["不明", "A", "B", "O", "AB"], index=0, horizontal=True, key="aisho_b2")

    render_gold_divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💕 相性を鑑定する 💕", key="btn_aisho_start"):
            try:
                bd1 = date(y1, m1, d1)
                bd2 = date(y2, m2, d2)
            except ValueError:
                st.error("無効な日付です。正しい生年月日を入力してください。")
                return

            time1 = st.session_state.get("aisho_t1", "").strip()
            place1 = st.session_state.get("aisho_p1", "").strip()
            blood1 = st.session_state.get("aisho_b1", "不明")
            time2 = st.session_state.get("aisho_t2", "").strip()
            place2 = st.session_state.get("aisho_p2", "").strip()
            blood2 = st.session_state.get("aisho_b2", "不明")

            st.session_state.aisho_person1 = PersonInput(
                name=name1.strip() if name1.strip() else "1人目",
                birth_date=bd1,
                birth_time=time1 if time1 else None,
                birth_place=place1 if place1 else None,
                blood_type=blood1 if blood1 != "不明" else None,
            )
            st.session_state.aisho_person2 = PersonInput(
                name=name2.strip() if name2.strip() else "2人目",
                birth_date=bd2,
                birth_time=time2 if time2 else None,
                birth_place=place2 if place2 else None,
                blood_type=blood2 if blood2 != "不明" else None,
            )
            st.session_state.page = "aisho_loading"
            st.rerun()

    if st.button("← 戻る", key="btn_back_aisho"):
        st.session_state.page = "top"
        st.rerun()


# ============================================================
# 相性占い: ローディング + 鑑定生成
# ============================================================
def render_aisho_loading_page():
    """相性占い: 2人分の計算 + 相性鑑定生成"""
    from core.sanmei import calculate_sanmei
    from core.western import calculate_western
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.ziwei import calculate_ziwei
    from core.models import DivinationBundle
    from core.tarot import draw_tarot
    from ai.interpreter import generate_aisho_reading

    person1 = st.session_state.aisho_person1
    person2 = st.session_state.aisho_person2

    render_star_deco("💕")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">💕 ふたりの星を読んでいます…</div>',
        unsafe_allow_html=True
    )

    with st.status("✦ 占術エンジン起動中…", expanded=True) as status:
        st.write(f"✧ {person1.name}さんの命式を計算中…")
        s1 = calculate_sanmei(person1)
        w1 = calculate_western(person1)
        k1 = calculate_kyusei(person1)
        n1 = calculate_numerology(person1)
        t1 = draw_tarot(1, major_only=True)[0]
        z1 = calculate_ziwei(person1)
        bundle1 = DivinationBundle(
            person=person1, sanmei=s1, western=w1, kyusei=k1,
            numerology=n1, tarot=t1, ziwei=z1,
            has_birth_time=person1.birth_time is not None,
            has_blood_type=person1.blood_type is not None,
        )
        st.write(f"✧ {person1.name}さん ── 完了")

        st.write(f"✧ {person2.name}さんの命式を計算中…")
        s2 = calculate_sanmei(person2)
        w2 = calculate_western(person2)
        k2 = calculate_kyusei(person2)
        n2 = calculate_numerology(person2)
        t2 = draw_tarot(1, major_only=True)[0]
        z2 = calculate_ziwei(person2)
        bundle2 = DivinationBundle(
            person=person2, sanmei=s2, western=w2, kyusei=k2,
            numerology=n2, tarot=t2, ziwei=z2,
            has_birth_time=person2.birth_time is not None,
            has_blood_type=person2.blood_type is not None,
        )
        st.write(f"✧ {person2.name}さん ── 完了")

        st.write("✧ ふたりの相性を分析中…")
        aisho_result = generate_aisho_reading(bundle1, bundle2)
        status.update(label="✦ 相性鑑定完了 ✦", state="complete")

    st.session_state.aisho_bundle1 = bundle1
    st.session_state.aisho_bundle2 = bundle2
    st.session_state.aisho_result = aisho_result
    st.session_state.page = "aisho_result"
    st.rerun()


# ============================================================
# 相性占い: 結果画面
# ============================================================
def render_aisho_result_page():
    """相性占い結果表示"""
    from ui.components import render_aisho_result

    bundle1 = st.session_state.aisho_bundle1
    bundle2 = st.session_state.aisho_bundle2
    result = st.session_state.aisho_result

    render_star_deco("💕")
    n1 = bundle1.person.name or "1人目"
    n2 = bundle2.person.name or "2人目"
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.4em;">{n1} × {n2} の相性</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    render_aisho_result(bundle1, bundle2, result)

    render_gold_divider()

    # くろちゃんに相性の個別質問
    _render_aisho_chat(bundle1, bundle2, result)

    render_gold_divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💕 もう一組鑑定する", key="btn_aisho_again"):
            st.session_state.page = "aisho_input"
            st.rerun()
    with col2:
        if st.button("✧ TOPに戻る ✧", key="btn_aisho_top"):
            st.session_state.page = "top"
            st.rerun()


# ============================================================
# 対話型タロット占い（Phase 2a）
# ============================================================

TAROT_QUESTION_EXAMPLES = [
    "転職すべきか迷っています",
    "今の恋人との未来は？",
    "今年後半の運勢を教えて",
    "AとBどちらを選ぶべき？",
    "今の自分に必要なメッセージ",
]


def render_tarot_input_page():
    """対話型タロット: 質問入力（生年月日は共通保存値を使用）"""
    render_star_deco("🃏")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">タロット占い</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uranai-subtitle">～ カードに問いかける ～</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    # 保存済みデータをロード
    _load_people_db()
    saved_name = st.session_state.get("_saved_name", "")
    saved_year = st.session_state.get("_saved_year", 1990)
    saved_month = st.session_state.get("_saved_month", 5)
    saved_day = st.session_state.get("_saved_day", 15)
    has_person = st.session_state.get("_input_restored", False) or st.session_state.get("person") is not None

    if has_person and saved_name:
        st.markdown(f"""
<div style="text-align:center; color:#9B8FC4; font-size:0.9em; margin-bottom:10px;">
{saved_name}さん（{saved_year}/{saved_month}/{saved_day}生まれ）
</div>
""", unsafe_allow_html=True)
        # 別の人を占いたい場合
        if st.button("👤 別の人を占う", key="btn_tarot_change_person"):
            st.session_state._input_restored = False
            st.session_state.person = None
            st.rerun()
    else:
        # 登録済みの人がいたらクイック選択
        _render_people_quick_select()
        # 生年月日入力
        st.text_input("お名前", value=saved_name, placeholder="例: ひでさん", key="tarot_name")
        years = list(range(1930, date.today().year))
        tc1, tc2, tc3 = st.columns(3)
        year_idx = years.index(saved_year) if saved_year in years else years.index(1990)
        with tc1:
            saved_year = st.selectbox("年", options=years, index=year_idx, key="tarot_year")
        with tc2:
            saved_month = st.selectbox("月", options=list(range(1, 13)), index=max(0, saved_month - 1), key="tarot_month")
        with tc3:
            saved_day = st.selectbox("日", options=list(range(1, 32)), index=max(0, saved_day - 1), key="tarot_day")
        render_gold_divider()

    # 質問入力
    st.markdown("""
<div style="text-align:center; color:#C9A84C; font-size:1.1em; margin-bottom:8px;">
何を占いたいですか？
</div>
""", unsafe_allow_html=True)

    question = st.text_input(
        "あなたの質問",
        value="",
        placeholder="例: 転職すべきか迷っています",
        key="tarot_q_input",
        label_visibility="collapsed"
    )

    st.markdown("""
<div style="color:#9B8FC4; font-size:0.8em; text-align:center; margin-top:-10px;">
例: 転職すべきか / 今の恋人との未来 / 今年の運勢 / AかBか
</div>
""", unsafe_allow_html=True)

    render_gold_divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔮 くろちゃんに相談する", key="btn_tarot_deepen"):
            q = st.session_state.get("tarot_q_input", "").strip()
            if not q:
                st.error("⚠ 質問を入力してください")
                return

            try:
                birth_date = date(saved_year, saved_month, saved_day)
            except ValueError:
                st.error("⚠ 無効な日付です")
                return

            t_name = st.session_state.get("tarot_name", saved_name).strip() if not has_person else saved_name
            st.session_state.tarot_person = PersonInput(
                birth_date=birth_date,
                name=t_name if t_name else None,
            )
            # 名前をキーにデータを記憶
            _save_person(t_name, saved_year, saved_month, saved_day)

            st.session_state.tarot_question = q
            st.session_state.tarot_deepen_history = []
            st.session_state.page = "tarot_deepen"
            st.rerun()

    if st.button("← 戻る", key="btn_back_tarot_input"):
        st.session_state.page = "top"
        st.rerun()


def render_tarot_deepen_page():
    """対話型タロット: くろちゃんが質問を深掘り"""
    from ai.interpreter import generate_deepen_question
    from core.sanmei import calculate_sanmei
    from core.western import calculate_western
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.ziwei import calculate_ziwei
    from core.tarot import draw_tarot
    from core.models import DivinationBundle

    question = st.session_state.tarot_question
    history = st.session_state.get("tarot_deepen_history", [])

    # 命式を事前計算（深掘り質問に使う）
    if "tarot_bundle" not in st.session_state:
        person = st.session_state.tarot_person
        s = calculate_sanmei(person)
        w = calculate_western(person)
        k = calculate_kyusei(person)
        n = calculate_numerology(person)
        t = draw_tarot(1, major_only=True)[0]
        z = calculate_ziwei(person)
        bundle = DivinationBundle(
            person=person, sanmei=s, western=w, kyusei=k, numerology=n, tarot=t, ziwei=z,
            has_birth_time=person.birth_time is not None,
            has_blood_type=person.blood_type is not None,
        )
        st.session_state.tarot_bundle = bundle

    render_star_deco("🔮")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.3em;">くろちゃんからの質問</div>',
        unsafe_allow_html=True
    )

    render_gold_divider()

    # 元の質問を表示
    st.markdown(f"""
<div style="text-align:center; color:#9B8FC4; font-size:0.9em; margin-bottom:15px;">
あなたの問い: 「{question}」
</div>
""", unsafe_allow_html=True)

    # 過去の深掘りを表示
    for h in history:
        st.markdown(f"""
<div style="background:rgba(201,168,76,0.1); border-left:3px solid #C9A84C; padding:10px 15px; margin:8px 0; border-radius:0 6px 6px 0;">
<div style="color:#C9A84C; font-size:0.85em;">🔮 くろちゃん</div>
<div style="color:#E0D8C8; font-size:0.95em; margin:4px 0;">{h['empathy']}</div>
<div style="color:#E0D8C8; font-size:0.95em; font-weight:bold;">{h['follow_up']}</div>
</div>
<div style="background:rgba(155,143,196,0.1); border-left:3px solid #9B8FC4; padding:10px 15px; margin:8px 0 15px; border-radius:0 6px 6px 0;">
<div style="color:#9B8FC4; font-size:0.85em;">🙋 あなた</div>
<div style="color:#E0D8C8; font-size:0.95em;">{h['answer']}</div>
</div>
""", unsafe_allow_html=True)

    # 深掘りが2回未満ならAIに質問を生成してもらう
    if len(history) < 2:
        # コンテキスト構築
        ctx = "\n".join(f"Q: {h['follow_up']}\nA: {h['answer']}" for h in history)

        if f"_deepen_data_{len(history)}" not in st.session_state:
            with st.spinner("くろちゃんが考え中…"):
                bundle = st.session_state.get("tarot_bundle")
                deepen_data = generate_deepen_question(question, ctx, bundle=bundle)
                st.session_state[f"_deepen_data_{len(history)}"] = deepen_data
        else:
            deepen_data = st.session_state[f"_deepen_data_{len(history)}"]

        # くろちゃんの質問を表示
        st.markdown(f"""
<div style="background:rgba(201,168,76,0.1); border-left:3px solid #C9A84C; padding:10px 15px; margin:8px 0; border-radius:0 6px 6px 0;">
<div style="color:#C9A84C; font-size:0.85em;">🔮 くろちゃん</div>
<div style="color:#E0D8C8; font-size:0.95em; margin:4px 0;">{deepen_data.get('empathy', '')}</div>
<div style="color:#E0D8C8; font-size:0.95em; font-weight:bold;">{deepen_data.get('follow_up', '')}</div>
</div>
""", unsafe_allow_html=True)

        # 選択肢ボタン
        choices = deepen_data.get("choices", [])
        for i, choice in enumerate(choices):
            if st.button(f"💬 {choice}", key=f"btn_deepen_choice_{len(history)}_{i}"):
                history.append({
                    "empathy": deepen_data.get("empathy", ""),
                    "follow_up": deepen_data.get("follow_up", ""),
                    "answer": choice,
                })
                st.session_state.tarot_deepen_history = history
                # 深掘りデータをクリア（次のラウンド用）
                st.session_state.pop(f"_deepen_data_{len(history)-1}", None)
                st.rerun()

        # 自由入力
        free = st.text_input("自分の言葉で答える", placeholder="自由に入力", key=f"deepen_free_{len(history)}", label_visibility="collapsed")
        if free:
            if st.button("💬 送信", key=f"btn_deepen_free_{len(history)}"):
                history.append({
                    "empathy": deepen_data.get("empathy", ""),
                    "follow_up": deepen_data.get("follow_up", ""),
                    "answer": free,
                })
                st.session_state.tarot_deepen_history = history
                st.session_state.pop(f"_deepen_data_{len(history)-1}", None)
                st.rerun()

    render_gold_divider()

    # 「カードを引く」ボタン（深掘り1回以上でも出す）
    if len(history) >= 1:
        # 深掘り結果を質問に統合
        enriched_q = question + "\n" + "\n".join(
            f"（{h['follow_up']} → {h['answer']}）" for h in history
        )

        st.markdown("""
<div style="text-align:center; color:#C9A84C; font-size:0.95em; margin:10px 0;">
✦ 占的が明確になりました ✦
</div>
""", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🃏 カードを引く 🃏", key="btn_tarot_draw_after_deepen"):
                st.session_state.tarot_question = enriched_q
                st.session_state.page = "tarot_loading"
                st.rerun()

    # スキップボタン（深掘りなしで引きたい場合）
    if len(history) == 0:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("→ 深掘りなしでカードを引く", key="btn_skip_deepen"):
            st.session_state.page = "tarot_loading"
            st.rerun()


def render_tarot_loading_page():
    """対話型タロット: 占術計算 + スプレッド選択 + カード引き"""

    from core.sanmei import calculate_sanmei
    from core.western import calculate_western
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.ziwei import calculate_ziwei
    from core.tarot import draw_tarot
    from core.models import DivinationBundle
    from ai.interpreter import select_tarot_spread

    render_star_deco("🃏")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">🃏 カードをシャッフルしています…</div>',
        unsafe_allow_html=True
    )

    person = st.session_state.tarot_person
    question = st.session_state.tarot_question

    with st.status("✦ タロット準備中…", expanded=True) as status:
        # 占術計算
        st.write("✧ 命式を計算中…")
        sanmei = calculate_sanmei(person)
        western = calculate_western(person)
        kyusei = calculate_kyusei(person)
        numerology = calculate_numerology(person)
        ziwei = calculate_ziwei(person)
        st.write(f"✧ 命式計算完了")

        # スプレッド選択
        st.write("✧ 質問に最適な展開法を選択中…")
        spread_info = select_tarot_spread(question)
        st.write(f"✧ 展開法: {spread_info['spread_name']}（{spread_info['n_cards']}枚）")
        if spread_info.get("reason"):
            st.write(f"  → {spread_info['reason']}")

        # カード引き
        st.write(f"✧ {spread_info['n_cards']}枚のカードを引いています…")
        cards = draw_tarot(spread_info["n_cards"])
        st.write("✧ カードが引かれました")

        # ダミーのタロット（bundleに必要）
        dummy_tarot = cards[0]

        bundle = DivinationBundle(
            person=person,
            sanmei=sanmei,
            western=western,
            kyusei=kyusei,
            numerology=numerology,
            tarot=dummy_tarot,
            ziwei=ziwei,
            has_birth_time=person.birth_time is not None,
            has_blood_type=person.blood_type is not None,
        )

        status.update(label="✦ カード準備完了 ✦", state="complete")

    # セッションに保存
    st.session_state.tarot_bundle = bundle
    st.session_state.tarot_spread = spread_info
    st.session_state.tarot_cards = cards
    st.session_state.tarot_revealed = 0  # めくられた枚数
    st.session_state.page = "tarot_reveal"
    st.rerun()


def render_tarot_reveal_page():
    """対話型タロット: カード展開（3Dフリップめくり演出）"""
    import streamlit.components.v1 as components
    import base64
    import os
    from PIL import Image
    import io

    spread_info = st.session_state.tarot_spread
    cards = st.session_state.tarot_cards
    question = st.session_state.tarot_question
    revealed = st.session_state.get("tarot_revealed", 0)
    n = len(cards)

    render_star_deco("🃏")
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.3em;">{spread_info["spread_name"]}</div>',
        unsafe_allow_html=True
    )

    # 質問表示（enriched questionの最初の行だけ表示）
    q_display = question.split("\n")[0]
    st.markdown(
        f'<div class="uranai-subtitle" style="font-size:0.9em;">「{q_display}」</div>',
        unsafe_allow_html=True
    )

    render_gold_divider()

    # カード画像をbase64に変換（HTML内で使うため）
    img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tarot_images")

    # スートごとのシンボル（小アルカナ画像がない場合のフォールバック）
    SUIT_SYMBOLS = {
        "wands": "🪄", "cups": "🏆", "swords": "⚔️", "pentacles": "⭐",
        "ワンド": "🪄", "カップ": "🏆", "ソード": "⚔️", "ペンタクル": "⭐",
    }

    def card_to_base64(card):
        # 大アルカナ画像を探す
        img_path = os.path.join(img_dir, f"major_{card.card_number:02d}.jpg")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            if card.is_reversed:
                img = img.rotate(180)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            return base64.b64encode(buf.getvalue()).decode()
        # 小アルカナ: image_keyで探す
        if card.image_key:
            alt_path = os.path.join(img_dir, f"{card.image_key}.jpg")
            if os.path.exists(alt_path):
                img = Image.open(alt_path)
                if card.is_reversed:
                    img = img.rotate(180)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=80)
                return base64.b64encode(buf.getvalue()).decode()
        return ""

    # カードデータをJSONで準備
    cards_json = []
    for i, card in enumerate(cards):
        pos = spread_info["positions"][i] if i < len(spread_info["positions"]) else f"カード{i+1}"
        pos_text = "逆位置" if card.is_reversed else "正位置"
        b64 = card_to_base64(card)
        # 小アルカナのスートシンボル（画像がない場合に表示）
        suit_sym = ""
        if not b64 and hasattr(card, "image_key") and card.image_key:
            for skey, sym in SUIT_SYMBOLS.items():
                if skey in card.image_key or skey in card.card_name:
                    suit_sym = sym
                    break
            if not suit_sym:
                suit_sym = "✦"
        cards_json.append({
            "pos": pos,
            "name": card.card_name,
            "name_en": card.card_name_en,
            "pos_text": pos_text,
            "img": b64,
            "suit_symbol": suit_sym,
        })

    import json as _json
    cards_data = _json.dumps(cards_json, ensure_ascii=False)

    # HTML/CSS/JS カードフリップコンポーネント
    html_code = f"""
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; }}
  .cards-container {{
    display: flex; justify-content: center; gap: 12px;
    padding: 10px 0; flex-wrap: wrap;
  }}
  .card-slot {{
    perspective: 800px; width: {min(160, 580 // n)}px; text-align: center;
  }}
  .card-label {{
    color: #C9A84C; font-size: 0.85em; margin-bottom: 6px; font-family: sans-serif;
  }}
  .card-flip {{
    position: relative; width: 100%; padding-top: 150%;
    transform-style: preserve-3d; transition: transform 0.7s ease;
    cursor: pointer;
  }}
  .card-flip.flipped {{ transform: rotateY(180deg); }}
  .card-flip.waiting {{ opacity: 0.4; cursor: default; }}
  .card-flip.next {{ animation: pulse 1.5s ease-in-out infinite; }}
  @keyframes pulse {{
    0%, 100% {{ box-shadow: 0 0 8px rgba(201,168,76,0.3); }}
    50% {{ box-shadow: 0 0 20px rgba(201,168,76,0.8); }}
  }}
  .card-face {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    backface-visibility: hidden; border-radius: 8px; overflow: hidden;
  }}
  .card-back {{
    background: linear-gradient(135deg, #1a1040, #2d1b69, #1a1040);
    border: 2px solid #C9A84C; display: flex; align-items: center;
    justify-content: center; border-radius: 8px;
  }}
  .card-back span {{ color: #C9A84C; font-size: 1.8em; letter-spacing: 5px; }}
  .card-front {{
    transform: rotateY(180deg); border: 2px solid #C9A84C;
    border-radius: 8px; background: #1a1040;
  }}
  .card-front img {{ width: 100%; height: 80%; object-fit: contain; background: #f5f0e0; }}
  .card-info {{
    padding: 4px; text-align: center; font-family: sans-serif;
  }}
  .card-info .name {{ color: #C9A84C; font-size: 0.85em; font-weight: bold; }}
  .card-info .sub {{ color: #9B8FC4; font-size: 0.7em; }}
  .tap-hint {{
    color: #C9A84C; font-size: 0.8em; text-align: center;
    margin-top: 6px; font-family: sans-serif; animation: blink 2s infinite;
  }}
  @keyframes blink {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}
  .done-msg {{
    text-align: center; color: #C9A84C; font-size: 1.1em;
    margin: 20px 0; font-family: sans-serif;
  }}
</style>

<div class="cards-container" id="cardsContainer"></div>
<div id="tapHint" class="tap-hint">👆 カードをタップしてめくる</div>
<div id="doneArea" style="display:none;">
  <div class="done-msg">✦ 全てのカードが開きました ✦</div>
</div>

<script>
const cardsData = {cards_data};
const alreadyRevealed = {revealed};
let currentReveal = alreadyRevealed;

const container = document.getElementById('cardsContainer');

cardsData.forEach((card, i) => {{
  const slot = document.createElement('div');
  slot.className = 'card-slot';

  const label = document.createElement('div');
  label.className = 'card-label';
  label.textContent = card.pos;
  slot.appendChild(label);

  const flip = document.createElement('div');
  flip.className = 'card-flip';
  flip.dataset.index = i;

  if (i < currentReveal) {{
    flip.classList.add('flipped');
  }} else if (i === currentReveal) {{
    flip.classList.add('next');
  }} else {{
    flip.classList.add('waiting');
  }}

  // Back face
  const back = document.createElement('div');
  back.className = 'card-face card-back';
  back.innerHTML = '<span>✦☽✦</span>';
  flip.appendChild(back);

  // Front face
  const front = document.createElement('div');
  front.className = 'card-face card-front';
  if (card.img) {{
    front.innerHTML = '<img src="data:image/jpeg;base64,' + card.img + '">' +
      '<div class="card-info"><div class="name">' + card.name + '</div>' +
      '<div class="sub">' + card.name_en + '</div>' +
      '<div class="sub" style="color:' + (card.pos_text === '逆位置' ? '#FF6B9D' : '#C9A84C') + ';">' + card.pos_text + '</div></div>';
  }} else {{
    // 小アルカナ: 画像なしの場合スートシンボル＋カード名を表示
    const sym = card.suit_symbol || '✦';
    const rotateStyle = card.pos_text === '逆位置' ? 'transform:rotate(180deg);' : '';
    front.innerHTML = '<div style="width:100%;height:80%;background:linear-gradient(135deg,#1a1040,#2d1569);display:flex;flex-direction:column;align-items:center;justify-content:center;' + rotateStyle + '">' +
      '<div style="font-size:2.5em;margin-bottom:8px;">' + sym + '</div>' +
      '<div style="color:#C9A84C;font-size:0.9em;font-weight:bold;">' + card.name + '</div>' +
      '</div>' +
      '<div class="card-info"><div class="name">' + card.name + '</div>' +
      '<div class="sub">' + card.name_en + '</div>' +
      '<div class="sub" style="color:' + (card.pos_text === '逆位置' ? '#FF6B9D' : '#C9A84C') + ';">' + card.pos_text + '</div></div>';
  }}
  flip.appendChild(front);

  flip.addEventListener('click', () => {{
    if (parseInt(flip.dataset.index) !== currentReveal) return;
    flip.classList.remove('next');
    flip.classList.add('flipped');
    currentReveal++;

    // Update next card
    const allFlips = container.querySelectorAll('.card-flip');
    allFlips.forEach((f, j) => {{
      if (j === currentReveal) {{
        f.classList.remove('waiting');
        f.classList.add('next');
      }}
    }});

    document.getElementById('tapHint').textContent =
      currentReveal < cardsData.length
        ? '👆 次のカードをタップ'
        : '';

    if (currentReveal >= cardsData.length) {{
      setTimeout(() => {{
        document.getElementById('tapHint').style.display = 'none';
        document.getElementById('doneArea').style.display = 'block';
      }}, 800);
    }}
  }});

  slot.appendChild(flip);
  container.appendChild(slot);
}});

if (currentReveal >= cardsData.length) {{
  document.getElementById('tapHint').style.display = 'none';
  document.getElementById('doneArea').style.display = 'block';
}}

function goToReading() {{
  // 複数の方法でStreamlitにページ遷移を通知
  try {{
    // 方法1: 親フレームのURL変更
    const params = new URLSearchParams(window.parent.location.search);
    params.set('tarot_done', '1');
    window.parent.location.search = params.toString();
  }} catch(e) {{
    try {{
      // 方法2: topフレーム
      const params2 = new URLSearchParams(window.top.location.search);
      params2.set('tarot_done', '1');
      window.top.location.search = params2.toString();
    }} catch(e2) {{
      // 方法3: ボタンテキスト変更でユーザーにStreamlitボタンを押すよう促す
      document.querySelector('.done-btn').textContent = '↓ 下のボタンを押してください ↓';
      document.querySelector('.done-btn').style.background = '#9B8FC4';
    }}
  }}
}}
</script>
"""

    # query paramsでフリップ完了を検知
    params = st.query_params
    if params.get("tarot_done") == "1":
        st.query_params.clear()
        st.session_state.tarot_revealed = n
        st.session_state.page = "tarot_generating"
        st.rerun()

    # カード高さを計算（カード数に応じて）
    if n <= 3:
        card_h = 480
    elif n <= 4:
        card_h = 450
    else:
        card_h = 650  # 5枚：2行になるので高さを十分に
    components.html(html_code, height=card_h, scrolling=False)

    # カードをめくった後に押すボタン（常に表示）
    st.markdown("""
<div style="text-align:center; color:#9B8FC4; font-size:0.85em; margin:10px 0;">
全てのカードをめくったら ↓
</div>
""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✦ カードの声を聴く ✦", key="btn_tarot_interpret_main"):
            st.session_state.tarot_revealed = n
            st.session_state.page = "tarot_generating"
            st.rerun()


def render_tarot_generating_page():
    """対話型タロット: AI鑑定生成"""
    from ai.interpreter import generate_interactive_tarot

    bundle = st.session_state.tarot_bundle
    question = st.session_state.tarot_question
    spread_info = st.session_state.tarot_spread
    cards = st.session_state.tarot_cards

    render_star_deco("🃏")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">✦ カードが語り始めています…</div>',
        unsafe_allow_html=True
    )

    with st.status("✦ タロット鑑定生成中…", expanded=True) as status:
        st.write("✧ カードと星の声を統合中…")
        result = generate_interactive_tarot(bundle, question, spread_info, cards)
        status.update(label="✦ 鑑定完了 ✦", state="complete")

    st.session_state.tarot_result = result
    st.session_state.page = "tarot_result"
    st.rerun()


def render_tarot_result_page():
    """対話型タロット: 鑑定結果表示"""
    bundle = st.session_state.tarot_bundle
    question = st.session_state.tarot_question
    spread_info = st.session_state.tarot_spread
    cards = st.session_state.tarot_cards
    result = st.session_state.tarot_result
    name = bundle.person.name

    render_star_deco("🃏")
    title_text = f"{name}さんへ — " if name else ""
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.3em;">{title_text}カードからのメッセージ</div>',
        unsafe_allow_html=True
    )

    render_gold_divider()

    # 質問の表示
    st.markdown(f"""
<div style="text-align:center; color:#9B8FC4; font-size:0.9em; margin-bottom:15px;">
「{question}」に対する {spread_info["spread_name"]} の鑑定
</div>
""", unsafe_allow_html=True)

    # カード展開表示（全カード表面）
    n = len(cards)
    cols = st.columns(n)
    for i in range(n):
        with cols[i]:
            pos_name = spread_info["positions"][i] if i < len(spread_info["positions"]) else f"カード{i+1}"
            st.markdown(
                f'<div style="text-align:center; color:#C9A84C; font-size:0.85em; margin-bottom:5px;">{pos_name}</div>',
                unsafe_allow_html=True
            )
            render_tarot_card_simple(cards[i])

    render_gold_divider()

    # 鑑定結果
    headline = result.get("headline", "")
    reading = result.get("reading", "")
    closing = result.get("closing", "")

    if headline:
        st.markdown(f"""
<div style="text-align:center; font-size:1.2em; color:#C9A84C; font-weight:bold; margin:15px 0;">
「{headline}」
</div>
""", unsafe_allow_html=True)

    if reading:
        st.markdown(f"""
<div style="line-height:2.0; font-size:0.95em; color:#E0D8C8; padding:10px 5px;">
{reading}
</div>
""", unsafe_allow_html=True)

    if closing:
        st.markdown(f"""
<div style="text-align:center; color:#9B8FC4; font-style:italic; margin:20px 0; font-size:0.95em;">
— {closing}
</div>
""", unsafe_allow_html=True)

    render_gold_divider()

    # くろちゃんに追加質問チャット
    _render_tarot_chat(bundle, question, spread_info, cards, result)

    render_gold_divider()

    # フッター
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🃏 もう一度引く", key="btn_tarot_again"):
            st.session_state.page = "tarot_input"
            st.rerun()
    with col2:
        if st.button("✧ TOPに戻る ✧", key="btn_tarot_top"):
            st.session_state.page = "top"
            st.rerun()


def _render_tarot_chat(bundle, question, spread_info, cards, initial_result):
    """くろちゃんへの追加質問チャット — 毎回1枚カードを引いて回答"""
    from ai.interpreter import _format_all_data_summary, SYSTEM_PROMPT_BASE, _call_api_text
    from core.tarot import draw_tarot

    st.markdown("""
<div style="text-align:center; margin:15px 0 8px;">
<span style="color:#C9A84C; font-size:1.05em; font-weight:bold;">🔮 くろちゃんに聞く</span><br>
<span style="color:#9B8FC4; font-size:0.8em;">追加の質問ごとに1枚カードを引いてお答えします</span>
</div>
""", unsafe_allow_html=True)

    # チャット履歴の初期化
    if "tarot_chat_history" not in st.session_state:
        st.session_state.tarot_chat_history = []

    # 過去のチャットを表示（カード付き）
    for chat in st.session_state.tarot_chat_history:
        with st.chat_message("user", avatar="🙋"):
            st.write(chat["question"])
        with st.chat_message("assistant", avatar="🔮"):
            # 引いたカードを表示
            extra_card = chat.get("card")
            if extra_card:
                c1, c2 = st.columns([1, 3])
                with c1:
                    render_tarot_card_simple(extra_card)
                with c2:
                    st.write(chat["answer"])
            else:
                st.write(chat["answer"])

    # 入力欄
    tc_col1, tc_col2 = st.columns([5, 1])
    with tc_col1:
        follow_up = st.text_input(
            "質問", placeholder="例: 恋愛について もう1枚引いて",
            key="tarot_chat_input", label_visibility="collapsed"
        )
    with tc_col2:
        send_clicked = st.button("📨", key="btn_tarot_chat_send")

    if (send_clicked or follow_up) and follow_up:
        # 1枚カードを引く
        extra_card = draw_tarot(1)[0]

        # カード情報をテキスト化
        cards_text = "\n".join(
            f"- [{spread_info['positions'][i] if i < len(spread_info['positions']) else f'カード{i+1}'}] "
            f"{c.card_name}（{c.card_name_en}）{'逆位置' if c.is_reversed else '正位置'}"
            for i, c in enumerate(cards)
        )

        extra_pos = "逆位置" if extra_card.is_reversed else "正位置"
        extra_kw = "、".join(extra_card.keywords)

        # 命式データ
        data_summary = _format_all_data_summary(bundle)

        # 会話コンテキスト構築
        prev_reading = initial_result.get("reading", "")
        prev_chat = "\n".join(
            f"Q: {c['question']}\nA: {c['answer']}" for c in st.session_state.tarot_chat_history
        )

        prompt = f"""## 前の鑑定の文脈
質問: 「{question}」
展開法: {spread_info["spread_name"]}
元のカード:
{cards_text}

前の鑑定（要約）:
{prev_reading[:1000]}

{"## これまでの会話" + chr(10) + prev_chat if prev_chat else ""}

## 追加の質問
「{follow_up}」

## この質問に対して引いたカード
{extra_card.card_name}（{extra_card.card_name_en}）— {extra_pos}
キーワード: {extra_kw}
メッセージ: {extra_card.message}

## 命式データ
{data_summary[:800]}

## 指示
追加の質問に対して、**新しく引いたカード「{extra_card.card_name}（{extra_pos}）」**を中心に回答してください。
- 「この質問に対してカードを1枚引いたら、〇〇が出た」という流れで始める
- カードの意味を質問に直結させる
- 元のスプレッドとの関連があれば触れる
- 命式データとの関連があれば触れる
- 200〜500文字程度
- 目の前の人に語りかけるように
- JSONではなく、普通のテキストで回答"""

        with st.chat_message("user", avatar="🙋"):
            st.write(follow_up)

        with st.chat_message("assistant", avatar="🔮"):
            with st.spinner("🃏 カードを1枚引いています…"):
                try:
                    answer = _call_api_text(SYSTEM_PROMPT_BASE, prompt, max_tokens=1000)
                except Exception:
                    answer = f"カードを引いたら「{extra_card.card_name}（{extra_pos}）」が出ました。{extra_card.message}"

            # カードと回答を横並びで表示
            c1, c2 = st.columns([1, 3])
            with c1:
                render_tarot_card_simple(extra_card)
            with c2:
                st.write(answer)

        # 履歴に追加
        st.session_state.tarot_chat_history.append({
            "question": follow_up,
            "answer": answer,
            "card": extra_card,
        })


# ============================================================
# 通常鑑定の追加質問チャット
# ============================================================
def _render_general_chat(bundle, course, results):
    """通常鑑定結果の下に追加質問チャット"""
    from ai.interpreter import _format_all_data_summary, SYSTEM_PROMPT_BASE, _call_api_text

    name = bundle.person.name or "あなた"

    st.markdown(f"""
<div style="text-align:center; margin:15px 0 8px;">
<span style="color:#C9A84C; font-size:1.05em; font-weight:bold;">🔮 くろちゃんに聞く</span><br>
<span style="color:#9B8FC4; font-size:0.8em;">{name}さんの命式について、何でも聞いてください</span>
</div>
""", unsafe_allow_html=True)

    if "general_chat_history" not in st.session_state:
        st.session_state.general_chat_history = []

    for chat in st.session_state.general_chat_history:
        with st.chat_message("user", avatar="🙋"):
            st.write(chat["question"])
        with st.chat_message("assistant", avatar="🔮"):
            st.write(chat["answer"])

    gc_col1, gc_col2 = st.columns([5, 1])
    with gc_col1:
        follow_up = st.text_input(
            "質問", placeholder="例: 過去一番運が悪かった時期は？",
            key="general_chat_input", label_visibility="collapsed"
        )
    with gc_col2:
        send_clicked = st.button("📨", key="btn_general_send")

    if (send_clicked or follow_up) and follow_up:
        data_summary = _format_all_data_summary(bundle)

        # 鑑定結果のテキストを集約
        reading_texts = []
        for k, v in results.items():
            if isinstance(v, dict) and "reading" in v:
                reading_texts.append(v["reading"][:500])
        readings_context = "\n---\n".join(reading_texts)[:2000]

        prev_chat = "\n".join(
            f"Q: {c['question']}\nA: {c['answer']}"
            for c in st.session_state.general_chat_history
        )

        prompt = f"""## {name}さんの命式データ
{data_summary}

## これまでの鑑定内容（要約）
{readings_context}

{"## これまでの会話" + chr(10) + prev_chat if prev_chat else ""}

## 追加の質問
「{follow_up}」

## 指示
{name}さんの命式データと鑑定内容を踏まえて、追加の質問に答えてください。
- 算命学・西洋占星術・九星気学・数秘術のデータを必要に応じて参照
- 200〜500文字程度で簡潔に
- 具体的な年月や時期を聞かれたら、天中殺・大運・年運・トランジットから推測して答える
- 目の前の人に語りかけるように
- JSONではなく普通のテキストで回答"""

        with st.chat_message("user", avatar="🙋"):
            st.write(follow_up)

        with st.chat_message("assistant", avatar="🔮"):
            with st.spinner("くろちゃんが考え中…"):
                try:
                    answer = _call_api_text(SYSTEM_PROMPT_BASE, prompt, max_tokens=1000)
                except Exception:
                    answer = "ごめんね、今ちょっと集中できなくて…もう一度聞いてもらえる？"
            st.write(answer)

        st.session_state.general_chat_history.append({
            "question": follow_up,
            "answer": answer,
        })


# ============================================================
# 相性占いの追加質問チャット
# ============================================================
def _render_aisho_chat(bundle1, bundle2, result):
    """相性占い結果の下に追加質問チャット"""
    from ai.interpreter import _format_all_data_summary, SYSTEM_PROMPT_BASE, _call_api_text

    n1 = bundle1.person.name or "1人目"
    n2 = bundle2.person.name or "2人目"

    st.markdown(f"""
<div style="text-align:center; margin:15px 0 8px;">
<span style="color:#FF6B9D; font-size:1.05em; font-weight:bold;">💕 くろちゃんに聞く</span><br>
<span style="color:#9B8FC4; font-size:0.8em;">{n1}さんと{n2}さんの相性について、何でも聞いてください</span>
</div>
""", unsafe_allow_html=True)

    if "aisho_chat_history" not in st.session_state:
        st.session_state.aisho_chat_history = []

    for chat in st.session_state.aisho_chat_history:
        with st.chat_message("user", avatar="🙋"):
            st.write(chat["question"])
        with st.chat_message("assistant", avatar="💕"):
            st.write(chat["answer"])

    ac_col1, ac_col2 = st.columns([5, 1])
    with ac_col1:
        follow_up = st.text_input(
            "質問", placeholder="例: ケンカしちゃうけどうまく折り合いつけたい",
            key="aisho_chat_input", label_visibility="collapsed"
        )
    with ac_col2:
        send_clicked = st.button("📨", key="btn_aisho_send")

    if (send_clicked or follow_up) and follow_up:
        data1 = _format_all_data_summary(bundle1)
        data2 = _format_all_data_summary(bundle2)
        reading = result.get("reading", "")[:1500]

        prev_chat = "\n".join(
            f"Q: {c['question']}\nA: {c['answer']}"
            for c in st.session_state.aisho_chat_history
        )

        prompt = f"""## {n1}さんの命式データ
{data1[:1000]}

## {n2}さんの命式データ
{data2[:1000]}

## 相性鑑定内容（要約）
{reading}

{"## これまでの会話" + chr(10) + prev_chat if prev_chat else ""}

## 追加の質問
「{follow_up}」

## 指示
{n1}さんと{n2}さんの相性について、追加の質問に答えてください。
- 両者の命式データ（日干の五行関係、中央星の相性、太陽/月星座の相性など）を参照
- ケンカ・すれ違い等の質問には、五行の相生相剋や天中殺の重なりから具体的に分析
- 200〜500文字程度で簡潔に
- 具体的なアドバイスを含める
- 目の前の人に語りかけるように
- JSONではなく普通のテキストで回答"""

        with st.chat_message("user", avatar="🙋"):
            st.write(follow_up)

        with st.chat_message("assistant", avatar="💕"):
            with st.spinner("くろちゃんが考え中…"):
                try:
                    answer = _call_api_text(SYSTEM_PROMPT_BASE, prompt, max_tokens=1000)
                except Exception:
                    answer = "ごめんね、今ちょっと集中できなくて…もう一度聞いてもらえる？"
            st.write(answer)

        st.session_state.aisho_chat_history.append({
            "question": follow_up,
            "answer": answer,
        })


# ============================================================
# 裏メニューの自由質問チャット
# ============================================================
def _render_ura_chat(bundle):
    """裏メニューでの自由質問チャット"""
    from ai.interpreter import _format_all_data_summary, SYSTEM_PROMPT_BASE, _call_api_text

    name = bundle.person.name or "この人"

    st.markdown(f"""
<div style="text-align:center; margin:15px 0 8px;">
<span style="color:#C9A84C; font-size:1.05em; font-weight:bold;">🔮 くろちゃんに聞く</span><br>
<span style="color:#9B8FC4; font-size:0.8em;">{name}さんの命式について自由に質問</span>
</div>
""", unsafe_allow_html=True)

    if "ura_chat_history" not in st.session_state:
        st.session_state.ura_chat_history = []

    for chat in st.session_state.ura_chat_history:
        with st.chat_message("user", avatar="🙋"):
            st.write(chat["question"])
        with st.chat_message("assistant", avatar="🔮"):
            st.write(chat["answer"])

    uc_col1, uc_col2 = st.columns([5, 1])
    with uc_col1:
        follow_up = st.text_input(
            "質問", placeholder="例: この人の弱点は？ / 口説き方は？",
            key="ura_chat_input", label_visibility="collapsed"
        )
    with uc_col2:
        send_clicked = st.button("📨", key="btn_ura_send")

    if (send_clicked or follow_up) and follow_up:
        data_summary = _format_all_data_summary(bundle)

        prev_chat = "\n".join(
            f"Q: {c['question']}\nA: {c['answer']}"
            for c in st.session_state.ura_chat_history
        )

        prompt = f"""## {name}さんの命式データ
{data_summary}

{"## これまでの会話" + chr(10) + prev_chat if prev_chat else ""}

## 質問
「{follow_up}」

## 指示
{name}さんの命式データを踏まえて質問に答えてください。
- これは占い師の裏メニュー（ひでさん専用画面）での質問
- 飲み屋で使えるネタ、口説き方、相手の弱点、攻め方など実践的な回答OK
- 200〜400文字程度で簡潔に
- JSONではなく普通のテキストで回答"""

        with st.chat_message("user", avatar="🙋"):
            st.write(follow_up)

        with st.chat_message("assistant", avatar="🔮"):
            with st.spinner("くろちゃんが考え中…"):
                try:
                    answer = _call_api_text(SYSTEM_PROMPT_BASE, prompt, max_tokens=800)
                except Exception:
                    answer = "ごめんね、今ちょっと集中できなくて…もう一度聞いてもらえる？"
            st.write(answer)

        st.session_state.ura_chat_history.append({
            "question": follow_up,
            "answer": answer,
        })


# ============================================================
# テーマ別鑑定結果の追加質問チャット
# ============================================================
THEME_CHAT_LABELS = {
    "love": "恋愛運", "marriage": "結婚運", "career": "仕事運",
    "future10": "10年後", "shine": "輝く生き方",
}

def _render_theme_chat(bundle, theme_key, theme_data):
    """テーマ別鑑定結果の下に追加質問チャット"""
    from ai.interpreter import _format_all_data_summary, SYSTEM_PROMPT_BASE, _call_api_text

    name = bundle.person.name or "あなた"
    theme_label = THEME_CHAT_LABELS.get(theme_key, theme_key)

    st.markdown(f"""
<div style="text-align:center; margin:15px 0 8px;">
<span style="color:#C9A84C; font-size:1.05em; font-weight:bold;">🔮 くろちゃんに聞く</span><br>
<span style="color:#9B8FC4; font-size:0.8em;">{name}さんの{theme_label}についてもっと詳しく</span>
</div>
""", unsafe_allow_html=True)

    chat_key = f"theme_chat_{theme_key}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    for chat in st.session_state[chat_key]:
        with st.chat_message("user", avatar="🙋"):
            st.write(chat["question"])
        with st.chat_message("assistant", avatar="🔮"):
            st.write(chat["answer"])

    th_col1, th_col2 = st.columns([5, 1])
    with th_col1:
        follow_up = st.text_input(
            "質問", placeholder=f"例: {theme_label}で気をつけることは？",
            key=f"theme_chat_input_{theme_key}", label_visibility="collapsed"
        )
    with th_col2:
        send_clicked = st.button("📨", key=f"btn_theme_chat_send_{theme_key}")

    if (send_clicked or follow_up) and follow_up:
        data_summary = _format_all_data_summary(bundle)
        reading = theme_data.get("reading", "")[:1500]

        prev_chat = "\n".join(
            f"Q: {c['question']}\nA: {c['answer']}"
            for c in st.session_state[chat_key]
        )

        prompt = f"""## {name}さんの命式データ
{data_summary}

## {theme_label}の鑑定内容
{reading}

{"## これまでの会話" + chr(10) + prev_chat if prev_chat else ""}

## 追加の質問
「{follow_up}」

## 指示
{name}さんの{theme_label}について、命式データと鑑定内容を踏まえて追加の質問に答えてください。
- 200〜500文字程度で簡潔に
- 具体的な時期やアドバイスを含める
- JSONではなく普通のテキストで回答"""

        with st.chat_message("user", avatar="🙋"):
            st.write(follow_up)

        with st.chat_message("assistant", avatar="🔮"):
            with st.spinner("くろちゃんが考え中…"):
                try:
                    answer = _call_api_text(SYSTEM_PROMPT_BASE, prompt, max_tokens=1000)
                except Exception:
                    answer = "ごめんね、今ちょっと集中できなくて…もう一度聞いてもらえる？"
            st.write(answer)

        st.session_state[chat_key].append({
            "question": follow_up,
            "answer": answer,
        })
