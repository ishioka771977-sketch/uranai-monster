"""
UIスタイル定義（ui/styles.py）
ダーク神秘テーマのCSS定義
"""

CUSTOM_CSS = """
<style>
/* ===== 全体背景 ===== */
.stApp {
    background: linear-gradient(180deg, #0E0B1E 0%, #1A0B2E 50%, #0E0B1E 100%);
    min-height: 100vh;
}

/* ===== ゴールドグラデーション見出し ===== */
h1, h2, h3 {
    background: linear-gradient(90deg, #C9A84C, #F5D78E, #C9A84C);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: bold;
}

/* ===== メインタイトル ===== */
.uranai-title {
    text-align: center;
    font-size: 2.2em;
    font-weight: bold;
    background: linear-gradient(90deg, #C9A84C, #F5D78E, #C9A84C);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.1em;
    margin: 0.5em 0;
}

.uranai-subtitle {
    text-align: center;
    color: #9B8FC4;
    font-size: 0.95em;
    margin-bottom: 1.5em;
    letter-spacing: 0.05em;
}

/* ===== 星空装飾テキスト ===== */
.star-deco {
    text-align: center;
    color: #C9A84C;
    font-size: 1.4em;
    letter-spacing: 0.3em;
    margin: 0.3em 0;
}

/* ===== 結果カード ===== */
.divination-card {
    background: rgba(26, 21, 53, 0.85);
    border: 1px solid rgba(201, 168, 76, 0.4);
    border-radius: 14px;
    padding: 20px 22px;
    margin: 12px 0;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.15);
}

/* ===== カードヘッダー ===== */
.card-header {
    font-size: 1.15em;
    font-weight: bold;
    color: #C9A84C;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ===== 鑑定文本文 ===== */
.reading-text {
    color: #E8E0F0;
    font-size: 0.98em;
    line-height: 1.8;
    margin: 8px 0;
}

/* ===== 占術タグ ===== */
.uranai-tag {
    display: inline-block;
    background: rgba(139, 92, 246, 0.2);
    border: 1px solid rgba(139, 92, 246, 0.5);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78em;
    color: #C4B5FD;
    margin: 3px 2px;
}

.uranai-tag-gold {
    display: inline-block;
    background: rgba(201, 168, 76, 0.15);
    border: 1px solid rgba(201, 168, 76, 0.4);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78em;
    color: #F5D78E;
    margin: 3px 2px;
}

/* ===== 補完情報バッジ ===== */
.badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid rgba(201, 168, 76, 0.2);
}

.badge-item {
    background: rgba(14, 11, 30, 0.6);
    border: 1px solid rgba(201, 168, 76, 0.25);
    border-radius: 10px;
    padding: 6px 12px;
    text-align: center;
    min-width: 80px;
}

.badge-label {
    font-size: 0.7em;
    color: #9B8FC4;
    display: block;
}

.badge-value {
    font-size: 0.9em;
    color: #F5D78E;
    font-weight: bold;
    display: block;
}

/* ===== タロットカード ===== */
.tarot-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 16px 0;
}

.tarot-card-face {
    width: 140px;
    background: linear-gradient(135deg, #1A1535 0%, #2D1B5E 100%);
    border: 2px solid #C9A84C;
    border-radius: 10px;
    padding: 20px 12px;
    text-align: center;
    box-shadow: 0 0 25px rgba(201, 168, 76, 0.3), inset 0 0 20px rgba(139, 92, 246, 0.1);
    margin-bottom: 12px;
}

.tarot-card-back {
    width: 140px;
    height: 200px;
    background: linear-gradient(135deg, #1A1535 0%, #2D1B5E 100%);
    border: 2px solid #C9A84C;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 25px rgba(201, 168, 76, 0.3);
    font-size: 2em;
    margin-bottom: 12px;
}

.tarot-number {
    color: #9B8FC4;
    font-size: 0.75em;
    margin-bottom: 4px;
}

.tarot-name-jp {
    color: #F5D78E;
    font-size: 1.3em;
    font-weight: bold;
    margin: 4px 0;
}

.tarot-name-en {
    color: #9B8FC4;
    font-size: 0.7em;
    margin-bottom: 8px;
}

.tarot-position {
    font-size: 0.75em;
    padding: 2px 10px;
    border-radius: 10px;
    display: inline-block;
    margin-top: 4px;
}

.tarot-position-upright {
    background: rgba(52, 211, 153, 0.2);
    color: #34D399;
    border: 1px solid #34D399;
}

.tarot-position-reversed {
    background: rgba(251, 191, 36, 0.2);
    color: #FBBF24;
    border: 1px solid #FBBF24;
}

/* ===== 開運メッセージの強調 ===== */
.lucky-item {
    background: rgba(201, 168, 76, 0.08);
    border-left: 3px solid #C9A84C;
    padding: 8px 14px;
    margin: 6px 0;
    border-radius: 0 8px 8px 0;
    color: #E8E0F0;
    font-size: 0.92em;
}

/* ===== プログレス・ローディング ===== */
.loading-item {
    color: #9B8FC4;
    font-size: 0.9em;
    padding: 4px 0;
}

.loading-item-done {
    color: #34D399;
    font-size: 0.9em;
    padding: 4px 0;
}

/* ===== ボタン ===== */
.stButton > button {
    background: linear-gradient(135deg, #8B5CF6 0%, #C9A84C 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 25px !important;
    padding: 12px 32px !important;
    font-size: 1.05em !important;
    font-weight: bold !important;
    letter-spacing: 0.05em !important;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4) !important;
    transition: all 0.2s ease !important;
    width: 100%;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.6) !important;
}

/* ===== セレクトボックス・インプット ===== */
.stSelectbox > div > div {
    background-color: #1A1535 !important;
    border-color: rgba(201, 168, 76, 0.3) !important;
    color: #E8E0F0 !important;
}

/* ===== 区切り線 ===== */
.gold-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #C9A84C, transparent);
    margin: 16px 0;
}

/* ===== 天中殺警告 ===== */
.tenchusatsu-warning {
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.4);
    border-radius: 10px;
    padding: 10px 14px;
    color: #FBBF24;
    font-size: 0.88em;
    margin: 8px 0;
}

.tenchusatsu-safe {
    background: rgba(52, 211, 153, 0.1);
    border: 1px solid rgba(52, 211, 153, 0.3);
    border-radius: 10px;
    padding: 8px 14px;
    color: #34D399;
    font-size: 0.85em;
    margin: 8px 0;
}

/* ===== スマホ対応 ===== */
@media (max-width: 600px) {
    .uranai-title { font-size: 1.7em; }
    .divination-card { padding: 15px 16px; }
    .badge-item { min-width: 70px; }
}
</style>
"""
