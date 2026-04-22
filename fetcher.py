"""fetcher.py - HTTP通信担当

URLを受け取り、HTMLコンテンツを返す。
"""

import requests


def fetch_page(url: str, timeout: int = 5) -> tuple[bool, str]:
    """指定URLのHTMLを取得する。

    Args:
        url: 取得先のURL
        timeout: タイムアウト秒数（デフォルト5秒）

    Returns:
        (成功フラグ, HTMLまたはエラーメッセージ) のタプル
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        # 文字コード自動判定
        response.encoding = response.apparent_encoding

        return True, response.text

    except requests.exceptions.ConnectionError:
        return False, "エラー: 接続できませんでした。URLを確認してください。"
    except requests.exceptions.Timeout:
        return False, "エラー: 接続がタイムアウトしました。"
    except requests.exceptions.HTTPError as e:
        return False, f"エラー: HTTPエラーが発生しました（{e.response.status_code}）"
    except requests.exceptions.MissingSchema:
        return False, "エラー: URLの形式が正しくありません（http:// または https:// で始めてください）"
    except requests.exceptions.RequestException as e:
        return False, f"エラー: 通信中に問題が発生しました（{e}）"
