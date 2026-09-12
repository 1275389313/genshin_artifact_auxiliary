'''不同分辨率、缩放率适配，贴图坐标、圣遗物坐标、截图坐标定位'''

import ctypes
import os
import time

RATIO_16_9 = 16 / 9
RATIO_16_10 = 16 / 10

# 旧版 16:9 / 16:10 判定略收紧，边框取整后 4K 容易掉到 else。
_BAND_16_10 = (1.52, 1.68)
_BAND_16_9 = (1.68, 1.86)
_NEAREST_MAX_DELTA = 0.12
_NEAR_16_9_FALLBACK = 0.18
_LARGE_WINDOW_PX = 1600

# Win10/11 窗口边框（100% DPI 逻辑像素）；已是物理像素时再乘 SCALE。
_CHROME_LEFT = 7
_CHROME_TOP = 31
_CHROME_X = 14
_CHROME_Y = 38

# 最小化窗口 GetWindowRect 约为 (-32000, -32000, ...)，不是 4K 计算错误。
_MINIMIZED_COORD_MAX = -16000
WAIT_MSG_MISSING = '未找到游戏窗口，请启动游戏！'
WAIT_MSG_MINIMIZED = '游戏窗口已最小化或不可见，请还原「原神」窗口（不要最小化）后重试'

# paste_window.PasteWindow 以宽 1280 时 24px 为参考；合计贴图放在部位数字下方。
PASTE_REF_WIDTH = 1280
SLOT_PASTE_REF_PX = 24


def set_process_dpi_awareness():
    '''Per-Monitor V2（失败则降级）。须在读屏幕/窗口矩形和创建 Qt 之前调用。'''
    if os.name != 'nt':
        return 'skipped-non-windows'
    try:
        user32 = ctypes.windll.user32
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return 'Per-Monitor-V2'
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return 'Per-Monitor'
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return 'System-DPI-Aware'
    except Exception:
        pass
    return 'unaware'


def read_dpi(hwnd=None, logpixelsx=None):
    '''窗口 DPI；GetDpiForWindow / GetDpiForSystem / LOGPIXELSX。'''
    if os.name == 'nt':
        try:
            if hwnd:
                dpi = int(ctypes.windll.user32.GetDpiForWindow(int(hwnd)))
                if dpi > 0:
                    return dpi
        except Exception:
            pass
        try:
            dpi = int(ctypes.windll.user32.GetDpiForSystem())
            if dpi > 0:
                return dpi
        except Exception:
            pass
    if logpixelsx:
        return int(logpixelsx)
    return 96


def compute_scale(width_r, width_s, dpi=None):
    '''显示缩放。DPI 感知后 GetSystemMetrics 已是物理像素，不能再用 DESKTOPHORZRES/SM 当 SCALE。'''
    width_r = float(width_r or 0)
    width_s = float(width_s or 0)
    metrics_scale = (width_r / width_s) if width_s else 1.0
    dpi_scale = (float(dpi) / 96.0) if dpi else None
    if dpi_scale and abs(metrics_scale - 1.0) < 0.05 and dpi_scale > 1.05:
        return dpi_scale
    if abs(metrics_scale - 1.0) >= 0.05:
        return metrics_scale
    return dpi_scale or metrics_scale or 1.0


def rect_already_physical(left, top, right, bottom, scale, desktop_w, desktop_h, dpi_aware=False):
    '''GetWindowRect 是否已是物理像素（再乘 SCALE 会把 4K 拉成 8K、比例变形）。'''
    raw_w = float(right) - float(left)
    raw_h = float(bottom) - float(top)
    if raw_w <= 0 or raw_h <= 0:
        return bool(dpi_aware)
    if dpi_aware:
        return True
    if scale > 1.01 and raw_w * scale > desktop_w * 1.15:
        return True
    if abs(raw_w - desktop_w) <= 24 and abs(raw_h - desktop_h) <= 80:
        return True
    return False


