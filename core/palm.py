"""
占いモンスター 手相鑑定モジュール (Round 5 統合設計書準拠)

機能:
- 画像前処理（HEIC対応、リサイズ、JPEG化、base64化）
- 画像品質チェック（明度・ブレ・解像度、numpy のみで cv2 不要）
- session_state クリーンアップ
- 監査ログ（ハッシュのみ、画像本体は記録しない）
"""
import os
import io
import json
import base64
import hashlib
import logging
from pathlib import Path

import numpy as np
from PIL import Image

# HEIC (iPhone) 対応
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # pillow-heif 未インストール環境では JPG/PNG のみ対応

# 知識ベース読み込み
_KB_PATH = Path(__file__).parent.parent / "data" / "palm_kb.json"
try:
    with open(_KB_PATH, encoding="utf-8") as f:
        PALM_KB = json.load(f)
except FileNotFoundError:
    PALM_KB = {}

# ============================================================
# 画像前処理
# ============================================================

def preprocess_image(uploaded_file) -> dict:
    """
    Streamlit の UploadedFile / BytesIO / camera_input 結果を、
    1600px 以下の JPEG bytes と base64 に変換する。

    Returns:
        {
            "bytes": bytes,
            "base64": str,
            "size": (width, height),
            "original_size": (width, height),
        }
    """
    img = Image.open(uploaded_file)
    original_size = img.size

    if img.mode != "RGB":
        img = img.convert("RGB")

    max_dim = 1600
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, optimize=True)
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    final_size = img.size

    img.close()
    buf.close()

    return {
        "bytes": img_bytes,
        "base64": img_b64,
        "size": final_size,
        "original_size": original_size,
    }

# ============================================================
# 画像品質チェック (numpy のみ、cv2 不要)
# ============================================================

def _laplacian_variance(gray: np.ndarray) -> float:
    """OpenCV を使わずラプラシアン分散を計算（ブレ検出）"""
    kernel = np.array(
        [[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32
    )
    h, w = gray.shape
    if h < 3 or w < 3:
        return 0.0
    out = np.zeros((h - 2, w - 2), dtype=np.float32)
    for i in range(3):
        for j in range(3):
            out += kernel[i, j] * gray[i:i + h - 2, j:j + w - 2].astype(np.float32)
    return float(out.var())


def check_quality(img_bytes: bytes) -> dict:
    """
    画像品質をチェックする。

    Returns:
        {
            "ok": bool,
            "issues": [str, ...],
            "metrics": {
                "brightness": float,
                "blur_score": float,
                "size": (w, h),
            },
        }
    """
    img = Image.open(io.BytesIO(img_bytes))
    gray_full = np.array(img.convert("L"))
    issues = []
    metrics = {}

    # 明度（平均輝度）
    brightness = float(np.mean(gray_full))
    metrics["brightness"] = round(brightness, 1)
    if brightness < 80:
        issues.append(
            f"暗すぎます（明度 {brightness:.0f}）。明るい場所で撮り直してください。"
        )
    elif brightness > 240:
        issues.append(
            "明るすぎます（白とびの可能性）。直射日光を避けてください。"
        )

    # ブレ検出（縮小して計算）
    small = np.array(img.convert("L").resize((400, 400)))
    blur = _laplacian_variance(small)
    metrics["blur_score"] = round(blur, 1)
    if blur < 50:
        issues.append(
            f"ブレています（鮮明度 {blur:.0f}）。手と腕を固定して撮り直してください。"
        )

    # 解像度
    w, h = img.size
    metrics["size"] = (w, h)
    if min(w, h) < 600:
        issues.append("解像度が低すぎます。1000px以上で撮影してください。")

    img.close()

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "metrics": metrics,
    }

# ============================================================
# セッション管理
# ============================================================

PALM_SESSION_KEYS = [
    "_palm_image_bytes",
    "_palm_image_b64",
    "_palm_left",
    "_palm_right",
    "_palm_camera",
    "_palm_upload",
    "_palm_quality",
    "_palm_hand",
    "_palm_result",
]


def cleanup_session_state(st):
    """鑑定終了後、画像関連の session_state を全削除"""
    for k in PALM_SESSION_KEYS:
        if k in st.session_state:
            try:
                del st.session_state[k]
            except Exception:
                pass

# ============================================================
# 監査ログ (画像本体は記録しない)
# ============================================================

def log_palm_reading_audit(user_id: str, hand: str, img_bytes: bytes):
    """監査ログ。画像本体ではなくハッシュ値のみ記録"""
    h = hashlib.sha256(img_bytes).hexdigest()[:16]
    logging.info(
        f"palm_reading: user={user_id} hand={hand} img_hash={h} size={len(img_bytes)}"
    )
