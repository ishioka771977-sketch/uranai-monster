"""
占いモンスター 認証モジュール
- 石岡組共通 Supabase Auth (device-token方式) を HTTP経由で利用
- 既存4アプリ (有給ナビ/KYナビ/鉄知/型知) と同じ /api/auth/* を呼び出す
"""
import os
import platform
from typing import Optional

import requests
import streamlit as st

# 認証ハブ: 有給ナビの /api/auth/* を呼ぶ
AUTH_API_BASE = (
    os.environ.get("AUTH_API_BASE")
    or (st.secrets.get("AUTH_API_BASE") if hasattr(st, "secrets") and "AUTH_API_BASE" in st.secrets else None)
    or "https://yukyu-navi.vercel.app"
)

APP_NAME = "uranai-monster"

# session_state キー
KEY_DEVICE_TOKEN = "_auth_device_token"
KEY_USER = "_auth_user"
KEY_SESSION = "_auth_session"
KEY_PROFILE = "_auth_profile"


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
# 認証状態クエリ
# ----------------------------------------------------------------------
def is_authenticated() -> bool:
    """Auth セッションが確立済みかつ enabled_apps に占いモンスターが含まれているか"""
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
    user = get_user() or {}
    return user.get("displayName", "")


def is_admin() -> bool:
    prof = get_profile() or {}
    return prof.get("role") == "admin"


def logout():
    """全認証関連 session_state をクリア"""
    for key in (KEY_DEVICE_TOKEN, KEY_USER, KEY_SESSION, KEY_PROFILE):
        st.session_state.pop(key, None)


def try_auto_login() -> bool:
    """device_token が session_state にあれば自動ログイン試行"""
    if is_authenticated():
        return True
    token = st.session_state.get(KEY_DEVICE_TOKEN)
    if not token:
        return False
    result = perform_device_login(device_token=token)
    if not result["ok"]:
        return False
    return is_authenticated()