def is_minimized_or_invalid_rect(left, top, right, bottom, iconic=False):
    '''最小化 / 无效客户区：IsIconic、坐标接近 -32000、宽高非正。'''
    if iconic:
        return True
    try:
        left = float(left)
        top = float(top)
        right = float(right)
        bottom = float(bottom)
    except (TypeError, ValueError):
        return True
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return True
    if (left <= _MINIMIZED_COORD_MAX or top <= _MINIMIZED_COORD_MAX
            or right <= _MINIMIZED_COORD_MAX or bottom <= _MINIMIZED_COORD_MAX):
        return True
    return False


def is_invalid_grab_bbox(x, y, w, h):
    '''ImageGrab.grab 在 w/h<=0 时会 ValueError: Coordinate lower < upper。'''
    try:
        x = float(x)
        y = float(y)
        w = float(w)
        h = float(h)
    except (TypeError, ValueError):
        return True
    if w <= 0 or h <= 0:
        return True
    if x + w <= x or y + h <= y:
        return True
    return is_minimized_or_invalid_rect(x, y, x + w, y + h)


def decide_window_wait(hwnd, iconic, rect):
    '''返回需打印的等待提示；窗口可用则 None。与「未找到游戏窗口」同一套循环。'''
    if not hwnd:
        return WAIT_MSG_MISSING
    if rect is None or len(rect) != 4:
        return WAIT_MSG_MINIMIZED
    if is_minimized_or_invalid_rect(
            rect[0], rect[1], rect[2], rect[3], iconic=bool(iconic)):
        return WAIT_MSG_MINIMIZED
    return None


def classify_aspect(ratio, w_width=0, w_hight=0):
    '''返回 (kind, warn, hard_fail)。kind: 16:10 / 16:9 / unsupported。'''
    ratio = float(ratio)
    w_width = float(w_width or 0)
    d9 = abs(ratio - RATIO_16_9)
    d10 = abs(ratio - RATIO_16_10)
    if _BAND_16_10[0] <= ratio <= _BAND_16_10[1]:
        return '16:10', None, False
    if _BAND_16_9[0] < ratio <= _BAND_16_9[1]:
        return '16:9', None, False
    if d10 <= _NEAREST_MAX_DELTA and d10 <= d9:
        return '16:10', f'宽高比 {ratio:.4f} 接近 16:10，按 16:10 缩放坐标', False
    if d9 <= _NEAREST_MAX_DELTA:
        return '16:9', f'宽高比 {ratio:.4f} 接近 16:9，按 16:9 缩放坐标', False
    if w_width >= _LARGE_WINDOW_PX and d9 <= _NEAR_16_9_FALLBACK:
        msg = (f'宽高比 {ratio:.4f} 略超出 16:9 区间，但窗口较大且接近 16:9，'
               f'按 16:9 缩放坐标继续（4K/无边框可用）。若贴图偏移请改用无边框。')
        return '16:9', msg, False
    msg = (f'当前游戏窗口宽高比 {ratio:.4f} 暂不支持（非 16:9 / 16:10）。'
           f'请使用 16:9 或 16:10 窗口/无边框（含 4K），然后重新扫描。')
    return 'unsupported', msg, True


def slot_paste_height(w_width):
    '''部位贴图物理高度，与 paste_window.scale = w_width/1280/SCALE 一致。'''
    return SLOT_PASTE_REF_PX * float(w_width) / PASTE_REF_WIDTH


def paste_qt_scale(w_width=None, display_scale=None):
    '''贴图窗口 Qt 缩放：w_width/1280/SCALE。SCALE<=0 时当 1，避免导入或刷新除零。'''
    w = float(w_width if w_width is not None else globals().get('w_width') or PASTE_REF_WIDTH)
    s = float(display_scale if display_scale is not None else globals().get('SCALE') or 1.0)
    if s <= 0:
        s = 1.0
    return w / PASTE_REF_WIDTH / s


def total_overlay_y(slot_overlay_y, w_width, gap):
    '''合计贴图顶边：部位数字底边 + 间隙，避免盖住单件框。'''
    return slot_overlay_y + slot_paste_height(w_width) + gap


