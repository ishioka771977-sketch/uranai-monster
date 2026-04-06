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
    render_bansho_course,
    render_tarot_card_back, render_tarot_card_face,
    render_tarot_card_simple,
    render_theme_result,
)
from core.models import PersonInput
import urllib.parse as _urlparse
import html as _html_mod
import streamlit.components.v1 as _stc


# ============================================================
# 共有機能ヘルパー
# ============================================================
_THEME_LABELS = {
    "love": "恋愛運", "marriage": "結婚運", "career": "仕事運",
    "future10": "10年後の自分", "shine": "最大限に輝く生き方",
}

_REL_LABELS = {
    "love": "恋愛相性", "marriage": "結婚相性",
    "boss_subordinate": "上司×部下", "business": "仕事パートナー",
    "parent_child": "親子", "friend": "友人",
}


def _build_share_text(title: str, subtitle: str, headline: str, reading: str, closing: str) -> str:
    """共有用テキストを組み立てる"""
    import re
    # HTMLタグ除去
    reading_clean = re.sub(r'<[^>]+>', '', reading).strip() if reading else ""
    headline_clean = re.sub(r'<[^>]+>', '', headline).strip() if headline else ""
    closing_clean = re.sub(r'<[^>]+>', '', closing).strip() if closing else ""

    lines = ["✦ 占いモンスターくろたん ✦", ""]
    if title:
        lines.append(title)
    if subtitle:
        lines.append(subtitle)
    lines.append("")
    if headline_clean:
        lines.append(f"「{headline_clean}」")
        lines.append("")
    if reading_clean:
        lines.append(reading_clean)
        lines.append("")
    if closing_clean:
        lines.append(f"— {closing_clean}")
    return "\n".join(lines)


def _build_share_digest(title: str, headline: str, closing: str) -> str:
    """共有用ダイジェスト（短縮版、300文字以内）— LINE/メール/メッセージ用"""
    import re
    headline_clean = re.sub(r'<[^>]+>', '', headline).strip() if headline else ""
    closing_clean = re.sub(r'<[^>]+>', '', closing).strip() if closing else ""

    lines = ["✦ 占いモンスターくろたん ✦", ""]
    if title:
        lines.append(title)
    lines.append("")
    if headline_clean:
        lines.append(f"「{headline_clean}」")
    if closing_clean:
        lines.append("")
        lines.append(f"— {closing_clean}")
    lines.append("")
    lines.append("▼ 全文はアプリで確認")
    return "\n".join(lines)


def _render_share_buttons(share_text: str, key_suffix: str, pdf_html: str = "",
                          digest: str = ""):
    """共有ボタン群を描画: LINE / ネイティブ共有 / コピー / PDF"""
    import json as _json_share

    st.markdown("""
<div style="text-align:center; margin:15px 0 8px;">
<span style="color:#BFA350; font-size:0.95em; font-weight:bold;">✦ 鑑定結果を共有 ✦</span>
</div>""", unsafe_allow_html=True)

    # JavaScriptにテキストを安全に渡すためJSON化
    text_json = _json_share.dumps(share_text, ensure_ascii=False)
    # LINE用ダイジェスト（短縮版）
    digest_text = digest or share_text
    digest_encoded = _urlparse.quote(digest_text, safe='')
    line_url = f"https://line.me/R/share?text={digest_encoded}"

    # streamlit.components.v1.html でJSを確実に実行
    share_html = f"""
<div style="text-align:center; font-family: 'Zen Kaku Gothic New', sans-serif;">
  <a href="{line_url}" target="_blank" id="btn_line_{key_suffix}" style="
    display:inline-block; padding:10px 20px; margin:4px; border-radius:6px;
    font-size:0.9em; font-weight:bold; cursor:pointer; text-decoration:none;
    border: 1px solid #06C755; color:#fff; background:#06C755;
  ">💬 LINEで送る</a>

  <button id="btn_share_{key_suffix}" style="
    display:inline-block; padding:10px 20px; margin:4px; border-radius:6px;
    font-size:0.9em; font-weight:bold; cursor:pointer;
    border: 1px solid #BFA350; color:#0A0A0A; background:#BFA350;
  ">📤 メール・メッセージで共有</button>

  <button id="btn_copy_{key_suffix}" style="
    display:inline-block; padding:10px 20px; margin:4px; border-radius:6px;
    font-size:0.9em; font-weight:bold; cursor:pointer;
    border: 1px solid #2A2A2A; color:#F0EBE0; background:#1A1A1A;
  ">📋 全文をコピー</button>

  <div id="msg_{key_suffix}" style="color:#7CB87C; font-size:0.85em; margin-top:6px; min-height:20px;"></div>
</div>

<script>
(function() {{
  var fullText = {text_json};

  document.getElementById('btn_share_{key_suffix}').addEventListener('click', function() {{
    if (navigator.share) {{
      navigator.share({{
        title: '占いモンスターくろたん 鑑定結果',
        text: fullText
      }}).catch(function(e) {{
        if (e.name !== 'AbortError') {{
          fallbackCopy();
        }}
      }});
    }} else {{
      fallbackCopy();
    }}
  }});

  document.getElementById('btn_copy_{key_suffix}').addEventListener('click', function() {{
    doCopy(fullText, '✓ 全文をコピーしました！LINEやメールに貼り付けてください');
  }});

  function fallbackCopy() {{
    doCopy(fullText, '✓ コピーしました！LINEやメールに貼り付けてください');
  }}

  function doCopy(text, msg) {{
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(text).then(function() {{
        showMsg(msg);
      }}).catch(function() {{
        textAreaCopy(text, msg);
      }});
    }} else {{
      textAreaCopy(text, msg);
    }}
  }}

  function textAreaCopy(text, msg) {{
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy'); showMsg(msg); }}
    catch(e) {{ showMsg('⚠ コピーできませんでした。テキストを長押しで選択してください'); }}
    document.body.removeChild(ta);
  }}

  function showMsg(text) {{
    var el = document.getElementById('msg_{key_suffix}');
    el.textContent = text;
    setTimeout(function() {{ el.textContent = ''; }}, 3000);
  }}
}})();
</script>
"""
    _stc.html(share_html, height=120)

    # PDF ダウンロード
    if pdf_html:
        st.download_button(
            label="📄 PDFで保存",
            data=pdf_html.encode("utf-8"),
            file_name="鑑定結果.html",
            mime="text/html",
            key=f"btn_pdf_{key_suffix}",
            use_container_width=True,
        )
        st.caption("ダウンロード後、ブラウザで開いて「印刷 → PDF保存」で変換できます")


