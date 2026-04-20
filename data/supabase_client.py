"""占いモンスター Supabase クライアント

顧客管理・鑑定履歴・OAuthトークン永続化の CRUD を提供。
st.secrets から接続情報を取得。
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional

import streamlit as st

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore
    Client = None  # type: ignore


# ============================================================
# 接続管理
# ============================================================
_client_lock = threading.Lock()
_client_cache: dict[str, Any] = {}


def _get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """st.secrets → 環境変数の順で取得"""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def get_supabase_client() -> Optional["Client"]:
    """Supabase Client をキャッシュ付きで返す。未設定時は None。"""
    if create_client is None:
        return None
    with _client_lock:
        if "client" not in _client_cache:
            url = _get_secret("SUPABASE_URL")
            key = _get_secret("SUPABASE_SERVICE_ROLE_KEY") or _get_secret("SUPABASE_ANON_KEY")
            if not url or not key:
                _client_cache["client"] = None
            else:
                try:
                    _client_cache["client"] = create_client(url, key)
                except Exception:
                    _client_cache["client"] = None
        return _client_cache["client"]


def get_user_id() -> Optional[str]:
    """現在のユーザID（ひでさん固定）を返す。

    将来的に auth.uid() を使うが、今は st.secrets["URANAI_USER_ID"] を読む。
    """
    return _get_secret("URANAI_USER_ID")


def is_available() -> bool:
    """Supabaseが利用可能か"""
    return get_supabase_client() is not None and get_user_id() is not None


# ============================================================
# customers CRUD
# ============================================================
_CUSTOMER_COLUMNS = (
    "id,name,real_name,name_kana,gender,birth_year,birth_month,birth_day,"
    "birth_time,birth_place,blood_type,email,tags,memo,last_divined,"
    "divined_count,created_at,updated_at"
)


def list_customers(
    order_by: str = "last_divined",  # "last_divined" | "name_kana" | "created_at"
    desc: bool = True,
    tag_filter: Optional[list[str]] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """顧客一覧を取得。

    Args:
        order_by: ソート列
        desc: 降順なら True
        tag_filter: 指定された全タグを含む顧客のみ（AND検索）
        search: 名前・本名・メモ・タグに対する部分一致検索
    """
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return []
    try:
        q = client.table("customers").select(_CUSTOMER_COLUMNS).eq("user_id", uid)
        if tag_filter:
            # tags @> ['a','b'] で AND 含有
            q = q.contains("tags", tag_filter)
        if search:
            # PostgRESTのor構文で部分一致
            s = search.replace("%", "").replace(",", " ")
            q = q.or_(
                f"name.ilike.%{s}%,real_name.ilike.%{s}%,memo.ilike.%{s}%"
            )
        q = q.order(order_by, desc=desc, nullsfirst=not desc)
        res = q.execute()
        return res.data or []
    except Exception as e:
        print(f"[supabase] list_customers error: {e}")
        return []


def get_customer_by_name(name: str) -> Optional[dict]:
    """表示名で顧客を1件取得"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None or not name:
        return None
    try:
        res = (
            client.table("customers")
            .select(_CUSTOMER_COLUMNS)
            .eq("user_id", uid)
            .eq("name", name)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"[supabase] get_customer_by_name error: {e}")
        return None


def upsert_customer(data: dict) -> Optional[dict]:
    """顧客をINSERT or UPDATE。`name` をキーに UPSERT。

    既存レコードがあれば updated_at だけ新しくして他フィールドは上書き。
    """
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return None
    name = (data.get("name") or "").strip()
    if not name:
        return None
    payload = {
        "user_id": uid,
        "name": name,
        "real_name": data.get("real_name"),
        "name_kana": data.get("name_kana"),
        "gender": data.get("gender"),
        "birth_year": data.get("birth_year") or data.get("year"),
        "birth_month": data.get("birth_month") or data.get("month"),
        "birth_day": data.get("birth_day") or data.get("day"),
        "birth_time": data.get("birth_time") or data.get("time"),
        "birth_place": data.get("birth_place") or data.get("place"),
        "blood_type": data.get("blood_type") or data.get("blood"),
        "email": data.get("email"),
        "tags": _normalize_tags(data.get("tags")),
        "memo": data.get("memo"),
    }
    # None除去
    payload = {k: v for k, v in payload.items() if v is not None}
    try:
        res = (
            client.table("customers")
            .upsert(payload, on_conflict="user_id,name")
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"[supabase] upsert_customer error: {e}")
        return None


def delete_customer(customer_id: str) -> bool:
    """顧客を削除（divination_history は ON DELETE CASCADE で自動削除）"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return False
    try:
        (
            client.table("customers")
            .delete()
            .eq("user_id", uid)
            .eq("id", customer_id)
            .execute()
        )
        return True
    except Exception as e:
        print(f"[supabase] delete_customer error: {e}")
        return False


def all_tags() -> list[str]:
    """全顧客のタグをユニーク化して返す（サジェスト用）"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return []
    try:
        res = (
            client.table("customers")
            .select("tags")
            .eq("user_id", uid)
            .execute()
        )
        bag = set()
        for row in (res.data or []):
            for t in (row.get("tags") or []):
                if t:
                    bag.add(t)
        return sorted(bag)
    except Exception as e:
        print(f"[supabase] all_tags error: {e}")
        return []


