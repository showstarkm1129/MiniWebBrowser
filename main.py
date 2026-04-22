"""miniWebBrowser - エントリーポイント

PyQt6でミニWebブラウザのUIを構築する。
7-1: ローディング表示
7-2: 戻るボタン（履歴管理）
7-3: ウィンドウタイトル連動
7-4: QThreadによる非同期通信
履歴パネル: サイドに閲覧履歴リストを表示
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
    QSplitter,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QListWidget,
    QListWidgetItem,
    QLabel,
)
from PyQt6.QtCore import Qt


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
        self.resize(1000, 650)
        self._current_url = ""
        self._history = []          # 戻る用の履歴スタック（URLのリスト）
        self._history_log = []      # 表示用の履歴ログ（URL, タイトル）のリスト
        self._worker = None         # 現在のワーカースレッド
        self._init_ui()

    def _init_ui(self):
        """UIウィジェットを初期化・配置する"""
        # 中央ウィジェット
        central = QWidget()
        self.setCentralWidget(central)

        # メインレイアウト（縦並び）
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # --- 上部ナビゲーションバー ---
        nav_layout = QHBoxLayout()

        self.back_button = QPushButton("← 戻る")
        self.back_button.setFixedWidth(80)
        self.back_button.clicked.connect(self._on_back)
        self.back_button.setEnabled(False)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URLを入力してください")
        self.url_input.returnPressed.connect(self._on_go)

        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self._on_go)

        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.url_input)
        nav_layout.addWidget(self.go_button)
        main_layout.addLayout(nav_layout)

        # --- 下部：左に履歴パネル、右にコンテンツ（QSplitterで可変幅） ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 履歴パネル（左）
        history_panel = QWidget()
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(2)

        history_label = QLabel("📋 閲覧履歴")
        history_label.setStyleSheet("font-weight: bold; padding: 4px;")
        history_layout.addWidget(history_label)

        self.history_list = QListWidget()
        self.history_list.setWordWrap(True)
        self.history_list.itemDoubleClicked.connect(self._on_history_item_clicked)
        self.history_list.setToolTip("ダブルクリックでページを再表示")
        history_layout.addWidget(self.history_list)

        clear_button = QPushButton("履歴をクリア")
        clear_button.clicked.connect(self._on_clear_history)
        history_layout.addWidget(clear_button)

        splitter.addWidget(history_panel)

        # コンテンツエリア（右）
        self.text_area = QTextBrowser()
        self.text_area.setOpenLinks(False)
        self.text_area.anchorClicked.connect(self._on_link_clicked)
        splitter.addWidget(self.text_area)

        # 初期幅比率：履歴パネル220px : コンテンツ残り
        splitter.setSizes([220, 780])

        main_layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_go(self):
        """Goボタン押下（またはEnterキー）時の処理"""
        url = self.url_input.text().strip()
        if not url:
            return
        self._navigate(url)

    def _on_link_clicked(self, qurl: QUrl):
        """テキスト内のリンクがクリックされた時の処理"""
        self._navigate(qurl.toString())

    def _on_back(self):
        """戻るボタン押下時の処理"""
        if len(self._history) >= 2:
            self._history.pop()
            prev_url = self._history.pop()
            self._navigate(prev_url)

    def _on_history_item_clicked(self, item: QListWidgetItem):
        """履歴アイテムをダブルクリックした時の処理"""
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self._navigate(url)

    def _on_clear_history(self):
        """履歴クリアボタン押下時の処理"""
        self._history_log.clear()
        self.history_list.clear()

    # ------------------------------------------------------------------
    # ナビゲーション
    # ------------------------------------------------------------------

    def _navigate(self, url: str):
        """指定URLに非同期で遷移する"""
        self.text_area.setText("読み込み中...")
        self._current_url = url
        self.url_input.setText(url)

        self.go_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.back_button.setEnabled(False)

        self._worker = FetchWorker(url)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.start()

    def _on_fetch_finished(self, success: bool, content: str, url: str):
        """HTTP通信完了時の処理"""
        self.go_button.setEnabled(True)
        self.url_input.setEnabled(True)

        if success:
            title = get_title(content)
            display_title = title if title else url

            # ウィンドウタイトル更新
            self.setWindowTitle(f"{display_title} - miniWebBrowser")

            # コンテンツ表示
            styled_html = parse_html(content, base_url=url)
            self.text_area.setHtml(styled_html)

            # 戻るボタン用の履歴スタックに追加
            self._history.append(url)

            # 履歴ログに追加（重複は除かず、時系列順に記録）
            self._history_log.append((url, display_title))
            self._add_history_item(url, display_title)

        else:
            self.setWindowTitle("miniWebBrowser")
            self.text_area.setText(content)

        self.back_button.setEnabled(len(self._history) >= 2)
        self._worker = None

    def _add_history_item(self, url: str, title: str):
        """履歴リストの先頭に新しいアイテムを追加する"""
        # 表示テキスト：タイトル（短縮）とURL
        short_title = title if len(title) <= 30 else title[:28] + "…"
        item = QListWidgetItem(f"{short_title}\n{url}")
        item.setData(Qt.ItemDataRole.UserRole, url)  # URLをメタデータとして保持
        item.setToolTip(url)
        # 最新を先頭に挿入
        self.history_list.insertItem(0, item)


def main():
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
