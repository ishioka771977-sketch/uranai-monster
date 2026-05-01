"""
占いモンスター ログイン画面 (Phase 1 Auth)
- ペアリング (6桁コード) または 管理者ログイン (社員番号 + 管理者パスワード)
"""
import os
import platform

import streamlit as st

import auth as _auth


def _get_admin_password() -> str:
    """secrets / 環境変数から管理者パスワードを取得。未設定なら空文字。"""
    pw = os.environ.get("ADMIN_LOGIN_PASSWORD", "")
    if pw:
        return pw
    try:
        return str(st.secrets.get("ADMIN_LOGIN_PASSWORD", "")) or ""
    except Exception:
        return ""


# ----------------------------------------------------------------------
# エラーメッセージ日本語化
# ----------------------------------------------------------------------
_PAIR_ERR_JP = {
    "code_required": "コードを入力してください",
    "invalid_code": "コードが正しくないか、既に使用されています",
    "expired": "コードの有効期限が切れています。管理者に再発行を依頼してください",
    "user_not_found": "ユーザーが見つかりません",
    "employee_mismatch": "社員番号とコードが一致しません",
    "inactive_user": "このアカウントは無効化されています",
    "device_create_failed": "デバイス登録に失敗しました。もう一度お試しください",
    "network_error": "認証サーバーに接続できません。ネットワークを確認してください",
}

_LOGIN_ERR_JP = {
    "invalid_device": "デバイス登録が失効しています。再度ペアリングしてください",
    "inactive": "このアカウントは無効化されています",
    "app_not_allowed": "このアカウントには占いモンスターへのアクセス権がありません。管理者にお問い合わせください",
    "admin_only": "このログイン方法は管理者・テストアカウント専用です。ペアリングタブをご利用ください",
    "session_issue_failed": "セッションの発行に失敗しました。しばらくしてから再度お試しください",
    "no_token_provided": "ログイン情報がありません",
    "network_error": "認証サーバーに接続できません",
}


def _localize_pair_error(code: str) -> str:
    return _PAIR_ERR_JP.get(code, f"ペアリングエラー: {code}")


def _localize_login_error(code: str) -> str:
    return _LOGIN_ERR_JP.get(code, f"ログインエラー: {code}")


# ----------------------------------------------------------------------
# メイン描画
# ----------------------------------------------------------------------
def render_login_page():
    """ログイン画面を描画する（ペアリング / 管理者ログインの2タブ）。"""
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

    # 中央寄せコンテナ
    col_left, col_main, col_right = st.columns([1, 4, 1])
    with col_main:
        tab_pair, tab_admin = st.tabs(
            ["📥 ペアリング", "👑 管理者ログイン"]
        )

        # ----- タブ1: 6桁コードペアリング -----
        with tab_pair:
            st.markdown(
                '<div style="color:#8A8478; font-size:0.86em; padding:8px 0 12px; line-height:1.6;">'
                '管理者から発行された <strong>6桁コード</strong> を入力してください。<br>'
                '初回のみペアリングが必要です。次回以降はこのブラウザに記憶されます。'
                '</div>',
                unsafe_allow_html=True,
            )
            emp_num = st.text_input(
                "社員番号 (4桁)",
                max_chars=4,
                key="_login_emp_num",
                placeholder="例: 0001",
            )
            code = st.text_input(
                "ペアリングコード (6桁)",
                max_chars=6,
                key="_login_code",
                placeholder="例: 123456",
            )
            device_label = st.text_input(
                "この機器の名前 (任意)",
                value=f"占いモンスター ({platform.system()})",
                key="_login_device_label",
            )

            if st.button("✦ ペアリング ✦", use_container_width=True, key="_btn_pair"):
                if not emp_num.strip() or not code.strip():
                    st.error("社員番号と6桁コードを入力してください")
                else:
                    with st.spinner("ペアリング中..."):
                        pair_result = _auth.perform_pairing(
                            emp_num.strip(), code.strip(), device_label.strip()
                        )
                    if not pair_result["ok"]:
                        st.error(_localize_pair_error(pair_result.get("error", "")))
                    else:
                        # ペアリング成功 → 即 device-login でセッション確立
                        with st.spinner("ログイン中..."):
                            login_result = _auth.perform_device_login(
                                device_token=st.session_state.get(_auth.KEY_DEVICE_TOKEN)
                            )
                        if not login_result["ok"]:
                            st.error(_localize_login_error(login_result.get("error", "")))
                        elif not _auth.is_authenticated():
                            st.error(
                                "このアカウントには占いモンスターへのアクセス権がありません。"
                                "管理者に enabled_apps への追加を依頼してください。"
                            )
                        else:
                            disp = pair_result["user"].get("displayName", "")
                            st.success(f"ログイン成功！ ようこそ、{disp} さん")
                            st.rerun()

        # ----- タブ2: 管理者/テストアカウント直接ログイン -----
        with tab_admin:
            _admin_pw_required = _get_admin_password()
            if not _admin_pw_required:
                st.error(
                    "🔒 管理者ログインは現在無効化されています。\n\n"
                    "Streamlit Cloud Secrets の `ADMIN_LOGIN_PASSWORD` が未設定です。"
                    "管理者にお問い合わせください。"
                )
            else:
                st.markdown(
                    '<div style="color:#8A8478; font-size:0.86em; padding:8px 0 12px; line-height:1.6;">'
                    '<strong>管理者・テストアカウント専用</strong> の即時ログインです。<br>'
                    '社員番号と <strong>管理者パスワード</strong> の両方が必要です。'
                    '</div>',
                    unsafe_allow_html=True,
                )
                admin_emp = st.text_input(
                    "社員番号 (4桁)",
                    max_chars=4,
                    key="_admin_emp_num",
                    placeholder="例: 0001",
                )
                admin_pw_input = st.text_input(
                    "管理者パスワード",
                    type="password",
                    key="_admin_pw_input",
                    placeholder="管理者から伝えられたパスワードを入力",
                )
                if st.button("✦ ログイン ✦", use_container_width=True, key="_btn_admin_login"):
                    if not admin_emp.strip() or not admin_pw_input:
                        st.error("社員番号と管理者パスワードを入力してください")
                    elif admin_pw_input != _admin_pw_required:
                        st.error("管理者パスワードが正しくありません")
                    else:
                        with st.spinner("ログイン中..."):
                            result = _auth.perform_device_login(
                                employee_number=admin_emp.strip()
                            )
                        if not result["ok"]:
                            st.error(_localize_login_error(result.get("error", "")))
                        elif not _auth.is_authenticated():
                            st.error(
                                "このアカウントには占いモンスターへのアクセス権がありません。"
                            )
                        else:
                            st.success("ログイン成功！")
                            st.rerun()
