"""週次バックアップモジュール

customers / divination_history を CSV 化して Gドライブに保存。
4週分を保持し、5週目以降は自動削除。

2026-04-20 追加：顧客データ消失事故を受けて、くろたん追加指令書により実装。
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional

from data import supabase_client as _sb
from data import gdrive_client as _gd


BACKUP_FOLDER_PATH = "石岡秀貴の頭脳/占いモンスター/バックアップ"
KEEP_WEEKS = 4  # 最新4週分を保持


# ============================================================
# CSV 変換
# ============================================================
def _rows_to_csv(rows: list[dict], columns: list[str]) -> bytes:
    """dictのリストをCSV bytesに変換。Excel対応のBOM付きUTF-8。"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        out = {}
        for c in columns:
            v = row.get(c)
            # 配列はセミコロン区切りに
            if isinstance(v, list):
                out[c] = ";".join(str(x) for x in v)
            elif v is None:
                out[c] = ""
            else:
                out[c] = str(v)
        writer.writerow(out)
    # Excel で開いたときに日本語が化けないよう BOM 付き
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


_CUSTOMER_COLS = [
    "id", "name", "real_name", "name_kana", "gender",
    "birth_year", "birth_month", "birth_day", "birth_time", "birth_place",
    "blood_type", "email", "tags", "memo",
    "last_divined", "divined_count", "created_at", "updated_at",
]

_HISTORY_COLS = [
    "id", "customer_id", "customer_name", "divined_at",
    "course_name", "divination_types",
    "pdf_saved", "gdrive_file_id", "gdrive_file_url",
    "created_at",
]


# ============================================================
# Gドライブ 操作補助
# ============================================================
def _list_backup_files() -> list[dict]:
    """バックアップフォルダ内のCSVファイル一覧（name, id, createdTime）"""
    svc = _gd._get_service()  # type: ignore
    if svc is None:
        return []
    folder_id = _gd._ensure_folder_path(BACKUP_FOLDER_PATH)  # type: ignore
    if folder_id is None:
        return []
    try:
        q = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        res = svc.files().list(
            q=q,
            fields="files(id,name,createdTime)",
            orderBy="createdTime desc",
            pageSize=100,
        ).execute()
        return res.get("files", [])
    except Exception as e:
        print(f"[backup] list error: {e}")
        return []


def _upload_csv(filename: str, csv_bytes: bytes) -> Optional[dict]:
    """CSVをバックアップフォルダにアップロード"""
    from googleapiclient.http import MediaIoBaseUpload
    svc = _gd._get_service()  # type: ignore
    if svc is None:
        return None
    folder_id = _gd._ensure_folder_path(BACKUP_FOLDER_PATH)  # type: ignore
    if folder_id is None:
        return None
    try:
        meta = {
            "name": filename,
            "parents": [folder_id],
            "mimeType": "text/csv",
        }
        media = MediaIoBaseUpload(io.BytesIO(csv_bytes), mimetype="text/csv", resumable=False)
        result = svc.files().create(
            body=meta, media_body=media, fields="id,webViewLink",
        ).execute()
        return {"id": result.get("id"), "webViewLink": result.get("webViewLink", "")}
    except Exception as e:
        print(f"[backup] upload error for {filename}: {e}")
        return None


def _rotate_old_files() -> int:
    """KEEP_WEEKS 以前の古いファイルを削除。削除件数を返す。

    customers_backup_*.csv と history_backup_*.csv をそれぞれ KEEP_WEEKS 世代だけ残す。
    """
    svc = _gd._get_service()  # type: ignore
    if svc is None:
        return 0
    files = _list_backup_files()
    if not files:
        return 0
    # prefix ごとにグルーピング
    by_kind: dict[str, list[dict]] = {}
    for f in files:
        name = f.get("name", "")
        if name.startswith("customers_backup_"):
            by_kind.setdefault("customers", []).append(f)
        elif name.startswith("history_backup_"):
            by_kind.setdefault("history", []).append(f)
    deleted = 0
    for kind, lst in by_kind.items():
        # createdTime 降順でソート済みの想定
        lst_sorted = sorted(lst, key=lambda x: x.get("createdTime", ""), reverse=True)
        to_delete = lst_sorted[KEEP_WEEKS:]
        for f in to_delete:
            try:
                svc.files().delete(fileId=f["id"]).execute()
                deleted += 1
                print(f"[backup] rotated: {f.get('name')}")
            except Exception as e:
                print(f"[backup] rotate delete error ({f.get('name')}): {e}")
    return deleted