def _build_pdf_html(title: str, subtitle: str, headline: str, reading: str, closing: str) -> str:
    """印刷用のスタイル付きHTMLを生成"""
    import re
    reading_clean = re.sub(r'<[^>]+>', '', reading).strip() if reading else ""
    headline_clean = re.sub(r'<[^>]+>', '', headline).strip() if headline else ""
    closing_clean = re.sub(r'<[^>]+>', '', closing).strip() if closing else ""

    reading_html = _html_mod.escape(reading_clean).replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>{_html_mod.escape(title)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&family=Zen+Kaku+Gothic+New&display=swap');
  body {{ font-family: 'Zen Kaku Gothic New', sans-serif; background: #0A0A0A; color: #F0EBE0; max-width: 720px; margin: 40px auto; padding: 30px; }}
  h1 {{ font-family: 'Noto Serif JP', serif; text-align: center; color: #BFA350; font-size: 1.5em; margin-bottom: 5px; }}
  .subtitle {{ text-align: center; color: #8A8478; font-size: 0.9em; margin-bottom: 25px; }}
  .headline {{ text-align: center; font-size: 1.2em; color: #D4B96A; font-weight: bold; margin: 20px 0; }}
  .reading {{ line-height: 2.0; font-size: 0.95em; padding: 15px 0; white-space: pre-wrap; }}
  .closing {{ text-align: center; color: #8A8478; font-style: italic; margin: 25px 0; font-size: 0.95em; }}
  .divider {{ border-top: 1px solid #2A2A2A; margin: 20px 0; }}
  .footer {{ text-align: center; color: #5A5A5A; font-size: 0.75em; margin-top: 30px; }}
  @media print {{
    body {{ background: white; color: #333; }}
    h1 {{ color: #8B7530; }}
    .headline {{ color: #8B7530; }}
    .reading {{ color: #333; }}
    .closing {{ color: #666; }}
    .divider {{ border-color: #ccc; }}
  }}
</style>
</head>
<body>
<h1>✦ 占いモンスターくろたん ✦</h1>
<div class="subtitle">{_html_mod.escape(title)}<br>{_html_mod.escape(subtitle)}</div>
<div class="divider"></div>
{"<div class='headline'>「" + _html_mod.escape(headline_clean) + "」</div>" if headline_clean else ""}
<div class="reading">{reading_html}</div>
{"<div class='closing'>— " + _html_mod.escape(closing_clean) + "</div>" if closing_clean else ""}
<div class="divider"></div>
<div class="footer">占いモンスターくろたん — {date.today().strftime('%Y/%m/%d')} 鑑定</div>
</body>
</html>"""


# ============================================================
# TOP画面
# ============================================================
def render_top_page():
    """TOP画面: アプリ名 + 鑑定スタートボタン"""
    render_star_deco("✦ ☽ ✦")

    st.markdown(
        '<div class="uranai-title">占いモンスターくろたん</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uranai-subtitle">～ あなたの星を読む ～</div>',
        unsafe_allow_html=True
    )

    render_gold_divider()

    st.markdown("""
<div style="text-align:center; color:#8A8478; font-size:0.9em; margin:20px 0 30px;">
  生年月日を入れるだけで<br>
  算命学・西洋占星術・九星気学・数秘術・タロットで<br>
  <span style="color:#BFA350">あなたの本質と今年の運命を鑑定します</span>
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
        if st.button("✦ 相性鑑定 ✦", key="btn_aisho"):
            st.session_state.page = "aisho_input"
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📋 名簿管理", key="btn_meibo"):
            st.session_state.page = "meibo"
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🌟 開運アドバイス", key="btn_kaiyun"):
            st.session_state.page = "kaiyun_input"
            st.rerun()


# ============================================================
# 入力データ記憶（JSONファイル永続化 + session_state）
# ============================================================
import json as _json
import os as _os

_DATA_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data")
_PEOPLE_DB_PATH = _os.path.join(_DATA_DIR, "people_db.json")
_FOLDERS_DB_PATH = _os.path.join(_DATA_DIR, "folders_db.json")


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
        _os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_PEOPLE_DB_PATH, "w", encoding="utf-8") as f:
            _json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_folders_db() -> dict:
    """フォルダ定義を読み込み。形式: {"フォルダ名": ["名前1", "名前2", ...]}"""
    if "_folders_db" in st.session_state and st.session_state._folders_db is not None:
        return st.session_state._folders_db
    try:
        if _os.path.exists(_FOLDERS_DB_PATH):
            with open(_FOLDERS_DB_PATH, encoding="utf-8") as f:
                fdb = _json.load(f)
            st.session_state._folders_db = fdb
            return fdb
    except Exception:
        pass
    st.session_state._folders_db = {}
    return {}


def _persist_folders_db(fdb: dict):
    """フォルダ定義をJSONファイルに保存"""
    try:
        _os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_FOLDERS_DB_PATH, "w", encoding="utf-8") as f:
            _json.dump(fdb, f, ensure_ascii=False, indent=2)
        st.session_state._folders_db = fdb
    except Exception:
        pass


def _save_person(name, year, month, day, time_str="", place="", blood="不明", gender="男性"):
    """鑑定した人のデータをsession_state + ファイルに記憶"""
    st.session_state._saved_name = name
    st.session_state._saved_gender = gender
    st.session_state._saved_year = year
    st.session_state._saved_month = month
    st.session_state._saved_day = day
    st.session_state._saved_time = time_str
    st.session_state._saved_place = place
    st.session_state._saved_blood = blood

    from datetime import datetime as _dt
    db = _load_people_db()
    if name:
        existing = db.get(name, {})
        db[name] = {
            "name": name, "gender": gender, "year": year, "month": month, "day": day,
            "time": time_str, "place": place, "blood": blood,
            "last_divined": _dt.now().strftime("%Y-%m-%d %H:%M"),
            "divined_count": existing.get("divined_count", 0) + 1,
            "created_at": existing.get("created_at", _dt.now().strftime("%Y-%m-%d")),
        }
        st.session_state._people_db = db
        _persist_people_db(db)


def _select_person(p: dict):
    """人物データをセッションに読み込む（選択時共通処理）"""
    name = p.get("name", "")
    gender = p.get("gender", "男性")
    year = int(p.get("year", 1990))
    month = int(p.get("month", 5))
    day = int(p.get("day", 15))
    time_val = p.get("time", "")
    place = p.get("place", "")
    blood = p.get("blood", "不明")

    # 共通保存値（通常鑑定ページ用）
    st.session_state._saved_name = name
    st.session_state._saved_gender = gender
    st.session_state._saved_year = year
    st.session_state._saved_month = month
    st.session_state._saved_day = day
    st.session_state._saved_time = time_val
    st.session_state._saved_place = place
    st.session_state._saved_blood = blood
    st.session_state._input_key_ver = st.session_state.get("_input_key_ver", 0) + 1

    # タロットページのウィジェットキーにも直接セット
    st.session_state["tarot_name"] = name
    st.session_state["tarot_gender"] = gender
    st.session_state["tarot_year"] = year
    st.session_state["tarot_month"] = month
    st.session_state["tarot_day"] = day

    # 開運ページのウィジェットキーにも直接セット
    st.session_state["kaiyun_name"] = name
    st.session_state["kaiyun_gender"] = gender
    st.session_state["kaiyun_y"] = year
    st.session_state["kaiyun_m"] = month
    st.session_state["kaiyun_d"] = day

    st.rerun()


def _render_person_row(name: str, p: dict, key_prefix: str, people_db: dict, show_folder_assign: bool = False):
    """人物1行を描画（選択ボタン + 削除ボタン）"""
    year = p.get('year', '')
    month = p.get('month', '')
    day = p.get('day', '')
    gender = p.get('gender', '')
    blood = p.get('blood', '')
    blood_str = f" {blood}型" if blood and blood != "不明" else ""
    time_str = p.get('time', '')
    time_disp = f" {time_str}生" if time_str else ""
    divined = p.get('last_divined', '')
    divined_str = f"  🕐{divined}" if divined else ""

    col1, col2 = st.columns([5, 1])
    with col1:
        label = f"👤 {name}　{year}/{month}/{day}{time_disp}　{gender}{blood_str}{divined_str}"
        if st.button(label, key=f"btn_{key_prefix}_{name}", use_container_width=True):
            _select_person(p)
    with col2:
        if st.button("🗑", key=f"btn_del_{key_prefix}_{name}", help=f"{name}を削除"):
            del people_db[name]
            # フォルダからも削除
            fdb = _load_folders_db()
            for folder_names_list in fdb.values():
                if name in folder_names_list:
                    folder_names_list.remove(name)
            _persist_folders_db(fdb)
            st.session_state._people_db = people_db
            _persist_people_db(people_db)
            st.rerun()


def _render_people_quick_select():
    """顧客リスト — タブ切り替え式（全顧客 / 鑑定履歴 / カスタムフォルダ）"""
    people_db = _load_people_db()
    folders_db = _load_folders_db()

    # 顧客もフォルダも空の場合は何も表示しない
    if not people_db and not folders_db:
        return

    with st.expander("顧客リスト", expanded=False, icon="📋"):
        # タブ名を動的に構築
        folder_names = list(folders_db.keys())
        tab_labels = ["全顧客一覧", "鑑定履歴"] + [f"📁 {fn}" for fn in folder_names] + ["⚙ フォルダ管理"]
        tabs = st.tabs(tab_labels)

        # ── タブ: 全顧客一覧 ──
        with tabs[0]:
            if not people_db:
                st.caption("まだ顧客データがありません")
            else:
                names = list(people_db.keys())
                for name in sorted(names):
                    _render_person_row(name, people_db[name], "all", people_db)
                st.markdown(f'<div style="color:#5A5A5A;font-size:0.72em;text-align:right;">{len(names)}件</div>', unsafe_allow_html=True)

        # ── タブ: 鑑定履歴（last_divined順） ──
        with tabs[1]:
            divined = [(n, p) for n, p in people_db.items() if p.get("last_divined")]
            divined.sort(key=lambda x: x[1].get("last_divined", ""), reverse=True)
            if not divined:
                st.caption("まだ鑑定履歴がありません")
            else:
                for name, p in divined:
                    count = p.get("divined_count", 1)
                    _render_person_row(name, p, "hist", people_db)
                st.markdown(f'<div style="color:#5A5A5A;font-size:0.72em;text-align:right;">{len(divined)}件</div>', unsafe_allow_html=True)

        # ── タブ: カスタムフォルダ（各フォルダ） ──
        for fi, fname in enumerate(folder_names):
            with tabs[2 + fi]:
                members = folders_db.get(fname, [])
                if not members:
                    st.caption("このフォルダは空です")
                else:
                    for mname in members:
                        p = people_db.get(mname)
                        if p:
                            _render_person_row(mname, p, f"f{fi}", people_db)
                        else:
                            st.markdown(f'<span style="color:#5A5A5A;font-size:0.8em;">⚠ {mname}（データなし）</span>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#5A5A5A;font-size:0.72em;text-align:right;">{len(members)}件</div>', unsafe_allow_html=True)

                # フォルダに追加
                available = [n for n in people_db.keys() if n not in members]
                if available:
                    add_col1, add_col2 = st.columns([3, 1])
                    with add_col1:
                        selected = st.multiselect(
                            "追加する顧客", available, key=f"add_to_f{fi}", label_visibility="collapsed",
                            placeholder="顧客を選択して追加..."
                        )
                    with add_col2:
                        if st.button("＋追加", key=f"btn_add_f{fi}") and selected:
                            folders_db[fname].extend(selected)
                            _persist_folders_db(folders_db)
                            st.rerun()

                # フォルダからメンバーを外す
                if members:
                    rm_col1, rm_col2 = st.columns([3, 1])
                    with rm_col1:
                        remove_sel = st.multiselect(
                            "外す顧客", members, key=f"rm_from_f{fi}", label_visibility="collapsed",
                            placeholder="フォルダから外す..."
                        )
                    with rm_col2:
                        if st.button("－外す", key=f"btn_rm_f{fi}") and remove_sel:
                            for rn in remove_sel:
                                if rn in folders_db[fname]:
                                    folders_db[fname].remove(rn)
                            _persist_folders_db(folders_db)
                            st.rerun()

        # ── タブ: フォルダ管理 ──
        with tabs[-1]:
            st.markdown('<div style="color:#BFA350;font-size:0.9em;font-weight:bold;margin-bottom:8px;">フォルダ管理</div>', unsafe_allow_html=True)

            # 既存フォルダ一覧 + 削除
            if folder_names:
                for fi, fname in enumerate(folder_names):
                    fc1, fc2 = st.columns([4, 1])
                    with fc1:
                        count = len(folders_db.get(fname, []))
                        st.markdown(f'📁 **{fname}**　<span style="color:#5A5A5A;font-size:0.8em;">({count}件)</span>', unsafe_allow_html=True)
                    with fc2:
                        if st.button("🗑", key=f"btn_delfolder_{fi}", help=f"フォルダ「{fname}」を削除"):
                            del folders_db[fname]
                            _persist_folders_db(folders_db)
                            st.rerun()
            else:
                st.caption("フォルダはまだありません")

            # 新規フォルダ作成
            st.markdown("---")
            new_col1, new_col2 = st.columns([3, 1])
            with new_col1:
                new_fname = st.text_input("新しいフォルダ名", key="new_folder_name", placeholder="例: 鹿島建設セミナー", label_visibility="collapsed")
            with new_col2:
                if st.button("📁 作成", key="btn_create_folder"):
                    if new_fname and new_fname not in folders_db:
                        folders_db[new_fname] = []
                        _persist_folders_db(folders_db)
                        st.rerun()

            # 一括インポート
            st.markdown("---")
            st.markdown('<div style="color:#BFA350;font-size:0.85em;font-weight:bold;">一括インポート</div>', unsafe_allow_html=True)
            st.caption("以下の形式に対応（自動判定）:\n・名前, 年, 月, 日\n・名前, 1990/3/15\n・名前, 1990-03-15\n・名前, H2.3.15（和暦）\n・名前, 1990/3/15, 男性\n・名前, 1990/3/15, 男性, A")
            import_text = st.text_area(
                "一括入力", key="bulk_import", height=120, label_visibility="collapsed",
                placeholder="太郎, 1985/3/15\n花子, 1990/8/22\n太郎, H2.3.15\n..."
            )
            import_folder = st.text_input("インポート先フォルダ（空欄＝フォルダなし）", key="import_folder", placeholder="例: 鹿島建設セミナー", label_visibility="collapsed")
            if st.button("📥 一括登録", key="btn_bulk_import"):
                if import_text.strip():
                    count = 0
                    errors = []
                    for line in import_text.strip().split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        # カンマまたはスペースで分割
                        if "," in line:
                            parts = [p.strip() for p in line.split(",")]
                        else:
                            parts = line.split()
                        if len(parts) < 2:
                            errors.append(f"形式エラー: {line}")
                            continue
                        pname = parts[0]
                        date_str = parts[1]
                        pgender = parts[2] if len(parts) > 2 else ""
                        pblood = parts[3] if len(parts) > 3 else "不明"
                        ptime = parts[4] if len(parts) > 4 else ""

                        # 日付パース
                        pyear, pmonth, pday = None, None, None
                        try:
                            if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit() and parts[3].isdigit():
                                # 旧形式: 名前,年,月,日
                                pyear, pmonth, pday = int(parts[1]), int(parts[2]), int(parts[3])
                                pgender = parts[4] if len(parts) > 4 else ""
                                pblood = parts[5] if len(parts) > 5 else "不明"
                                ptime = parts[6] if len(parts) > 6 else ""
                            elif "/" in date_str:
                                dp = date_str.split("/")
                                pyear, pmonth, pday = int(dp[0]), int(dp[1]), int(dp[2])
                            elif "-" in date_str:
                                dp = date_str.split("-")
                                pyear, pmonth, pday = int(dp[0]), int(dp[1]), int(dp[2])
                            elif "." in date_str:
                                # 和暦: H2.3.15, S55.1.1, R1.5.1 等
                                import re
                                wm = re.match(r'([MTSHR])(\d+)\.(\d+)\.(\d+)', date_str)
                                if wm:
                                    era_map = {"M": 1867, "T": 1911, "S": 1925, "H": 1988, "R": 2018}
                                    base = era_map.get(wm.group(1), 1988)
                                    pyear = base + int(wm.group(2))
                                    pmonth, pday = int(wm.group(3)), int(wm.group(4))
                                else:
                                    dp = date_str.split(".")
                                    pyear, pmonth, pday = int(dp[0]), int(dp[1]), int(dp[2])
                            else:
                                # 漢字形式: 平成2年3月15日
                                import re
                                km = re.match(r'(明治|大正|昭和|平成|令和)(\d+)年(\d+)月(\d+)日', date_str)
                                if km:
                                    era_map2 = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}
                                    base = era_map2.get(km.group(1), 1988)
                                    pyear = base + int(km.group(2))
                                    pmonth, pday = int(km.group(3)), int(km.group(4))
                        except (ValueError, IndexError):
                            pass

                        if pyear and pmonth and pday:
                            people_db[pname] = {
                                "name": pname, "gender": pgender,
                                "year": pyear, "month": pmonth, "day": pday,
                                "time": ptime, "place": "", "blood": pblood,
                                "created_at": "",
                            }
                            if import_folder:
                                if import_folder not in folders_db:
                                    folders_db[import_folder] = []
                                if pname not in folders_db[import_folder]:
                                    folders_db[import_folder].append(pname)
                            count += 1
                        else:
                            errors.append(f"日付解析失敗: {line}")

                    st.session_state._people_db = people_db
                    _persist_people_db(people_db)
                    if import_folder:
                        _persist_folders_db(folders_db)
                    st.success(f"{count}人を登録しました" + (f"（📁 {import_folder}）" if import_folder else ""))
                    if errors:
                        st.warning("\\n".join(errors))
                    st.rerun()


# ============================================================
# 名簿管理画面
# ============================================================

def _parse_date_flexible(date_str: str):
    """柔軟な日付パーサー: 西暦・和暦・漢字和暦に対応"""
    import re
    date_str = date_str.strip()

    # yyyy/mm/dd or yyyy-mm-dd
    for sep in ['/', '-']:
        if sep in date_str:
            parts = date_str.split(sep)
            if len(parts) == 3:
                try:
                    return int(parts[0]), int(parts[1]), int(parts[2])
                except ValueError:
                    pass

    # 和暦アルファベット: H2.3.15, S55.1.1, R1/5/1 等
    wm = re.match(r'([MTSHR])(\d+)[./](\d+)[./](\d+)', date_str)
    if wm:
        era_map = {"M": 1867, "T": 1911, "S": 1925, "H": 1988, "R": 2018}
        base = era_map.get(wm.group(1), 1988)
        return base + int(wm.group(2)), int(wm.group(3)), int(wm.group(4))

    # 漢字和暦: 平成2年3月15日
    km = re.match(r'(明治|大正|昭和|平成|令和)(\d+)年(\d+)月(\d+)日', date_str)
    if km:
        era_map2 = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}
        base = era_map2.get(km.group(1), 1988)
        return base + int(km.group(2)), int(km.group(3)), int(km.group(4))

    return None, None, None


def _detect_column_mapping(headers: list) -> dict:
    """ヘッダー行からカラム名を自動検出してマッピングを返す"""
    mapping = {}
    name_candidates = ["名前", "氏名", "name", "お名前", "顧客名", "Name"]
    date_candidates = ["生年月日", "誕生日", "birthday", "birth_date", "Birthday", "生年月日（西暦）"]
    year_candidates = ["年", "year", "Year", "生年"]
    month_candidates = ["月", "month", "Month", "生月"]
    day_candidates = ["日", "day", "Day", "生日"]
    gender_candidates = ["性別", "gender", "sex", "Gender", "Sex"]
    blood_candidates = ["血液型", "blood", "blood_type", "Blood", "血液"]
    time_candidates = ["出生時刻", "時刻", "time", "birth_time", "Time", "生時"]
    place_candidates = ["出生地", "場所", "place", "birth_place", "Place", "出身地"]

    for i, h in enumerate(headers):
        if h is None:
            continue
        h_str = str(h).strip()
        if h_str in name_candidates:
            mapping["name"] = i
        elif h_str in date_candidates:
            mapping["date"] = i
        elif h_str in year_candidates:
            mapping["year"] = i
        elif h_str in month_candidates:
            mapping["month"] = i
        elif h_str in day_candidates:
            mapping["day"] = i
        elif h_str in gender_candidates:
            mapping["gender"] = i
        elif h_str in blood_candidates:
            mapping["blood"] = i
        elif h_str in time_candidates:
            mapping["time"] = i
        elif h_str in place_candidates:
            mapping["place"] = i
    return mapping


def _parse_file_rows(rows: list, headers: list) -> list:
    """ファイルの行データを解析して人物辞書のリストを返す"""
    mapping = _detect_column_mapping(headers)
    if "name" not in mapping:
        return []

    results = []
    for row in rows:
        try:
            name = str(row[mapping["name"]]).strip() if mapping["name"] < len(row) and row[mapping["name"]] else ""
            if not name:
                continue

            year, month, day = None, None, None
            if "date" in mapping and mapping["date"] < len(row) and row[mapping["date"]]:
                year, month, day = _parse_date_flexible(str(row[mapping["date"]]))
            if year is None and "year" in mapping and "month" in mapping and "day" in mapping:
                try:
                    yi = mapping["year"]
                    mi = mapping["month"]
                    di = mapping["day"]
                    if yi < len(row) and mi < len(row) and di < len(row):
                        year = int(float(str(row[yi])))
                        month = int(float(str(row[mi])))
                        day = int(float(str(row[di])))
                except (ValueError, TypeError):
                    pass

            if not year or not month or not day:
                results.append({"name": name, "error": "日付解析失敗"})
                continue

            gender = ""
            if "gender" in mapping and mapping["gender"] < len(row) and row[mapping["gender"]]:
                gender = str(row[mapping["gender"]]).strip()
            blood = "不明"
            if "blood" in mapping and mapping["blood"] < len(row) and row[mapping["blood"]]:
                blood = str(row[mapping["blood"]]).strip()
            time_str = ""
            if "time" in mapping and mapping["time"] < len(row) and row[mapping["time"]]:
                time_str = str(row[mapping["time"]]).strip()
            place = ""
            if "place" in mapping and mapping["place"] < len(row) and row[mapping["place"]]:
                place = str(row[mapping["place"]]).strip()

            results.append({
                "name": name, "year": year, "month": month, "day": day,
                "gender": gender, "blood": blood, "time": time_str, "place": place,
            })
        except Exception:
            continue
    return results


def render_meibo_page():
    """名簿管理画面: 顧客データの登録・編集・インポート"""
    import io
    import csv
    import re

    people_db = _load_people_db()
    folders_db = _load_folders_db()

    # ── ヘッダー ──
    render_star_deco("✦")
    st.markdown("""
<div style="text-align:center; margin-bottom:5px;">
  <span style="color:#BFA350; font-size:1.5em; font-weight:bold;">✦ 名簿管理 ✦</span><br>
  <span style="color:#8A8478; font-size:0.85em;">顧客データの登録・編集・インポート</span>
</div>
""", unsafe_allow_html=True)
    render_gold_divider()

    # ── セクション切り替え（タブ） ──
    tab_upload, tab_text, tab_list, tab_folders = st.tabs([
        "📂 ファイル取込", "📝 テキスト一括", "👥 顧客一覧", "📁 フォルダ管理"
    ])

    # ==================================================================
    # タブA: ファイルアップロード（CSV / Excel）
    # ==================================================================
    with tab_upload:
        st.markdown('<div style="color:#BFA350;font-size:0.95em;font-weight:bold;margin:8px 0;">CSV / Excelファイルから一括登録</div>', unsafe_allow_html=True)
        st.caption("対応カラム: 名前（必須）, 生年月日 or 年/月/日, 性別, 血液型, 出生時刻, 出生地")

        uploaded = st.file_uploader(
            "CSVまたはExcelファイル", type=["csv", "xlsx"],
            key="meibo_upload", label_visibility="collapsed"
        )

        if uploaded:
            parsed_rows = []
            file_headers = []
            error_msg = None

            try:
                if uploaded.name.endswith('.csv'):
                    content = uploaded.read().decode('utf-8-sig')
                    reader = csv.reader(io.StringIO(content))
                    all_rows = list(reader)
                    if all_rows:
                        file_headers = all_rows[0]
                        data_rows = all_rows[1:]
                        parsed_rows = _parse_file_rows(data_rows, file_headers)
                elif uploaded.name.endswith('.xlsx'):
                    try:
                        import openpyxl
                    except ImportError:
                        error_msg = "openpyxlがインストールされていません。pip install openpyxl を実行してください。"
                    if not error_msg:
                        wb = openpyxl.load_workbook(uploaded, read_only=True)
                        ws = wb.active
                        all_rows_xl = list(ws.iter_rows(values_only=True))
                        if all_rows_xl:
                            file_headers = [str(c) if c else "" for c in all_rows_xl[0]]
                            data_rows = [list(r) for r in all_rows_xl[1:]]
                            parsed_rows = _parse_file_rows(data_rows, file_headers)
                        wb.close()
            except Exception as e:
                error_msg = f"ファイル読み込みエラー: {e}"

            if error_msg:
                st.error(error_msg)
            elif parsed_rows:
                # プレビュー
                valid = [r for r in parsed_rows if "error" not in r]
                errors = [r for r in parsed_rows if "error" in r]

                st.markdown(f'<div style="color:#D4B96A;font-size:0.9em;">検出: {len(valid)}件（エラー: {len(errors)}件）</div>', unsafe_allow_html=True)

                if valid:
                    import pandas as pd
                    preview_data = []
                    for r in valid:
                        preview_data.append({
                            "名前": r["name"],
                            "生年月日": f"{r['year']}/{r['month']}/{r['day']}",
                            "性別": r.get("gender", ""),
                            "血液型": r.get("blood", "不明"),
                            "時刻": r.get("time", ""),
                            "出生地": r.get("place", ""),
                        })
                    st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

                if errors:
                    with st.expander(f"⚠ エラー {len(errors)}件", expanded=False):
                        for e in errors:
                            st.caption(f"・{e['name']}: {e.get('error', '')}")

                # フォルダ選択
                folder_options = ["（フォルダなし）"] + list(folders_db.keys())
                upload_folder = st.selectbox("登録先フォルダ", folder_options, key="upload_folder")
                new_folder_for_upload = st.text_input("または新規フォルダ名", key="upload_new_folder", placeholder="新しいフォルダを作成して登録")

                if st.button("📥 確定して登録", key="btn_confirm_upload"):
                    count = 0
                    target_folder = new_folder_for_upload.strip() if new_folder_for_upload.strip() else (upload_folder if upload_folder != "（フォルダなし）" else "")
                    for r in valid:
                        pname = r["name"]
                        existing = people_db.get(pname, {})
                        people_db[pname] = {
                            "name": pname,
                            "gender": r.get("gender", ""),
                            "year": r["year"], "month": r["month"], "day": r["day"],
                            "time": r.get("time", ""),
                            "place": r.get("place", ""),
                            "blood": r.get("blood", "不明"),
                            "created_at": existing.get("created_at", ""),
                            "last_divined": existing.get("last_divined", ""),
                            "divined_count": existing.get("divined_count", 0),
                        }
                        if target_folder:
                            if target_folder not in folders_db:
                                folders_db[target_folder] = []
                            if pname not in folders_db[target_folder]:
                                folders_db[target_folder].append(pname)
                        count += 1
                    st.session_state._people_db = people_db
                    _persist_people_db(people_db)
                    if target_folder:
                        _persist_folders_db(folders_db)
                    st.success(f"{count}人を登録しました" + (f"（📁 {target_folder}）" if target_folder else ""))
                    st.rerun()
            else:
                st.warning("データが見つかりませんでした。ヘッダー行に「名前」カラムが必要です。")

    # ==================================================================
    # タブB: テキスト一括インポート
    # ==================================================================
    with tab_text:
        st.markdown('<div style="color:#BFA350;font-size:0.95em;font-weight:bold;margin:8px 0;">テキスト一括インポート</div>', unsafe_allow_html=True)
        st.caption(
            "以下の形式に対応（自動判定）:\n"
            "・名前, 年, 月, 日\n"
            "・名前, 1990/3/15\n"
            "・名前, 1990-03-15\n"
            "・名前, H2.3.15（和暦）\n"
            "・名前, 平成2年3月15日\n"
            "・名前, 1990/3/15, 男性\n"
            "・名前, 1990/3/15, 男性, A"
        )
        import_text = st.text_area(
            "一括入力", key="meibo_bulk_import", height=160, label_visibility="collapsed",
            placeholder="太郎, 1985/3/15\n花子, 1990/8/22\n次郎, H2.3.15\n..."
        )

        # フォルダ選択
        folder_options = ["（フォルダなし）"] + list(folders_db.keys())
        text_folder = st.selectbox("登録先フォルダ", folder_options, key="meibo_text_folder")
        new_folder_for_text = st.text_input("または新規フォルダ名", key="meibo_text_new_folder", placeholder="新しいフォルダを作成して登録")

        if st.button("📥 一括登録", key="btn_meibo_bulk"):
            if import_text.strip():
                count = 0
                errors = []
                target_folder = new_folder_for_text.strip() if new_folder_for_text.strip() else (text_folder if text_folder != "（フォルダなし）" else "")

                for line in import_text.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if "," in line:
                        parts = [p.strip() for p in line.split(",")]
                    else:
                        parts = line.split()
                    if len(parts) < 2:
                        errors.append(f"形式エラー: {line}")
                        continue

                    pname = parts[0]
                    date_str = parts[1]
                    pgender = parts[2] if len(parts) > 2 else ""
                    pblood = parts[3] if len(parts) > 3 else "不明"
                    ptime = parts[4] if len(parts) > 4 else ""

                    pyear, pmonth, pday = None, None, None
                    try:
                        if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit() and parts[3].isdigit():
                            pyear, pmonth, pday = int(parts[1]), int(parts[2]), int(parts[3])
                            pgender = parts[4] if len(parts) > 4 else ""
                            pblood = parts[5] if len(parts) > 5 else "不明"
                            ptime = parts[6] if len(parts) > 6 else ""
                        else:
                            pyear, pmonth, pday = _parse_date_flexible(date_str)
                    except (ValueError, IndexError):
                        pass

                    if pyear and pmonth and pday:
                        existing = people_db.get(pname, {})
                        people_db[pname] = {
                            "name": pname, "gender": pgender,
                            "year": pyear, "month": pmonth, "day": pday,
                            "time": ptime, "place": "", "blood": pblood,
                            "created_at": existing.get("created_at", ""),
                            "last_divined": existing.get("last_divined", ""),
                            "divined_count": existing.get("divined_count", 0),
                        }
                        if target_folder:
                            if target_folder not in folders_db:
                                folders_db[target_folder] = []
                            if pname not in folders_db[target_folder]:
                                folders_db[target_folder].append(pname)
                        count += 1
                    else:
                        errors.append(f"日付解析失敗: {line}")

                st.session_state._people_db = people_db
                _persist_people_db(people_db)
                if target_folder:
                    _persist_folders_db(folders_db)
                st.success(f"{count}人を登録しました" + (f"（📁 {target_folder}）" if target_folder else ""))
                if errors:
                    st.warning("\n".join(errors))
                st.rerun()

    # ==================================================================
    # タブC: 顧客一覧
    # ==================================================================
    with tab_list:
        st.markdown(f'<div style="color:#BFA350;font-size:0.95em;font-weight:bold;margin:8px 0;">登録顧客一覧（{len(people_db)}件）</div>', unsafe_allow_html=True)

        if not people_db:
            st.caption("まだ顧客データがありません")
        else:
            # 検索フィルター
            search_q = st.text_input("🔍 名前で検索", key="meibo_search", placeholder="名前を入力...", label_visibility="collapsed")

            names_sorted = sorted(people_db.keys())
            if search_q:
                names_sorted = [n for n in names_sorted if search_q.lower() in n.lower()]

            if not names_sorted:
                st.caption("該当する顧客がいません")
            else:
                # テーブル表示
                import pandas as pd
                table_data = []
                for name in names_sorted:
                    p = people_db[name]
                    table_data.append({
                        "名前": name,
                        "生年月日": f"{p.get('year','')}/{p.get('month','')}/{p.get('day','')}",
                        "性別": p.get("gender", ""),
                        "血液型": p.get("blood", "不明"),
                        "鑑定回数": p.get("divined_count", 0),
                        "最終鑑定日": p.get("last_divined", "―"),
                    })
                st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

                # 個別削除
                st.markdown("---")
                st.markdown('<div style="color:#8A8478;font-size:0.8em;margin-bottom:6px;">個別削除</div>', unsafe_allow_html=True)
                del_target = st.selectbox("削除する顧客", ["（選択）"] + names_sorted, key="meibo_del_target", label_visibility="collapsed")
                if st.button("🗑 削除", key="btn_meibo_del"):
                    if del_target and del_target != "（選択）" and del_target in people_db:
                        del people_db[del_target]
                        # フォルダからも削除
                        for folder_member_list in folders_db.values():
                            if del_target in folder_member_list:
                                folder_member_list.remove(del_target)
                        st.session_state._people_db = people_db
                        _persist_people_db(people_db)
                        _persist_folders_db(folders_db)
                        st.success(f"「{del_target}」を削除しました")
                        st.rerun()

    # ==================================================================
    # タブD: フォルダ管理
    # ==================================================================
    with tab_folders:
        st.markdown('<div style="color:#BFA350;font-size:0.95em;font-weight:bold;margin:8px 0;">フォルダ管理</div>', unsafe_allow_html=True)

        # 新規フォルダ作成
        fc1, fc2 = st.columns([3, 1])
        with fc1:
            new_fname = st.text_input("新しいフォルダ名", key="meibo_new_folder_name", placeholder="例: 鹿島建設セミナー", label_visibility="collapsed")
        with fc2:
            if st.button("📁 作成", key="btn_meibo_create_folder"):
                if new_fname and new_fname not in folders_db:
                    folders_db[new_fname] = []
                    _persist_folders_db(folders_db)
                    st.rerun()

        st.markdown("---")

        folder_names = list(folders_db.keys())
        if not folder_names:
            st.caption("フォルダはまだありません")
        else:
            for fi, fname in enumerate(folder_names):
                members = folders_db.get(fname, [])
                with st.expander(f"📁 {fname}（{len(members)}件）", expanded=False):
                    # メンバー一覧
                    if members:
                        for mname in members:
                            p = people_db.get(mname)
                            if p:
                                st.markdown(
                                    f'<span style="color:#F0EBE0;font-size:0.85em;">👤 {mname}　{p.get("year","")}/{p.get("month","")}/{p.get("day","")}　{p.get("gender","")}　{p.get("blood","不明")}型</span>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(f'<span style="color:#5A5A5A;font-size:0.8em;">⚠ {mname}（データなし）</span>', unsafe_allow_html=True)
                    else:
                        st.caption("このフォルダは空です")

                    # メンバー追加
                    available = [n for n in people_db.keys() if n not in members]
                    if available:
                        add_c1, add_c2 = st.columns([3, 1])
                        with add_c1:
                            add_sel = st.multiselect(
                                "追加する顧客", available, key=f"meibo_add_f{fi}", label_visibility="collapsed",
                                placeholder="顧客を選択して追加..."
                            )
                        with add_c2:
                            if st.button("＋追加", key=f"btn_meibo_add_f{fi}") and add_sel:
                                folders_db[fname].extend(add_sel)
                                _persist_folders_db(folders_db)
                                st.rerun()

                    # メンバー削除
                    if members:
                        rm_c1, rm_c2 = st.columns([3, 1])
                        with rm_c1:
                            rm_sel = st.multiselect(
                                "外す顧客", members, key=f"meibo_rm_f{fi}", label_visibility="collapsed",
                                placeholder="フォルダから外す..."
                            )
                        with rm_c2:
                            if st.button("－外す", key=f"btn_meibo_rm_f{fi}") and rm_sel:
                                for rn in rm_sel:
                                    if rn in folders_db[fname]:
                                        folders_db[fname].remove(rn)
                                _persist_folders_db(folders_db)
                                st.rerun()

                    # フォルダ削除
                    st.markdown("---")
                    if st.button(f"🗑 「{fname}」フォルダを削除", key=f"btn_meibo_delfolder_{fi}"):
                        del folders_db[fname]
                        _persist_folders_db(folders_db)
                        st.rerun()

    # ── 戻るボタン ──
    st.markdown("<br>", unsafe_allow_html=True)
    render_gold_divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← TOPに戻る", key="btn_back_meibo"):
            st.session_state.page = "top"
            st.rerun()


# ============================================================
# 入力画面
# ============================================================
def render_input_page():
    """生年月日入力画面"""

    # ファイルから保存済みデータを復元
    _load_people_db()

    # デフォルト値（復元済みなら復元値、なければ初期値）
    saved_name = st.session_state.get("_saved_name", "")
    saved_gender = st.session_state.get("_saved_gender", "男性")
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

    # 性別
    gender_options = ["男性", "女性", "その他"]
    gender_idx = gender_options.index(saved_gender) if saved_gender in gender_options else 0
    st.radio(
        "性別",
        options=gender_options,
        index=gender_idx,
        horizontal=True,
        key=f"input_gender_{kv}"
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
            input_gender = st.session_state.get(f"input_gender_{kv}", "男性")
            input_time = st.session_state.get(f"input_time_{kv}", "").strip()
            input_place = st.session_state.get(f"input_place_{kv}", "").strip()
            input_blood = st.session_state.get(f"input_blood_{kv}", "不明")

            # セッションステートに保存
            st.session_state.person = PersonInput(
                birth_date=birth_date,
                name=input_name if input_name else None,
                gender=input_gender,
                birth_time=input_time if input_time else None,
                birth_place=input_place if input_place else None,
                blood_type=input_blood if input_blood != "不明" else None,
            )

            # 名前をキーにデータを記憶
            _save_person(
                input_name, year, month, day, input_time, input_place, input_blood, input_gender
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
<div style="text-align:center; color:#8A8478; font-size:0.85em; margin-bottom:10px;">
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
        if st.button("⚡ 万象学", key="btn_bansho"):
            _start_course("万象学")

    if st.button("✧ フルコース ✧", key="btn_full", use_container_width=True):
        _start_course("フルコース")

    render_gold_divider()

    # テーマ別深掘り鑑定セクション（コース選択と並列）
    st.markdown("""
<div style="text-align:center; margin:20px 0 10px;">
<span style="color:#BFA350; font-size:1.15em; font-weight:bold;">✦ テーマで深掘り ✦</span><br>
<span style="color:#8A8478; font-size:0.85em;">全占術を横断した深掘り鑑定</span>
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

    # くろたんに自由質問（裏メニュー）
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

    if course == "万象学":
        # 万象学もAI鑑定文を生成
        with st.status("✦ 万象学コース鑑定生成中…", expanded=True) as status:
            st.write("✧ エネルギー診断からAI鑑定文を生成中…")
            from ai.interpreter import generate_bansho_reading
            result = generate_bansho_reading(bundle)
            status.update(label="✦ 万象学コース鑑定完了 ✦", state="complete")
        st.session_state.course_results["bansho"] = result
    elif course == "フルコース":
        with st.status("✦ フルコース鑑定生成中…", expanded=True) as status:
            st.write("✧ 6占術を同時に鑑定中…")
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

    # 共有ボタン — 結果のすぐ下
    _theme_label = _THEME_LABELS.get(theme_key, theme_key)
    _th_title = f"{name}さん — {_theme_label}" if name else _theme_label
    _th_subtitle = f"{d.year}年{d.month}月{d.day}日生まれ"
    _th_text = _build_share_text(_th_title, _th_subtitle, theme_data.get("headline", ""), theme_data.get("reading", ""), theme_data.get("closing", ""))
    _th_pdf = _build_pdf_html(_th_title, _th_subtitle, theme_data.get("headline", ""), theme_data.get("reading", ""), theme_data.get("closing", ""))
    _th_digest = _build_share_digest(_th_title, theme_data.get("headline", ""), theme_data.get("closing", ""))
    _render_share_buttons(_th_text, f"theme_{theme_key}", _th_pdf, _th_digest)

    render_gold_divider()

    # くろたんにテーマ関連の質問
    _render_theme_chat(bundle, theme_key, theme_data)

    render_gold_divider()

    # 他のテーマも見る
    st.markdown("""
<div style="text-align:center; margin:20px 0 10px;">
<span style="color:#BFA350; font-size:1.0em;">✦ 他のテーマも深掘り ✦</span>
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

    # 共有ボタン — 鑑定結果のすぐ下に配置
    _cr_title = f"{name}さん — {course}" if name else course
    _cr_subtitle = f"{d.year}年{d.month}月{d.day}日生まれ"
    if course == "フルコース":
        _syn = results.get("synthesis", {})
        _cr_hl = _syn.get("headline", "")
        _cr_rd = _syn.get("reading", "")
        _cr_cl = _syn.get("closing", "")
    else:
        _ckey_map = {"算命学": "sanmei", "星座": "western", "九星気学": "kyusei", "数秘術": "numerology", "タロット": "tarot", "紫微斗数": "ziwei", "万象学": "bansho"}
        _cdata = results.get(_ckey_map.get(course, course), {})
        _cr_hl = _cdata.get("headline", _cdata.get("one_line", ""))
        _cr_rd = _cdata.get("reading", _cdata.get("nichikan_reading", _cdata.get("sun_reading", _cdata.get("honmei_reading", _cdata.get("life_path_reading", "")))))
        _cr_cl = _cdata.get("closing", "")
    _cr_text = _build_share_text(_cr_title, _cr_subtitle, _cr_hl, _cr_rd, _cr_cl)
    _cr_pdf = _build_pdf_html(_cr_title, _cr_subtitle, _cr_hl, _cr_rd, _cr_cl)
    _cr_digest = _build_share_digest(_cr_title, _cr_hl, _cr_cl)
    _render_share_buttons(_cr_text, "course", _cr_pdf, _cr_digest)

    render_gold_divider()

    # テーマ別深掘り鑑定セクション
    _render_theme_section(bundle)

    render_gold_divider()

    # くろたんに個別質問チャット
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
        "万象学": "bansho",
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
    elif course == "万象学":
        render_bansho_course(bundle, data)


def _render_full_course_result(bundle, results):
    """フルコース選択時: タブ構造で全コース表示"""
    tab_names = ["✦ 総合", "算命学", "星座", "九星気学", "数秘術", "紫微斗数", "万象学", "タロット"]
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
        render_bansho_course(bundle)

    with tabs[7]:
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
<span style="color:#BFA350; font-size:1.15em; font-weight:bold;">✦ もっと深く見る ✦</span><br>
<span style="color:#8A8478; font-size:0.85em;">テーマを選ぶと、全占術を横断した深掘り鑑定が生成されます</span>
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
    """相性鑑定: 2人分の生年月日入力 + 関係性選択"""
    from core.aisho_scoring import RELATIONSHIP_CATEGORIES

    render_star_deco("✦")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">相性鑑定</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uranai-subtitle">～ ふたりの星を読む ～</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    # --- 1人目（ひでさん固定オプション） ---
    use_hidesan = st.checkbox("1人目をひでさんに固定する", value=st.session_state.get("aisho_use_hidesan", False), key="aisho_use_hidesan")

    # --- ヘルパー: 顧客選択時にwidgetキーを直接書き換えてrerun ---
    def _on_sel_change(db, sel_key, name_key, y_key, m_key, d_key, g_key, t_key, p_key, b_key):
        """on_changeコールバック: 顧客選択時に各widgetキーへ直接書き込み"""
        sel = st.session_state.get(sel_key, "（手入力）")
        if sel != "（手入力）" and sel in db:
            p = db[sel]
            st.session_state[name_key] = p.get("name", sel)
            st.session_state[y_key] = p.get("year", 1990)
            st.session_state[m_key] = p.get("month", 5)
            st.session_state[d_key] = p.get("day", 15)
            gv = p.get("gender", "男性")
            if gv in ["男性", "女性", "その他"]:
                st.session_state[g_key] = gv
            st.session_state[t_key] = p.get("time", "") or ""
            st.session_state[p_key] = p.get("place", "") or ""
            bv = p.get("blood", "不明") or "不明"
            if bv in ["不明", "A", "B", "O", "AB"]:
                st.session_state[b_key] = bv

    if use_hidesan:
        st.markdown('<div style="color:#BFA350; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">✦ 1人目: ひでさん（固定）</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#8A8478; font-size:0.85em; margin:0 0 10px;">1977/5/24 函館市 A型</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#BFA350; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">✦ 1人目</div>', unsafe_allow_html=True)

        # 顧客リストから選択
        db = _load_people_db()
        if db:
            ppl_names = ["（手入力）"] + sorted(db.keys())
            _cb_args1 = (db, "aisho_sel1", "aisho_name1", "aisho_y1", "aisho_m1", "aisho_d1", "aisho_gender1", "aisho_t1", "aisho_p1", "aisho_b1")
            st.selectbox("顧客リストから選択", options=ppl_names, index=0, key="aisho_sel1",
                         on_change=_on_sel_change, args=_cb_args1)

        name1 = st.text_input("お名前", value="", placeholder="例: ひでさん", key="aisho_name1")
        gender1 = st.radio("性別", options=["男性", "女性", "その他"], index=0, horizontal=True, key="aisho_gender1")

        years = list(range(1930, date.today().year))
        c1a, c1b, c1c = st.columns(3)
        with c1a:
            y1 = st.selectbox("年", options=years, index=years.index(1990), key="aisho_y1")
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
    st.markdown('<div style="color:#D4837A; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">✦ 2人目</div>', unsafe_allow_html=True)

    # 顧客リストから選択
    db = _load_people_db()
    if db:
        ppl_names2 = ["（手入力）"] + sorted(db.keys())
        _cb_args2 = (db, "aisho_sel2", "aisho_name2", "aisho_y2", "aisho_m2", "aisho_d2", "aisho_gender2", "aisho_t2", "aisho_p2", "aisho_b2")
        st.selectbox("顧客リストから選択", options=ppl_names2, index=0, key="aisho_sel2",
                     on_change=_on_sel_change, args=_cb_args2)

    name2 = st.text_input("お名前", value="", placeholder="例: ゆうこ", key="aisho_name2")
    gender2 = st.radio("性別", options=["男性", "女性", "その他"], index=1, horizontal=True, key="aisho_gender2")

    years2 = list(range(1930, date.today().year))
    c2a, c2b, c2c = st.columns(3)
    with c2a:
        y2 = st.selectbox("年", options=years2, index=years2.index(1990), key="aisho_y2")
    with c2b:
        m2 = st.selectbox("月", options=list(range(1, 13)), index=4, key="aisho_m2")
    with c2c:
        d2 = st.selectbox("日", options=list(range(1, 32)), index=14, key="aisho_d2")

    with st.expander("▼ もっと詳しく（任意）", expanded=False):
        t2 = st.text_input("出生時刻", value="", placeholder="HH:MM", key="aisho_t2")
        p2 = st.text_input("出生地", value="", placeholder="都市名", key="aisho_p2")
        b2 = st.radio("血液型", options=["不明", "A", "B", "O", "AB"], index=0, horizontal=True, key="aisho_b2")

    render_gold_divider()

    # --- 関係性カテゴリ選択 ---
    st.markdown('<div style="color:#BFA350; font-size:1.1em; font-weight:bold; margin:10px 0 8px;">✦ 2人の関係性を選んでください</div>', unsafe_allow_html=True)

    cat_keys = list(RELATIONSHIP_CATEGORIES.keys())
    cat_labels = [f"{RELATIONSHIP_CATEGORIES[k]['icon']} {RELATIONSHIP_CATEGORIES[k]['label']}" for k in cat_keys]

    # 2行3列のボタンレイアウト
    row1 = st.columns(3)
    row2 = st.columns(3)
    rows = [row1, row2]

    selected_rel = st.session_state.get("aisho_relationship", "love")

    for i, key in enumerate(cat_keys):
        cat = RELATIONSHIP_CATEGORIES[key]
        r = i // 3
        c = i % 3
        with rows[r][c]:
            is_selected = (selected_rel == key)
            btn_style = "border:2px solid #BFA350; background:#1A1A1A;" if is_selected else "border:1px solid #2A2A2A; background:#121212;"
            if st.button(
                f"{cat['icon']} {cat['label']}",
                key=f"btn_rel_{key}",
                use_container_width=True,
            ):
                st.session_state.aisho_relationship = key
                st.rerun()

    # 選択中の関係性を表示
    sel_cat = RELATIONSHIP_CATEGORIES.get(selected_rel, RELATIONSHIP_CATEGORIES['love'])
    st.markdown(f'<div style="text-align:center; color:#8A8478; font-size:0.85em; margin:5px 0 15px;">{sel_cat["icon"]} {sel_cat["label"]}: {sel_cat["description"]}</div>', unsafe_allow_html=True)

    render_gold_divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✦ 鑑定する ✦", key="btn_aisho_start"):
            if use_hidesan:
                bd1 = date(1977, 5, 24)
                person1 = PersonInput(
                    name="ひでさん", gender="男性", birth_date=bd1,
                    birth_time="1:34", birth_place="函館市", blood_type="A",
                )
            else:
                try:
                    bd1 = date(y1, m1, d1)
                except ValueError:
                    st.error("1人目の日付が無効です。")
                    return
                time1 = st.session_state.get("aisho_t1", "").strip()
                place1 = st.session_state.get("aisho_p1", "").strip()
                blood1 = st.session_state.get("aisho_b1", "不明")
                g1 = st.session_state.get("aisho_gender1", "男性")
                person1 = PersonInput(
                    name=name1.strip() if name1.strip() else "1人目",
                    gender=g1, birth_date=bd1,
                    birth_time=time1 if time1 else None,
                    birth_place=place1 if place1 else None,
                    blood_type=blood1 if blood1 != "不明" else None,
                )

            try:
                bd2 = date(y2, m2, d2)
            except ValueError:
                st.error("2人目の日付が無効です。")
                return

            time2 = st.session_state.get("aisho_t2", "").strip()
            place2 = st.session_state.get("aisho_p2", "").strip()
            blood2 = st.session_state.get("aisho_b2", "不明")
            g2 = st.session_state.get("aisho_gender2", "女性")

            st.session_state.aisho_person1 = person1
            st.session_state.aisho_person2 = PersonInput(
                name=name2.strip() if name2.strip() else "2人目",
                gender=g2, birth_date=bd2,
                birth_time=time2 if time2 else None,
                birth_place=place2 if place2 else None,
                blood_type=blood2 if blood2 != "不明" else None,
            )
            if "aisho_relationship" not in st.session_state:
                st.session_state.aisho_relationship = "love"
            st.session_state.page = "aisho_loading"
            st.rerun()

    render_gold_divider()

    # チーム分析への導線
    st.markdown('<div style="text-align:center; color:#8A8478; font-size:0.85em; margin:5px 0;">3人以上のチーム全体を分析したい場合はこちら↓</div>', unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns([1, 2, 1])
    with col_t2:
        if st.button("👥 チーム分析", key="btn_goto_team"):
            st.session_state.page = "team_input"
            st.rerun()

    if st.button("← 戻る", key="btn_back_aisho"):
        st.session_state.page = "top"
        st.rerun()


# ============================================================
# 相性占い: ローディング + 鑑定生成
# ============================================================
def render_aisho_loading_page():
    """相性鑑定: 2人分の計算 + 相性鑑定生成（関係性対応版）"""
    from core.sanmei import calculate_sanmei
    from core.western import calculate_western
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.ziwei import calculate_ziwei
    from core.models import DivinationBundle
    from core.tarot import draw_tarot
    from ai.interpreter import generate_aisho_reading
    from core.aisho_scoring import RELATIONSHIP_CATEGORIES

    person1 = st.session_state.aisho_person1
    person2 = st.session_state.aisho_person2
    relationship = st.session_state.get("aisho_relationship", "love")
    rel_cat = RELATIONSHIP_CATEGORIES.get(relationship, RELATIONSHIP_CATEGORIES['love'])

    render_star_deco("✦")
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.5em;">✦ ふたりの星を読んでいます…</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="text-align:center; color:#8A8478; font-size:0.9em;">{rel_cat["icon"]} {rel_cat["label"]}</div>',
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

        st.write(f"✧ {rel_cat['label']}の相性を分析中…")
        aisho_result = generate_aisho_reading(bundle1, bundle2, relationship)
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
    """相性鑑定 結果表示（関係性対応版）"""
    from ui.components import render_aisho_result
    from core.aisho_scoring import RELATIONSHIP_CATEGORIES

    bundle1 = st.session_state.aisho_bundle1
    bundle2 = st.session_state.aisho_bundle2
    result = st.session_state.aisho_result
    relationship = st.session_state.get("aisho_relationship", "love")
    rel_cat = RELATIONSHIP_CATEGORIES.get(relationship, RELATIONSHIP_CATEGORIES['love'])

    render_star_deco("✦")
    n1 = bundle1.person.name or "1人目"
    n2 = bundle2.person.name or "2人目"
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.4em;">{n1} × {n2}</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="text-align:center; color:#8A8478; font-size:0.9em; margin:-5px 0 10px;">{rel_cat["icon"]} {rel_cat["label"]}</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    render_aisho_result(bundle1, bundle2, result, relationship)

    render_gold_divider()

    # 共有ボタン — 結果のすぐ下
    _ai_title = f"{n1} × {n2} — {_REL_LABELS.get(relationship, '相性鑑定')}"
    _d1 = bundle1.person.birth_date
    _d2 = bundle2.person.birth_date
    _ai_subtitle = f"{_d1.year}/{_d1.month}/{_d1.day} × {_d2.year}/{_d2.month}/{_d2.day}"
    _ai_text = _build_share_text(_ai_title, _ai_subtitle, result.get("headline", ""), result.get("reading", ""), result.get("closing", ""))
    _ai_pdf = _build_pdf_html(_ai_title, _ai_subtitle, result.get("headline", ""), result.get("reading", ""), result.get("closing", ""))
    _ai_digest = _build_share_digest(_ai_title, result.get("headline", ""), result.get("closing", ""))
    _render_share_buttons(_ai_text, "aisho", _ai_pdf, _ai_digest)

    render_gold_divider()

    # くろたんに相性の個別質問
    _render_aisho_chat(bundle1, bundle2, result)

    render_gold_divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✦ もう一組鑑定する", key="btn_aisho_again"):
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
<div style="text-align:center; color:#8A8478; font-size:0.9em; margin-bottom:10px;">
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
        saved_gender = st.session_state.get("_saved_gender", "男性")
        gender_options = ["男性", "女性", "その他"]
        gender_idx = gender_options.index(saved_gender) if saved_gender in gender_options else 0
        st.radio("性別", options=gender_options, index=gender_idx, horizontal=True, key="tarot_gender")
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
<div style="text-align:center; color:#BFA350; font-size:1.1em; margin-bottom:8px;">
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
<div style="color:#8A8478; font-size:0.8em; text-align:center; margin-top:-10px;">
例: 転職すべきか / 今の恋人との未来 / 今年の運勢 / AかBか
</div>
""", unsafe_allow_html=True)

    render_gold_divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔮 くろたんに相談する", key="btn_tarot_deepen"):
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
            t_gender = st.session_state.get("tarot_gender", st.session_state.get("_saved_gender", "男性"))
            st.session_state.tarot_person = PersonInput(
                birth_date=birth_date,
                name=t_name if t_name else None,
                gender=t_gender,
            )
            # 名前をキーにデータを記憶
            _save_person(t_name, saved_year, saved_month, saved_day, gender=t_gender)

            st.session_state.tarot_question = q
            st.session_state.tarot_deepen_history = []
            # 前回のbundleと深掘りデータをクリア（新しい相談者用に再計算させる）
            st.session_state.pop("tarot_bundle", None)
            st.session_state.pop("_deepen_data_0", None)
            st.session_state.pop("_deepen_data_1", None)
            st.session_state.page = "tarot_deepen"
            st.rerun()

    if st.button("← 戻る", key="btn_back_tarot_input"):
        st.session_state.page = "top"
        st.rerun()


def render_tarot_deepen_page():
    """対話型タロット: くろたんが質問を深掘り"""
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
        '<div class="uranai-title" style="font-size:1.3em;">くろたんからの質問</div>',
        unsafe_allow_html=True
    )

    render_gold_divider()

    # 元の質問を表示
    st.markdown(f"""
<div style="text-align:center; color:#8A8478; font-size:0.9em; margin-bottom:15px;">
あなたの問い: 「{question}」
</div>
""", unsafe_allow_html=True)

    # 過去の深掘りを表示
    for h in history:
        st.markdown(f"""
<div style="background:rgba(201,168,76,0.1); border-left:3px solid #BFA350; padding:10px 15px; margin:8px 0; border-radius:0 6px 6px 0;">
<div style="color:#BFA350; font-size:0.85em;">🔮 くろたん</div>
<div style="color:#F0EBE0; font-size:0.95em; margin:4px 0;">{h['empathy']}</div>
<div style="color:#F0EBE0; font-size:0.95em; font-weight:bold;">{h['follow_up']}</div>
</div>
<div style="background:rgba(155,143,196,0.1); border-left:3px solid #8A8478; padding:10px 15px; margin:8px 0 15px; border-radius:0 6px 6px 0;">
<div style="color:#8A8478; font-size:0.85em;">🙋 あなた</div>
<div style="color:#F0EBE0; font-size:0.95em;">{h['answer']}</div>
</div>
""", unsafe_allow_html=True)

    # 深掘りが2回未満ならAIに質問を生成してもらう
    if len(history) < 2:
        # コンテキスト構築
        ctx = "\n".join(f"Q: {h['follow_up']}\nA: {h['answer']}" for h in history)

        if f"_deepen_data_{len(history)}" not in st.session_state:
            with st.spinner("くろたんが考え中…"):
                bundle = st.session_state.get("tarot_bundle")
                deepen_data = generate_deepen_question(question, ctx, bundle=bundle)
                st.session_state[f"_deepen_data_{len(history)}"] = deepen_data
        else:
            deepen_data = st.session_state[f"_deepen_data_{len(history)}"]

        # くろたんの質問を表示
        st.markdown(f"""
<div style="background:rgba(201,168,76,0.1); border-left:3px solid #BFA350; padding:10px 15px; margin:8px 0; border-radius:0 6px 6px 0;">
<div style="color:#BFA350; font-size:0.85em;">🔮 くろたん</div>
<div style="color:#F0EBE0; font-size:0.95em; margin:4px 0;">{deepen_data.get('empathy', '')}</div>
<div style="color:#F0EBE0; font-size:0.95em; font-weight:bold;">{deepen_data.get('follow_up', '')}</div>
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
<div style="text-align:center; color:#BFA350; font-size:0.95em; margin:10px 0;">
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
    color: #BFA350; font-size: 0.85em; margin-bottom: 6px; font-family: sans-serif;
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
    background: linear-gradient(135deg, #1A1A1A, #222222, #1A1A1A);
    border: 2px solid #BFA350; display: flex; align-items: center;
    justify-content: center; border-radius: 8px;
  }}
  .card-back span {{ color: #BFA350; font-size: 1.8em; letter-spacing: 5px; }}
  .card-front {{
    transform: rotateY(180deg); border: 2px solid #BFA350;
    border-radius: 8px; background: #1A1A1A;
  }}
  .card-front img {{ width: 100%; height: 80%; object-fit: contain; background: #f5f0e0; }}
  .card-info {{
    padding: 4px; text-align: center; font-family: sans-serif;
  }}
  .card-info .name {{ color: #BFA350; font-size: 0.85em; font-weight: bold; }}
  .card-info .sub {{ color: #8A8478; font-size: 0.7em; }}
  .tap-hint {{
    color: #BFA350; font-size: 0.8em; text-align: center;
    margin-top: 6px; font-family: sans-serif; animation: blink 2s infinite;
  }}
  @keyframes blink {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}
  .done-msg {{
    text-align: center; color: #BFA350; font-size: 1.1em;
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
      '<div class="sub" style="color:' + (card.pos_text === '逆位置' ? '#D4837A' : '#BFA350') + ';">' + card.pos_text + '</div></div>';
  }} else {{
    // 小アルカナ: 画像なしの場合スートシンボル＋カード名を表示
    const sym = card.suit_symbol || '✦';
    const rotateStyle = card.pos_text === '逆位置' ? 'transform:rotate(180deg);' : '';
    front.innerHTML = '<div style="width:100%;height:80%;background:linear-gradient(135deg,#1A1A1A,#222222);display:flex;flex-direction:column;align-items:center;justify-content:center;' + rotateStyle + '">' +
      '<div style="font-size:2.5em;margin-bottom:8px;">' + sym + '</div>' +
      '<div style="color:#BFA350;font-size:0.9em;font-weight:bold;">' + card.name + '</div>' +
      '</div>' +
      '<div class="card-info"><div class="name">' + card.name + '</div>' +
      '<div class="sub">' + card.name_en + '</div>' +
      '<div class="sub" style="color:' + (card.pos_text === '逆位置' ? '#D4837A' : '#BFA350') + ';">' + card.pos_text + '</div></div>';
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
      document.querySelector('.done-btn').style.background = '#8A8478';
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
<div style="text-align:center; color:#8A8478; font-size:0.85em; margin:10px 0;">
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
<div style="text-align:center; color:#8A8478; font-size:0.9em; margin-bottom:15px;">
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
                f'<div style="text-align:center; color:#BFA350; font-size:0.85em; margin-bottom:5px;">{pos_name}</div>',
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
<div style="text-align:center; font-size:1.2em; color:#BFA350; font-weight:bold; margin:15px 0;">
「{headline}」
</div>
""", unsafe_allow_html=True)

    if reading:
        st.markdown(f"""
<div style="line-height:2.0; font-size:0.95em; color:#F0EBE0; padding:10px 5px;">
{reading}
</div>
""", unsafe_allow_html=True)

    if closing:
        st.markdown(f"""
<div style="text-align:center; color:#8A8478; font-style:italic; margin:20px 0; font-size:0.95em;">
— {closing}
</div>
""", unsafe_allow_html=True)

    render_gold_divider()

    # 共有ボタン — 結果のすぐ下
    _tr_title = f"{name}さんへ — タロット鑑定" if name else "タロット鑑定"
    _tr_subtitle = f"質問: 「{question}」 / {spread_info['spread_name']}"
    _card_names = " / ".join([f"{c.card_name}{'(R)' if c.is_reversed else ''}" for c in cards])
    _tr_reading = f"カード: {_card_names}\n\n{reading}" if reading else f"カード: {_card_names}"
    _tr_text = _build_share_text(_tr_title, _tr_subtitle, headline, _tr_reading, closing)
    _tr_pdf = _build_pdf_html(_tr_title, _tr_subtitle, headline, _tr_reading, closing)
    _tr_digest = _build_share_digest(_tr_title, headline, closing)
    _render_share_buttons(_tr_text, "tarot", _tr_pdf, _tr_digest)

    render_gold_divider()

    # くろたんに追加質問チャット
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
    """くろたんへの追加質問チャット — 毎回1枚カードを引いて回答"""
    from ai.interpreter import _format_all_data_summary, SYSTEM_PROMPT_BASE, _call_api_text
    from core.tarot import draw_tarot

    st.markdown("""
<div style="text-align:center; margin:15px 0 8px;">
<span style="color:#BFA350; font-size:1.05em; font-weight:bold;">🔮 くろたんに聞く</span><br>
<span style="color:#8A8478; font-size:0.8em;">追加の質問ごとに1枚カードを引いてお答えします</span>
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
<span style="color:#BFA350; font-size:1.05em; font-weight:bold;">🔮 くろたんに聞く</span><br>
<span style="color:#8A8478; font-size:0.8em;">{name}さんの命式について、何でも聞いてください</span>
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
            with st.spinner("くろたんが考え中…"):
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
<span style="color:#D4837A; font-size:1.05em; font-weight:bold;">✦ くろたんに聞く</span><br>
<span style="color:#8A8478; font-size:0.8em;">{n1}さんと{n2}さんの相性について、何でも聞いてください</span>
</div>
""", unsafe_allow_html=True)

    if "aisho_chat_history" not in st.session_state:
        st.session_state.aisho_chat_history = []

    for chat in st.session_state.aisho_chat_history:
        with st.chat_message("user", avatar="🙋"):
            st.write(chat["question"])
        with st.chat_message("assistant", avatar="✦"):
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

        with st.chat_message("assistant", avatar="✦"):
            with st.spinner("くろたんが考え中…"):
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
<span style="color:#BFA350; font-size:1.05em; font-weight:bold;">🔮 くろたんに聞く</span><br>
<span style="color:#8A8478; font-size:0.8em;">{name}さんの命式について自由に質問</span>
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
            with st.spinner("くろたんが考え中…"):
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
<span style="color:#BFA350; font-size:1.05em; font-weight:bold;">🔮 くろたんに聞く</span><br>
<span style="color:#8A8478; font-size:0.8em;">{name}さんの{theme_label}についてもっと詳しく</span>
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
            with st.spinner("くろたんが考え中…"):
                try:
                    answer = _call_api_text(SYSTEM_PROMPT_BASE, prompt, max_tokens=1000)
                except Exception:
                    answer = "ごめんね、今ちょっと集中できなくて…もう一度聞いてもらえる？"
            st.write(answer)

        st.session_state[chat_key].append({
            "question": follow_up,
            "answer": answer,
        })


# ============================================================
# チーム分析: 入力画面
# ============================================================
TEAM_TYPES = {
    'workplace': {'label': '現場チーム', 'icon': '🏗'},
    'organization': {'label': '組織', 'icon': '🏢'},
    'friends': {'label': '仲間', 'icon': '🍻'},
    'family': {'label': '家族', 'icon': '👨‍👧'},
    'other': {'label': 'その他', 'icon': '📋'},
}


def render_team_input_page():
    """チーム分析: メンバー選択画面"""
    render_star_deco("👥")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">チーム分析</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uranai-subtitle">～ チーム全体のバランスを可視化する ～</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    db = _load_people_db()
    fdb = _load_folders_db()

    # メンバー選択
    st.markdown('<div style="color:#BFA350; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">✦ メンバーを選択</div>', unsafe_allow_html=True)

    # フォルダから一括追加
    if fdb:
        folder_names = list(fdb.keys())
        sel_folder = st.selectbox("フォルダから一括追加", options=["（選択しない）"] + folder_names, key="team_folder_sel")
        if sel_folder != "（選択しない）" and sel_folder in fdb:
            folder_members = fdb[sel_folder]
            if st.button(f"📂 「{sel_folder}」の全員を追加", key="btn_team_folder_add"):
                if "team_selected_members" not in st.session_state:
                    st.session_state.team_selected_members = set()
                for m in folder_members:
                    if m in db:
                        st.session_state.team_selected_members.add(m)
                st.rerun()

    # 個別選択（チェックボックス）
    if "team_selected_members" not in st.session_state:
        st.session_state.team_selected_members = set()

    if db:
        st.markdown('<div style="color:#8A8478; font-size:0.85em; margin:8px 0;">顧客リストから個別選択:</div>', unsafe_allow_html=True)
        for name in sorted(db.keys()):
            is_checked = name in st.session_state.team_selected_members
            if st.checkbox(name, value=is_checked, key=f"team_cb_{name}"):
                st.session_state.team_selected_members.add(name)
            else:
                st.session_state.team_selected_members.discard(name)

    selected = st.session_state.team_selected_members
    st.markdown(f'<div style="color:#D4B96A; font-size:0.9em; margin:10px 0;">選択中: {len(selected)}名</div>', unsafe_allow_html=True)

    render_gold_divider()

    # チーム種類の選択
    st.markdown('<div style="color:#BFA350; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">✦ チームの種類</div>', unsafe_allow_html=True)
    team_type = st.session_state.get("team_type", "workplace")
    cols = st.columns(len(TEAM_TYPES))
    for i, (key, tt) in enumerate(TEAM_TYPES.items()):
        with cols[i]:
            if st.button(f"{tt['icon']} {tt['label']}", key=f"btn_tt_{key}", use_container_width=True):
                st.session_state.team_type = key
                st.rerun()
    sel_tt = TEAM_TYPES.get(team_type, TEAM_TYPES['workplace'])
    st.markdown(f'<div style="text-align:center; color:#8A8478; font-size:0.85em; margin:5px 0;">{sel_tt["icon"]} {sel_tt["label"]}</div>', unsafe_allow_html=True)

    render_gold_divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("👥 チームを分析する", key="btn_team_start"):
            if len(selected) < 2:
                st.error("2名以上を選択してください。")
                return
            st.session_state.page = "team_loading"
            st.rerun()

    if st.button("← 戻る", key="btn_back_team"):
        st.session_state.page = "aisho_input"
        st.rerun()


# ============================================================
# チーム分析: ローディング + 計算
# ============================================================
def render_team_loading_page():
    """チーム分析: 全メンバーの計算 + AI診断生成"""
    from core.sanmei import calculate_sanmei
    from core.western import calculate_western
    from core.kyusei import calculate_kyusei
    from core.numerology import calculate_numerology
    from core.ziwei import calculate_ziwei
    from core.models import DivinationBundle
    from core.tarot import draw_tarot
    from core.bansho_energy import get_energy_band, ENERGY_BAND_DETAIL, HONNOU_MAP

    db = _load_people_db()
    selected = st.session_state.get("team_selected_members", set())
    team_type_key = st.session_state.get("team_type", "workplace")
    team_type = TEAM_TYPES.get(team_type_key, TEAM_TYPES['workplace'])

    render_star_deco("👥")
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.5em;">👥 チームを分析中…</div>',
        unsafe_allow_html=True
    )

    bundles = []
    with st.status("✦ 全メンバーを計算中…", expanded=True) as status:
        for name in sorted(selected):
            if name not in db:
                continue
            p = db[name]
            try:
                person = PersonInput(
                    name=name,
                    gender=p.get("gender", ""),
                    birth_date=date(p["year"], p["month"], p["day"]),
                    birth_time=p.get("time") or None,
                    birth_place=p.get("place") or None,
                    blood_type=p.get("blood") if p.get("blood") != "不明" else None,
                )
                st.write(f"✧ {name}さんを計算中…")
                s = calculate_sanmei(person)
                w = calculate_western(person)
                k = calculate_kyusei(person)
                n = calculate_numerology(person)
                t = draw_tarot(1, major_only=True)[0]
                z = calculate_ziwei(person)
                bundle = DivinationBundle(
                    person=person, sanmei=s, western=w, kyusei=k,
                    numerology=n, tarot=t, ziwei=z,
                    has_birth_time=person.birth_time is not None,
                    has_blood_type=person.blood_type is not None,
                )
                bundles.append(bundle)
            except Exception as ex:
                st.write(f"⚠ {name}さんの計算でエラー: {ex}")

        st.write("✧ チーム分析を集計中…")

        # チーム統計を計算
        energies = []
        honnou_totals = {"守備": 0, "表現": 0, "魅力": 0, "攻撃": 0, "学習": 0}
        tenchusatsu_calendar = {}

        for b in bundles:
            e = b.sanmei.bansho_energy
            if e:
                energies.append((b.person.name, e.total_energy, e.energy_type, e.top_honnou, e.second_honnou))
                for h, s_val in e.honnou_ranking:
                    honnou_totals[h] = honnou_totals.get(h, 0) + s_val
            # 天中殺年
            tc_years = b.sanmei.tenchusatsu_years or []
            for y in tc_years:
                if 2026 <= y <= 2030:
                    tenchusatsu_calendar.setdefault(y, []).append(b.person.name)

        avg_energy = sum(e[1] for e in energies) // len(energies) if energies else 0
        max_e = max(energies, key=lambda x: x[1]) if energies else ("", 0)
        min_e = min(energies, key=lambda x: x[1]) if energies else ("", 0)
        max_diff = max_e[1] - min_e[1] if energies else 0

        # 五本能バランス（%）
        total_honnou = sum(honnou_totals.values()) or 1
        honnou_pcts = {h: round(v / total_honnou * 100) for h, v in honnou_totals.items()}
        missing = [h for h, pct in honnou_pcts.items() if pct < 5]

        # AI鑑定文を生成
        st.write("✧ くろたんがチーム診断文を作成中…")
        team_result = _generate_team_reading(
            bundles, team_type, energies, avg_energy, max_diff,
            max_e, min_e, honnou_pcts, missing, tenchusatsu_calendar
        )

        status.update(label="✦ チーム分析完了 ✦", state="complete")

    st.session_state.team_bundles = bundles
    st.session_state.team_energies = energies
    st.session_state.team_avg_energy = avg_energy
    st.session_state.team_max_diff = max_diff
    st.session_state.team_max_e = max_e
    st.session_state.team_min_e = min_e
    st.session_state.team_honnou_pcts = honnou_pcts
    st.session_state.team_missing = missing
    st.session_state.team_tc_calendar = tenchusatsu_calendar
    st.session_state.team_result = team_result
    st.session_state.page = "team_result"
    st.rerun()


def _generate_team_reading(bundles, team_type, energies, avg_energy, max_diff,
                           max_e, min_e, honnou_pcts, missing, tc_calendar):
    """チーム分析のAI鑑定文を生成"""
    from ai.interpreter import _get_client, _parse_json_response
    from google.genai import types

    member_lines = []
    for name, energy, etype, h1, h2 in energies:
        member_lines.append(f"- {name}: エネルギー{energy}（{etype}）, 第1本能={h1}, 第2本能={h2}")
    member_data = "\n".join(member_lines)

    tc_lines = []
    for y in sorted(tc_calendar.keys()):
        members = "、".join(tc_calendar[y])
        tc_lines.append(f"- {y}年: {members}が天中殺")
    tc_text = "\n".join(tc_lines) if tc_lines else "（2026〜2030年に天中殺メンバーなし）"

    honnou_text = " / ".join(f"{h}{pct}%" for h, pct in honnou_pcts.items())
    missing_text = "、".join(missing) if missing else "なし"

    system_prompt = f"""あなたは「占いモンスターくろたん」。チーム分析の専門家。
複数人のエネルギー指数・五本能・天中殺データを基に、チーム全体の診断を行う。

【鑑定の原則】
1. チームの強みを最初に明確にする
2. 弱点は「補い方」とセットで提示する
3. エネルギー差が大きいメンバー間の注意点を具体的に指摘する
4. 誰が何を担当すべきかの役割分担を提案する
5. 天中殺のタイミングを考慮した年間戦略を提案する
6. 「このチームだからこそできること」をポジティブに語る
7. 断定口調で語る。"""

    user_prompt = f"""【チーム情報】
チーム種類: {team_type['icon']} {team_type['label']}
メンバー数: {len(energies)}名

【メンバーデータ】
{member_data}

【チーム統計】
- 平均エネルギー: {avg_energy}
- 最大エネルギー差: {max_diff}（{max_e[0]} {max_e[1]} ↔ {min_e[0]} {min_e[1]}）
- 五本能バランス: {honnou_text}
- 欠落本能: {missing_text}
- 天中殺カレンダー:
{tc_text}

以上のデータを基に、チーム総合診断を行ってください。
2,000〜3,000文字。

出力はJSON:
{{"headline": "チームの特徴を一言で（15〜30文字）", "reading": "チーム診断本文（2,000〜3,000文字）", "closing": "チームへの締めの一言（30〜60文字）"}}"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=5000 + 4096,
                temperature=0.9,
                thinking_config=types.ThinkingConfig(thinking_budget=4096),
            ),
        )
        text = response.text or ""
        result = _parse_json_response(text)
        if result and result.get("reading"):
            return result
    except Exception as ex:
        print(f"[チーム分析] AI生成エラー: {ex}")

    return {
        "headline": f"{len(energies)}名のチーム分析",
        "reading": f"チーム平均エネルギー: {avg_energy}\n最大差: {max_diff}\n五本能: {honnou_text}",
        "closing": "チームの強みを活かして進め。",
    }


# ============================================================
# チーム分析: 結果画面
# ============================================================
def render_team_result_page():
    """チーム分析の結果表示"""
    from core.bansho_energy import get_energy_percent

    bundles = st.session_state.get("team_bundles", [])
    energies = st.session_state.get("team_energies", [])
    avg_energy = st.session_state.get("team_avg_energy", 0)
    max_diff = st.session_state.get("team_max_diff", 0)
    max_e = st.session_state.get("team_max_e", ("", 0))
    min_e = st.session_state.get("team_min_e", ("", 0))
    honnou_pcts = st.session_state.get("team_honnou_pcts", {})
    missing = st.session_state.get("team_missing", [])
    tc_calendar = st.session_state.get("team_tc_calendar", {})
    result = st.session_state.get("team_result", {})

    render_star_deco("👥")
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.4em;">👥 チーム分析結果</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="text-align:center; color:#8A8478; font-size:0.9em;">{len(energies)}名 / 平均エネルギー {avg_energy}</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    # --- エネルギーマップ ---
    st.markdown('<div style="color:#BFA350; font-weight:bold; margin:12px 0 8px; font-size:1.1em;">⚡ チームエネルギーマップ</div>', unsafe_allow_html=True)
    for name, energy, etype, h1, h2 in sorted(energies, key=lambda x: x[1], reverse=True):
        pct = get_energy_percent(energy)
        st.markdown(f"""
<div style="display:flex; align-items:center; margin:4px 0; font-size:0.88em;">
<span style="color:#D4B96A; min-width:80px;">{name}</span>
<span style="color:#BFA350; font-weight:bold; min-width:40px;">{energy}</span>
<div style="flex:1; background:#222; border-radius:4px; height:16px; margin:0 8px; overflow:hidden;">
<div style="width:{pct}%; height:100%; background:linear-gradient(90deg,#BFA350,#D4B96A); border-radius:4px;"></div>
</div>
<span style="color:#8A8478; font-size:0.8em;">{etype}</span>
</div>""", unsafe_allow_html=True)

    if max_diff > 0:
        st.markdown(f'<div style="text-align:center; color:#8A8478; font-size:0.85em; margin:8px 0;">最大差: {max_diff}（{max_e[0]} ↔ {min_e[0]}）</div>', unsafe_allow_html=True)

    render_gold_divider()

    # --- 五本能バランス ---
    st.markdown('<div style="color:#BFA350; font-weight:bold; margin:12px 0 8px; font-size:1.1em;">🎯 チーム五本能バランス</div>', unsafe_allow_html=True)
    honnou_colors = {"守備": "#7CB87C", "表現": "#D4837A", "魅力": "#D4B96A", "攻撃": "#BFA350", "学習": "#7CA3B8"}
    for h, pct in honnou_pcts.items():
        color = honnou_colors.get(h, "#BFA350")
        bar_w = max(2, pct)
        st.markdown(f"""
<div style="display:flex; align-items:center; margin:3px 0; font-size:0.88em;">
<span style="color:{color}; min-width:55px;">{h}</span>
<div style="flex:1; background:#222; border-radius:4px; height:14px; margin:0 8px; overflow:hidden;">
<div style="width:{bar_w}%; height:100%; background:{color}; border-radius:4px;"></div>
</div>
<span style="color:#8A8478; min-width:35px;">{pct}%</span>
</div>""", unsafe_allow_html=True)

    if missing:
        st.markdown(f'<div style="color:#C47A6A; font-size:0.85em; margin:8px 0;">⚠ チームの弱点: {", ".join(missing)}が不足</div>', unsafe_allow_html=True)

    render_gold_divider()

    # --- 天中殺カレンダー ---
    if tc_calendar:
        st.markdown('<div style="color:#BFA350; font-weight:bold; margin:12px 0 8px; font-size:1.1em;">📅 天中殺カレンダー</div>', unsafe_allow_html=True)
        for y in sorted(tc_calendar.keys()):
            members = "、".join(tc_calendar[y])
            st.markdown(f'<div style="color:#8A8478; font-size:0.88em; margin:2px 0;">{y}年: <span style="color:#C47A6A;">{members}</span> が天中殺</div>', unsafe_allow_html=True)
        render_gold_divider()

    # --- AI鑑定文 ---
    headline = result.get("headline", "")
    reading = result.get("reading", "")
    closing = result.get("closing", "")

    st.markdown(f"""<div class="divination-card" style="border-color:#BFA350;">
<div class="card-header" style="color:#BFA350;">👥 くろたんのチーム診断</div>
<div style="text-align:center; margin:12px 0;">
<span style="font-size:1.2em; color:#D4B96A; font-weight:bold;">「{headline}」</span>
</div>
<div class="reading-text" style="line-height:2.0; white-space:pre-wrap;">{reading}</div>
<div class="gold-divider"></div>
<div style="text-align:center; margin-top:14px; font-size:1.05em; color:#BFA350; font-style:italic; line-height:1.8;">
✦ {closing} ✦
</div>
</div>""", unsafe_allow_html=True)

    render_gold_divider()

    # 共有ボタン
    _tm_title = f"チーム分析結果（{len(energies)}名）"
    _tm_members = "、".join([e[0] for e in energies])
    _tm_subtitle = f"メンバー: {_tm_members}"
    _tm_text = _build_share_text(_tm_title, _tm_subtitle, headline, reading, closing)
    _tm_pdf = _build_pdf_html(_tm_title, _tm_subtitle, headline, reading, closing)
    _tm_digest = _build_share_digest(_tm_title, headline, closing)
    _render_share_buttons(_tm_text, "team", _tm_pdf, _tm_digest)

    render_gold_divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👥 別のチームを分析", key="btn_team_again"):
            st.session_state.team_selected_members = set()
            st.session_state.page = "team_input"
            st.rerun()
    with col2:
        if st.button("✧ TOPに戻る ✧", key="btn_team_top"):
            st.session_state.page = "top"
            st.rerun()


# ============================================================
# 開運アドバイス
# ============================================================

def render_kaiyun_input_page():
    """開運アドバイス: 人物選択 → 日運・月運・年運・大運を表示"""
    from core.sanmei import calculate_sanmei, TENCHUSATSU_JUNISHI

    render_star_deco("🌟")
    st.markdown(
        '<div class="uranai-title" style="font-size:1.5em;">開運アドバイス</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uranai-subtitle">～ 今日の運勢から10年運まで ～</div>',
        unsafe_allow_html=True
    )
    render_gold_divider()

    # --- ひでさん固定オプション ---
    use_hidesan = st.checkbox(
        "ひでさんに固定する",
        value=st.session_state.get("kaiyun_use_hidesan", False),
        key="kaiyun_use_hidesan",
    )

    if use_hidesan:
        st.markdown(
            '<div style="color:#BFA350; font-size:1.1em; font-weight:bold; margin:10px 0 5px;">'
            '✦ ひでさん（固定）</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="color:#8A8478; font-size:0.85em; margin:0 0 10px;">'
            '1977/5/24 男性</div>',
            unsafe_allow_html=True,
        )
    else:
        # 顧客リストから選択（ボタン一覧形式）
        _render_people_quick_select()

        saved_name = st.session_state.get("kaiyun_name", "")
        saved_gender = st.session_state.get("kaiyun_gender", "男性")
        saved_year = st.session_state.get("kaiyun_y", 1990)
        saved_month = st.session_state.get("kaiyun_m", 5)
        saved_day = st.session_state.get("kaiyun_d", 15)

        name = st.text_input("お名前", value=saved_name, placeholder="例: ひでさん", key="kaiyun_name")
        gender_options = ["男性", "女性", "その他"]
        gender_idx = gender_options.index(saved_gender) if saved_gender in gender_options else 0
        gender = st.radio("性別", options=gender_options, index=gender_idx, horizontal=True, key="kaiyun_gender")

        years = list(range(1930, date.today().year))
        year_idx = years.index(saved_year) if saved_year in years else years.index(1990)
        ca, cb, cc = st.columns(3)
        with ca:
            y = st.selectbox("年", options=years, index=year_idx, key="kaiyun_y")
        with cb:
            m = st.selectbox("月", options=list(range(1, 13)), index=max(0, saved_month - 1), key="kaiyun_m")
        with cc:
            d = st.selectbox("日", options=list(range(1, 32)), index=max(0, saved_day - 1), key="kaiyun_d")

    render_gold_divider()

    # --- 送信ボタン ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🌟 開運を見る", key="btn_kaiyun_go"):
            if use_hidesan:
                name = "ひでさん"
                gender = "男性"
                y, m, d = 1977, 5, 24
            else:
                name = st.session_state.get("kaiyun_name", "").strip()
                gender = st.session_state.get("kaiyun_gender", "男性")
                y = st.session_state.get("kaiyun_y", 1990)
                m = st.session_state.get("kaiyun_m", 5)
                d = st.session_state.get("kaiyun_d", 15)

            if not name:
                st.warning("お名前を入力してください")
                return

            try:
                person = PersonInput(birth_date=date(y, m, d), name=name, gender=gender)
            except ValueError:
                st.error("日付が不正です。正しい年月日を選択してください。")
                return

            sanmei = calculate_sanmei(person)
            person_data = {
                "day_kan": sanmei.hi_kan,
                "year_kan": sanmei.nen_kan,
                "month_kan": sanmei.tsuki_kan,
                "month_shi": sanmei.tsuki_shi,
                "tenchusatsu": TENCHUSATSU_JUNISHI.get(sanmei.tenchusatsu, []),
                "special_kaku": sanmei.kakkyoku or "",
            }

            st.session_state.kaiyun_person = person
            st.session_state.kaiyun_sanmei = sanmei
            st.session_state.kaiyun_person_data = person_data
            st.session_state.page = "kaiyun_result"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← TOPに戻る", key="btn_kaiyun_input_back"):
        st.session_state.page = "top"
        st.rerun()


def render_kaiyun_result_page():
    """開運アドバイス結果: 4タブ（今日の運勢 / カレンダー / 月運・年運 / 大運）"""
    import calendar as cal_mod
    from datetime import timedelta
    from core.kaiyun import (
        calc_lucky_score, calc_monthly_calendar,
        generate_monthly_advice, generate_yearly_advice,
        calc_taiun, get_current_taiun,
        DAILY_KANSEI, ROKUYO_DETAIL, JUNICHOKU_DETAIL,
    )

    person = st.session_state.get("kaiyun_person")
    sanmei = st.session_state.get("kaiyun_sanmei")
    person_data = st.session_state.get("kaiyun_person_data")

    if not person or not person_data:
        st.session_state.page = "kaiyun_input"
        st.rerun()
        return

    today = date.today()
    name = person.name

    render_star_deco("🌟")
    st.markdown(
        f'<div class="uranai-title" style="font-size:1.4em;">🌟 {_html_mod.escape(name)} の開運アドバイス</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="text-align:center; color:#8A8478; font-size:0.85em;">'
        f'{person.birth_date.strftime("%Y/%m/%d")} 生 | 日干: {sanmei.hi_kan}'
        f' | {sanmei.tenchusatsu}</div>',
        unsafe_allow_html=True,
    )
    render_gold_divider()

    # --- 4タブ ---
    tab1, tab2, tab3, tab4 = st.tabs(["📅 今日の運勢", "📆 開運カレンダー", "📊 月運・年運", "🔮 大運（10年運）"])

    # ================================================================
    # Tab 1: 今日の運勢
    # ================================================================
    with tab1:
        _render_kaiyun_daily_tab(today, person_data, name)

    # ================================================================
    # Tab 2: 開運カレンダー
    # ================================================================
    with tab2:
        _render_kaiyun_calendar_tab(today, person_data)

    # ================================================================
    # Tab 3: 月運・年運
    # ================================================================
    with tab3:
        _render_kaiyun_monthly_yearly_tab(today, person_data)

    # ================================================================
    # Tab 4: 大運（10年運）
    # ================================================================
    with tab4:
        _render_kaiyun_taiun_tab(person, person_data)

    # --- 戻るボタン ---
    render_gold_divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌟 別の人を見る", key="btn_kaiyun_another"):
            st.session_state.page = "kaiyun_input"
            st.rerun()
    with col2:
        if st.button("← TOPに戻る", key="btn_kaiyun_back_top"):
            st.session_state.page = "top"
            st.rerun()


# --- Tab 1 helper ---
def _render_kaiyun_daily_tab(today, person_data, name):
    from datetime import timedelta
    from core.kaiyun import (
        calc_lucky_score, DAILY_KANSEI, ROKUYO_DETAIL, JUNICHOKU_DETAIL,
    )

    result = calc_lucky_score(today, person_data)
    score = result["score"]

    # スコアの色
    if score >= 8:
        score_color = "#BFA350"
        score_label = "最高の運気！"
    elif score >= 5:
        score_color = "#F0EBE0"
        score_label = "好調"
    else:
        score_color = "#8A8478"
        score_label = "控えめな日"

    tcs_mark = ' <span style="color:#C47A6A;">⚠ 天中殺日</span>' if result["tenchusatsu"] else ""

    # スコア表示
    bar_pct = score * 10
    st.markdown(f"""
<div style="text-align:center; margin:15px 0 5px;">
  <span style="color:#8A8478; font-size:0.85em;">{today.strftime("%Y年%m月%d日")} の運勢</span>
</div>
<div style="text-align:center; margin:5px 0;">
  <span style="color:{score_color}; font-size:2.8em; font-weight:bold;">{score}</span>
  <span style="color:#8A8478; font-size:1.2em;"> / 10</span>
</div>
<div style="text-align:center; margin:2px 0 8px;">
  <span style="color:{score_color}; font-size:1.0em; font-weight:bold;">{score_label}</span>{tcs_mark}
</div>
<div style="max-width:300px; margin:0 auto 15px; background:#222; border-radius:8px; height:12px; overflow:hidden;">
  <div style="width:{bar_pct}%; height:100%; background:linear-gradient(90deg,{score_color},{score_color}88); border-radius:8px;"></div>
</div>
""", unsafe_allow_html=True)

    # 詳細カード
    kansei_info = DAILY_KANSEI.get(result["kansei"], DAILY_KANSEI["比劫"])
    rokuyo_info = ROKUYO_DETAIL.get(result["rokuyo"], {})
    junichoku_info = JUNICHOKU_DETAIL.get(result["junichoku"], {})

    st.markdown(f"""
<div style="background:#1A1A1A; border:1px solid #2A2A2A; border-radius:10px; padding:15px; margin:10px 0;">
  <div style="display:flex; flex-wrap:wrap; gap:8px 20px; margin-bottom:10px;">
    <span style="color:#8A8478; font-size:0.85em;">日干支: <span style="color:#D4B96A;">{result["day_kanshi"]}</span></span>
    <span style="color:#8A8478; font-size:0.85em;">六曜: <span style="color:#D4B96A;">{result["rokuyo"]}</span>
      <span style="color:#555; font-size:0.8em;">({rokuyo_info.get("luck", "")})</span></span>
    <span style="color:#8A8478; font-size:0.85em;">十二直: <span style="color:#D4B96A;">{result["junichoku"]}</span>
      <span style="color:#555; font-size:0.8em;">({junichoku_info.get("luck", "")})</span></span>
  </div>
  <div style="color:#BFA350; font-size:0.95em; font-weight:bold; margin:8px 0 4px;">
    ✦ {kansei_info["theme"]}（{result["kansei"]}）
  </div>
  <div style="color:#F0EBE0; font-size:0.88em; line-height:1.7; margin:6px 0;">
    {result["advice"]}
  </div>
</div>
""", unsafe_allow_html=True)

    # 六曜・十二直の詳細
    st.markdown(f"""
<div style="background:#0A0A0A; border:1px solid #2A2A2A; border-radius:8px; padding:12px; margin:8px 0;">
  <div style="color:#8A8478; font-size:0.82em; margin:3px 0;">
    <span style="color:#D4B96A;">六曜</span> {result["rokuyo"]}: {rokuyo_info.get("advice", "")}
  </div>
  <div style="color:#8A8478; font-size:0.82em; margin:3px 0;">
    <span style="color:#D4B96A;">十二直</span> {result["junichoku"]}: {junichoku_info.get("advice", "")}
  </div>
</div>
""", unsafe_allow_html=True)

    # 天中殺警告
    if result["tenchusatsu"]:
        st.markdown("""
<div style="background:#2A1A1A; border:1px solid #C47A6A; border-radius:8px; padding:12px; margin:10px 0;">
  <span style="color:#C47A6A; font-weight:bold;">⚠ 天中殺日</span>
  <span style="color:#8A8478; font-size:0.85em;"> — 新しい決断や大きな契約は避け、既存の仕事を丁寧に進めましょう。</span>
</div>
""", unsafe_allow_html=True)

    render_gold_divider()

    # 3日間プレビュー
    st.markdown(
        '<div style="color:#BFA350; font-weight:bold; margin:10px 0 8px; font-size:0.95em;">📅 3日間の運勢</div>',
        unsafe_allow_html=True,
    )
    for offset in range(3):
        d = today + timedelta(days=offset)
        r = calc_lucky_score(d, person_data)
        s = r["score"]
        if s >= 8:
            sc = "#BFA350"
        elif s >= 5:
            sc = "#F0EBE0"
        else:
            sc = "#8A8478"
        tcs_icon = " ⚠" if r["tenchusatsu"] else ""
        label = "今日" if offset == 0 else ("明日" if offset == 1 else "明後日")
        kansei_info_d = DAILY_KANSEI.get(r["kansei"], DAILY_KANSEI["比劫"])
        bar_w = s * 10
        st.markdown(f"""
<div style="background:#1A1A1A; border:1px solid #2A2A2A; border-radius:8px; padding:10px 12px; margin:5px 0;">
  <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:4px;">
    <span style="color:#8A8478; font-size:0.82em; min-width:60px;">{label} {d.strftime("%m/%d")}</span>
    <span style="color:{sc}; font-size:1.3em; font-weight:bold;">{s}</span>
    <span style="color:#8A8478; font-size:0.78em;">{r["day_kanshi"]} {r["rokuyo"]}{tcs_icon}</span>
    <span style="color:#D4B96A; font-size:0.78em;">{kansei_info_d["theme"]}</span>
  </div>
  <div style="background:#222; border-radius:4px; height:6px; margin:6px 0 0; overflow:hidden;">
    <div style="width:{bar_w}%; height:100%; background:{sc}; border-radius:4px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)


# --- Tab 2 helper ---
def _render_kaiyun_calendar_tab(today, person_data):
    import calendar as cal_mod
    from core.kaiyun import calc_monthly_calendar, DAILY_KANSEI

    # 月セレクタ
    cal_year = st.session_state.get("kaiyun_cal_year", today.year)
    cal_month = st.session_state.get("kaiyun_cal_month", today.month)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("◀ 前月", key="btn_kaiyun_prev"):
            if cal_month == 1:
                cal_month = 12
                cal_year -= 1
            else:
                cal_month -= 1
            st.session_state.kaiyun_cal_year = cal_year
            st.session_state.kaiyun_cal_month = cal_month
            st.rerun()
    with c2:
        st.markdown(
            f'<div style="text-align:center; color:#BFA350; font-size:1.2em; font-weight:bold;">'
            f'{cal_year}年{cal_month}月</div>',
            unsafe_allow_html=True,
        )
    with c3:
        if st.button("次月 ▶", key="btn_kaiyun_next"):
            if cal_month == 12:
                cal_month = 1
                cal_year += 1
            else:
                cal_month += 1
            st.session_state.kaiyun_cal_year = cal_year
            st.session_state.kaiyun_cal_month = cal_month
            st.rerun()

    # カレンダーデータ取得
    cal_data = calc_monthly_calendar(cal_year, cal_month, person_data)
    days_data = {int(d["date"].split("-")[2]): d for d in cal_data["days"]}

    # ベスト/ワースト
    best = cal_data["best_day"]
    worst = cal_data["worst_day"]

    if best:
        best_d = best["date"].split("-")[2].lstrip("0")
        st.markdown(
            f'<div style="text-align:center; margin:8px 0; font-size:0.88em;">'
            f'<span style="color:#BFA350;">★ ベスト: {best_d}日 (スコア{best["score"]})</span>'
            f' / <span style="color:#8A8478;">▼ ワースト: {worst["date"].split("-")[2].lstrip("0")}日 (スコア{worst["score"]})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # カレンダーHTML生成
    cal = cal_mod.Calendar(firstweekday=6)  # Sunday start
    weeks = cal.monthdayscalendar(cal_year, cal_month)

    dow_labels = ["日", "月", "火", "水", "木", "金", "土"]
    dow_colors = ["#C47A6A", "#F0EBE0", "#F0EBE0", "#F0EBE0", "#F0EBE0", "#F0EBE0", "#7CA3B8"]

    html = '<div style="width:100%; overflow-x:auto;">'
    html += '<table style="width:100%; border-collapse:collapse; min-width:320px; table-layout:fixed;">'
    # ヘッダー
    html += '<tr>'
    for i, dow in enumerate(dow_labels):
        html += f'<th style="color:{dow_colors[i]}; font-size:0.75em; padding:4px 2px; text-align:center; border-bottom:1px solid #2A2A2A;">{dow}</th>'
    html += '</tr>'

    for week in weeks:
        html += '<tr>'
        for day_num in week:
            if day_num == 0:
                html += '<td style="padding:3px 1px; border:1px solid #1A1A1A;"></td>'
            else:
                d_info = days_data.get(day_num)
                if d_info:
                    s = d_info["score"]
                    is_tcs = d_info["tenchusatsu"]
                    if s >= 8:
                        bg = "#2A2510"
                        num_color = "#BFA350"
                    elif s >= 5:
                        bg = "#1A1A1A"
                        num_color = "#F0EBE0"
                    else:
                        bg = "#151515"
                        num_color = "#8A8478"
                    border = "border:2px solid #C47A6A;" if is_tcs else "border:1px solid #2A2A2A;"
                    is_today = (cal_year == today.year and cal_month == today.month and day_num == today.day)
                    today_mark = '<span style="color:#BFA350; font-size:0.55em;">TODAY</span>' if is_today else ""
                    best_mark = "★" if best and int(best["date"].split("-")[2]) == day_num else ""
                    html += (
                        f'<td style="background:{bg}; {border} border-radius:4px; padding:2px; text-align:center; vertical-align:top;">'
                        f'<div style="font-size:0.7em; color:{num_color}; font-weight:bold;">{day_num}</div>'
                        f'<div style="font-size:0.95em; color:{num_color}; font-weight:bold;">{s}{best_mark}</div>'
                        f'<div style="font-size:0.5em; color:#555;">{d_info["rokuyo"][:1]}</div>'
                        f'{today_mark}'
                        f'</td>'
                    )
                else:
                    html += f'<td style="padding:3px 1px; border:1px solid #1A1A1A; text-align:center;"><span style="color:#555; font-size:0.7em;">{day_num}</span></td>'
        html += '</tr>'
    html += '</table></div>'

    st.markdown(html, unsafe_allow_html=True)

    # 日別詳細（expander）
    st.markdown(
        '<div style="color:#BFA350; font-weight:bold; margin:15px 0 5px; font-size:0.9em;">📋 日別詳細</div>',
        unsafe_allow_html=True,
    )
    for d_info in cal_data["days"]:
        day_num = int(d_info["date"].split("-")[2])
        s = d_info["score"]
        tcs_icon = " ⚠" if d_info["tenchusatsu"] else ""
        kansei_info = DAILY_KANSEI.get(d_info["kansei"], DAILY_KANSEI["比劫"])
        with st.expander(f"{day_num}日  スコア{s}{tcs_icon}  {d_info['day_kanshi']} {d_info['rokuyo']} — {kansei_info['theme']}"):
            st.markdown(f"""
<div style="color:#F0EBE0; font-size:0.85em; line-height:1.6;">
{d_info["advice"]}
</div>
""", unsafe_allow_html=True)


# --- Tab 3 helper ---
def _render_kaiyun_monthly_yearly_tab(today, person_data):
    from core.kaiyun import (
        generate_monthly_advice, generate_yearly_advice, DAILY_KANSEI,
    )

    # --- 月運 ---
    st.markdown(
        '<div style="color:#BFA350; font-weight:bold; margin:10px 0 8px; font-size:1.1em;">📆 今月の運勢</div>',
        unsafe_allow_html=True,
    )
    month_adv = generate_monthly_advice(person_data, today.year, today.month)
    kansei_info_m = DAILY_KANSEI.get(month_adv["kansei"], DAILY_KANSEI["比劫"])

    tcs_month_html = ""
    if month_adv["tenchusatsu_month"]:
        tcs_month_html = """
<div style="background:#2A1A1A; border:1px solid #C47A6A; border-radius:6px; padding:8px; margin:8px 0;">
  <span style="color:#C47A6A; font-weight:bold;">⚠ 天中殺月</span>
  <span style="color:#8A8478; font-size:0.85em;"> — 新規事業・大きな決断は翌月以降に。</span>
</div>"""

    st.markdown(f"""
<div style="background:#1A1A1A; border:1px solid #2A2A2A; border-radius:10px; padding:15px; margin:8px 0;">
  <div style="color:#8A8478; font-size:0.82em; margin-bottom:6px;">
    {today.year}年{today.month}月 | 月干支: <span style="color:#D4B96A;">{month_adv["month_kanshi"]}</span>
    | 通変星: <span style="color:#D4B96A;">{month_adv["kansei"]}</span>
  </div>
  <div style="color:#BFA350; font-size:1.05em; font-weight:bold; margin:8px 0;">
    ✦ {month_adv["theme"]}
  </div>
  <div style="color:#F0EBE0; font-size:0.88em; line-height:1.7; margin:6px 0;">
    <span style="color:#D4B96A;">◎ やると良いこと:</span> {month_adv["do"]}
  </div>
  <div style="color:#F0EBE0; font-size:0.88em; line-height:1.7; margin:4px 0;">
    <span style="color:#C47A6A;">△ 注意:</span> {month_adv["dont"]}
  </div>
  {tcs_month_html}
</div>
""", unsafe_allow_html=True)

    render_gold_divider()

    # --- 年運 ---
    st.markdown(
        '<div style="color:#BFA350; font-weight:bold; margin:10px 0 8px; font-size:1.1em;">📊 今年の運勢</div>',
        unsafe_allow_html=True,
    )
    year_adv = generate_yearly_advice(person_data, today.year)

    tcs_year_html = ""
    if year_adv["tenchusatsu_year"]:
        tcs_year_html = """
<div style="background:#2A1A1A; border:1px solid #C47A6A; border-radius:6px; padding:8px; margin:8px 0;">
  <span style="color:#C47A6A; font-weight:bold;">⚠ 天中殺年</span>
  <span style="color:#8A8478; font-size:0.85em;"> — 守りと内省の年。新規の大きな決断は極力避けましょう。</span>
</div>"""

    keywords_html = " ".join(
        [f'<span style="background:#2A2510; color:#BFA350; padding:2px 8px; border-radius:12px; font-size:0.82em; margin:2px;">{kw}</span>'
         for kw in year_adv["keywords"]]
    )

    st.markdown(f"""
<div style="background:#1A1A1A; border:1px solid #2A2A2A; border-radius:10px; padding:15px; margin:8px 0;">
  <div style="color:#8A8478; font-size:0.82em; margin-bottom:6px;">
    {today.year}年 | 年干支: <span style="color:#D4B96A;">{year_adv["year_kanshi"]}</span>
    | 通変星: <span style="color:#D4B96A;">{year_adv["kansei"]}</span>
  </div>
  <div style="color:#BFA350; font-size:1.05em; font-weight:bold; margin:8px 0;">
    ✦ {year_adv["theme"]}
  </div>
  <div style="margin:8px 0;">{keywords_html}</div>
  <div style="color:#F0EBE0; font-size:0.88em; line-height:1.7; margin:6px 0;">
    <span style="color:#D4B96A;">◎ やると良いこと:</span> {year_adv["do"]}
  </div>
  <div style="color:#F0EBE0; font-size:0.88em; line-height:1.7; margin:4px 0;">
    <span style="color:#C47A6A;">△ 注意:</span> {year_adv["dont"]}
  </div>
  <div style="color:#8A8478; font-size:0.85em; line-height:1.6; margin:8px 0; padding-top:8px; border-top:1px solid #2A2A2A;">
    ⚡ {year_adv["energy_advice"]}
  </div>
  {tcs_year_html}
</div>
""", unsafe_allow_html=True)


# --- Tab 4 helper ---
def _render_kaiyun_taiun_tab(person, person_data):
    from core.kaiyun import calc_taiun, get_current_taiun, DAILY_KANSEI

    today = date.today()
    gender_str = person.gender
    birth_date = person.birth_date

    taiun_list = calc_taiun(person_data, birth_date, gender_str)
    current_taiun = get_current_taiun(taiun_list, birth_date.year, today.year)
    current_age = today.year - birth_date.year

    st.markdown(
        f'<div style="color:#BFA350; font-weight:bold; margin:10px 0 8px; font-size:1.1em;">'
        f'🔮 大運タイムライン（現在{current_age}歳）</div>',
        unsafe_allow_html=True,
    )

    # タイムライン表示
    for entry in taiun_list:
        is_current = (entry == current_taiun)
        is_tcs = entry["is_taiun_tenchusatsu"]

        if is_current:
            border_color = "#BFA350"
            bg = "#1A1A10"
            marker = "★ "
        elif is_tcs:
            border_color = "#C47A6A"
            bg = "#1A1515"
            marker = "⚠ "
        else:
            border_color = "#2A2A2A"
            bg = "#1A1A1A"
            marker = ""

        kansei_info = DAILY_KANSEI.get(entry["kansei"], DAILY_KANSEI["比劫"])
        age_range = f'{entry["start_age"]}〜{entry["end_age"]}歳'
        year_range = f'({birth_date.year + entry["start_age"]}〜{birth_date.year + entry["end_age"]}年)'

        tcs_badge = ""
        if is_tcs:
            tcs_badge = '<span style="color:#C47A6A; font-size:0.75em; margin-left:6px;">⚠天中殺</span>'

        st.markdown(f"""
<div style="background:{bg}; border-left:4px solid {border_color}; border-radius:0 8px 8px 0;
            padding:10px 12px; margin:5px 0; position:relative;">
  <div style="display:flex; align-items:center; flex-wrap:wrap; gap:4px 12px;">
    <span style="color:{border_color}; font-weight:bold; font-size:1.0em;">{marker}{entry["kanshi"]}</span>
    <span style="color:#8A8478; font-size:0.82em;">{age_range} {year_range}</span>
    {tcs_badge}
  </div>
  <div style="display:flex; flex-wrap:wrap; gap:4px 14px; margin-top:4px;">
    <span style="color:#8A8478; font-size:0.8em;">五行: <span style="color:#D4B96A;">{entry["gogyo"]}</span></span>
    <span style="color:#8A8478; font-size:0.8em;">本能: <span style="color:#D4B96A;">{entry["honnou"]}</span></span>
    <span style="color:#8A8478; font-size:0.8em;">通変星: <span style="color:#D4B96A;">{entry["kansei"]}</span></span>
    <span style="color:#8A8478; font-size:0.8em;">{kansei_info["theme"]}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # 現在の大運 詳細ボックス
    if current_taiun:
        render_gold_divider()
        ct = current_taiun
        ct_kansei = DAILY_KANSEI.get(ct["kansei"], DAILY_KANSEI["比劫"])
        ct_age = f'{ct["start_age"]}〜{ct["end_age"]}歳'
        ct_years = f'{birth_date.year + ct["start_age"]}〜{birth_date.year + ct["end_age"]}年'

        tcs_detail = ""
        if ct["is_taiun_tenchusatsu"]:
            tcs_years_str = ", ".join([str(y) for y in ct["tenchusatsu_years"]]) if ct["tenchusatsu_years"] else "期間全体"
            tcs_detail = f"""
<div style="background:#2A1A1A; border:1px solid #C47A6A; border-radius:6px; padding:8px; margin:8px 0;">
  <span style="color:#C47A6A; font-weight:bold;">⚠ 大運天中殺</span>
  <span style="color:#8A8478; font-size:0.85em;"> — この期間は天中殺の影響あり。特に {tcs_years_str} 年は注意。</span>
</div>"""

        st.markdown(f"""
<div style="background:#1A1A10; border:2px solid #BFA350; border-radius:10px; padding:15px; margin:10px 0;">
  <div style="color:#BFA350; font-size:1.05em; font-weight:bold; margin-bottom:8px;">
    ★ 現在の大運: {ct["kanshi"]}（{ct_age} / {ct_years}）
  </div>
  <div style="color:#8A8478; font-size:0.85em; margin:4px 0;">
    五行: <span style="color:#D4B96A;">{ct["gogyo"]}</span> |
    本能: <span style="color:#D4B96A;">{ct["honnou"]}</span> |
    通変星: <span style="color:#D4B96A;">{ct["kansei"]}</span>
  </div>
  <div style="color:#BFA350; font-size:0.95em; font-weight:bold; margin:10px 0 4px;">
    ✦ {ct_kansei["theme"]}
  </div>
  <div style="color:#F0EBE0; font-size:0.88em; line-height:1.7; margin:4px 0;">
    <span style="color:#D4B96A;">◎</span> {ct_kansei["do"]}
  </div>
  <div style="color:#F0EBE0; font-size:0.88em; line-height:1.7; margin:4px 0;">
    <span style="color:#C47A6A;">△</span> {ct_kansei["dont"]}
  </div>
  {tcs_detail}
</div>
""", unsafe_allow_html=True)
