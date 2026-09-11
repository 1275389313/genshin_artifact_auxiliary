'''参数设置页面'''

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFormLayout, QLineEdit, QCheckBox, QHBoxLayout
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator
from doc import coefficient_path, load_settings, save_settings
import json, score

class SettingsPage(QWidget):
    go_back = Signal()
    settings_saved = Signal(dict)

    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.form_layout = QFormLayout()

        hint = QLabel('贴图主数字是有效词条。下面系数只用于可选的旧版 30/40/50 评分。')
        hint.setWordWrap(True)
        self.form_layout.addRow(hint)

        self.hotkey_edit = QLineEdit('f8')
        self.hotkey_edit.setPlaceholderText('例如 f8')
        self.form_layout.addRow(QLabel('五件扫描快捷键'), self.hotkey_edit)

        self.delay_edit = QLineEdit('450')
        self.delay_edit.setValidator(QIntValidator(200, 3000))
        self.form_layout.addRow(QLabel('扫描点击间隔(ms)'), self.delay_edit)

        self.old_score_check = QCheckBox('显示旧版加权评分（默认关闭）')
        self.form_layout.addRow(self.old_score_check)

        # 创建表单控件
        self.line_edits = {}
        for key, value in score.coefficient.items():
            label = QLabel(key)
            line_edit = QLineEdit(str(value))
            line_edit.setValidator(QDoubleValidator())  # 限制输入为浮点数
            self.line_edits[key] = line_edit
            self.form_layout.addRow(label, line_edit)

        buttons = QHBoxLayout()
        save_button = QPushButton("保存设置")
        save_button.clicked.connect(self.save_settings)
        back_button = QPushButton("返回")
        back_button.clicked.connect(self.go_back.emit)
        buttons.addWidget(save_button)
        buttons.addWidget(back_button)
        self.form_layout.addRow(buttons)

        self.setLayout(self.form_layout)
        self.reload_fields()

    def showEvent(self, event):
        self.reload_fields()
        super().showEvent(event)

    def reload_fields(self):
        settings = load_settings()
        self.hotkey_edit.setText(str(settings.get('scan_hotkey') or 'f8'))
        self.delay_edit.setText(str(settings.get('scan_delay_ms') or 450))
        self.old_score_check.setChecked(bool(settings.get('show_old_score')))
        for key, line_edit in self.line_edits.items():
            if key in score.coefficient:
                line_edit.setText(str(score.coefficient[key]))
    
    def save_settings(self):
        # 从表单中读取用户输入的值
        new_coefficient = {}
        for key, line_edit in self.line_edits.items():
            try:
                new_coefficient[key] = float(line_edit.text())
            except ValueError:
                new_coefficient[key] = score.coefficient[key]  # 如果输入无效，保留原值

        # 更新变量
        score.coefficient = new_coefficient

        # 更新配置文件
        with open(coefficient_path, "w", encoding = 'utf-8') as f:
            json.dump(new_coefficient, f, ensure_ascii = False)

        try:
            delay_ms = int(self.delay_edit.text())
        except ValueError:
            delay_ms = 450
        settings = {
            'scan_hotkey': (self.hotkey_edit.text() or 'f8').strip().lower(),
            'show_old_score': self.old_score_check.isChecked(),
            'scan_delay_ms': delay_ms,
        }
        save_settings(settings)
        self.settings_saved.emit(settings)

        # 关闭设置页面
        self.go_back.emit()