# ============================================================
# メイン関数
# ============================================================
def run_backup(triggered_by: str = "manual") -> dict:
    """バックアップ実行。

    Returns:
        {"ok": bool, "message": str, "customers_count": int, "history_count": int,
         "customers_file_id": str, "history_file_id": str}
    """
    result: dict = {
        "ok": False,
        "message": "",
        "customers_count": 0,
        "history_count": 0,
        "customers_file_id": None,
        "history_file_id": None,
    }

    # 事前チェック
    if not _sb.is_available():
        result["message"] = "Supabase 未接続"
        return result
    if not _gd.is_configured() or not _gd.is_authenticated():
        result["message"] = "Gドライブ未認証（設定ページで OAuth 認証してください）"
        return result

    try:
        # 1. Supabaseからデータ取得
        customers = _sb.fetch_all_customers_for_backup()
        history = _sb.fetch_all_history_for_backup()
        result["customers_count"] = len(customers)
        result["history_count"] = len(history)

        # 2. CSV化
        today = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d")
        customers_csv = _rows_to_csv(customers, _CUSTOMER_COLS)
        history_csv = _rows_to_csv(history, _HISTORY_COLS)

        # 3. Gドライブへアップロード
        c_up = _upload_csv(f"customers_backup_{today}.csv", customers_csv)
        h_up = _upload_csv(f"history_backup_{today}.csv", history_csv)

        if c_up is None or h_up is None:
            err = "Gドライブアップロード失敗"
            result["message"] = err
            _sb.record_backup_log(
                customers_count=len(customers),
                history_count=len(history),
                customers_file_id=c_up.get("id") if c_up else None,
                history_file_id=h_up.get("id") if h_up else None,
                triggered_by=triggered_by,
                status="failed",
                error_message=err,
            )
            return result

        result["customers_file_id"] = c_up["id"]
        result["history_file_id"] = h_up["id"]

        # 4. 世代ローテーション
        rotated = _rotate_old_files()

        # 5. ログ記録
        _sb.record_backup_log(
            customers_count=len(customers),
            history_count=len(history),
            customers_file_id=c_up["id"],
            history_file_id=h_up["id"],
            triggered_by=triggered_by,
            status="success",
        )

        result["ok"] = True
        result["message"] = (
            f"✓ バックアップ完了（顧客{len(customers)}件、履歴{len(history)}件）"
            + (f" / 古い世代{rotated}件削除" if rotated else "")
        )
        return result

    except Exception as e:
        err = f"予期しないエラー: {e}"
        result["message"] = err
        try:
            _sb.record_backup_log(
                customers_count=result["customers_count"],
                history_count=result["history_count"],
                customers_file_id=None,
                history_file_id=None,
                triggered_by=triggered_by,
                status="failed",
                error_message=str(e)[:500],
            )
        except Exception:
            pass
        return result


def get_last_backup_at() -> Optional[datetime]:
    """最終バックアップ実行時刻（成功したもの）"""
    return _sb.get_last_backup_at()


def maybe_auto_backup(min_interval_days: int = 7) -> Optional[dict]:
    """前回成功から min_interval_days 以上経っていれば自動でバックアップ。

    条件未達 or 前提不足なら None を返す。実行したら結果dictを返す。
    """
    if not _sb.is_available():
        return None
    if not _gd.is_configured() or not _gd.is_authenticated():
        return None
    last = get_last_backup_at()
    now = datetime.now(timezone.utc)
    if last is not None:
        if now - last < timedelta(days=min_interval_days):
            return None
    return run_backup(triggered_by="auto")
