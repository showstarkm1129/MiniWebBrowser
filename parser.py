"""parser.py - HTML解析担当

HTMLを解析して、QTextBrowser用の簡易HTMLに変換する。
"""

from bs4 import BeautifulSoup, Tag


# 除去するタグ一覧
_REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]

# 保持するタグ（見出し・段落・リスト等）
_KEEP_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "ul", "ol", "br", "hr"}


def parse_html(html: str) -> str:
    """HTML文字列を解析し、QTextBrowser用の簡易HTMLを返す。

    - h1は大きく、h2は中くらい、h3は少し大きめ
    - p, li, その他のテキストは普通サイズ
    - 不要なタグ（script, style, nav, footer等）は除去

    Args:
        html: 解析対象のHTML文字列

    Returns:
        QTextBrowser表示用のHTML文字列
    """
    soup = BeautifulSoup(html, "html.parser")

    # 不要なタグを除去
    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()

    # 簡易HTMLを構築
    output_parts = []

    for element in soup.find_all(True):
        tag_name = element.name

        if tag_name in ("h1",):
            text = element.get_text(strip=True)
            if text:
                output_parts.append(
                    f'<h1 style="font-size: 24px; font-weight: bold; '
                    f'margin: 16px 0 8px 0;">{text}</h1>'
                )

        elif tag_name in ("h2",):
            text = element.get_text(strip=True)
            if text:
                output_parts.append(
                    f'<h2 style="font-size: 20px; font-weight: bold; '
                    f'margin: 12px 0 6px 0;">{text}</h2>'
                )

        elif tag_name in ("h3",):
            text = element.get_text(strip=True)
            if text:
                output_parts.append(
                    f'<h3 style="font-size: 17px; font-weight: bold; '
                    f'margin: 10px 0 5px 0;">{text}</h3>'
                )

        elif tag_name in ("h4", "h5", "h6"):
            text = element.get_text(strip=True)
            if text:
                output_parts.append(
                    f'<p style="font-size: 15px; font-weight: bold; '
                    f'margin: 8px 0 4px 0;">{text}</p>'
                )

        elif tag_name == "p":
            text = element.get_text(strip=True)
            if text:
                output_parts.append(
                    f'<p style="font-size: 14px; margin: 6px 0;">{text}</p>'
                )

        elif tag_name == "li":
            text = element.get_text(strip=True)
            if text:
                output_parts.append(
                    f'<p style="font-size: 14px; margin: 3px 0 3px 20px;">'
                    f'• {text}</p>'
                )

    # 空の場合はフォールバック
    if not output_parts:
        text = soup.get_text(separator="\n", strip=True)
        if text:
            output_parts.append(f'<p style="font-size: 14px;">{text}</p>')

    return "\n".join(output_parts)
