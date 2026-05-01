"""
占いモンスター ログイン画面 (シンプル化版 — パスワード1個方式)
ひでさん専用ツールのため、社員番号/6桁ペアリングコード等の社員管理仕組みは撤廃。
強い管理者パスワード1個で認証する。
"""
import platform

import streamlit as st

import auth as _auth


def render_login_page():
    """シンプルなパスワード入力画面"""
    # ヘッダー（占いモンスター風: 紫＋金）
    st.markdown(
        '<div style="text-align:center; margin:50px 0 16px;">'
        '<div style="font-size:2.4em; color:#BFA350; letter-spacing:0.18em; '
        'font-family:Noto Serif JP, serif;">✧ 占いモンスターくろたん ✧</div>'
        '<div style="color:#8A8478; margin-top:10px; letter-spacing:0.1em; font-size:0.92em;">'
        '— 認証してご利用ください —</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_left, col_main, col_right = st.columns([1, 4, 1])
    with col_main:
        # secrets が未設定ならフェイルセキュア
        if not _auth.get_admin_password():
            st.error(
                "🔒 認証システムが無効化されています。\n\n"
                "Streamlit Cloud Secrets の `ADMIN_LOGIN_PASSWORD` が未設定です。"
                "管理者にお問い合わせください。"
            )
            return

        st.markdown(
            '<div style="color:#8A8478; font-size:0.86em; padding:8px 0 12px; line-height:1.6;">'
            'パスワードを入力してください。<br>'
            '次回以降はこのブラウザに自動ログインで記憶されます。'
            '</div>',
            unsafe_allow_html=True,
        )

        # st.form を使うことで:
        # - 「Press Enter to apply」が消える（ボタン押下で全 widget 値が一括確定）
        # - Enter キーでも submit_button が押せる
        # - rerun のタイミングが制御できる
        with st.form("login_form", clear_on_submit=False):
            password = st.text_input(
                "パスワード",
                type="password",
                key="_login_password",
                placeholder="管理者パスワード（長文）",
            )
            # 機器ラベルは記録用。サーバー保存はしないが、UI に「複数機器を使い分けてる感」を残す
            st.text_input(
                "この機器の名前 (任意・記録用)",
                value=f"占いモンスター ({platform.system()})",
                key="_login_device_label",
            )
            submitted = st.form_submit_button("✦ ログイン ✦", use_container_width=True)

        if submitted:
            if not password:
                st.error("パスワードを入力してください")
            else:
                result = _auth.perform_password_login(password)
                if result["ok"]:
                    st.success("ログイン成功！")
                    st.rerun()
                else:
                    err = result.get("error", "")
                    if err == "wrong_password":
                        st.error("パスワードが正しくありません")
                    elif err == "admin_password_not_set":
                        st.error("認証システムが無効化されています")
                    else:
                        st.error(f"ログインエラー: {err}")
