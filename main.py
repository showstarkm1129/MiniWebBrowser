"""miniWebBrowser - エントリーポイント

PyQt6でミニWebブラウザのUIを構築する。
"""

import sys

from fetcher import fetch_page
from parser import parse_html
from PyQt6.QtCore import QUrl
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


class BrowserWindow(QMainWindow):
    """メインウィンドウクラス"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("miniWebBrowser")
        self.resize(800, 600)
        self._current_url = ""
        self._init_ui()

    def _init_ui(self):
        """UIウィジェットを初期化・配置する"""
        # 中央ウィジェット
        central = QWidget()
        self.setCentralWidget(central)

        # メインレイアウト（縦並び）
        main_layout = QVBoxLayout(central)

        # --- 上部：URL入力欄 + Goボタン（横並び） ---
        nav_layout = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URLを入力してください")
        self.url_input.returnPressed.connect(self._on_go)

        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self._on_go)

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

    def _navigate(self, url: str):
        """指定URLに遷移する"""
        self._current_url = url
        self.url_input.setText(url)

        success, content = fetch_page(url)
        if success:
            styled_html = parse_html(content, base_url=url)
            self.text_area.setHtml(styled_html)
        else:
            self.text_area.setText(content)


def main():
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