def _chrome_offsets(scale, already_physical):
    if already_physical and scale > 1.01:
        return (_CHROME_LEFT * scale, _CHROME_TOP * scale,
                _CHROME_X * scale, _CHROME_Y * scale)
    return (_CHROME_LEFT, _CHROME_TOP, _CHROME_X, _CHROME_Y)


def _is_borderless(phys_w, phys_h, desktop_w, desktop_h):
    slop_w = max(16, desktop_w * 0.012)
    slop_h = max(48, desktop_h * 0.03)
    return abs(phys_w - desktop_w) <= slop_w and abs(phys_h - desktop_h) <= slop_h


def correct_window_rect(left, top, right, bottom, scale, desktop_w, desktop_h,
                        client_rect=None, dpi_aware=False):
    '''客户区优先；避免 SCALE 连乘；无客户区时再做标题栏修正。返回 (x, y, w, h, already_physical, source)。'''
    already = rect_already_physical(
        left, top, right, bottom, scale, desktop_w, desktop_h, dpi_aware)
    mul = 1.0 if already else scale

    if client_rect:
        cl, ct, cr, cb = client_rect
        cw, ch = float(cr) - float(cl), float(cb) - float(ct)
        if cw >= 64 and ch >= 64:
            return (cl * mul, ct * mul, cw * mul, ch * mul, already, 'client')

    phys_l, phys_t = left * mul, top * mul
    phys_w = (right - left) * mul
    phys_h = (bottom - top) * mul
    if _is_borderless(phys_w, phys_h, desktop_w, desktop_h):
        return (phys_l, phys_t, phys_w, phys_h, already, 'borderless')

    dx, dy, dw, dh = _chrome_offsets(scale, already)
    return ((left + dx) * mul, (top + dy) * mul,
            (right - left - dw) * mul, (bottom - top - dh) * mul,
            already, 'caption')


def layout_16_10(w_left, w_top, w_width, w_hight):
    slot_oy = 82 / 1600 * w_hight + w_top
    total_oy = total_overlay_y(slot_oy, w_width, 14 / 1600 * w_hight)
    return dict(
        x_initial_A=303 / 2560 * w_width + w_left,
        y_initial_A=424 / 1600 * w_hight + w_top,
        x_offset_A=195 / 2560 * w_width,
        y_offset_A=234 / 1600 * w_hight,
        x_left_A=156 / 2560 * w_width + w_left,
        x_right_A=321 / 2560 * w_width + w_left,
        y_top_A=238 / 1600 * w_hight + w_top,
        y_bottom_A=442 / 1600 * w_hight + w_top,
        x_grab_A=1776 / 2560 * w_width + w_left,
        y_grab_A=169 / 1600 * w_hight + w_top,
        w_grab_A=602 / 2560 * w_width,
        h_grab_A=725 / 1600 * w_hight,
        row_A=5, col_A=8,
        x_initial_B=200 / 2560 * w_width + w_left,
        y_initial_B=355 / 1600 * w_hight + w_top,
        x_offset_B=189 / 2560 * w_width,
        y_offset_B=225 / 1600 * w_hight,
        x_left_B=48 / 2560 * w_width + w_left,
        x_right_B=216 / 2560 * w_width + w_left,
        y_top_B=167 / 1600 * w_hight + w_top,
        y_bottom_B=371 / 1600 * w_hight + w_top,
        x_grab_B=1947 / 2560 * w_width + w_left,
        y_grab_B=149 / 1600 * w_hight + w_top,
        w_grab_B=551 / 2560 * w_width,
        h_grab_B=504 / 1600 * w_hight,
        row_B=6, col_B=4,
        slot_click_B=[
            (112 / 2560 * w_width + w_left, 58 / 1600 * w_hight + w_top),
            (265 / 2560 * w_width + w_left, 58 / 1600 * w_hight + w_top),
            (413 / 2560 * w_width + w_left, 58 / 1600 * w_hight + w_top),
            (556 / 2560 * w_width + w_left, 58 / 1600 * w_hight + w_top),
            (706 / 2560 * w_width + w_left, 58 / 1600 * w_hight + w_top),
        ],
        slot_overlay_B=[
            (138 / 2560 * w_width + w_left, slot_oy),
            (291 / 2560 * w_width + w_left, slot_oy),
            (439 / 2560 * w_width + w_left, slot_oy),
            (582 / 2560 * w_width + w_left, slot_oy),
            (732 / 2560 * w_width + w_left, slot_oy),
        ],
        total_overlay_B=(200 / 2560 * w_width + w_left, total_oy),
    )


