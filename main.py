"""
占いモンスターくろたん Phase 1a
メインエントリーポイント（Streamlit）

画面フロー: TOP → 入力 → ローディング → 裏メニュー → 鑑定生成 → 結果
起動: streamlit run main.py
"""
import os
import streamlit as st

# Streamlit Cloud: secretsからAPIキーを環境変数に設定
for _key in (
    "GEMINI_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASS",
    "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY",
    "URANAI_USER_ID",
    "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI",
    "ANTHROPIC_API_KEY", "AI_PROVIDER", "CLAUDE_MODEL",
    "AUTH_API_BASE",
):
    if not os.environ.get(_key):
        try:
            if _key in st.secrets:
                os.environ[_key] = st.secrets[_key]
        except Exception:
            pass

# ページ設定（最初に呼ぶ）
st.set_page_config(
    page_title="占いモンスターくろたん",
    page_icon="✧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# バージョン情報（リビルドが反映されたか確認用）
# - 環境変数 STREAMLIT_RUNTIME_BUILD_ID は Streamlit Cloud がビルドごとに設定
# - フォールバックでデプロイファイルの mtime を JST 表示
# - main.py だけでなく ai/interpreter.py の更新時刻も見る
#   （プロンプト更新だけpushされた場合に main.py の mtime が古いままになるバグ対策）
# ============================================================
def _get_build_info() -> str:
    bid = os.environ.get("STREAMLIT_RUNTIME_BUILD_ID")
    if bid:
        return f"build:{bid[:8]}"
    try:
        import datetime as _dt
        # チェック対象ファイル一覧（複数ファイルの最新更新時刻を採用）
        files = [__file__]
        base = os.path.dirname(os.path.abspath(__file__))
        for rel in ("ai/interpreter.py", "ai/palm_interpreter.py", "auth.py", "ui/login_page.py"):
            p = os.path.join(base, rel)
            if os.path.exists(p):
                files.append(p)
        latest_ts = max((os.path.getmtime(f) for f in files), default=0)
        # JST (UTC+9) で表示
        jst = _dt.timezone(_dt.timedelta(hours=9))
        return "JST " + _dt.datetime.fromtimestamp(latest_ts, tz=jst).strftime("%m/%d %H:%M")
    except Exception:
        return "build:?"

_BUILD_INFO = _get_build_info()

# ============================================================
# 認証ゲート: Supabase Auth (device-token 方式)
# 旧 APP_PASSWORD は 2026-04-28 に完全撤去
# ============================================================
import auth as _auth_mod
from ui.login_page import render_login_page as _render_login_page

_auth_state = _auth_mod.try_auto_login_state()

if _auth_state == "loading":
    # localStorage チェック中。JS 完了を待つため『確認中』表示してすぐ rerun。
    st.markdown(
        '<div style="text-align:center; margin-top:80px;">'
        '<div style="font-size:2.5em; color:#BFA350; letter-spacing:0.2em;">✧</div>'
        '<div style="color:#8A8478; margin-top:12px; letter-spacing:0.1em;">認証情報を確認中…</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    import time as _time_t
    _time_t.sleep(0.4)
    st.rerun()

_auth_ok = _auth_state == "ok"

if not _auth_ok:
    _render_login_page()
    st.stop()

# 認証済み → localStorage への token 保存を確実に実行（自動ログイン用）
# perform_password_login の直後に streamlit_js_eval を呼んでも、その後 st.rerun() で
# component が描画されないため JS が実行されない。ここで毎 rerun 確認することで、
# component が画面に embed されて setItem が走る。
_auth_mod.ensure_token_persisted()


from ui.styles import CUSTOM_CSS
from ui.pages import (
    render_top_page,
    render_input_page,
    render_loading_page,
    render_ura_menu_page,
    render_generating_page,
    render_generating_theme_page,
    render_theme_result_page,
    render_result_page,
    render_aisho_input_page,
    render_aisho_loading_page,
    render_aisho_result_page,
    render_team_input_page,
    render_team_loading_page,
    render_team_result_page,
    render_tarot_input_page,
    render_tarot_deepen_page,
    render_tarot_loading_page,
    render_tarot_reveal_page,
    render_tarot_generating_page,
    render_tarot_result_page,
    render_meibo_page,
    render_kaiyun_input_page,
    render_kaiyun_result_page,
    render_palm_input_page,
    render_palm_loading_page,
    render_palm_result_page,
    render_settings_page,
)

# CSSを注入
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# サイドバーにログアウトボタン
if _auth_ok:
    with st.sidebar:
        st.markdown('<div style="color:#BFA350; font-size:0.9em; padding:6px 0;">✧ メニュー ✧</div>', unsafe_allow_html=True)
        _disp = _auth_mod.get_display_name()
        if _disp:
            st.markdown(
                f'<div style="color:#8A8478; font-size:0.82em; padding:2px 0 6px;">'
                f'👤 {_disp} さん</div>',
                unsafe_allow_html=True,
            )
        if st.button("🚪 ログアウト", key="_logout_btn", use_container_width=True):
            _auth_mod.logout()
            for _k in list(st.session_state.keys()):
                try:
                    del st.session_state[_k]
                except Exception:
                    pass
            st.rerun()
        # ビルド情報（リビルドが反映されたか確認用）
        st.caption(f"🔧 {_BUILD_INFO}")

# セッション初期化
if "page" not in st.session_state:
    st.session_state.page = "top"

# 自動バックアップチェック（1セッションに1回だけ実施）
if not st.session_state.get("_auto_backup_checked"):
    st.session_state["_auto_backup_checked"] = True
    try:
        from core.backup import maybe_auto_backup
        _bk_result = maybe_auto_backup(min_interval_days=7)
        if _bk_result and _bk_result.get("ok"):
            print(f"[startup] auto backup done: {_bk_result.get('message')}")
    except Exception as _e:
        print(f"[startup] auto backup check failed: {_e}")

# ルーティング
page = st.session_state.page

if page == "top":
    render_top_page()
elif page == "input":
    render_input_page()
elif page == "loading":
    render_loading_page()
elif page == "ura_menu":
    render_ura_menu_page()
elif page == "generating":
    render_generating_page()
elif page == "generating_theme":
    render_generating_theme_page()
elif page == "theme_result":
    render_theme_result_page()
elif page == "result":
    render_result_page()
elif page == "aisho_input":
    render_aisho_input_page()
elif page == "aisho_loading":
    render_aisho_loading_page()
elif page == "aisho_result":
    render_aisho_result_page()
elif page == "team_input":
    render_team_input_page()
elif page == "team_loading":
    render_team_loading_page()
elif page == "team_result":
    render_team_result_page()
elif page == "tarot_input":
    render_tarot_input_page()
elif page == "tarot_deepen":
    render_tarot_deepen_page()
elif page == "tarot_loading":
    render_tarot_loading_page()
elif page == "tarot_reveal":
    render_tarot_reveal_page()
elif page == "tarot_generating":
    render_tarot_generating_page()
elif page == "tarot_result":
    render_tarot_result_page()
elif page == "meibo":
    render_meibo_page()
elif page == "kaiyun_input":
    render_kaiyun_input_page()
elif page == "kaiyun_result":
    render_kaiyun_result_page()
elif page == "palm_input":
    render_palm_input_page()
elif page == "palm_loading":
    render_palm_loading_page()
elif page == "palm_result":
    render_palm_result_page()
elif page == "settings":
    render_settings_page()
else:
    st.session_state.page = "top"
    st.rerun()
