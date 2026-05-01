"""
占いモンスター 認証モジュール
- 主: パスワード1個認証（ひでさん専用、Streamlit Cloud Secrets `ADMIN_LOGIN_PASSWORD`）
- 副: 旧 Supabase Auth (device-token方式) — 後方互換のため関数は残す
"""
import hashlib
import os
import platform
from typing import Optional

import requests
import streamlit as st

def _get_auth_api_base() -> str:
    """環境変数 → secrets.toml → デフォルトの順で AUTH_API_BASE を取得。
    secrets.toml が存在しなくても安全に動作。"""
    env_val = os.environ.get("AUTH_API_BASE")
    if env_val:
        return env_val
    try:
        if "AUTH_API_BASE" in st.secrets:
            return st.secrets["AUTH_API_BASE"]
    except Exception:
        # StreamlitSecretNotFoundError 等は無視
        pass
    return "https://yukyu-navi.vercel.app"


# 認証ハブ: 有給ナビの /api/auth/* を呼ぶ
AUTH_API_BASE = _get_auth_api_base()

APP_NAME = "uranai-monster"

# session_state キー
KEY_DEVICE_TOKEN = "_auth_device_token"
KEY_USER = "_auth_user"
KEY_SESSION = "_auth_session"
KEY_PROFILE = "_auth_profile"
KEY_PASSWORD_OK = "_auth_password_ok"


# ----------------------------------------------------------------------
# パスワード認証（メイン経路、ひでさん専用）
# ----------------------------------------------------------------------
def get_admin_password() -> str:
    """secrets / 環境変数から管理者パスワードを取得。未設定なら空文字。"""
    pw = os.environ.get("ADMIN_LOGIN_PASSWORD", "")
    if pw:
        return pw
    try:
        return str(st.secrets.get("ADMIN_LOGIN_PASSWORD", "")) or ""
    except Exception:
        return ""


def _password_token(password: str) -> str:
    """パスワードのハッシュをトークンとして使う（localStorage 保存用）"""
    return "pw:" + hashlib.sha256(password.encode("utf-8")).hexdigest()


def perform_password_login(password: str) -> dict:
    """パスワード一致でセッション確立。device-token として password hash を保存。"""
    expected = get_admin_password()
    if not expected:
        return {"ok": False, "error": "admin_password_not_set"}
    if password != expected:
        return {"ok": False, "error": "wrong_password"}
    token = _password_token(password)
    st.session_state[KEY_PASSWORD_OK] = True
    st.session_state[KEY_DEVICE_TOKEN] = token
    _save_token_to_browser(token)
    return {"ok": True}


# ----------------------------------------------------------------------
# HTTP API ラッパー
# ----------------------------------------------------------------------
def perform_pairing(employee_number: str, code: str, device_label: str = "") -> dict:
    """
    /api/auth/pair に POST してデバイストークンを発行。
    成功時 session_state に device_token と user を保存。
    """
    payload = {
        "employeeNumber": employee_number,
        "code": code,
        "deviceLabel": device_label or f"占いモンスター ({platform.system()})",
    }
    try:
        res = requests.post(
            f"{AUTH_API_BASE}/api/auth/pair",
            json=payload,
            timeout=15,
        )
    except requests.RequestException as e:
        return {"ok": False, "error": "network_error", "message": str(e)}

    if res.status_code == 200:
        data = res.json()
        st.session_state[KEY_DEVICE_TOKEN] = data["deviceToken"]
        st.session_state[KEY_USER] = data.get("user", {})
        # ブラウザ localStorage にも保存（永続化）
        _save_token_to_browser(data["deviceToken"])
        return {"ok": True, "user": data.get("user", {})}

    try:
        err = res.json().get("error", f"http_{res.status_code}")
    except Exception:
        err = f"http_{res.status_code}"
    return {"ok": False, "error": err}