def layout_16_9(w_left, w_top, w_width, w_hight):
    slot_oy = 62 / 1080 * w_hight + w_top
    total_oy = total_overlay_y(slot_oy, w_width, 14 / 1080 * w_hight)
    return dict(
        x_initial_A=226 / 1920 * w_width + w_left,
        y_initial_A=317 / 1080 * w_hight + w_top,
        x_offset_A=146 / 1920 * w_width,
        y_offset_A=175 / 1080 * w_hight,
        x_left_A=117 / 1920 * w_width + w_left,
        x_right_A=242 / 1920 * w_width + w_left,
        y_top_A=179 / 1080 * w_hight + w_top,
        y_bottom_A=333 / 1080 * w_hight + w_top,
        x_grab_A=1331 / 1920 * w_width + w_left,
        y_grab_A=120 / 1080 * w_hight + w_top,
        w_grab_A=450 / 1920 * w_width,
        h_grab_A=550 / 1080 * w_hight,
        row_A=5, col_A=8,
        x_initial_B=147 / 1920 * w_width + w_left,
        y_initial_B=261 / 1080 * w_hight + w_top,
        x_offset_B=142 / 1920 * w_width,
        y_offset_B=168 / 1080 * w_hight,
        x_left_B=37 / 1920 * w_width + w_left,
        x_right_B=164 / 1920 * w_width + w_left,
        y_top_B=125 / 1080 * w_hight + w_top,
        y_bottom_B=278 / 1080 * w_hight + w_top,
        x_grab_B=1461 / 1920 * w_width + w_left,
        y_grab_B=111 / 1080 * w_hight + w_top,
        w_grab_B=413 / 1920 * w_width,
        h_grab_B=378 / 1080 * w_hight,
        row_B=5, col_B=4,
        slot_click_B=[
            (84 / 1920 * w_width + w_left, 44 / 1080 * w_hight + w_top),
            (199 / 1920 * w_width + w_left, 44 / 1080 * w_hight + w_top),
            (310 / 1920 * w_width + w_left, 44 / 1080 * w_hight + w_top),
            (417 / 1920 * w_width + w_left, 44 / 1080 * w_hight + w_top),
            (530 / 1920 * w_width + w_left, 44 / 1080 * w_hight + w_top),
        ],
        slot_overlay_B=[
            (104 / 1920 * w_width + w_left, slot_oy),
            (218 / 1920 * w_width + w_left, slot_oy),
            (329 / 1920 * w_width + w_left, slot_oy),
            (437 / 1920 * w_width + w_left, slot_oy),
            (549 / 1920 * w_width + w_left, slot_oy),
        ],
        total_overlay_B=(150 / 1920 * w_width + w_left, total_oy),
    )


def build_positions(layout):
    position_A = []
    for i in range(layout['row_A']):
        for j in range(layout['col_A']):
            position_A.append((
                layout['x_initial_A'] + j * layout['x_offset_A'],
                layout['y_initial_A'] + i * layout['y_offset_A'],
            ))
    position_B = []
    for i in range(layout['row_B']):
        for j in range(layout['col_B']):
            position_B.append((
                layout['x_initial_B'] + j * layout['x_offset_B'],
                layout['y_initial_B'] + i * layout['y_offset_B'],
            ))
    xarray_A = [(layout['x_left_A'] + i * layout['x_offset_A'],
                 layout['x_right_A'] + i * layout['x_offset_A'])
                for i in range(layout['col_A'])]
    yarray_A = [(layout['y_top_A'] + i * layout['y_offset_A'],
                 layout['y_bottom_A'] + i * layout['y_offset_A'])
                for i in range(layout['row_A'])]
    xarray_B = [(layout['x_left_B'] + i * layout['x_offset_B'],
                 layout['x_right_B'] + i * layout['x_offset_B'])
                for i in range(layout['col_B'])]
    yarray_B = [(layout['y_top_B'] + i * layout['y_offset_B'],
                 layout['y_bottom_B'] + i * layout['y_offset_B'])
                for i in range(layout['row_B'])]
    return position_A, position_B, xarray_A, yarray_A, xarray_B, yarray_B


