"""
タロット画像ダウンロードスクリプト
ライダー・ウェイト版（1909年・パブリックドメイン）
Wikipedia Commonsから大アルカナ22枚をダウンロード
"""
import sys
import urllib.request
import os
sys.stdout.reconfigure(encoding='utf-8')

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "tarot_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Wikipedia Commons の公式URLマッピング（大アルカナ22枚）
TAROT_URLS = [
    ("major_00", "https://upload.wikimedia.org/wikipedia/commons/9/90/RWS_Tarot_00_Fool.jpg"),
    ("major_01", "https://upload.wikimedia.org/wikipedia/commons/d/de/RWS_Tarot_01_Magician.jpg"),
    ("major_02", "https://upload.wikimedia.org/wikipedia/commons/8/88/RWS_Tarot_02_High_Priestess.jpg"),
    ("major_03", "https://upload.wikimedia.org/wikipedia/commons/d/d2/RWS_Tarot_03_Empress.jpg"),
    ("major_04", "https://upload.wikimedia.org/wikipedia/commons/c/c3/RWS_Tarot_04_Emperor.jpg"),
    ("major_05", "https://upload.wikimedia.org/wikipedia/commons/8/8d/RWS_Tarot_05_Hierophant.jpg"),
    ("major_06", "https://upload.wikimedia.org/wikipedia/commons/3/3a/TheLovers.jpg"),
    ("major_07", "https://upload.wikimedia.org/wikipedia/commons/9/9b/RWS_Tarot_07_Chariot.jpg"),
    ("major_08", "https://upload.wikimedia.org/wikipedia/commons/f/f5/RWS_Tarot_08_Strength.jpg"),
    ("major_09", "https://upload.wikimedia.org/wikipedia/commons/4/4d/RWS_Tarot_09_Hermit.jpg"),
    ("major_10", "https://upload.wikimedia.org/wikipedia/commons/3/3c/RWS_Tarot_10_Wheel_of_Fortune.jpg"),
    ("major_11", "https://upload.wikimedia.org/wikipedia/commons/e/e0/RWS_Tarot_11_Justice.jpg"),
    ("major_12", "https://upload.wikimedia.org/wikipedia/commons/2/2b/RWS_Tarot_12_Hanged_Man.jpg"),
    ("major_13", "https://upload.wikimedia.org/wikipedia/commons/d/d7/RWS_Tarot_13_Death.jpg"),
    ("major_14", "https://upload.wikimedia.org/wikipedia/commons/f/f8/RWS_Tarot_14_Temperance.jpg"),
    ("major_15", "https://upload.wikimedia.org/wikipedia/commons/5/55/RWS_Tarot_15_Devil.jpg"),
    ("major_16", "https://upload.wikimedia.org/wikipedia/commons/5/53/RWS_Tarot_16_Tower.jpg"),
    ("major_17", "https://upload.wikimedia.org/wikipedia/commons/d/db/RWS_Tarot_17_Star.jpg"),
    ("major_18", "https://upload.wikimedia.org/wikipedia/commons/7/7f/RWS_Tarot_18_Moon.jpg"),
    ("major_19", "https://upload.wikimedia.org/wikipedia/commons/1/17/RWS_Tarot_19_Sun.jpg"),
    ("major_20", "https://upload.wikimedia.org/wikipedia/commons/d/dd/RWS_Tarot_20_Judgement.jpg"),
    ("major_21", "https://upload.wikimedia.org/wikipedia/commons/f/ff/RWS_Tarot_21_World.jpg"),
]

def download_all():
    headers = {"User-Agent": "Mozilla/5.0 (OccultBot/1.0; public domain tarot download)"}
    success = 0
    for key, url in TAROT_URLS:
        filepath = os.path.join(IMAGES_DIR, f"{key}.jpg")
        if os.path.exists(filepath):
            print(f"  スキップ（既存）: {key}.jpg")
            success += 1
            continue
        try:
            import time
            time.sleep(1.5)  # レートリミット対策
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                with open(filepath, "wb") as f:
                    f.write(resp.read())
            print(f"  ✓ ダウンロード完了: {key}.jpg")
            success += 1
        except Exception as e:
            print(f"  ✗ 失敗: {key} → {e}")

    print(f"\n完了: {success}/{len(TAROT_URLS)} 枚")
    return success == len(TAROT_URLS)

if __name__ == "__main__":
    print("タロット画像ダウンロード中（ライダー・ウェイト版・パブリックドメイン）")
    print(f"保存先: {IMAGES_DIR}")
    print()
    ok = download_all()
    if ok:
        print("\n✓ 全22枚ダウンロード完了！")
    else:
        print("\n⚠ 一部失敗。再実行すると続きから試行します。")
