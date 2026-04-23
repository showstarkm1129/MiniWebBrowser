"""miniWebBrowser - エントリーポイント

PyQt6でミニWebブラウザのUIを構築する。

セッション4-A：BrowserTab 切り出し（リファクタリング）
- BrowserTab(QWidget) にナビゲーション状態・ロジックを集約
- BrowserWindow はUI制御のみ担当し、BrowserTab のシグナルで連動
- 見た目・動作はフェーズ1完成時と同一
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


class BrowserTab(QWidget):
    """1タブ分のコンテンツと状態を管理するウィジェット。

    シグナルで BrowserWindow に通知し、Window 側は状態を持たない。
    """

    url_changed = pyqtSignal(str)               # URL バー更新
    title_changed = pyqtSignal(str)             # ウィンドウタイトル更新
    nav_state_changed = pyqtSignal(bool, bool)  # (back_enabled, forward_enabled) + ロード完了通知
    load_started = pyqtSignal()                 # ロード開始（ボタン無効化）
    page_loaded = pyqtSignal(str, str)          # (url, display_title) 履歴パネル追加用

    def __init__(self):
        super().__init__()
        self._current_url = ""
        self._history = []        # 戻るボタン用スタック（現在URLを含まない）
        self._forward_stack = []  # 進むボタン用スタック
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.text_area = QTextBrowser()
        self.text_area.setOpenLinks(False)
        self.text_area.anchorClicked.connect(self._on_link_clicked)
        layout.addWidget(self.text_area)

    # --- プロパティ ---

    @property
    def current_url(self) -> str:
        return self._current_url

    @property
    def can_go_back(self) -> bool:
        return len(self._history) > 0

    @property
    def can_go_forward(self) -> bool:
        return len(self._forward_stack) > 0

    # --- スロット ---

    def _on_link_clicked(self, qurl: QUrl):
        self.navigate(qurl.toString())

    # --- ナビゲーション（BrowserWindow から呼ばれる） ---

    def navigate(self, url: str):
        """通常遷移：現在URLを戻るスタックに積み、進むスタックをクリア"""
        if self._current_url:
            self._history.append(self._current_url)
        self._forward_stack.clear()
        self._start_fetch(url)

    def go_back(self):
        if self._history:
            self._forward_stack.append(self._current_url)
            self._start_fetch(self._history.pop())

    def go_forward(self):
        if self._forward_stack:
            self._history.append(self._current_url)
            self._start_fetch(self._forward_stack.pop())

    def reload(self):
        if self._current_url:
            self._start_fetch(self._current_url)

    # --- 内部フェッチ処理 ---

    def _start_fetch(self, url: str):
        """履歴操作なしでフェッチを開始する"""
        self._current_url = url
        self.text_area.setText("読み込み中...")
        self.url_changed.emit(url)
        self.load_started.emit()

        self._worker = FetchWorker(url)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.start()

    def _on_fetch_finished(self, success: bool, content: str, url: str):
        if success:
            title = get_title(content)
            display_title = title if title else url
            self.title_changed.emit(f"{display_title} - miniWebBrowser")
            styled_html = parse_html(content, base_url=url)
            self.text_area.setHtml(styled_html)
            self.page_loaded.emit(url, display_title)
        else:
            self.title_changed.emit("miniWebBrowser")
            self.text_area.setText(content)

        self.nav_state_changed.emit(self.can_go_back, self.can_go_forward)
        self._worker = None


class BrowserWindow(QMainWindow):
    """メインウィンドウ。UIの配置と BrowserTab との連動を担当する。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("miniWebBrowser")
        self.resize(900, 650)
        self._history_log = []
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

        QShortcut(QKeySequence("F5"), self).activated.connect(self._on_reload)

        # --- コンテンツ + 履歴パネル（QSplitter） ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tab = BrowserTab()
        self._connect_tab(self.tab)
        self.splitter.addWidget(self.tab)

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

    def _connect_tab(self, tab: BrowserTab):
        """BrowserTab のシグナルを Window の各スロットに接続する"""
        tab.url_changed.connect(self.url_input.setText)
        tab.title_changed.connect(self.setWindowTitle)
        tab.load_started.connect(self._on_load_started)
        tab.nav_state_changed.connect(self._on_nav_state_changed)
        tab.page_loaded.connect(self._add_history_item)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_go(self):
        url = self.url_input.text().strip()
        if not url:
            return
        self.tab.navigate(url)

    def _on_back(self):
        self.tab.go_back()

    def _on_forward(self):
        self.tab.go_forward()

    def _on_reload(self):
        self.tab.reload()

    def _on_load_started(self):
        """ロード中はすべての操作ボタンを無効化する"""
        self.go_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.back_button.setEnabled(False)
        self.forward_button.setEnabled(False)
        self.reload_button.setEnabled(False)

    def _on_nav_state_changed(self, back_enabled: bool, forward_enabled: bool):
        """ロード完了後にボタン状態を復元する"""
        self.go_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.reload_button.setEnabled(True)
        self.back_button.setEnabled(back_enabled)
        self.forward_button.setEnabled(forward_enabled)

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
            self.tab.navigate(url)

    def _on_clear_history(self):
        self._history_log.clear()
        self.history_list.clear()

    def _add_history_item(self, url: str, title: str):
        self._history_log.append((url, title))
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
