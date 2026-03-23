"""
小アルカナ画像ダウンロードスクリプト
ライダー・ウェイト版（1909年・パブリックドメイン）
Wikipedia Commonsから小アルカナ56枚をダウンロード
"""
import sys
import urllib.request
import os
import time

sys.stdout.reconfigure(encoding='utf-8')

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "tarot_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Wikipedia Commons URLマッピング（小アルカナ56枚）
# ライダー・ウェイト・スミス版 — パブリックドメイン（1909年出版）
MINOR_URLS = [
    # === ワンド（Wands） ===
    ("minor_wands_01", "https://upload.wikimedia.org/wikipedia/commons/1/11/Wands01.jpg"),
    ("minor_wands_02", "https://upload.wikimedia.org/wikipedia/commons/0/0f/Wands02.jpg"),
    ("minor_wands_03", "https://upload.wikimedia.org/wikipedia/commons/f/ff/Wands03.jpg"),
    ("minor_wands_04", "https://upload.wikimedia.org/wikipedia/commons/a/a4/Wands04.jpg"),
    ("minor_wands_05", "https://upload.wikimedia.org/wikipedia/commons/9/9d/Wands05.jpg"),
    ("minor_wands_06", "https://upload.wikimedia.org/wikipedia/commons/3/3b/Wands06.jpg"),
    ("minor_wands_07", "https://upload.wikimedia.org/wikipedia/commons/e/e4/Wands07.jpg"),
    ("minor_wands_08", "https://upload.wikimedia.org/wikipedia/commons/6/6b/Wands08.jpg"),
    ("minor_wands_09", "https://upload.wikimedia.org/wikipedia/commons/4/4d/Tarot_Nine_of_Wands.jpg"),
    ("minor_wands_10", "https://upload.wikimedia.org/wikipedia/commons/0/0b/Wands10.jpg"),
    ("minor_wands_11", "https://upload.wikimedia.org/wikipedia/commons/6/6a/Wands11.jpg"),
    ("minor_wands_12", "https://upload.wikimedia.org/wikipedia/commons/1/16/Wands12.jpg"),
    ("minor_wands_13", "https://upload.wikimedia.org/wikipedia/commons/0/0d/Wands13.jpg"),
    ("minor_wands_14", "https://upload.wikimedia.org/wikipedia/commons/c/ce/Wands14.jpg"),
    # === カップ（Cups） ===
    ("minor_cups_01", "https://upload.wikimedia.org/wikipedia/commons/3/36/Cups01.jpg"),
    ("minor_cups_02", "https://upload.wikimedia.org/wikipedia/commons/f/f8/Cups02.jpg"),
    ("minor_cups_03", "https://upload.wikimedia.org/wikipedia/commons/7/7a/Cups03.jpg"),
    ("minor_cups_04", "https://upload.wikimedia.org/wikipedia/commons/3/35/Cups04.jpg"),
    ("minor_cups_05", "https://upload.wikimedia.org/wikipedia/commons/d/d7/Cups05.jpg"),
    ("minor_cups_06", "https://upload.wikimedia.org/wikipedia/commons/1/17/Cups06.jpg"),
    ("minor_cups_07", "https://upload.wikimedia.org/wikipedia/commons/a/ae/Cups07.jpg"),
    ("minor_cups_08", "https://upload.wikimedia.org/wikipedia/commons/6/60/Cups08.jpg"),
    ("minor_cups_09", "https://upload.wikimedia.org/wikipedia/commons/2/24/Cups09.jpg"),
    ("minor_cups_10", "https://upload.wikimedia.org/wikipedia/commons/8/84/Cups10.jpg"),
    ("minor_cups_11", "https://upload.wikimedia.org/wikipedia/commons/a/ad/Cups11.jpg"),
    ("minor_cups_12", "https://upload.wikimedia.org/wikipedia/commons/f/fa/Cups12.jpg"),
    ("minor_cups_13", "https://upload.wikimedia.org/wikipedia/commons/6/62/Cups13.jpg"),
    ("minor_cups_14", "https://upload.wikimedia.org/wikipedia/commons/0/04/Cups14.jpg"),
    # === ソード（Swords） ===
    ("minor_swords_01", "https://upload.wikimedia.org/wikipedia/commons/1/1a/Swords01.jpg"),
    ("minor_swords_02", "https://upload.wikimedia.org/wikipedia/commons/9/9e/Swords02.jpg"),
    ("minor_swords_03", "https://upload.wikimedia.org/wikipedia/commons/0/02/Swords03.jpg"),
    ("minor_swords_04", "https://upload.wikimedia.org/wikipedia/commons/b/bf/Swords04.jpg"),
    ("minor_swords_05", "https://upload.wikimedia.org/wikipedia/commons/2/23/Swords05.jpg"),
    ("minor_swords_06", "https://upload.wikimedia.org/wikipedia/commons/2/29/Swords06.jpg"),
    ("minor_swords_07", "https://upload.wikimedia.org/wikipedia/commons/3/34/Swords07.jpg"),
    ("minor_swords_08", "https://upload.wikimedia.org/wikipedia/commons/a/a7/Swords08.jpg"),
    ("minor_swords_09", "https://upload.wikimedia.org/wikipedia/commons/2/2f/Swords09.jpg"),
    ("minor_swords_10", "https://upload.wikimedia.org/wikipedia/commons/d/d4/Swords10.jpg"),
    ("minor_swords_11", "https://upload.wikimedia.org/wikipedia/commons/4/4c/Swords11.jpg"),
    ("minor_swords_12", "https://upload.wikimedia.org/wikipedia/commons/b/b0/Swords12.jpg"),
    ("minor_swords_13", "https://upload.wikimedia.org/wikipedia/commons/d/d4/Swords13.jpg"),
    ("minor_swords_14", "https://upload.wikimedia.org/wikipedia/commons/3/33/Swords14.jpg"),
    # === ペンタクル（Pentacles） ===
    ("minor_pentacles_01", "https://upload.wikimedia.org/wikipedia/commons/f/fd/Pents01.jpg"),
    ("minor_pentacles_02", "https://upload.wikimedia.org/wikipedia/commons/9/9f/Pents02.jpg"),
    ("minor_pentacles_03", "https://upload.wikimedia.org/wikipedia/commons/4/42/Pents03.jpg"),
    ("minor_pentacles_04", "https://upload.wikimedia.org/wikipedia/commons/3/35/Pents04.jpg"),
    ("minor_pentacles_05", "https://upload.wikimedia.org/wikipedia/commons/9/96/Pents05.jpg"),
    ("minor_pentacles_06", "https://upload.wikimedia.org/wikipedia/commons/a/a6/Pents06.jpg"),
    ("minor_pentacles_07", "https://upload.wikimedia.org/wikipedia/commons/6/6a/Pents07.jpg"),
    ("minor_pentacles_08", "https://upload.wikimedia.org/wikipedia/commons/4/49/Pents08.jpg"),
    ("minor_pentacles_09", "https://upload.wikimedia.org/wikipedia/commons/f/f0/Pents09.jpg"),
    ("minor_pentacles_10", "https://upload.wikimedia.org/wikipedia/commons/4/42/Pents10.jpg"),
    ("minor_pentacles_11", "https://upload.wikimedia.org/wikipedia/commons/e/ec/Pents11.jpg"),
    ("minor_pentacles_12", "https://upload.wikimedia.org/wikipedia/commons/d/d5/Pents12.jpg"),
    ("minor_pentacles_13", "https://upload.wikimedia.org/wikipedia/commons/8/88/Pents13.jpg"),
    ("minor_pentacles_14", "https://upload.wikimedia.org/wikipedia/commons/1/1c/Pents14.jpg"),
]


