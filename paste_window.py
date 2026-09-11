'''贴图窗口，显示单独的评分结果'''

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget
import location

scale = location.w_width / 1280 / location.SCALE

class PasteWindow(QWidget):
    def __init__(self):
        super().__init__()

        # 设置贴图窗口属性：透明、无边框透明、置顶
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    
        # 贴图窗口内容
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel('Er!')
        # 字体大小
        font = self.label.font()
        font.setPointSize(9 * scale)
        self.label.setFont(font)
        self.label.setFixedSize(24 * scale, 24 * scale)
        self.label.setAlignment(Qt.AlignCenter)
        # qss = 'border-image: url(paste.png);'
        qss = 'background-color: rgb(255, 255, 255)'
        self.label.setStyleSheet(qss)
        layout.addWidget(self.label)
        self.setLayout(layout)

        # 快捷键Ctrl+Z关闭贴图窗口，需焦点在主窗口
        self.shortcut = QShortcut(QKeySequence('Ctrl+Z'), self)
        self.shortcut.activated.connect(self.close)

    def close(self):
        self.hide()


class TotalPasteWindow(QWidget):
    '''角色页合计贴图，比单件评分框更宽。'''

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel('有效词条 0.0')
        font = self.label.font()
        font.setPointSize(max(8, int(10 * scale)))
        self.label.setFont(font)
        self.label.setFixedSize(int(180 * scale), int(28 * scale))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet('background-color: rgb(255, 255, 255)')
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.shortcut = QShortcut(QKeySequence('Ctrl+Z'), self)
        self.shortcut.activated.connect(self.hide)

    def close(self):
        self.hide()