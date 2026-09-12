'''主窗口'''

import sys, os
import ctypes

def _set_process_dpi_awareness_early():
    '''在导入 Qt / 读取窗口矩形之前设 Per-Monitor V2，截图、点击、贴图共用物理像素。'''
    if os.name != 'nt':
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

_set_process_dpi_awareness_early()

import qdarktheme
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QStackedLayout, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from main_page import MainPage
from settings_page import SettingsPage

# 角色下拉 + 扫描/清除行 + 五件只读摘要（可两行）+ 页脚；仍可手动缩放。
DEFAULT_WINDOW_SIZE = QSize(480, 620)
MIN_WINDOW_SIZE = QSize(400, 480)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), 'src/keqing.ico')))
        self.setWindowTitle("刻晴办公桌")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(MIN_WINDOW_SIZE)
        self.resize(DEFAULT_WINDOW_SIZE)
        self.move(0, 0)

        self.stacked_layout = QStackedLayout()
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)

        self.main_page = MainPage()
        self.settings_page = SettingsPage()

        self.stacked_layout.addWidget(self.main_page)
        self.stacked_layout.addWidget(self.settings_page)

        self.main_page.open_settings.connect(self.show_settings)
        self.settings_page.go_back.connect(self.show_main)
        self.settings_page.settings_saved.connect(self.main_page.apply_settings)

        central_widget = QWidget()
        central_widget.setLayout(self.stacked_layout)
        self.setCentralWidget(central_widget)
        self._keep_usable_size()

    def _keep_usable_size(self, previous=None):
        '''adjustSize() 会跟内容收缩；保证不小于默认，且不丢掉用户已经拉大的尺寸。'''
        w = max(self.width(), DEFAULT_WINDOW_SIZE.width())
        h = max(self.height(), DEFAULT_WINDOW_SIZE.height())
        if previous is not None:
            w = max(w, previous.width())
            h = max(h, previous.height())
        hint = self.sizeHint()
        w = max(w, hint.width())
        h = max(h, hint.height())
        self.resize(w, h)

    def show_settings(self):
        previous = self.size()
        self.main_page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.settings_page.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.stacked_layout.setCurrentWidget(self.settings_page)
        self.adjustSize()
        self._keep_usable_size(previous)

    def show_main(self):
        previous = self.size()
        self.main_page.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.settings_page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.stacked_layout.setCurrentWidget(self.main_page)
        self.adjustSize()
        self._keep_usable_size(previous)

def main():

    app = QApplication(sys.argv)
    app.setStyleSheet(qdarktheme.load_stylesheet("light"))
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == '__main__':
    main()