"""
鑑定結果メール送信モジュール

方式: Gmail作成画面をブラウザで直接開く（mailto: / Gmail URL）
→ 認証不要、Google Workspace でも確実に動作
"""
import re
import urllib.parse


def build_email_text(title: str, subtitle: str, headline: str,
                     reading: str, closing: str) -> str:
    """鑑定結果をプレーンテキスト形式に変換する"""
    from datetime import date

    reading_clean = re.sub(r'<[^>]+>', '', reading).strip() if reading else ""
    headline_clean = re.sub(r'<[^>]+>', '', headline).strip() if headline else ""
    closing_clean = re.sub(r'<[^>]+>', '', closing).strip() if closing else ""

    lines = ["✦ 占いモンスターくろたん ✦", ""]
    if title:
        lines.append(title)
    if subtitle:
        lines.append(subtitle)
    lines.append("")
    lines.append("━" * 30)
    lines.append("")
    if headline_clean:
        lines.append(f"「{headline_clean}」")
        lines.append("")
    if reading_clean:
        lines.append(reading_clean)
        lines.append("")
    if closing_clean:
        lines.append(f"— {closing_clean}")
        lines.append("")
    lines.append("━" * 30)
    lines.append(f"占いモンスターくろたん — {date.today().strftime('%Y/%m/%d')} 鑑定")
    return "\n".join(lines)


def build_gmail_url(to_email: str, subject: str, body: str) -> str:
    """Gmail作成画面のURLを生成する"""
    params = {
        "view": "cm",
        "to": to_email,
        "su": subject,
        "body": body,
    }
    return "https://mail.google.com/mail/?authuser=0&" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
