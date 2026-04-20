"""既存 people_db.json を Supabase の customers テーブルに移行するスクリプト

使い方:
  1. .streamlit/secrets.toml に SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / URANAI_USER_ID を設定
  2. cd uranai_monster
  3. python scripts/migrate_people_db_to_supabase.py

実行すると:
  - data/people_db.json の全レコードを customers テーブルに UPSERT
  - data/people_db.json → data/people_db.json.bak にリネーム
  - data/folders_db.json が存在すれば同じく .bak にリネーム
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# プロジェクトルートをパスに追加
_here = Path(__file__).resolve().parent
_root = _here.parent
sys.path.insert(0, str(_root))

# .streamlit/secrets.toml を先に読み込む（st.secrets 経由）
try:
    import streamlit as st  # noqa: F401
except Exception as e:
    print(f"Streamlit import failed: {e}")
    sys.exit(1)

from data.supabase_client import (  # noqa: E402
    get_supabase_client,
    get_user_id,
    upsert_customer,
)


DATA_DIR = _root / "data"
PEOPLE_DB_PATH = DATA_DIR / "people_db.json"
FOLDERS_DB_PATH = DATA_DIR / "folders_db.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ! {path.name} 読み込み失敗: {e}")
        return {}


def main():
    print("=== 占いモンスター 顧客データ Supabase 移行 ===\n")

    client = get_supabase_client()
    uid = get_user_id()
    if client is None:
        print("❌ Supabase クライアントが初期化できませんでした。")
        print("   .streamlit/secrets.toml に以下が設定されているか確認してください:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_ROLE_KEY  (または SUPABASE_ANON_KEY)")
        sys.exit(1)
    if not uid:
        print("❌ URANAI_USER_ID が未設定です。")
        print("   .streamlit/secrets.toml に URANAI_USER_ID を設定してください。")
        sys.exit(1)

    print(f"✓ Supabase 接続OK")
    print(f"✓ user_id = {uid}\n")

    # ── 1. 既存 JSON 読み込み ──
    people_db = _load_json(PEOPLE_DB_PATH)
    folders_db = _load_json(FOLDERS_DB_PATH)

    print(f"people_db.json: {len(people_db)}件")
    print(f"folders_db.json: {len(folders_db)}個のフォルダ\n")

    if not people_db and not folders_db:
        print("移行対象データがありません。終了します。")
        return

    # ── 2. フォルダ → タグマッピング ──
    # 「フォルダに所属していた顧客にそのフォルダ名をタグとして付与」
    name_to_tags: dict[str, list[str]] = {}
    for folder_name, members in folders_db.items():
        if not isinstance(members, list):
            continue
        for member_name in members:
            name_to_tags.setdefault(member_name, []).append(folder_name)

    if folders_db:
        print("フォルダ→タグ変換マップ:")
        for n, ts in name_to_tags.items():
            print(f"  {n}: {ts}")
        print()

    # ── 3. 顧客レコードを順次 UPSERT ──
    success = 0
    failed = 0
    for name, record in people_db.items():
        if not name or not isinstance(record, dict):
            continue
        tags = name_to_tags.get(name, [])
        payload = {
            "name": name,
            "real_name": record.get("real_name"),
            "name_kana": record.get("name_kana"),
            "gender": record.get("gender"),
            "birth_year": record.get("year"),
            "birth_month": record.get("month"),
            "birth_day": record.get("day"),
            "birth_time": record.get("time"),
            "birth_place": record.get("place"),
            "blood_type": record.get("blood"),
            "email": record.get("email"),
            "tags": tags,
            "memo": record.get("memo"),
        }
        result = upsert_customer(payload)
        if result:
            success += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name}  (upsert失敗)")

    print(f"\n結果: 成功 {success} / 失敗 {failed}")

    # ── 4. 旧ファイルを .bak にリネーム ──
    if failed == 0 and success > 0:
        for src in (PEOPLE_DB_PATH, FOLDERS_DB_PATH):
            if src.exists():
                dst = src.with_suffix(src.suffix + ".bak")
                # 既に .bak があれば連番
                i = 1
                while dst.exists():
                    dst = src.with_suffix(f"{src.suffix}.bak{i}")
                    i += 1
                shutil.move(str(src), str(dst))
                print(f"  → {src.name} を {dst.name} にリネーム")
        print("\n✨ 移行完了")
    else:
        print("\n⚠ 失敗があったため、元ファイルは残しています。原因を確認してください。")


if __name__ == "__main__":
    main()
