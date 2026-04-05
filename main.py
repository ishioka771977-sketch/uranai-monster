"""
占いモンスターくろたん Phase 1a
メインエントリーポイント（Streamlit）

画面フロー: TOP → 入力 → ローディング → 裏メニュー → 鑑定生成 → 結果
起動: streamlit run main.py
"""
import os
import streamlit as st

# Streamlit Cloud: secretsからAPIキーを環境変数に設定
if not os.environ.get("GEMINI_API_KEY"):
    try:
        if "GEMINI_API_KEY" in st.secrets:
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

# ページ設定（最初に呼ぶ）
st.set_page_config(
    page_title="占いモンスターくろたん",
    page_icon="✧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from ui.styles import CUSTOM_CSS
from ui.pages import (
    render_top_page,
    render_input_page,
    render_loading_page,
    render_ura_menu_page,
    render_generating_page,
    render_generating_theme_page,
    render_theme_result_page,
    render_result_page,
    render_aisho_input_page,
    render_aisho_loading_page,
    render_aisho_result_page,
    render_team_input_page,
    render_team_loading_page,
    render_team_result_page,
    render_tarot_input_page,
    render_tarot_deepen_page,
    render_tarot_loading_page,
    render_tarot_reveal_page,
    render_tarot_generating_page,
    render_tarot_result_page,
    render_meibo_page,
    render_kaiyun_input_page,
    render_kaiyun_result_page,
)

# CSSを注入
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# セッション初期化
if "page" not in st.session_state:
    st.session_state.page = "top"

# ルーティング
page = st.session_state.page

if page == "top":
    render_top_page()
elif page == "input":
    render_input_page()
elif page == "loading":
    render_loading_page()
elif page == "ura_menu":
    render_ura_menu_page()
elif page == "generating":
    render_generating_page()
elif page == "generating_theme":
    render_generating_theme_page()
elif page == "theme_result":
    render_theme_result_page()
elif page == "result":
    render_result_page()
elif page == "aisho_input":
    render_aisho_input_page()
elif page == "aisho_loading":
    render_aisho_loading_page()
elif page == "aisho_result":
    render_aisho_result_page()
elif page == "team_input":
    render_team_input_page()
elif page == "team_loading":
    render_team_loading_page()
elif page == "team_result":
    render_team_result_page()
elif page == "tarot_input":
    render_tarot_input_page()
elif page == "tarot_deepen":
    render_tarot_deepen_page()
elif page == "tarot_loading":
    render_tarot_loading_page()
elif page == "tarot_reveal":
    render_tarot_reveal_page()
elif page == "tarot_generating":
    render_tarot_generating_page()
elif page == "tarot_result":
    render_tarot_result_page()
elif page == "meibo":
    render_meibo_page()
elif page == "kaiyun_input":
    render_kaiyun_input_page()
elif page == "kaiyun_result":
    render_kaiyun_result_page()
else:
    st.session_state.page = "top"
    st.rerun()