def perform_device_login(
    device_token: Optional[str] = None,
    employee_number: Optional[str] = None,
) -> dict:
    """
    /api/auth/device-login に POST してセッション+プロフィール取得。
    - device_token を渡すと通常ログイン（path A）
    - employee_number だけ渡すと管理者/テストアカウント直接ログイン（path R）
    """
    payload = {"appName": APP_NAME}
    if device_token:
        payload["deviceToken"] = device_token
    if employee_number:
        payload["employeeNumber"] = employee_number

    if not device_token and not employee_number:
        return {"ok": False, "error": "no_token_provided"}

    try:
        res = requests.post(
            f"{AUTH_API_BASE}/api/auth/device-login",
            json=payload,
            timeout=15,
        )
    except requests.RequestException as e:
        return {"ok": False, "error": "network_error", "message": str(e)}

    if res.status_code == 200:
        data = res.json()
        st.session_state[KEY_SESSION] = data.get("session")
        st.session_state[KEY_PROFILE] = data.get("profile", {})
        # path R の場合、新規 device_token も同梱されてくる
        if data.get("deviceToken"):
            st.session_state[KEY_DEVICE_TOKEN] = data["deviceToken"]
            # 管理者ログイン経路でもブラウザに永続化
            _save_token_to_browser(data["deviceToken"])
        return {"ok": True, "data": data}

    try:
        err = res.json().get("error", f"http_{res.status_code}")
    except Exception:
        err = f"http_{res.status_code}"
    # 失効トークンならクリア
    if err in ("invalid_device", "inactive"):
        st.session_state.pop(KEY_DEVICE_TOKEN, None)
        st.session_state.pop(KEY_SESSION, None)
        st.session_state.pop(KEY_PROFILE, None)
    return {"ok": False, "error": err}


# ----------------------------------------------------------------------
# 認証状態クエリ（パスワード経路 と 旧Supabase経路 の両対応）
# ----------------------------------------------------------------------
def is_authenticated() -> bool:
    """認証済みかチェック。パスワード経路 or 旧Supabase経路 どちらでも True を返す"""
    # 新: パスワード認証フラグ
    if st.session_state.get(KEY_PASSWORD_OK):
        return True
    # 旧: Supabase Auth 経路（後方互換）
    if not st.session_state.get(KEY_SESSION):
        return False
    prof = st.session_state.get(KEY_PROFILE) or {}
    enabled = prof.get("enabled_apps") or []
    return APP_NAME in enabled


def get_profile() -> Optional[dict]:
    return st.session_state.get(KEY_PROFILE)


def get_user() -> Optional[dict]:
    return st.session_state.get(KEY_USER)


def get_display_name() -> str:
    """表示名。パスワード経路ならひでさん固定、旧Supabaseならprofileから取る"""
    user = get_user() or {}
    name = user.get("displayName", "")
    if name:
        return name
    if st.session_state.get(KEY_PASSWORD_OK):
        return "ひでさん"
    return ""


def is_admin() -> bool:
    """admin 判定。ひでさん専用なのでパスワード経路なら常に True"""
    if st.session_state.get(KEY_PASSWORD_OK):
        return True
    prof = get_profile() or {}
    return prof.get("role") == "admin"


def logout():
    """全認証関連 session_state とブラウザ localStorage をクリア"""
    for key in (KEY_DEVICE_TOKEN, KEY_USER, KEY_SESSION, KEY_PROFILE, KEY_PASSWORD_OK):
        st.session_state.pop(key, None)
    _clear_token_from_browser()


# ----------------------------------------------------------------------
# localStorage 永続化（Streamlit セッション切れても、ブラウザ閉じても保持）
# ----------------------------------------------------------------------
LS_KEY = "uranai_device_token"

# localStorage 確認の状態フラグ（session_state キー）
KEY_LS_CHECK_DONE = "_auth_ls_check_done"
KEY_LS_VALUE = "_auth_ls_value"


