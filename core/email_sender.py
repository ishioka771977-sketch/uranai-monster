"""
Gmail SMTP経由でHTML形式の鑑定結果メールを送信するモジュール

使い方:
  send_result_email("相手@example.com", "鑑定結果: ひでさん", html_body)

必要な環境変数 / Streamlit secrets:
  GMAIL_ADDRESS   — 送信元Gmailアドレス
  GMAIL_APP_PASS  — Googleアプリパスワード（16桁）
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_gmail_credentials() -> tuple[str, str]:
    """Gmail認証情報を取得（環境変数 → Streamlit secrets）"""
    addr = os.environ.get("GMAIL_ADDRESS", "")
    pw = os.environ.get("GMAIL_APP_PASS", "")
    if addr and pw:
        return addr, pw

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            addr = st.secrets.get("GMAIL_ADDRESS", addr)
            pw = st.secrets.get("GMAIL_APP_PASS", pw)
    except Exception:
        pass

    return addr, pw


def is_email_configured() -> bool:
    """メール送信が設定済みかどうか"""
    addr, pw = _get_gmail_credentials()
    return bool(addr and pw)


def send_result_email(to_email: str, subject: str, html_body: str,
                      sender_name: str = "占いモンスターくろたん") -> dict:
    """
    Gmail SMTP経由でHTML形式の鑑定結果メールを送信する。

    Returns:
        {"ok": True} or {"ok": False, "error": "エラーメッセージ"}
    """
    addr, pw = _get_gmail_credentials()
    if not addr or not pw:
        return {"ok": False, "error": "Gmail設定が未完了です（GMAIL_ADDRESS / GMAIL_APP_PASS）"}

    if not to_email or "@" not in to_email:
        return {"ok": False, "error": "有効なメールアドレスを入力してください"}

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{addr}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # プレーンテキスト版（HTMLタグ除去）
        import re
        plain = re.sub(r'<[^>]+>', '', html_body)
        plain = re.sub(r'\n{3,}', '\n\n', plain).strip()
        msg.attach(MIMEText(plain, "plain", "utf-8"))

        # HTML版
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(addr, pw)
            server.send_message(msg)

        return {"ok": True}

    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "Gmail認証に失敗しました。アプリパスワードを確認してください"}
    except Exception as e:
        return {"ok": False, "error": f"送信エラー: {e}"}


def build_email_html(title: str, subtitle: str, headline: str,
                     reading: str, closing: str) -> str:
    """鑑定結果をメール用HTML形式に変換する"""
    import html as _h
    import re
    from datetime import date

    reading_clean = re.sub(r'<[^>]+>', '', reading).strip() if reading else ""
    headline_clean = re.sub(r'<[^>]+>', '', headline).strip() if headline else ""
    closing_clean = re.sub(r'<[^>]+>', '', closing).strip() if closing else ""

    reading_html = _h.escape(reading_clean).replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_h.escape(title)}</title>
</head>
<body style="margin:0; padding:0; background-color:#0A0A0A; font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN','Hiragino Sans',Meiryo,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0A0A0A;">
<tr><td align="center" style="padding:30px 15px;">

<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%; background-color:#121212; border-radius:12px; border:1px solid #2A2A2A;">

  <!-- ヘッダー -->
  <tr><td style="padding:30px 30px 15px; text-align:center;">
    <div style="color:#BFA350; font-size:24px; font-weight:bold; letter-spacing:0.05em;">✦ 占いモンスターくろたん ✦</div>
  </td></tr>

  <!-- タイトル -->
  <tr><td style="padding:5px 30px 5px; text-align:center;">
    <div style="color:#F0EBE0; font-size:16px;">{_h.escape(title)}</div>
    <div style="color:#8A8478; font-size:13px; margin-top:4px;">{_h.escape(subtitle)}</div>
  </td></tr>

  <!-- 区切り線 -->
  <tr><td style="padding:15px 30px;">
    <div style="border-top:1px solid #2A2A2A;"></div>
  </td></tr>

  <!-- ヘッドライン -->
  {"<tr><td style='padding:5px 30px; text-align:center;'><div style='color:#D4B96A; font-size:18px; font-weight:bold;'>「" + _h.escape(headline_clean) + "」</div></td></tr>" if headline_clean else ""}

  <!-- 本文 -->
  <tr><td style="padding:15px 30px;">
    <div style="color:#F0EBE0; font-size:14px; line-height:2.0;">{reading_html}</div>
  </td></tr>

  <!-- クロージング -->
  {"<tr><td style='padding:10px 30px; text-align:center;'><div style='color:#8A8478; font-style:italic; font-size:14px;'>— " + _h.escape(closing_clean) + "</div></td></tr>" if closing_clean else ""}

  <!-- 区切り線 -->
  <tr><td style="padding:15px 30px;">
    <div style="border-top:1px solid #2A2A2A;"></div>
  </td></tr>

  <!-- フッター -->
  <tr><td style="padding:10px 30px 30px; text-align:center;">
    <div style="color:#5A5A5A; font-size:11px;">占いモンスターくろたん — {date.today().strftime('%Y/%m/%d')} 鑑定</div>
  </td></tr>

</table>

</td></tr>
</table>
</body>
</html>"""