def _normalize_tags(tags) -> list[str]:
    """タグを正規化（trim、空除去、重複除去、順序保持）"""
    if not tags:
        return []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace("、", ",").split(",")]
    seen = set()
    out = []
    for t in tags:
        if not t:
            continue
        t = str(t).strip()
        if not t:
            continue
        # 大文字小文字区別せず重複排除（表示は最初に出た形を優先）
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


# ============================================================
# divination_history CRUD
# ============================================================
def record_divination(
    customer_id: Optional[str],
    customer_name: str,
    course_name: str,
    divination_types: Optional[list[str]] = None,
) -> Optional[dict]:
    """鑑定を1件記録。customerの last_divined / divined_count はトリガーで自動更新。"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return None
    payload = {
        "user_id": uid,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "course_name": course_name,
        "divination_types": divination_types or [],
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    try:
        res = client.table("divination_history").insert(payload).execute()
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"[supabase] record_divination error: {e}")
        return None


def list_history(limit: int = 100) -> list[dict]:
    """鑑定履歴を降順で取得"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return []
    try:
        res = (
            client.table("divination_history")
            .select("*")
            .eq("user_id", uid)
            .order("divined_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[supabase] list_history error: {e}")
        return []


def mark_history_pdf_saved(history_id: str, gdrive_file_id: str, gdrive_file_url: str = "") -> bool:
    """履歴レコードに PDF 保存情報を記録"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return False
    try:
        (
            client.table("divination_history")
            .update({
                "pdf_saved": True,
                "gdrive_file_id": gdrive_file_id,
                "gdrive_file_url": gdrive_file_url,
            })
            .eq("user_id", uid)
            .eq("id", history_id)
            .execute()
        )
        return True
    except Exception as e:
        print(f"[supabase] mark_history_pdf_saved error: {e}")
        return False


# ============================================================
# oauth_tokens CRUD
# ============================================================
def get_oauth_token(provider: str) -> Optional[dict]:
    """OAuth トークンを取得"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return None
    try:
        res = (
            client.table("oauth_tokens")
            .select("*")
            .eq("user_id", uid)
            .eq("provider", provider)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"[supabase] get_oauth_token error: {e}")
        return None


def get_last_backup_at() -> Optional[datetime]:
    """最終バックアップ実行時刻を返す（成功したもの）"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return None
    try:
        res = (
            client.table("backup_logs")
            .select("backup_at")
            .eq("user_id", uid)
            .eq("status", "success")
            .order("backup_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        raw = rows[0].get("backup_at")
        if not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception as e:
        print(f"[supabase] get_last_backup_at error: {e}")
        return None


def record_backup_log(
    *,
    customers_count: int,
    history_count: int,
    customers_file_id: Optional[str],
    history_file_id: Optional[str],
    triggered_by: str = "auto",
    status: str = "success",
    error_message: Optional[str] = None,
) -> Optional[dict]:
    """バックアップ実行ログを1件INSERT"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return None
    payload = {
        "user_id": uid,
        "customers_count": customers_count,
        "history_count": history_count,
        "customers_file_id": customers_file_id,
        "history_file_id": history_file_id,
        "triggered_by": triggered_by,
        "status": status,
        "error_message": error_message,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    try:
        res = client.table("backup_logs").insert(payload).execute()
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"[supabase] record_backup_log error: {e}")
        return None


def fetch_all_customers_for_backup() -> list[dict]:
    """customers 全件（バックアップ用、全カラム）"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return []
    try:
        res = (
            client.table("customers")
            .select("*")
            .eq("user_id", uid)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[supabase] fetch_all_customers_for_backup error: {e}")
        return []


def fetch_all_history_for_backup() -> list[dict]:
    """divination_history 全件（バックアップ用）"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return []
    try:
        res = (
            client.table("divination_history")
            .select("*")
            .eq("user_id", uid)
            .order("divined_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[supabase] fetch_all_history_for_backup error: {e}")
        return []


def save_oauth_token(
    provider: str,
    *,
    access_token: Optional[str],
    refresh_token: str,
    token_uri: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    scopes: Optional[list[str]] = None,
    expires_at: Optional[datetime] = None,
) -> bool:
    """OAuth トークンを UPSERT"""
    client = get_supabase_client()
    uid = get_user_id()
    if client is None or uid is None:
        return False
    payload = {
        "user_id": uid,
        "provider": provider,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_uri": token_uri,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": scopes,
        "expires_at": expires_at.astimezone(timezone.utc).isoformat() if expires_at else None,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    try:
        client.table("oauth_tokens").upsert(payload, on_conflict="user_id,provider").execute()
        return True
    except Exception as e:
        print(f"[supabase] save_oauth_token error: {e}")
        return False
