"""
UIスタイル定義（ui/styles.py）
高級サロン風テーマ — ブラック×ゴールド
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;500;700&family=Zen+Kaku+Gothic+New:wght@300;400;500;700&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded');

/* ===== Material Icons/Symbols リガチャ文字露出対策 =====
   Google Fonts が読めない環境（社内プロキシ等）でも、
   「upload」「arrow_right」等の素テキストが露出しないよう隠す */
.material-icons, .material-icons-outlined, .material-icons-round,
.material-icons-sharp, .material-icons-two-tone,
.material-symbols-rounded, .material-symbols-outlined, .material-symbols-sharp,
[class*="material-symbols"], [class*="material-icons"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                 'Material Icons', sans-serif !important;
    font-feature-settings: 'liga';
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    -webkit-font-feature-settings: 'liga';
    -webkit-font-smoothing: antialiased;
}
/* フォント読み込みに失敗した環境では素テキストが出る。
   リガチャ用文字列が表示されても見えないように color: transparent */
@supports not (font-variation-settings: normal) {
    .material-icons, .material-icons-outlined, .material-icons-round,
    .material-symbols-rounded, .material-symbols-outlined, .material-symbols-sharp,
    [class*="material-symbols"], [class*="material-icons"] {
        color: transparent !important;
    }
}

/* ===== グローバルフォント ===== */
.stApp, .stApp * {
    font-family: 'Zen Kaku Gothic New', sans-serif;
}

/* ===== 全体背景 ===== */
.stApp {
    background: linear-gradient(180deg, #0A0A0A 0%, #0F0F0F 50%, #0A0A0A 100%);
    min-height: 100vh;
}

/* ===== メインコンテナ幅・余白 ===== */
.block-container {
    max-width: 720px !important;
    padding: 2rem 1.5rem !important;
}

/* ===== ゴールドグラデーション見出し ===== */
h1, h2, h3 {
    background: linear-gradient(90deg, #BFA350, #D4B96A, #BFA350);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 500;
    font-family: 'Noto Serif JP', serif;
}

/* ===== メインタイトル ===== */
.uranai-title {
    text-align: center;
    font-size: 2em;
    font-weight: 500;
    font-family: 'Noto Serif JP', serif;
    background: linear-gradient(90deg, #BFA350, #D4B96A, #BFA350);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.15em;
    margin: 0.5em 0;
}

.uranai-subtitle {
    text-align: center;
    color: #8A8478;
    font-size: 0.95em;
    margin-bottom: 1.5em;
    letter-spacing: 0.08em;
}

/* ===== 星空装飾テキスト ===== */
.star-deco {
    text-align: center;
    color: #BFA350;
    font-size: 1.4em;
    letter-spacing: 0.3em;
    margin: 0.3em 0;
}

/* ===== 結果カード ===== */
.divination-card {
    background: #121212;
    border: 1px solid rgba(191, 163, 80, 0.2);
    border-radius: 8px;
    padding: 28px;
    margin: 20px 0;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

/* ===== カードヘッダー ===== */
.card-header {
    font-family: 'Noto Serif JP', serif;
    font-size: 1.1em;
    font-weight: 500;
    color: #BFA350;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 0.08em;
}

/* ===== 鑑定文本文 ===== */
.reading-text {
    color: #F0EBE0;
    font-size: 0.95em;
    line-height: 2.0;
    margin: 8px 0;
    letter-spacing: 0.03em;
}

/* ===== 占術タグ ===== */
.uranai-tag {
    display: inline-block;
    background: rgba(138, 132, 120, 0.12);
    border: 1px solid rgba(138, 132, 120, 0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78em;
    color: #A39E93;
    margin: 3px 2px;
}

.uranai-tag-gold {
    display: inline-block;
    background: rgba(191, 163, 80, 0.08);
    border: 1px solid rgba(191, 163, 80, 0.3);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78em;
    color: #D4B96A;
    margin: 3px 2px;
}

/* ===== 補完情報バッジ ===== */
.badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid rgba(191, 163, 80, 0.15);
}

.badge-item {
    background: rgba(10, 10, 10, 0.6);
    border: 1px solid rgba(191, 163, 80, 0.2);
    border-radius: 8px;
    padding: 6px 12px;
    text-align: center;
    min-width: 80px;
}

.badge-label {
    font-size: 0.7em;
    color: #8A8478;
    display: block;
}

.badge-value {
    font-size: 0.9em;
    color: #D4B96A;
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
    background: linear-gradient(135deg, #1A1A1A 0%, #222222 100%);
    border: 2px solid #BFA350;
    border-radius: 8px;
    padding: 20px 12px;
    text-align: center;
    box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
    margin-bottom: 12px;
}

.tarot-card-back {
    width: 140px;
    height: 200px;
    background: linear-gradient(135deg, #1A1A1A 0%, #222222 100%);
    border: 2px solid #BFA350;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
    font-size: 2em;
    margin-bottom: 12px;
}

.tarot-number {
    color: #8A8478;
    font-size: 0.75em;
    margin-bottom: 4px;
}

.tarot-name-jp {
    color: #D4B96A;
    font-size: 1.3em;
    font-weight: bold;
    font-family: 'Noto Serif JP', serif;
    margin: 4px 0;
}

.tarot-name-en {
    color: #8A8478;
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
    background: rgba(124, 184, 124, 0.15);
    color: #7CB87C;
    border: 1px solid #7CB87C;
}

.tarot-position-reversed {
    background: rgba(196, 149, 106, 0.15);
    color: #C4956A;
    border: 1px solid #C4956A;
}

/* ===== 開運メッセージの強調 ===== */
.lucky-item {
    background: rgba(191, 163, 80, 0.04);
    border-left: 2px solid #BFA350;
    padding: 10px 16px;
    margin: 8px 0;
    border-radius: 0 6px 6px 0;
    color: #F0EBE0;
    font-size: 0.92em;
}

/* ===== プログレス・ローディング ===== */
.loading-item {
    color: #8A8478;
    font-size: 0.9em;
    padding: 4px 0;
}

.loading-item-done {
    color: #7CB87C;
    font-size: 0.9em;
    padding: 4px 0;
}

/* ===== ボタン ===== */
.stButton > button {
    background: transparent !important;
    color: #BFA350 !important;
    border: 1px solid rgba(191, 163, 80, 0.5) !important;
    border-radius: 6px !important;
    padding: 14px 36px !important;
    font-size: 0.95em !important;
    font-weight: 500 !important;
    font-family: 'Noto Serif JP', serif !important;
    letter-spacing: 0.08em !important;
    box-shadow: none !important;
    transition: all 0.3s ease !important;
    width: 100%;
}

.stButton > button:hover {
    background: rgba(191, 163, 80, 0.08) !important;
    border-color: #BFA350 !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ===== セレクトボックス・インプット ===== */
.stSelectbox > div > div {
    background-color: #141414 !important;
    border-color: rgba(191, 163, 80, 0.2) !important;
    color: #F0EBE0 !important;
}

/* ===== 区切り線 ===== */
.gold-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(191, 163, 80, 0.3), transparent);
    margin: 24px 0;
}

/* ===== 天中殺警告 ===== */
.tenchusatsu-warning {
    background: rgba(196, 149, 106, 0.08);
    border: 1px solid rgba(196, 149, 106, 0.35);
    border-radius: 8px;
    padding: 10px 14px;
    color: #C4956A;
    font-size: 0.88em;
    margin: 8px 0;
}

.tenchusatsu-safe {
    background: rgba(124, 184, 124, 0.08);
    border: 1px solid rgba(124, 184, 124, 0.25);
    border-radius: 8px;
    padding: 8px 14px;
    color: #7CB87C;
    font-size: 0.85em;
    margin: 8px 0;
}

/* ===== タブ ===== */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: #8A8478 !important;
    font-family: 'Noto Serif JP', serif !important;
    font-size: 0.9em !important;
}
.stTabs [aria-selected="true"] {
    color: #BFA350 !important;
}

/* ===== チャットメッセージ ===== */
.stChatMessage {
    background: #121212 !important;
    border: 1px solid #2A2A2A !important;
}

/* ===== ステータス ===== */
.stStatus {
    background: #121212 !important;
    border-color: #2A2A2A !important;
}

/* ===== ファイルアップローダ（Dropzone全体を強制置換） =====
   Google Fonts が読めない環境で Material Icons のリガチャ "upload" 等が
   素テキスト露出するのを根絶するため、Dropzone内部を全部隠して独自UIを被せる */
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed rgba(191, 163, 80, 0.45) !important;
    background: rgba(20, 20, 20, 0.6) !important;
    padding: 24px 20px !important;
    border-radius: 10px !important;
    position: relative !important;
    min-height: 90px !important;
}
/* 内部要素を全て不可視化（クリック判定は残す） */
[data-testid="stFileUploaderDropzone"] > *,
[data-testid="stFileUploaderDropzone"] * {
    color: transparent !important;
    font-size: 0 !important;
    text-shadow: none !important;
}
[data-testid="stFileUploaderDropzone"] svg {
    display: none !important;
}
/* Dropzone 本体に独自のラベルを被せる */
[data-testid="stFileUploaderDropzone"]::after {
    content: "📂 ファイルをここにドロップ、またはクリックして選択（CSV / XLSX, 200MB以下）";
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #BFA350 !important;
    font-family: 'Zen Kaku Gothic New', sans-serif !important;
    font-size: 14px !important;
    letter-spacing: 0.05em;
    pointer-events: none;
    padding: 0 12px;
    text-align: center;
}

/* ===== expander の開閉マーカーを独自化（Material Symbols リガチャ露出対策） ===== */
details > summary,
summary[class*="st-emotion-cache"] {
    list-style: none !important;
}
details > summary::-webkit-details-marker,
summary[class*="st-emotion-cache"]::-webkit-details-marker {
    display: none !important;
}

/* Streamlit expander summary の先頭にカスタムマーカー（文字で実装） */
details > summary::before,
summary[class*="st-emotion-cache"]::before {
    content: "▶ ";
    color: #BFA350;
    margin-right: 4px;
    font-size: 0.85em;
}
details[open] > summary::before {
    content: "▼ ";
}

/* Streamlit の SVG/テキストマーカー（stExpanderIcon 以外）を隠す */
details summary span[aria-hidden="true"]:not([data-testid="stExpanderIcon"]):empty,
details summary svg:not([class*="uranai"]) {
    display: none !important;
}

/* ===== スマホ対応 ===== */
@media (max-width: 600px) {
    .uranai-title { font-size: 1.5em; }
    .divination-card { padding: 20px 16px; margin: 16px 0; }
    .badge-item { min-width: 65px; }
    .reading-text { font-size: 0.92em; line-height: 1.9; }
    .block-container { padding: 1rem 1rem !important; }
    .card-header { font-size: 1.0em; }
}
</style>
"""
