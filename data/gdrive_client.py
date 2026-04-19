"""Google Drive OAuth クライアント

鑑定結果PDFを ひでさんのGoogleドライブに直接保存する。
refresh token は Supabase `oauth_tokens` テーブルに永続化（Streamlit Cloud の
ephemeral filesystem 対策）。
"""
from __future__ import annotations

import io
import os
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional

import streamlit as st

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from google.auth.transport.requests import Request as GoogleRequest
except ImportError:  # pragma: no cover
    Credentials = None  # type: ignore
    Flow = None  # type: ignore
    build = None  # type: ignore
    MediaIoBaseUpload = None  # type: ignore
    GoogleRequest = None  # type: ignore

from data import supabase_client as _sb


SCOPES = ["https://www.googleapis.com/auth/drive.file"]
PROVIDER_NAME = "google_drive"
TARGET_FOLDER_PATH = "石岡秀貴の頭脳/占いモンスター/鑑定結果PDF"


# ============================================================
# 設定取得
# ============================================================
def _get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def _client_config() -> Optional[dict]:
    """OAuth client config を st.secrets から構築"""
    cid = _get_secret("GOOGLE_OAUTH_CLIENT_ID")
    csec = _get_secret("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect = _get_secret("GOOGLE_OAUTH_REDIRECT_URI")
    if not cid or not csec:
        return None
    return {
        "installed": {
            "client_id": cid,
            "client_secret": csec,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect] if redirect else ["urn:ietf:wg:oauth:2.0:oob"],
        }
    }


def is_configured() -> bool:
    return _client_config() is not None and Credentials is not None


# ============================================================
# OAuth フロー
# ============================================================
def build_auth_url() -> Optional[str]:
    """初回認証用URL（ひでさんがブラウザで開いてコードを取得する）"""
    cfg = _client_config()
    if cfg is None or Flow is None:
        return None
    redirect = _get_secret("GOOGLE_OAUTH_REDIRECT_URI") or "urn:ietf:wg:oauth:2.0:oob"
    flow = Flow.from_client_config(cfg, scopes=SCOPES, redirect_uri=redirect)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # refresh_token確保のため毎回同意を要求
    )
    return url


def exchange_code_for_token(code: str) -> bool:
    """認証コードをトークンに交換して Supabase に保存"""
    cfg = _client_config()
    if cfg is None or Flow is None:
        return False
    redirect = _get_secret("GOOGLE_OAUTH_REDIRECT_URI") or "urn:ietf:wg:oauth:2.0:oob"
    try:
        flow = Flow.from_client_config(cfg, scopes=SCOPES, redirect_uri=redirect)
        flow.fetch_token(code=code)
        creds = flow.credentials
        _save_credentials(creds)
        return True
    except Exception as e:
        print(f"[gdrive] token exchange error: {e}")
        return False


def _save_credentials(creds) -> None:
    """Credentials を Supabase に UPSERT"""
    cfg = _client_config()
    cid = cfg["installed"]["client_id"] if cfg else None
    csec = cfg["installed"]["client_secret"] if cfg else None
    _sb.save_oauth_token(
        PROVIDER_NAME,
        access_token=creds.token,
        refresh_token=creds.refresh_token or "",
        token_uri=creds.token_uri,
        client_id=cid,
        client_secret=csec,
        scopes=list(creds.scopes or SCOPES),
        expires_at=creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None,
    )


def _load_credentials() -> Optional["Credentials"]:
    """Supabase からトークンを読み込んで Credentials を作成。必要ならリフレッシュ。"""
    if Credentials is None:
        return None
    row = _sb.get_oauth_token(PROVIDER_NAME)
    if not row or not row.get("refresh_token"):
        return None
    try:
        creds = Credentials(
            token=row.get("access_token"),
            refresh_token=row.get("refresh_token"),
            token_uri=row.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=row.get("client_id"),
            client_secret=row.get("client_secret"),
            scopes=row.get("scopes") or SCOPES,
        )
        # expires_at が過去 or 不明なら refresh
        needs_refresh = True
        if row.get("expires_at"):
            try:
                exp = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                needs_refresh = exp <= datetime.now(timezone.utc) + timedelta(minutes=1)
            except Exception:
                pass
        if needs_refresh and GoogleRequest is not None:
            creds.refresh(GoogleRequest())
            _save_credentials(creds)
        return creds
    except Exception as e:
        print(f"[gdrive] load credentials error: {e}")
        return None


def is_authenticated() -> bool:
    """認証済み（refresh_tokenがSupabaseに保存済み）か"""
    row = _sb.get_oauth_token(PROVIDER_NAME)
    return bool(row and row.get("refresh_token"))


# ============================================================
# Drive 操作
# ============================================================
_service_lock = threading.Lock()
_service_cache: dict = {}


def _get_service():
    if build is None:
        return None
    with _service_lock:
        if "svc" not in _service_cache:
            creds = _load_credentials()
            if not creds:
                _service_cache["svc"] = None
            else:
                try:
                    _service_cache["svc"] = build("drive", "v3", credentials=creds, cache_discovery=False)
                except Exception as e:
                    print(f"[gdrive] build service error: {e}")
                    _service_cache["svc"] = None
        return _service_cache["svc"]


def clear_service_cache():
    """認証情報が変わったらキャッシュを破棄"""
    with _service_lock:
        _service_cache.pop("svc", None)


def _ensure_folder_path(path: str) -> Optional[str]:
    """指定パスのフォルダIDを返す（無ければ作成）"""
    svc = _get_service()
    if svc is None:
        return None
    parts = [p for p in path.split("/") if p.strip()]
    parent_id = "root"
    for name in parts:
        # 既存検索
        q = (
            f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder'"
            f" and '{parent_id}' in parents and trashed = false"
        )
        try:
            res = svc.files().list(q=q, fields="files(id,name)", pageSize=1).execute()
            items = res.get("files", [])
            if items:
                parent_id = items[0]["id"]
                continue
            # 作成
            meta = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id] if parent_id != "root" else [],
            }
            created = svc.files().create(body=meta, fields="id").execute()
            parent_id = created["id"]
        except Exception as e:
            print(f"[gdrive] folder ensure error for '{name}': {e}")
            return None
    return parent_id


def upload_pdf_bytes(filename: str, pdf_bytes: bytes, folder_path: str = TARGET_FOLDER_PATH) -> Optional[dict]:
    """PDFバイトをGドライブにアップロード。

    Returns:
        {"id": ファイルID, "webViewLink": 閲覧URL} or None
    """
    svc = _get_service()
    if svc is None or MediaIoBaseUpload is None:
        return None
    folder_id = _ensure_folder_path(folder_path)
    if folder_id is None:
        return None
    try:
        meta = {
            "name": filename,
            "parents": [folder_id],
            "mimeType": "application/pdf",
        }
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False)
        result = svc.files().create(
            body=meta, media_body=media, fields="id,webViewLink",
        ).execute()
        return {"id": result.get("id"), "webViewLink": result.get("webViewLink", "")}
    except Exception as e:
        print(f"[gdrive] upload error: {e}")
        return None


# ============================================================
# HTML → PDF 変換
# ============================================================
def html_to_pdf_bytes(html: str) -> Optional[bytes]:
    """HTML文字列をPDFバイトに変換（WeasyPrint）"""
    try:
        from weasyprint import HTML
    except Exception as e:
        print(f"[gdrive] weasyprint import error: {e}")
        return None
    try:
        return HTML(string=html).write_pdf()
    except Exception as e:
        print(f"[gdrive] html→pdf error: {e}")
        return None
