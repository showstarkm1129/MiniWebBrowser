"""miniWebBrowser - エントリーポイント

PyQt6でミニWebブラウザのUIを構築する。
7-1: ローディング表示
7-2: 戻るボタン（履歴管理）
7-3: ウィンドウタイトル連動
7-4: QThreadによる非同期通信
"""

import sys

from fetcher import fetch_page
from parser import parse_html, get_title
from PyQt6.QtCore import QUrl, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextBrowser,
)


class FetchWorker(QThread):
    """HTTP通信をバックグラウンドで実行するワーカースレッド。

    UIスレッドをブロックせずにWebページを取得するために、
    QThreadを使用して通信処理を別スレッドで実行する。
    通信完了時にfinishedシグナルで結果を返す。
    """

    finished = pyqtSignal(bool, str, str)  # (成功フラグ, コンテンツ, URL)

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def run(self):
        """バックグラウンドでHTTP通信を実行する"""
        success, content = fetch_page(self._url)
        self.finished.emit(success, content, self._url)


class BrowserWindow(QMainWindow):
    """メインウィンドウクラス"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("miniWebBrowser")
        self.resize(800, 600)
        self._current_url = ""
        self._history = []  # 閲覧履歴（URLのリスト）
        self._worker = None  # 現在のワーカースレッド
        self._init_ui()

    def _init_ui(self):
        """UIウィジェットを初期化・配置する"""
        # 中央ウィジェット
        central = QWidget()
        self.setCentralWidget(central)

        # メインレイアウト（縦並び）
        main_layout = QVBoxLayout(central)

        # --- 上部：戻るボタン + URL入力欄 + Goボタン（横並び） ---
        nav_layout = QHBoxLayout()

        # 【7-2】戻るボタン
        self.back_button = QPushButton("← 戻る")
        self.back_button.setFixedWidth(80)
        self.back_button.clicked.connect(self._on_back)
        self.back_button.setEnabled(False)  # 初期状態は無効

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URLを入力してください")
        self.url_input.returnPressed.connect(self._on_go)

        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self._on_go)

        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.url_input)
        nav_layout.addWidget(self.go_button)
        main_layout.addLayout(nav_layout)

        # --- 下部：テキスト表示エリア ---
        self.text_area = QTextBrowser()
        self.text_area.setOpenLinks(False)  # リンクを自動で開かない
        self.text_area.anchorClicked.connect(self._on_link_clicked)
        main_layout.addWidget(self.text_area)

    def _on_go(self):
        """Goボタン押下（またはEnterキー）時の処理"""
        url = self.url_input.text().strip()
        if not url:
            return
        self._navigate(url)

    def _on_link_clicked(self, qurl: QUrl):
        """テキスト内のリンクがクリックされた時の処理"""
        url = qurl.toString()
        self._navigate(url)

    def _on_back(self):
        """【7-2】戻るボタン押下時の処理"""
        if len(self._history) >= 2:
            # 現在のページを除去し、前のページに戻る
            self._history.pop()
            prev_url = self._history.pop()
            self._navigate(prev_url)

    def _navigate(self, url: str):
        """【7-4】指定URLに非同期で遷移する"""
        # 【7-1】ローディング表示
        self.text_area.setText("読み込み中...")
        self._current_url = url
        self.url_input.setText(url)

        # UIの操作を無効化（通信中）
        self.go_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.back_button.setEnabled(False)

        # バックグラウンドでHTTP通信を実行
        self._worker = FetchWorker(url)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.start()

    def _on_fetch_finished(self, success: bool, content: str, url: str):
        """HTTP通信完了時の処理"""
        # UIの操作を再有効化
        self.go_button.setEnabled(True)
        self.url_input.setEnabled(True)

        if success:
            # 【7-3】ウィンドウタイトルにページタイトルを反映
            title = get_title(content)
            if title:
                self.setWindowTitle(f"{title} - miniWebBrowser")
            else:
                self.setWindowTitle("miniWebBrowser")

            styled_html = parse_html(content, base_url=url)
            self.text_area.setHtml(styled_html)

            # 【7-2】履歴に追加
            self._history.append(url)
        else:
            self.setWindowTitle("miniWebBrowser")
            self.text_area.setText(content)

        # 【7-2】戻るボタンの有効/無効を更新
        self.back_button.setEnabled(len(self._history) >= 2)

        # ワーカーの後片付け
        self._worker = None


def main():
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
