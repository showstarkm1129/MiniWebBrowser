"""miniWebBrowser - エントリーポイント

PyQt6でミニWebブラウザのUIを構築する。

フェーズ1追加機能:
- 進むボタン（_forward_stack による履歴管理）
- 再読み込みボタン（F5ショートカット対応）
- URL欄クリックで全選択（UrlLineEdit）
"""

import sys

from fetcher import fetch_page
from parser import parse_html, get_title
from PyQt6.QtCore import QUrl, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
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


class FetchWorker(QThread):
    """HTTP通信をバックグラウンドで実行するワーカースレッド。"""

    finished = pyqtSignal(bool, str, str)  # (成功フラグ, コンテンツ, URL)

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def run(self):
        success, content = fetch_page(self._url)
        self.finished.emit(success, content, self._url)


class UrlLineEdit(QLineEdit):
    """クリックで全選択するURL入力欄"""

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()


class BrowserWindow(QMainWindow):
    """メインウィンドウクラス"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("miniWebBrowser")
        self.resize(900, 650)
        self._current_url = ""
        self._history = []        # 戻るボタン用スタック（現在URLを含まない）
        self._forward_stack = []  # 進むボタン用スタック
        self._history_log = []    # 表示用の履歴ログ
        self._worker = None
        self._history_visible = False
        self._init_ui()

    def _init_ui(self):
        """UIウィジェットを初期化・配置する"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # --- ナビゲーションバー ---
        nav_layout = QHBoxLayout()

        self.back_button = QPushButton("← 戻る")
        self.back_button.setFixedWidth(80)
        self.back_button.clicked.connect(self._on_back)
        self.back_button.setEnabled(False)

        self.forward_button = QPushButton("進む →")
        self.forward_button.setFixedWidth(80)
        self.forward_button.clicked.connect(self._on_forward)
        self.forward_button.setEnabled(False)

        self.url_input = UrlLineEdit()
        self.url_input.setPlaceholderText("URLを入力してください")
        self.url_input.returnPressed.connect(self._on_go)

        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self._on_go)

        self.reload_button = QPushButton("↺ 再読込")
        self.reload_button.setFixedWidth(80)
        self.reload_button.clicked.connect(self._on_reload)
        self.reload_button.setEnabled(False)

        self.history_toggle_button = QPushButton("📋 履歴")
        self.history_toggle_button.setFixedWidth(80)
        self.history_toggle_button.setCheckable(True)
        self.history_toggle_button.clicked.connect(self._on_toggle_history)

        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.url_input)
        nav_layout.addWidget(self.go_button)
        nav_layout.addWidget(self.reload_button)
        nav_layout.addWidget(self.history_toggle_button)
        main_layout.addLayout(nav_layout)

        # F5 ショートカット
        QShortcut(QKeySequence("F5"), self).activated.connect(self._on_reload)

        # --- コンテンツ + 履歴パネル（QSplitter） ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.text_area = QTextBrowser()
        self.text_area.setOpenLinks(False)
        self.text_area.anchorClicked.connect(self._on_link_clicked)
        self.splitter.addWidget(self.text_area)

        # 履歴パネル（右）
        history_panel = QWidget()
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(4, 4, 4, 4)
        history_layout.setSpacing(4)

        history_label = QLabel("📋 閲覧履歴")
        history_label.setStyleSheet("font-weight: bold; padding: 2px 4px;")
        history_layout.addWidget(history_label)

        self.history_list = QListWidget()
        self.history_list.setWordWrap(True)
        self.history_list.setToolTip("ダブルクリックでページを再表示")
        self.history_list.itemDoubleClicked.connect(self._on_history_item_clicked)
        history_layout.addWidget(self.history_list)

        clear_button = QPushButton("履歴をクリア")
        clear_button.clicked.connect(self._on_clear_history)
        history_layout.addWidget(clear_button)

        self.splitter.addWidget(history_panel)

        self.history_panel = history_panel
        history_panel.hide()

        main_layout.addWidget(self.splitter)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_go(self):
        url = self.url_input.text().strip()
        if not url:
            return
        self._navigate(url)

    def _on_link_clicked(self, qurl: QUrl):
        self._navigate(qurl.toString())

    def _on_back(self):
        if self._history:
            self._forward_stack.append(self._current_url)
            prev_url = self._history.pop()
            self._start_fetch(prev_url)

    def _on_forward(self):
        if self._forward_stack:
            self._history.append(self._current_url)
            next_url = self._forward_stack.pop()
            self._start_fetch(next_url)

    def _on_reload(self):
        if self._current_url:
            self._start_fetch(self._current_url)

    def _on_toggle_history(self):
        """履歴パネルの表示/非表示を切り替える"""
        self._history_visible = self.history_toggle_button.isChecked()
        if self._history_visible:
            self.history_panel.show()
            self.splitter.setSizes([680, 220])
        else:
            self.history_panel.hide()

    def _on_history_item_clicked(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self._navigate(url)

    def _on_clear_history(self):
        self._history_log.clear()
        self.history_list.clear()

    # ------------------------------------------------------------------
    # ナビゲーション
    # ------------------------------------------------------------------

    def _navigate(self, url: str):
        """通常遷移：現在URLを戻るスタックに積み、進むスタックをクリアしてフェッチ開始"""
        if self._current_url:
            self._history.append(self._current_url)
        self._forward_stack.clear()
        self._start_fetch(url)

    def _start_fetch(self, url: str):
        """履歴操作なしでフェッチを開始する（戻る・進む・再読込から呼ばれる）"""
        self.text_area.setText("読み込み中...")
        self._current_url = url
        self.url_input.setText(url)

        self.go_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.back_button.setEnabled(False)
        self.forward_button.setEnabled(False)
        self.reload_button.setEnabled(False)

        self._worker = FetchWorker(url)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.start()

    def _on_fetch_finished(self, success: bool, content: str, url: str):
        self.go_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.reload_button.setEnabled(True)

        if success:
            title = get_title(content)
            display_title = title if title else url

            self.setWindowTitle(f"{display_title} - miniWebBrowser")
            styled_html = parse_html(content, base_url=url)
            self.text_area.setHtml(styled_html)

            self._history_log.append((url, display_title))
            self._add_history_item(url, display_title)
        else:
            self.setWindowTitle("miniWebBrowser")
            self.text_area.setText(content)

        self.back_button.setEnabled(len(self._history) > 0)
        self.forward_button.setEnabled(len(self._forward_stack) > 0)
        self._worker = None

    def _add_history_item(self, url: str, title: str):
        short_title = title if len(title) <= 30 else title[:28] + "…"
        item = QListWidgetItem(f"{short_title}\n{url}")
        item.setData(Qt.ItemDataRole.UserRole, url)
        item.setToolTip(url)
        self.history_list.insertItem(0, item)


def main():
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