def resolve_layout(w_left, w_top, w_width, w_hight, ratio=None):
    if w_hight == 0:
        ratio = 1.0
    elif ratio is None:
        ratio = w_width / w_hight
    kind, warn, hard_fail = classify_aspect(ratio, w_width, w_hight)
    if kind == '16:10':
        layout = layout_16_10(w_left, w_top, w_width, w_hight)
    else:
        layout = layout_16_9(w_left, w_top, w_width, w_hight)
    return kind, warn, hard_fail, layout, ratio


try:
    import win32con, win32api, win32gui, win32print
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


def _client_rect_screen(hwnd):
    cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
    sx, sy = win32gui.ClientToScreen(hwnd, (0, 0))
    return (sx, sy, sx + (cr - cl), sy + (cb - ct))


def _find_game_window():
    window_sc = win32gui.FindWindow('UnityWndClass', '原神')
    window_start = win32gui.FindWindow('START Cloud Game', 'START云游戏-Game')
    return window_sc or window_start


def find_game_window():
    '''UnityWndClass/原神 或 START 云游戏。找不到或不在 Windows 上返回 0。'''
    if not _HAS_WIN32:
        return 0
    return _find_game_window()


class _Win32LayoutApi:
    '''真实 win32 读窗口；单测可换成假对象，避免 while True 等窗口。'''

    def find_window(self):
        return _find_game_window()

    def is_iconic(self, hwnd):
        return bool(win32gui.IsIconic(hwnd))

    def get_window_rect(self, hwnd):
        return tuple(win32gui.GetWindowRect(hwnd))

    def get_client_rect_screen(self, hwnd):
        return _client_rect_screen(hwnd)

    def desktop_metrics(self):
        dpi_mode = set_process_dpi_awareness()
        hDC = win32gui.GetDC(0)
        try:
            width_r = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
            height_r = win32print.GetDeviceCaps(hDC, win32con.DESKTOPVERTRES)
            logpixelsx = win32print.GetDeviceCaps(hDC, win32con.LOGPIXELSX)
        finally:
            win32gui.ReleaseDC(0, hDC)
        width_s = win32api.GetSystemMetrics(0)
        height_s = win32api.GetSystemMetrics(1)
        return dict(
            dpi_mode=dpi_mode,
            width_r=width_r,
            height_r=height_r,
            logpixelsx=logpixelsx,
            width_s=width_s,
            height_s=height_s,
        )


class _Win32ForegroundApi:
    def is_iconic(self, hwnd):
        return bool(win32gui.IsIconic(hwnd))

    def show_window(self, hwnd, cmd):
        flag = win32con.SW_RESTORE if cmd == 'restore' else win32con.SW_SHOW
        win32gui.ShowWindow(hwnd, flag)

    def set_foreground(self, hwnd):
        try:
            win32gui.BringWindowToTop(hwnd)
        except Exception:
            pass
        win32gui.SetForegroundWindow(hwnd)

    def get_foreground(self):
        return win32gui.GetForegroundWindow()

    def alt_down(self):
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)

    def alt_up(self):
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)