def download_all():
    headers = {"User-Agent": "Mozilla/5.0 (OccultBot/1.0; public domain tarot download)"}
    success = 0
    failed = []

    for key, url in MINOR_URLS:
        filepath = os.path.join(IMAGES_DIR, f"{key}.jpg")
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            print(f"  スキップ（既存）: {key}.jpg")
            success += 1
            continue
        try:
            time.sleep(1.5)  # レートリミット対策
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                with open(filepath, "wb") as f:
                    f.write(data)
            size_kb = len(data) / 1024
            print(f"  ✓ {key}.jpg ({size_kb:.0f}KB)")
            success += 1
        except Exception as e:
            print(f"  ✗ 失敗: {key} → {e}")
            failed.append(key)

    print(f"\n完了: {success}/{len(MINOR_URLS)} 枚")
    if failed:
        print(f"失敗: {', '.join(failed)}")
    return success, failed


if __name__ == "__main__":
    print("小アルカナ画像ダウンロード中（ライダー・ウェイト版・パブリックドメイン）")
    print(f"保存先: {IMAGES_DIR}")
    print()
    success, failed = download_all()
    if not failed:
        print("\n✓ 全56枚ダウンロード完了！")
    else:
        print("\n⚠ 一部失敗。再実行すると続きから試行します。")
