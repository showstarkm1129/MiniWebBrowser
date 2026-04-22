"""miniWebBrowser - エントリーポイント

PyQt6で空のウィンドウを表示する最小構成。
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow


class BrowserWindow(QMainWindow):
    """メインウィンドウクラス"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("miniWebBrowser")
        self.resize(800, 600)


def main():
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