def try_set_foreground(hwnd, api):
    '''还原最小化窗口并置前。SetForegroundWindow 失败时 ALT 技巧或 SW_RESTORE 再试。'''
    if not hwnd:
        return False

    def _is_fg():
        try:
            return api.get_foreground() == hwnd
        except Exception:
            return False

    try:
        if api.is_iconic(hwnd):
            api.show_window(hwnd, 'restore')
    except Exception:
        pass

    if _is_fg():
        return True

    try:
        api.set_foreground(hwnd)
    except Exception:
        pass
    if _is_fg():
        return True

    try:
        api.alt_down()
        try:
            api.set_foreground(hwnd)
        finally:
            api.alt_up()
    except Exception:
        try:
            api.alt_up()
        except Exception:
            pass
    if _is_fg():
        return True

    try:
        api.show_window(hwnd, 'restore')
        api.set_foreground(hwnd)
    except Exception:
        pass
    return _is_fg()


def bring_game_to_foreground(hwnd=None, settle_s=0.08):
    '''扫描/OCR 前把原神提到最前，不保持最小化。失败只打印，不抛。'''
    if not _HAS_WIN32:
        return False
    hwnd = hwnd or find_game_window()
    if not hwnd:
        print('未找到游戏窗口，无法置顶')
        return False
    api = _Win32ForegroundApi()
    before = None
    iconic = False
    try:
        before = api.get_foreground()
    except Exception:
        pass
    try:
        iconic = bool(api.is_iconic(hwnd))
    except Exception:
        iconic = False
    ok = try_set_foreground(hwnd, api)
    if ok and settle_s and (iconic or before != hwnd):
        time.sleep(settle_s)
    if not ok:
        print('SetForegroundWindow 失败，请手动点击原神窗口置于最前')
    return ok


def _publish_layout(layout, *, scale, window_hwnd, width_r_v, height_r_v,
                    w_left_v, w_top_v, w_width_v, w_hight_v, ratio_v, aspect_kind_v):
    '''把一次测量写入模块全局，供 MainPage / paste_window 读取。'''
    global SCALE, width_r, height_r, window
    global w_left, w_top, w_width, w_hight, ratio, aspect_kind
    global position_A, position_B, xarray_A, yarray_A, xarray_B, yarray_B

    SCALE = scale
    width_r, height_r = width_r_v, height_r_v
    window = window_hwnd
    w_left, w_top, w_width, w_hight = w_left_v, w_top_v, w_width_v, w_hight_v
    ratio = ratio_v
    aspect_kind = aspect_kind_v
    for key, value in layout.items():
        globals()[key] = value
    position_A, position_B, xarray_A, yarray_A, xarray_B, yarray_B = build_positions(layout)


def install_default_layout():
    '''无游戏窗口时的占位 1080p 16:9，保证 import / paste_window 不除零、不阻塞。'''
    kind, _warn, _hard, layout, ratio_v = resolve_layout(0, 0, 1920, 1080)
    _publish_layout(
        layout, scale=1.0, window_hwnd=0, width_r_v=1920, height_r_v=1080,
        w_left_v=0, w_top_v=0, w_width_v=1920, w_hight_v=1080,
        ratio_v=ratio_v, aspect_kind_v=kind)


def scan_geometry():
    '''角色装配页扫描用到的坐标快照（F8 前 MainPage 应刷新后再拷贝）。'''
    return dict(
        SCALE=SCALE,
        x_grab=x_grab_B,
        y_grab=y_grab_B,
        w_grab=w_grab_B,
        h_grab=h_grab_B,
        slot_click=list(slot_click_B),
        slot_overlay=list(slot_overlay_B),
        total_overlay=tuple(total_overlay_B),
        w_width=w_width,
        w_hight=w_hight,
        w_left=w_left,
        w_top=w_top,
        aspect_kind=aspect_kind,
        ratio=ratio,
    )


