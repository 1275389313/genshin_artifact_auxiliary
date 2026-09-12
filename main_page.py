'''主页面：角色装配页五件扫描与只读结果'''

import requests, json
from pynput import keyboard

from pynput.mouse import Button as MouseButton, Controller as MouseController

import doc, location, ocr, score, effective_rolls, equipped
from extention import ExtendedComboBox
from paste_window import PasteWindow, TotalPasteWindow

from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QLabel, QPushButton, QWidget, QGridLayout, QApplication
)


class MainPage(QWidget):
    open_settings = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_data()
        self.init_events()

    def init_ui(self):
        self.settingbtn = QPushButton('设置')
        self.settingbtn.clicked.connect(self.open_settings.emit)

        self.combobox = ExtendedComboBox()

        self.scanbtn = QPushButton('扫描五件 (F8)')
        self.clearbtn = QPushButton('清除贴图')
        self.clearbtn.setToolTip('隐藏游戏窗口上的有效词条贴图（Ctrl+Shift+Z），不删除已保存的扫描')
        self.set_total = QLabel('有效词条 0.0（0/5）')
        self.notice = QLabel('')
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet('color: #a15c00')

        self.slot_summary = []
        for _ in range(equipped.SLOT_COUNT):
            label = QLabel()
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.slot_summary.append(label)

        self.upgrade = QLabel()
        self.github = QLabel()
        self.github.setFixedSize(20, 20)
        pixmap = QPixmap('src/GitHub.png')
        pixmap = pixmap.scaled(16, 16)
        self.github.setPixmap(pixmap)

        self.layout = QGridLayout()
        self.layout.addWidget(self.combobox, 0, 0, 1, 3)
        self.layout.addWidget(self.settingbtn, 0, 3, Qt.AlignRight)
        self.layout.addWidget(self.scanbtn, 1, 0, 1, 2)
        self.layout.addWidget(self.clearbtn, 1, 2)
        self.layout.addWidget(self.set_total, 1, 3, Qt.AlignRight)
        self.layout.addWidget(self.notice, 2, 0, 1, 4)
        for i, label in enumerate(self.slot_summary):
            self.layout.addWidget(label, 3 + i, 0, 1, 4)
        self.layout.addWidget(self.upgrade, 8, 0, 1, 2, Qt.AlignLeft | Qt.AlignBottom)
        self.layout.addWidget(self.github, 8, 3, Qt.AlignRight | Qt.AlignBottom)
        self.setLayout(self.layout)

    def init_data(self):
        # 角色装配页坐标：详情 OCR + 五部位点击/贴图
        self.x_grab, self.y_grab, self.w_grab, self.h_grab = (
            location.x_grab_B, location.y_grab_B, location.w_grab_B, location.h_grab_B)
        self.SCALE = location.SCALE
        self.slot_click = location.slot_click_B
        self.slot_overlay = location.slot_overlay_B
        self.total_overlay = location.total_overlay_B

        self.equipped_artifact = equipped.empty_slots()
        self.equipped_rolls = equipped.empty_slots()
        self._scanning = False
        self._scan_index = 0
        self._scan_character = ''
        self._scan_hotkeys = None
        self._show_game_overlays = False
        self._mouse = MouseController()
        self.app_settings = doc.load_settings()

        self.slot_pastes = []
        for i in range(equipped.SLOT_COUNT):
            window = PasteWindow()
            self.slot_pastes.append(window)
            self.slot_pastes[i].move(self.slot_overlay[i][0] / self.SCALE, self.slot_overlay[i][1] / self.SCALE)
        self.total_paste = TotalPasteWindow()
        self.total_paste.move(self.total_overlay[0] / self.SCALE, self.total_overlay[1] / self.SCALE)

        self.character = effective_rolls.FALLBACK_NAME
        self.config = dict(effective_rolls.FALLBACK_CONFIG)

        with open(doc.character_path, 'r', encoding='utf-8') as f:
            self.characters = json.load(f)
        for key in self.characters:
            self.combobox.addItem(key)
        self.character = self.combobox.currentText()
        self.config, notice = effective_rolls.resolve_character_config(self.character, self.characters)
        self.notice.setText(notice or '')
        self._apply_character_scan()

        global myappid
        myappid = 'v0.9.0'
        try:
            response = requests.get(
                'https://api.github.com/repos/SkeathyTomas/genshin_artifact_auxiliary/releases/latest')
            tag = response.json()['tag_name']
            if myappid != tag:
                self.upgrade.setText('有新版本，点击右侧图标前往下载~')
            else:
                self.upgrade.setText(myappid)
        except:
            pass

    def init_events(self):
        self.combobox.currentIndexChanged.connect(self.current_index_changed)
        self.github.setCursor(Qt.PointingHandCursor)
        self.github.mousePressEvent = self.open_github
        self.scanbtn.clicked.connect(self.start_five_slot_scan)
        self.clearbtn.clicked.connect(self.clear_game_overlays)
        self.hotkey()
        self.bind_scan_hotkey()
        self.apply_old_score_visibility()

    def current_index_changed(self, index):
        if self._scanning:
            return
        self.character = self.combobox.currentText()
        self.config, notice = effective_rolls.resolve_character_config(self.character, self.characters)
        self.notice.setText(notice or '')
        self._show_game_overlays = False
        self.hide_slot_overlays()
        self._apply_character_scan()

    def open_github(self, event):
        QDesktopServices.openUrl(QUrl('https://github.com/SkeathyTomas/genshin_artifact_auxiliary/releases/latest'))

    def reset_myappid(self):
        self.upgrade.setText(myappid)

    def closeEvent(self, event):
        for item in self.slot_pastes:
            item.close()
        self.total_paste.close()

    def clear_game_overlays(self):
        '''隐藏游戏内部位+合计贴图；与 Ctrl+Shift+Z 相同，不删 equipped.json。'''
        print('reset!')
        self._show_game_overlays = False
        self.hide_slot_overlays()
        self.refresh_set_total()

    def hotkey(self):
        def on_activate():
            QTimer.singleShot(0, self.clear_game_overlays)

        h = keyboard.GlobalHotKeys({'<ctrl>+<shift>+z': on_activate})
        h.start()

    def apply_settings(self, settings=None):
        self.app_settings = settings or doc.load_settings()
        self.bind_scan_hotkey()
        self._recompute_equipped_rolls()
        self.apply_old_score_visibility()
        if self._show_game_overlays:
            for i in range(equipped.SLOT_COUNT):
                if self.equipped_artifact[i] is not None:
                    self.slot_pastes[i].label.setText('{:.1f}'.format(self.equipped_rolls[i]))
        self.refresh_set_total()

    def apply_old_score_visibility(self):
        self._refresh_summary()

    def _hotkey_spec(self, name):
        key = str(name or 'f8').strip().lower()
        if not key:
            key = 'f8'
        if not key.startswith('<'):
            key = '<' + key + '>'
        return key

    def bind_scan_hotkey(self):
        if self._scan_hotkeys is not None:
            try:
                self._scan_hotkeys.stop()
            except Exception:
                pass
            self._scan_hotkeys = None
        spec = self._hotkey_spec(self.app_settings.get('scan_hotkey'))

        def on_scan():
            QTimer.singleShot(0, self.start_five_slot_scan)

        try:
            listener = keyboard.GlobalHotKeys({spec: on_scan})
            listener.start()
            self._scan_hotkeys = listener
            self.scanbtn.setText('扫描五件 (' + spec.strip('<>').upper() + ')')
        except Exception as exc:
            print('bind scan hotkey failed', spec, exc)
            if spec != '<f8>':
                self.app_settings['scan_hotkey'] = 'f8'
                self.bind_scan_hotkey()

    def hide_slot_overlays(self):
        for item in self.slot_pastes:
            item.hide()
        self.total_paste.hide()

    def _recompute_equipped_rolls(self):
        for i in range(equipped.SLOT_COUNT):
            piece = self.equipped_artifact[i]
            if piece is None:
                self.equipped_rolls[i] = None
            else:
                self.equipped_rolls[i] = effective_rolls.cal_effective_rolls(piece[1], self.config)[1]

    def _refresh_summary(self):
        show_old = bool(self.app_settings.get('show_old_score'))
        for i in range(equipped.SLOT_COUNT):
            piece = self.equipped_artifact[i]
            old_score = None
            if show_old and piece is not None:
                old_score = score.cal_score(piece[1], self.config)[1]
            self.slot_summary[i].setText(
                equipped.format_slot_summary(i, piece, self.config, old_score=old_score))

    def _apply_character_scan(self):
        store = equipped.load_store(doc.equipped_path)
        self.equipped_artifact = equipped.get_character_slots(store, self.character)
        self._recompute_equipped_rolls()
        self._refresh_summary()
        self.refresh_set_total()

    def _persist_scan(self, name=None):
        name = name if name is not None else self.character
        equipped.upsert_character(doc.equipped_path, name, self.equipped_artifact)

    def refresh_set_total(self):
        total, counted = effective_rolls.sum_set_rolls(self.equipped_rolls)
        text = effective_rolls.format_set_total(total, counted)
        self.set_total.setText(text)
        if counted > 0 and self._show_game_overlays and not self._scanning:
            self.total_paste.label.setText(text)
            self.total_paste.move(self.total_overlay[0] / self.SCALE, self.total_overlay[1] / self.SCALE)
            self.total_paste.show()
        else:
            self.total_paste.hide()

    def start_five_slot_scan(self):
        if self._scanning:
            return
        self._scanning = True
        self._scan_index = 0
        self._scan_character = self.character
        self._show_game_overlays = True
        self.equipped_artifact = equipped.empty_slots()
        self.equipped_rolls = equipped.empty_slots()
        self.combobox.setEnabled(False)
        win = self.window()
        if win is not None:
            win.hide()
        self.total_paste.hide()
        for item in self.slot_pastes:
            item.hide()
        self._refresh_summary()
        self.refresh_set_total()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        QTimer.singleShot(80, self._scan_click_current)

    def _scan_click_current(self):
        if not self._scanning:
            return
        if self._scan_index >= equipped.SLOT_COUNT:
            self._finish_scan()
            return
        self.slot_pastes[self._scan_index].hide()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        x, y = self.slot_click[self._scan_index]
        try:
            self._mouse.position = (int(x), int(y))
            self._mouse.click(MouseButton.left, 1)
        except Exception as exc:
            print('scan click failed', exc)
            self._finish_scan()
            return
        delay = int(self.app_settings.get('scan_delay_ms') or 450)
        QTimer.singleShot(delay, self._scan_ocr_current)

    def _scan_ocr_current(self):
        if not self._scanning:
            return
        i = self._scan_index
        try:
            piece = list(ocr.rapid_ocr(self.x_grab, self.y_grab, self.w_grab, self.h_grab))
        except ValueError as exc:
            print(exc)
            self._finish_scan()
            return
        self.equipped_artifact[i] = piece
        rolls = effective_rolls.cal_effective_rolls(piece[1], self.config)
        self.equipped_rolls[i] = rolls[1]
        self.slot_pastes[i].label.setText('{:.1f}'.format(rolls[1]))
        self.slot_pastes[i].move(self.slot_overlay[i][0] / self.SCALE, self.slot_overlay[i][1] / self.SCALE)
        if self._show_game_overlays:
            self.slot_pastes[i].show()
        self._refresh_summary()
        self.refresh_set_total()
        self._scan_index += 1
        QTimer.singleShot(50, self._scan_click_current)

    def _finish_scan(self):
        self._scanning = False
        self.combobox.setEnabled(True)
        win = self.window()
        if win is not None:
            win.show()
            win.raise_()
        scanned = equipped.has_any_piece(self.equipped_artifact)
        self._persist_scan(self._scan_character)
        if not scanned:
            self._show_game_overlays = False
        if self.character != self._scan_character or not scanned:
            self._apply_character_scan()
        else:
            self._recompute_equipped_rolls()
            self._refresh_summary()
        self.refresh_set_total()
        self.upgrade.setText('五件扫描完成')
        self.timer = QTimer()
        self.timer.timeout.connect(self.reset_myappid)
        self.timer.start(2000)
