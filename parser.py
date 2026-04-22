"""parser.py - HTML解析担当

HTMLを解析して、QTextBrowser用の簡易HTMLに変換する。
"""

from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag


# 除去するタグ一覧
_REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]


def _render_inline(element, base_url: str) -> str:
    """要素内のテキストとリンクをインライン展開する。

    <a>タグはリンクとして保持し、相対URLを絶対URLに変換する。
    """
    parts = []
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                parts.append(text)
        elif isinstance(child, Tag):
            if child.name == "a" and child.get("href"):
                href = urljoin(base_url, child["href"])
                link_text = child.get_text(strip=True)
                if link_text:
                    parts.append(f'<a href="{href}">{link_text}</a>')
            else:
                # 再帰的にインライン展開
                inner = _render_inline(child, base_url)
                if inner:
                    parts.append(inner)
    return " ".join(parts)


def parse_html(html: str, base_url: str = "") -> str:
    """HTML文字列を解析し、QTextBrowser用の簡易HTMLを返す。

    - h1は大きく、h2は中くらい、h3は少し大きめ
    - p, li, その他のテキストは普通サイズ
    - <a>タグのリンクを保持（相対URL→絶対URL変換）
    - 不要なタグ（script, style, nav, footer等）は除去

    Args:
        html: 解析対象のHTML文字列
        base_url: 相対URL変換用のベースURL

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

        if tag_name == "h1":
            content = _render_inline(element, base_url)
            if content:
                output_parts.append(
                    f'<h1 style="font-size: 24px; font-weight: bold; '
                    f'margin: 16px 0 8px 0;">{content}</h1>'
                )

        elif tag_name == "h2":
            content = _render_inline(element, base_url)
            if content:
                output_parts.append(
                    f'<h2 style="font-size: 20px; font-weight: bold; '
                    f'margin: 12px 0 6px 0;">{content}</h2>'
                )

        elif tag_name == "h3":
            content = _render_inline(element, base_url)
            if content:
                output_parts.append(
                    f'<h3 style="font-size: 17px; font-weight: bold; '
                    f'margin: 10px 0 5px 0;">{content}</h3>'
                )

        elif tag_name in ("h4", "h5", "h6"):
            content = _render_inline(element, base_url)
            if content:
                output_parts.append(
                    f'<p style="font-size: 15px; font-weight: bold; '
                    f'margin: 8px 0 4px 0;">{content}</p>'
                )

        elif tag_name == "p":
            content = _render_inline(element, base_url)
            if content:
                output_parts.append(
                    f'<p style="font-size: 14px; margin: 6px 0;">{content}</p>'
                )

        elif tag_name == "li":
            content = _render_inline(element, base_url)
            if content:
                output_parts.append(
                    f'<p style="font-size: 14px; margin: 3px 0 3px 20px;">'
                    f'• {content}</p>'
                )

    # 空の場合はフォールバック
    if not output_parts:
        text = soup.get_text(separator="\n", strip=True)
        if text:
            output_parts.append(f'<p style="font-size: 14px;">{text}</p>')

    return "\n".join(output_parts)


def get_title(html: str) -> str:
    """HTMLから<title>タグの内容を取得する。

    Args:
        html: HTML文字列

    Returns:
        タイトル文字列（見つからない場合は空文字列）
    """
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    return ""
