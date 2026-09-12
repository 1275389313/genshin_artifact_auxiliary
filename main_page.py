'''主页面'''

import requests, json
from pynput import keyboard

from pynput.mouse import Button as MouseButton, Controller as MouseController

import doc, location, ocr, score, mona, effective_rolls
from extention import OutsideMouseManager, ExtendedComboBox
from paste_window import PasteWindow, TotalPasteWindow

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QLabel, QPushButton, QWidget, QGridLayout,
    QRadioButton, QComboBox, QLineEdit, QApplication
)
from PySide6.QtCore import Signal

class MainPage(QWidget):
    open_settings = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_data()
        self.init_events()

    def init_ui(self):
        # 背包/角色面板选择（Radio）
        self.radiobtn1 = QRadioButton('背包')
        self.radiobtn1.setChecked(True)
        self.radiobtn2 = QRadioButton('角色')
        self.type = '背包'

        # 设置按钮
        self.settingbtn = QPushButton('设置')
        self.settingbtn.clicked.connect(self.open_settings.emit)

        # 角色选择框
        self.combobox = ExtendedComboBox()

        # 角色页五件扫描
        self.scanbtn = QPushButton('扫描五件 (F8)')
        self.set_total = QLabel('有效词条 0.0（0/5）')
        self.notice = QLabel('')
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet('color: #a15c00')

        # 识别结果显示
        self.title = QLabel('请选择圣遗物，然后点击右键')
        self.name = []
        self.digit = []
        self.strengthen = []
        self.score = []
        for i in range(4):
            self.name.append(QComboBox())
            text = QLineEdit("0")
            text.setAlignment(Qt.AlignRight)
            self.digit.append(text)
            self.score.append(QLabel("0"))
            self.strengthen.append(QLabel("+0"))
            self.name[i].addItem('副属性词条' + str(i + 1))
            self.name[i].addItems(score.coefficient.keys())
            self.name[i].addItem('识别错误')

        self.confirm = QPushButton('确认修改')

        self.entries = QLabel('有效词条：0.0')
        self.total = QLabel('旧评分')
        self.score_total = QLabel('0')

        # 评分方案本地保存
        self.archive = ExtendedComboBox()
        self.archive.setEditable(True)
        self.archive.addItem('----保存此屏结果请输入名称----')
        self.save = QPushButton('保存')

        # GitHub图标与项目链接
        self.upgrade = QLabel()
        self.github = QLabel()
        self.github.setFixedSize(20, 20)
        pixmap = QPixmap('src/GitHub.png')
        pixmap = pixmap.scaled(16, 16)
        self.github.setPixmap(pixmap)

        # layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.radiobtn1, 0, 0)
        self.layout.addWidget(self.radiobtn2, 0, 1)
        self.layout.addWidget(self.settingbtn, 0, 2, 1, 2, Qt.AlignRight)
        self.layout.addWidget(self.combobox, 1, 0, 1, 4)
        self.layout.addWidget(self.scanbtn, 2, 0, 1, 2)
        self.layout.addWidget(self.set_total, 2, 2, 1, 2, Qt.AlignRight)
        self.layout.addWidget(self.notice, 3, 0, 1, 4)
        self.layout.addWidget(self.title, 4, 0, 1, 4)
        for i in range(4):
            self.layout.addWidget(self.name[i], i + 5, 0)
            self.layout.addWidget(self.digit[i], i + 5, 1)
            self.layout.addWidget(self.strengthen[i], i + 5, 2, Qt.AlignRight)
            self.layout.addWidget(self.score[i], i + 5, 3, Qt.AlignRight)
        self.layout.addWidget(self.confirm, 9, 0)
        self.layout.addWidget(self.entries, 9, 1, Qt.AlignRight)
        self.layout.addWidget(self.total, 9, 2, Qt.AlignRight)
        self.layout.addWidget(self.score_total, 9, 3, Qt.AlignRight)
        self.layout.addWidget(self.archive, 10, 0, 1, 3)
        self.layout.addWidget(self.save, 10, 3)
        self.layout.addWidget(self.upgrade, 11, 0, 1, 2, Qt.AlignLeft | Qt.AlignBottom)
        self.layout.addWidget(self.github, 11, 3, Qt.AlignRight | Qt.AlignBottom)

        self.setLayout(self.layout)

    def init_data(self):
        # 默认坐标信息-背包A
        self.position = location.position_A
        self.row, self.col = location.row_A, location.col_A
        self.xarray, self.yarray = location.xarray_A, location.yarray_A
        self.x_grab, self.y_grab, self.w_grab, self.h_grab = location.x_grab_A, location.y_grab_A, location.w_grab_A, location.h_grab_A
        self.SCALE = location.SCALE
        self.slot_click = location.slot_click_B
        self.slot_overlay = location.slot_overlay_B
        self.total_overlay = location.total_overlay_B

        # 贴图窗口组
        self.pastes = []
        self.id = -1
        self.artifact = {}
        self.score_result = [[0, 0, 0, 0], 0]
        self.roll_result = [[0, 0, 0, 0], 0.0]
        self.equipped_artifact = [None] * 5
        self.equipped_rolls = [None] * 5
        self._scanning = False
        self._scan_index = 0
        self._scan_hotkeys = None
        self._mouse = MouseController()
        self.app_settings = doc.load_settings()

        for i in range(self.row * self.col):
            window = PasteWindow()
            self.pastes.append(window)
            self.pastes[i].move(self.position[i][0] / self.SCALE, self.position[i][1] / self.SCALE)

        self.slot_pastes = []
        for i in range(5):
            window = PasteWindow()
            self.slot_pastes.append(window)
            self.slot_pastes[i].move(self.slot_overlay[i][0] / self.SCALE, self.slot_overlay[i][1] / self.SCALE)
        self.total_paste = TotalPasteWindow()
        self.total_paste.move(self.total_overlay[0] / self.SCALE, self.total_overlay[1] / self.SCALE)

        # 默认角色及配置（未选角色 = 常规主C-攻暴）
        self.character = effective_rolls.FALLBACK_NAME
        self.config = dict(effective_rolls.FALLBACK_CONFIG)

        # 加载角色列表
        with open(doc.character_path, 'r', encoding='utf-8') as f:
            self.characters = json.load(f)
        for key in self.characters:
            self.combobox.addItem(key)

        # 加载本地保存方案
        with open(doc.archive_path, 'r', encoding='utf-8') as fp:
            self.artifacts = json.load(fp)
        for name in self.artifacts[self.type]:
            self.archive.addItem(name)

        # 检查更新
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
        # 单选框
        self.radiobtn1.toggled.connect(lambda: self.radiobtn_state(self.radiobtn1))
        self.radiobtn2.toggled.connect(lambda: self.radiobtn_state(self.radiobtn2))

        # 角色选择
        self.combobox.currentIndexChanged.connect(self.current_index_changed)

        # 修改识别结果
        self.confirm.clicked.connect(self.confirm_clicked)

        # 方案选择
        self.archive.currentIndexChanged.connect(self.archive_index_changed)

        # 保存按钮
        self.save.clicked.connect(self.button_save)

        # GitHub图标点击
        self.github.setCursor(Qt.PointingHandCursor)
        self.github.mousePressEvent = self.open_github

        self.scanbtn.clicked.connect(self.start_five_slot_scan)

        # 鼠标事件管理器
        self.manager = OutsideMouseManager()
        self.manager.right_click.connect(self.open_new_window)
        self.manager.left_click.connect(self.left_click_artifact)

        # 快捷键
        self.hotkey()
        self.bind_scan_hotkey()
        self.apply_old_score_visibility()
        # 数据插入模式
        self.insert = False
        self.insert_mode()
        # 数据删除模式
        self.delete = False
        self.delete_mode()

    # 单选框面板选择事件
    def radiobtn_state(self, btn):
        if btn.text() == '背包':
            if btn.isChecked() == True:
                self.type = '背包'
                self.reset_archive()
                # 重置坐标信息
                # import location
                self.position = location.position_A
                self.row, self.col = location.row_A, location.col_A
                self.xarray, self.yarray = location.xarray_A, location.yarray_A
                self.x_grab, self.y_grab, self.w_grab, self.h_grab = location.x_grab_A, location.y_grab_A, location.w_grab_A, location.h_grab_A
                self.hide_slot_overlays()
                self.reset()

        if btn.text() == '角色':
            if btn.isChecked() == True:
                self.type = '角色'
                self.reset_archive()
                # 重置坐标信息
                # import location
                self.position = location.position_B
                self.row, self.col = location.row_B, location.col_B
                self.xarray, self.yarray = location.xarray_B, location.yarray_B
                self.x_grab, self.y_grab, self.w_grab, self.h_grab = location.x_grab_B, location.y_grab_B, location.w_grab_B, location.h_grab_B
                self.reset()

    # 重置保存结果选择框
    def reset_archive(self):
        self.archive.clear()
        self.archive.addItem('----保存此屏结果请输入名称----')
        for name in self.artifacts[self.type]:
            self.archive.addItem(name)

    # 选择框选择角色事件
    def current_index_changed(self, index):
        self.character = self.combobox.currentText()
        self.config, notice = effective_rolls.resolve_character_config(self.character, self.characters)
        self.notice.setText(notice or '')
        # 更新评分贴图（格子 + 五件页签）
        for i in range(len(self.pastes)):
            if self.pastes[i].isVisible() == True:
                self.roll_result = effective_rolls.cal_effective_rolls(self.artifact[str(i)][1], self.config)
                self.score_result = score.cal_score(self.artifact[str(i)][1], self.config)
                self.pastes[i].label.setText('{:.1f}'.format(self.roll_result[1]))
        for i in range(5):
            if self.equipped_artifact[i] is not None:
                rolls = effective_rolls.cal_effective_rolls(self.equipped_artifact[i][1], self.config)
                self.equipped_rolls[i] = rolls[1]
                self.slot_pastes[i].label.setText('{:.1f}'.format(rolls[1]))
        self.refresh_set_total()

        # 更新主程序评分详情
        if self.artifact != {}:
            self.fresh_main_window()

    # 修改识别结果按钮
    def confirm_clicked(self):
        if str(self.id) not in self.artifact:
            return
        self.artifact[str(self.id)][1] = {}
        for i in range(4):
            try:
                self.artifact[str(self.id)][1][self.name[i].currentText()] = float(self.digit[i].text())
            except:
                pass
        print(self.artifact[str(self.id)])
        if self.id != -1:
            self.fresh_main_window()
            self.fresh_paste_window()
        else:
            self.fresh_main_window()

    # 方案选择框事件
    def archive_index_changed(self, index):
        self.reset()

        currentText = self.archive.currentText()
        if currentText in self.artifacts[self.type]:
            self.artifact = self.artifacts[self.type][self.archive.currentText()].copy()
            print(self.artifact)
            for key in self.artifact:
                self.id = eval(key)
                if self.id != -1:
                    self.fresh_main_window()
                    self.fresh_paste_window()
                else:
                    self.fresh_main_window()

    # 保存方案按钮
    def button_save(self):
        new_archive = self.archive.currentText()
        if new_archive == '----保存此屏结果请输入名称----' or new_archive == '':
            hint_txt = '请输入名称~'
        elif self.artifact != {}:
            if new_archive not in self.artifacts[self.type].keys():
                self.archive.addItem(new_archive)
                hint_txt = '保存成功！'
            else:
                hint_txt = '更新成功！'
            self.artifacts[self.type].update({new_archive: self.artifact})
            dic_sorted = sorted(self.artifacts[self.type].items())
            self.artifacts[self.type] = {k: v for k, v in dic_sorted}
            with open(doc.archive_path, 'w', encoding='utf-8') as fp:
                json.dump(self.artifacts, fp, ensure_ascii=False)
            mona.update() #保存一次更新一次mona格式的导出
        else:
            hint_txt = '未识别圣遗物，无结果保存~'

        # 保存按钮结果提示
        self.upgrade.setText(hint_txt)
        self.timer = QTimer()
        self.timer.timeout.connect(self.reset_myappid)
        self.timer.start(2000)

    # 恢复版本号信息
    def reset_myappid(self):
        self.upgrade.setText(myappid)

    # 打开外部链接
    def open_github(self, event):
        QDesktopServices.openUrl(QUrl('https://github.com/SkeathyTomas/genshin_artifact_auxiliary/releases/latest'))

    # 启动贴图弹窗
    def open_new_window(self, x, y):
        if self._scanning:
            return
        # 根据鼠标事件定位贴图
        for i in range(self.col):
            if x >= self.xarray[i][0] and x <= self.xarray[i][1]:
                for j in range(self.row):
                    if y >= self.yarray[j][0] and y <= self.yarray[j][1]:
                        print(self.character + 'detected')
                        self.id = j * self.col + i
                        # 插入模式后移数据
                        if self.insert:
                            self.insert_data()
                        # 删除模式前移数据
                        if self.delete:
                            self.delete_data()
                            break
                        if self._scanning:
                            break
                        # ocr识别与结果返回并刷新主面板、贴图
                        self.id = j * self.col + i
                        try:
                            self.artifact[str(self.id)] = list(ocr.rapid_ocr(
                                self.x_grab, self.y_grab, self.w_grab, self.h_grab))
                        except ValueError as exc:
                            print(exc)
                            self._flash_status(str(exc), 5000)
                            break
                        self.fresh_main_window()
                        self.fresh_paste_window()
                        break
                break

    # 根据鼠标左键选择的圣遗物刷新主窗口圣遗物副属性和评分
    def left_click_artifact(self, x, y):
        if self._scanning:
            return
        for i in range(self.col):
            if x >= self.xarray[i][0] and x <= self.xarray[i][1]:
                for j in range(self.row):
                    if y >= self.yarray[j][0] and y <= self.yarray[j][1]:
                        id_temp = j * self.col + i
                        if self.pastes[id_temp].isVisible() == True:
                            self.id = id_temp
                            self.fresh_main_window()
                            break
                break

    # 刷新主程序（识别、选择、切换角色、修改后确认、加载本地数据）
    def fresh_main_window(self):
        self._apply_piece_to_form(self.artifact[str(self.id)])

    def _apply_piece_to_form(self, piece):
        self.title.setText('-'.join(piece[0]))
        self.roll_result = effective_rolls.cal_effective_rolls(piece[1], self.config)
        self.score_result = score.cal_score(piece[1], self.config)
        self.entries.setText('有效词条：' + '{:.1f}'.format(self.roll_result[1]))
        self.score_total.setText(str(self.score_result[1]))
        for i in range(4):
            if i < len(piece[1]):
                if list(piece[1].keys())[i] in score.coefficient.keys():
                    self.name[i].setCurrentText(list(piece[1].keys())[i])
                    self.digit[i].setText(str(list(piece[1].values())[i]))
                    self.score[i].setText('{:.1f}'.format(self.roll_result[0][i] if i < len(self.roll_result[0]) else 0.0))
                    self.strengthen[i].setText("+" + str(self.score_result[2][i]))
                else:
                    self.name[i].setCurrentText('识别错误')
                    self.digit[i].setText(list(piece[1].keys())[i])
                    self.score[i].setText('0.0')
                    self.strengthen[i].setText("+0")
            else:
                self.name[i].setCurrentText('识别错误')
                self.digit[i].setText('0')
                self.score[i].setText('0.0')
                self.strengthen[i].setText("+0")

    # 刷新圣遗物贴图（识别、修改后确认、加载本地数据，后于主面板更新）
    def fresh_paste_window(self):
        self.pastes[self.id].label.setText('{:.1f}'.format(self.roll_result[1]))
        self.pastes[self.id].show()

    # 推荐圣遗物，贴图底色突出
    def recommend_paste(self):
        qss = 'background-color: rgb(0, 255, 0)'
        for item in self.artifact:
            item
        self.pastes[self.id].label.setStyleSheet(qss)
        
    # 重置圣遗物数据&贴图窗口&主程序窗口
    def reset(self):
        # 主程序重置
        self.id = -1
        self.title.setText('请选择圣遗物，然后点击右键')
        for i in range(4):
            self.name[i].setCurrentText('副属性词条' + str(i + 1))
            self.digit[i].setText('0')
            self.score[i].setText('0')
            self.strengthen[i].setText("+0")
        self.score_total.setText('0')
        self.entries.setText('有效词条：0.0')
        self.equipped_artifact = [None] * 5
        self.equipped_rolls = [None] * 5
        self.refresh_set_total()

        # 数据重置
        self.pastes = []
        self.artifact = {}
        for i in range(self.row * self.col):
            window = PasteWindow()
            self.pastes.append(window)
            self.pastes[i].move(self.position[i][0] / self.SCALE, self.position[i][1] / self.SCALE)
        self.hide_slot_overlays()

    # 主窗口关闭则所有贴图窗口也关闭
    def closeEvent(self, event):
        for item in self.pastes:
            item.close()
        for item in self.slot_pastes:
            item.close()
        self.total_paste.close()

    # 全局快捷键Ctrl+Shift+Z重置贴图窗口
    def hotkey(self):
        def on_activate():
            print('reset!')
            # self.reset() # 为啥这里调用就闪退
            self.id = -1
            self.artifact = {}
            self.title.setText('请选择圣遗物，然后点击右键')
            for i in range(4):
                self.name[i].setCurrentText('副属性词条' + str(i + 1))
                # self.digit[i].setText('0')  # 不明原因引起闪退，reset()里也是因为这个
                self.score[i].setText('0')
                self.strengthen[i].setText("+0")
            self.score_total.setText('0')
            self.entries.setText('有效词条：0.0')
            self.equipped_artifact = [None] * 5
            self.equipped_rolls = [None] * 5
            for item in self.pastes:
                item.hide()
            self.hide_slot_overlays()
            self.refresh_set_total()

        h = keyboard.GlobalHotKeys({'<ctrl>+<shift>+z': on_activate})
        h.start()

    # 左Alt键插入新数据模式，之后的圣遗物后移一位
    def insert_mode(self):
        def on_press(key):
            if not self.insert and key == keyboard.Key.alt_l:
                print('insert start!')
                self.insert = True
                self.upgrade.setText('插入模式')

        def on_release(key):
            if key == keyboard.Key.alt_l:
                print('insert end!')
                self.insert = False
                self.upgrade.setText(myappid)

        l = keyboard.Listener(on_press=on_press, on_release=on_release)
        l.start()
    
    # 插入模式后移数据
    def insert_data(self):
        old = {}
        for key in self.artifact:
            if eval(key) >= self.id:
                new = self.artifact[key]
                self.artifact[key] = old
                old = new
        self.artifact[str(len(self.artifact))] = old
        print(self.artifact)
        # 贴图需要刷新
        for key in self.artifact:
            if eval(key) > self.id:
                self.id = eval(key)
                self.score_result = score.cal_score(self.artifact[str(self.id)][1], self.config)
                self.roll_result = effective_rolls.cal_effective_rolls(self.artifact[str(self.id)][1], self.config)
                self.fresh_paste_window()

    # 左Ctrl键删除数据模式，清空目标位置的数据，之后的圣遗物前移一位，一般用于尾部
    def delete_mode(self):
        def on_press(key):
            if not self.delete and key == keyboard.Key.ctrl_l:
                print('delete start!')
                self.delete = True
                self.upgrade.setText('删除模式')

        def on_release(key):
            if key == keyboard.Key.ctrl_l:
                print('delete end!')
                self.delete = False
                self.upgrade.setText(myappid)

        l = keyboard.Listener(on_press=on_press, on_release=on_release)
        l.start()

    # 删除模式前移数据
    def delete_data(self):
        for key in self.artifact:
            if key == list(self.artifact.keys())[-1]:
                self.artifact.pop(key, None)
                self.pastes[eval(key)].hide()
                break
            if eval(key) >= self.id:
                self.artifact[key] = self.artifact[list(self.artifact.keys())[eval(key) + 1]]
        print(self.artifact)
        # 主面板贴图需要刷新
        self.fresh_main_window()
        for key in self.artifact:
            if eval(key) >= self.id:
                self.id = eval(key)
                self.score_result = score.cal_score(self.artifact[str(self.id)][1], self.config)
                self.roll_result = effective_rolls.cal_effective_rolls(self.artifact[str(self.id)][1], self.config)
                self.fresh_paste_window()

    def apply_settings(self, settings=None):
        self.app_settings = settings or doc.load_settings()
        self.bind_scan_hotkey()
        self.apply_old_score_visibility()
        if self.id != -1 and str(self.id) in self.artifact:
            self.fresh_main_window()
        for i in range(len(self.pastes)):
            if self.pastes[i].isVisible() and str(i) in self.artifact:
                rolls = effective_rolls.cal_effective_rolls(self.artifact[str(i)][1], self.config)
                self.pastes[i].label.setText('{:.1f}'.format(rolls[1]))
        for i in range(5):
            if self.equipped_artifact[i] is not None:
                rolls = effective_rolls.cal_effective_rolls(self.equipped_artifact[i][1], self.config)
                self.equipped_rolls[i] = rolls[1]
                self.slot_pastes[i].label.setText('{:.1f}'.format(rolls[1]))
        self.refresh_set_total()

    def apply_old_score_visibility(self):
        show = bool(self.app_settings.get('show_old_score'))
        self.total.setVisible(show)
        self.score_total.setVisible(show)

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

    def refresh_set_total(self):
        total, counted = effective_rolls.sum_set_rolls(self.equipped_rolls)
        text = effective_rolls.format_set_total(total, counted)
        self.set_total.setText(text)
        if counted > 0 and self.type == '角色':
            self.total_paste.label.setText(text)
            self.total_paste.move(self.total_overlay[0] / self.SCALE, self.total_overlay[1] / self.SCALE)
            if not self._scanning:
                self.total_paste.show()
        else:
            self.total_paste.hide()

    def start_five_slot_scan(self):
        if self._scanning:
            return
        if self.type != '角色':
            self.upgrade.setText('请先切换到「角色」，并打开圣遗物装配页')
            self.timer = QTimer()
            self.timer.timeout.connect(self.reset_myappid)
            self.timer.start(2000)
            return
        self._scanning = True
        self._scan_index = 0
        win = self.window()
        if win is not None:
            win.hide()
        self.total_paste.hide()
        for item in self.slot_pastes:
            item.hide()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        try:
            location.bring_game_to_foreground()
        except Exception as exc:
            print('foreground game failed', exc)
        QTimer.singleShot(80, self._scan_click_current)

    def _flash_status(self, text, ms=4000):
        self.upgrade.setText(str(text))
        self.timer = QTimer()
        self.timer.timeout.connect(self.reset_myappid)
        self.timer.start(ms)

    def _scan_click_current(self):
        if not self._scanning:
            return
        if self._scan_index >= 5:
            self._finish_scan()
            return
        self.slot_pastes[self._scan_index].hide()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        try:
            location.bring_game_to_foreground()
        except Exception as exc:
            print('foreground game failed', exc)
        x, y = self.slot_click[self._scan_index]
        try:
            self._mouse.position = (int(x), int(y))
            self._mouse.click(MouseButton.left, 1)
        except Exception as exc:
            print('scan click failed', exc)
            self._finish_scan('扫描点击失败，请确认原神窗口在最前')
            return
        delay = int(self.app_settings.get('scan_delay_ms') or 450)
        QTimer.singleShot(delay, self._scan_ocr_current)

    def _scan_ocr_current(self):
        if not self._scanning:
            return
        i = self._scan_index
        try:
            location.bring_game_to_foreground()
            piece = list(ocr.rapid_ocr(self.x_grab, self.y_grab, self.w_grab, self.h_grab))
        except ValueError as exc:
            print(exc)
            self._finish_scan(str(exc))
            return
        self.equipped_artifact[i] = piece
        rolls = effective_rolls.cal_effective_rolls(piece[1], self.config)
        self.equipped_rolls[i] = rolls[1]
        self.slot_pastes[i].label.setText('{:.1f}'.format(rolls[1]))
        self.slot_pastes[i].move(self.slot_overlay[i][0] / self.SCALE, self.slot_overlay[i][1] / self.SCALE)
        self.slot_pastes[i].show()
        self.refresh_set_total()
        self._scan_index += 1
        QTimer.singleShot(50, self._scan_click_current)

    def _finish_scan(self, message=None):
        self._scanning = False
        self.id = -1
        win = self.window()
        if win is not None:
            win.show()
            win.raise_()
        last = None
        for piece in reversed(self.equipped_artifact):
            if piece is not None:
                last = piece
                break
        if last is not None:
            self._apply_piece_to_form(last)
        self.refresh_set_total()
        if message:
            self._flash_status(message, 5000)
        else:
            self._flash_status('五件扫描完成', 2000)