def _load_token_from_browser_state() -> tuple[Optional[str], bool]:
    """localStorage から token を取得。
    Returns: (token, is_loaded)
      - is_loaded=False: JS未完了。次の rerun で再試行すべき
      - is_loaded=True: 確定。token は値 or None
    """
    # 既に取得済みなら session_state から返す
    if st.session_state.get(KEY_LS_CHECK_DONE):
        return st.session_state.get(KEY_LS_VALUE), True

    try:
        from streamlit_js_eval import streamlit_js_eval
        # streamlit_js_eval は初回呼び出しで None を返し、JS 実行後に rerun で値が来る
        val = streamlit_js_eval(
            js_expressions=f"localStorage.getItem('{LS_KEY}') || ''",
            key="_palm_token_loader_v3",
        )
    except Exception:
        # ライブラリエラーは確定扱いで None
        st.session_state[KEY_LS_CHECK_DONE] = True
        st.session_state[KEY_LS_VALUE] = None
        return None, True

    if val is None:
        # JS 未完了
        return None, False

    # JS 完了。値があれば保存。"null" or 空文字列なら None
    s = str(val).strip()
    token = s if s and s != "null" else None
    st.session_state[KEY_LS_CHECK_DONE] = True
    st.session_state[KEY_LS_VALUE] = token
    return token, True


def _save_token_to_browser(token: str):
    """ブラウザ localStorage に device_token を保存"""
    try:
        from streamlit_js_eval import streamlit_js_eval
        # キーをタイムスタンプ込みでユニーク化（重複呼び出し回避）
        import time as _t
        streamlit_js_eval(
            js_expressions=f"localStorage.setItem('{LS_KEY}', '{token}'); 'saved'",
            key=f"_save_token_js_{int(_t.time() * 1000) % 1000000000}",
        )
        # session_state にも反映（次回ロード時の高速化）
        st.session_state[KEY_LS_CHECK_DONE] = True
        st.session_state[KEY_LS_VALUE] = token
    except Exception:
        pass


def _clear_token_from_browser():
    """ブラウザ localStorage から device_token を削除"""
    try:
        from streamlit_js_eval import streamlit_js_eval
        import time as _t
        streamlit_js_eval(
            js_expressions=f"localStorage.removeItem('{LS_KEY}'); 'cleared'",
            key=f"_clear_token_js_{int(_t.time() * 1000) % 1000000000}",
        )
    except Exception:
        pass
    # session_state も明示的にクリア
    st.session_state[KEY_LS_CHECK_DONE] = True
    st.session_state[KEY_LS_VALUE] = None


def try_auto_login() -> bool:
    """device_token が session_state または localStorage にあれば自動ログイン試行。
    互換性のため bool 戻り値（True=ログイン済 / False=未ログイン or 確認中）。
    確認中も含めた状態が必要な場合は try_auto_login_state() を使う。
    """
    state = try_auto_login_state()
    return state == "ok"


def try_auto_login_state() -> str:
    """自動ログイン状態を返す。
    - "ok": ログイン済み
    - "loading": localStorage 確認中（JS未完了）。呼び出し側は『認証情報確認中』を表示してすぐ rerun
    - "ng": トークン無し or 失効。ログイン画面へ
    """
    if is_authenticated():
        return "ok"

    # session_state にトークンあれば即試行
    token = st.session_state.get(KEY_DEVICE_TOKEN)

    # 無ければ localStorage から取得
    if not token:
        token, is_loaded = _load_token_from_browser_state()
        if not is_loaded:
            return "loading"
        if token:
            st.session_state[KEY_DEVICE_TOKEN] = token

    if not token:
        return "ng"

    # パスワードトークン (`pw:...`) のみを受け入れる。
    # 旧 Supabase device-token (`pw:` で始まらない) は受け入れない →
    # 過去のセッションで発行された device-token による自動ログインを完全に塞ぐ。
    if not token.startswith("pw:"):
        # 旧トークン → 即クリア + ログイン画面へ
        _clear_token_from_browser()
        return "ng"

    expected = get_admin_password()
    if not expected:
        _clear_token_from_browser()
        return "ng"
    if token != _password_token(expected):
        # パスワード変更等 → 失効
        _clear_token_from_browser()
        return "ng"

    st.session_state[KEY_PASSWORD_OK] = True
    return "ok"
