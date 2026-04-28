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
# パスワード認証（緊急ブロック指令 2026-04-26）
# ============================================================
def _get_app_password() -> str | None:
    """secrets から app password を取得。未設定ならNone。"""
    try:
        if "app" in st.secrets and "password" in st.secrets["app"]:
            return st.secrets["app"]["password"]
    except Exception:
        pass
    # 後方互換: フラットな APP_PASSWORD も許容
    try:
        if "APP_PASSWORD" in st.secrets:
            return st.secrets["APP_PASSWORD"]
    except Exception:
        pass
    return None


def _legacy_password_pass() -> bool:
    """旧 APP_PASSWORD が認証通過済みか判定（UI出さない）。
    APP_PASSWORD が secrets に設定されていない場合は False（バイパス禁止）。
    Auth 経由のログインを必須にする。"""
    expected = _get_app_password()
    if not expected:
        return False
    return bool(st.session_state.get("authenticated"))


def _legacy_password_login_inline():
    """旧 APP_PASSWORD のログインUIを描画（login_page.py の旧パスワードタブから呼ぶ）。"""
    expected = _get_app_password()
    if not expected:
        st.info("APP_PASSWORD 未設定（ローカル開発モード）")
        return
    password = st.text_input(
        "パスワード", type="password", key="_legacy_password",
        placeholder="合言葉を入力", label_visibility="collapsed",
    )
    if st.button("✦ 入場する ✦", use_container_width=True, key="_legacy_login_btn"):
        if password == expected:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います")


# ============================================================
# 認証ゲート: Supabase Auth (Phase 1) または 旧 APP_PASSWORD のどちらかが通れば access OK
# 並行運用期間 (2〜3日) 後、APP_PASSWORD は撤去予定
# ============================================================
import auth as _auth_mod
from ui.login_page import render_login_page as _render_login_page

_auth_ok = _auth_mod.try_auto_login()
_legacy_ok = _legacy_password_pass()

if not (_auth_ok or _legacy_ok):
    _render_login_page(legacy_password_check_fn=_legacy_password_login_inline)
    st.stop()


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
    render_settings_page,
)

# CSSを注入
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# サイドバーにログアウトボタン (Auth または APP_PASSWORD で認証中なら表示)
if _auth_ok or st.session_state.get("authenticated"):
    with st.sidebar:
        st.markdown('<div style="color:#BFA350; font-size:0.9em; padding:6px 0;">✧ メニュー ✧</div>', unsafe_allow_html=True)
        # 認証中ユーザー名表示 (Auth 経由の場合のみ)
        _disp = _auth_mod.get_display_name()
        if _disp:
            st.markdown(
                f'<div style="color:#8A8478; font-size:0.82em; padding:2px 0 6px;">'
                f'👤 {_disp} さん</div>',
                unsafe_allow_html=True,
            )
        if st.button("🚪 ログアウト", key="_logout_btn", use_container_width=True):
            # Auth セッションクリア
            _auth_mod.logout()
            # 旧 APP_PASSWORD フラグ
            st.session_state["authenticated"] = False
            # その他セッション状態
            for _k in list(st.session_state.keys()):
                if _k not in ("_login_password", "_legacy_password"):
                    try:
                        del st.session_state[_k]
                    except Exception:
                        pass
            st.rerun()

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
elif page == "settings":
    render_settings_page()
else:
    st.session_state.page = "top"
    st.rerun()
