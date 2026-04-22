"""parser.py - HTML解析担当

HTMLを解析して、人間が読めるテキストを抽出する。
"""

import re
from bs4 import BeautifulSoup


def parse_html(html: str) -> str:
    """HTML文字列を解析し、整形済みプレーンテキストを返す。

    - <script>タグと<style>タグは除去
    - get_text()でテキストを抽出
    - 連続する空行は1行にまとめる

    Args:
        html: 解析対象のHTML文字列

    Returns:
        整形済みプレーンテキスト
    """
    soup = BeautifulSoup(html, "html.parser")

    # 不要なタグを除去
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # テキスト抽出（改行で区切る）
    text = soup.get_text(separator="\n")

    # 連続する空行を1行にまとめる
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 前後の空白を除去
    text = text.strip()

    return text