def bootstrap_once(api=None, verbose=True):
    '''测量游戏窗口一次并更新布局。永不 sleep / while True。
    返回 (ok, msg)：ok 时 msg 为 None；失败时 msg 为 WAIT_MSG_*，且不覆盖已有有效布局。
    '''
    if api is None:
        if not _HAS_WIN32:
            if verbose:
                print(WAIT_MSG_MISSING)
            return False, WAIT_MSG_MISSING
        api = _Win32LayoutApi()

    metrics = api.desktop_metrics()
    dpi_mode = metrics.get('dpi_mode') or 'unaware'
    width_r_v = metrics.get('width_r') or 0
    height_r_v = metrics.get('height_r') or 0
    logpixelsx = metrics.get('logpixelsx')
    width_s = metrics.get('width_s') or 0
    dpi_aware = dpi_mode not in ('unaware', 'skipped-non-windows')

    window_hwnd = 0
    iconic = False
    rect = (0, 0, 0, 0)
    try:
        window_hwnd = api.find_window() or 0
    except Exception:
        window_hwnd = 0
    if window_hwnd:
        try:
            iconic = bool(api.is_iconic(window_hwnd))
        except Exception:
            iconic = False
        try:
            rect = tuple(api.get_window_rect(window_hwnd))
        except Exception:
            rect = (0, 0, 0, 0)
            iconic = True
    wait_msg = decide_window_wait(window_hwnd, iconic, rect)
    if wait_msg:
        if verbose:
            print(wait_msg)
        return False, wait_msg

    left, top, right, bottom = rect
    dpi = read_dpi(window_hwnd, logpixelsx)
    scale_v = compute_scale(width_r_v, width_s, dpi)
    if verbose:
        print(f'物理桌面{width_r_v, height_r_v}  GetSystemMetrics{width_s, metrics.get("height_s")}  '
              f'DPI={dpi}  SCALE={scale_v:.4f}  感知={dpi_mode}')
        print(f'原始 GetWindowRect{left, top, right, bottom}')
    client_rect = None
    try:
        client_rect = api.get_client_rect_screen(window_hwnd)
        if verbose:
            print(f'GetClientRect(screen){client_rect}')
    except Exception as exc:
        if verbose:
            print(f'GetClientRect 失败: {exc}')

    w_left_v, w_top_v, w_width_v, w_hight_v, already, src = correct_window_rect(
        left, top, right, bottom, scale_v, width_r_v, height_r_v,
        client_rect=client_rect, dpi_aware=dpi_aware)
    if verbose:
        print(f'修正后窗口 x,y,w,h{w_left_v, w_top_v, w_width_v, w_hight_v}  '
              f'already_physical={already}  source={src}')
    if (w_width_v <= 0 or w_hight_v <= 0
            or is_minimized_or_invalid_rect(
                w_left_v, w_top_v, w_left_v + w_width_v, w_top_v + w_hight_v)):
        if verbose:
            print(WAIT_MSG_MINIMIZED)
        return False, WAIT_MSG_MINIMIZED

    kind, warn, hard_fail, layout, ratio_v = resolve_layout(
        w_left_v, w_top_v, w_width_v, w_hight_v)
    if verbose:
        print(f'宽高比 ratio={ratio_v:.4f} → {kind}')
        if warn:
            print(warn)
        if hard_fail:
            print('请使用 16:9 或 16:10（窗口 / 无边框，含 4K），然后重新扫描')

    _publish_layout(
        layout, scale=scale_v, window_hwnd=window_hwnd,
        width_r_v=width_r_v, height_r_v=height_r_v,
        w_left_v=w_left_v, w_top_v=w_top_v, w_width_v=w_width_v, w_hight_v=w_hight_v,
        ratio_v=ratio_v, aspect_kind_v=kind)
    return True, None


def refresh_layout(api=None, verbose=True):
    '''扫描 / 贴图前重算窗口布局（分辨率或窗口大小变化后不必重启工具）。'''
    return bootstrap_once(api=api, verbose=verbose)


def prepare_scan_layout(api=None, restore=True, restore_fn=None, verbose=True):
    '''F8 前：尽量还原并置顶原神，再一次性刷新布局。失败返回 WAIT_MSG_*，不循环。'''
    if restore:
        fn = restore_fn if restore_fn is not None else bring_game_to_foreground
        if fn is bring_game_to_foreground:
            fn(settle_s=0.15)
        else:
            fn()
    return refresh_layout(api=api, verbose=verbose)


# 导入只装占位布局；Windows 上再尝试一次真实窗口（失败只打印，不 sleep）。
install_default_layout()
if _HAS_WIN32:
    bootstrap_once()
