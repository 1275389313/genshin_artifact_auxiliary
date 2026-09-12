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
           f'请使用 16:9 或 16:10 窗口/无边框（含 4K），然后重启软件。')
    return 'unsupported', msg, True


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
            (138 / 2560 * w_width + w_left, 82 / 1600 * w_hight + w_top),
            (291 / 2560 * w_width + w_left, 82 / 1600 * w_hight + w_top),
            (439 / 2560 * w_width + w_left, 82 / 1600 * w_hight + w_top),
            (582 / 2560 * w_width + w_left, 82 / 1600 * w_hight + w_top),
            (732 / 2560 * w_width + w_left, 82 / 1600 * w_hight + w_top),
        ],
        total_overlay_B=(200 / 2560 * w_width + w_left, 110 / 1600 * w_hight + w_top),
    )


def layout_16_9(w_left, w_top, w_width, w_hight):
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
            (104 / 1920 * w_width + w_left, 62 / 1080 * w_hight + w_top),
            (218 / 1920 * w_width + w_left, 62 / 1080 * w_hight + w_top),
            (329 / 1920 * w_width + w_left, 62 / 1080 * w_hight + w_top),
            (437 / 1920 * w_width + w_left, 62 / 1080 * w_hight + w_top),
            (549 / 1920 * w_width + w_left, 62 / 1080 * w_hight + w_top),
        ],
        total_overlay_B=(150 / 1920 * w_width + w_left, 82 / 1080 * w_hight + w_top),
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


def _bootstrap():
    global SCALE, width_r, height_r, window
    global w_left, w_top, w_width, w_hight, ratio, aspect_kind
    global x_initial_A, y_initial_A, x_offset_A, y_offset_A
    global x_left_A, x_right_A, y_top_A, y_bottom_A
    global x_grab_A, y_grab_A, w_grab_A, h_grab_A, row_A, col_A
    global x_initial_B, y_initial_B, x_offset_B, y_offset_B
    global x_left_B, x_right_B, y_top_B, y_bottom_B
    global x_grab_B, y_grab_B, w_grab_B, h_grab_B, row_B, col_B
    global slot_click_B, slot_overlay_B, total_overlay_B
    global position_A, position_B, xarray_A, yarray_A, xarray_B, yarray_B

    dpi_mode = set_process_dpi_awareness()
    hDC = win32gui.GetDC(0)
    width_r = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
    height_r = win32print.GetDeviceCaps(hDC, win32con.DESKTOPVERTRES)
    logpixelsx = win32print.GetDeviceCaps(hDC, win32con.LOGPIXELSX)
    win32gui.ReleaseDC(0, hDC)
    width_s = win32api.GetSystemMetrics(0)
    height_s = win32api.GetSystemMetrics(1)
    dpi_aware = dpi_mode not in ('unaware', 'skipped-non-windows')

    # 未找到、或最小化（GetWindowRect≈-32000）时循环等待，不把无效矩形当布局。
    while True:
        window = _find_game_window()
        iconic = False
        rect = (0, 0, 0, 0)
        if window:
            try:
                iconic = bool(win32gui.IsIconic(window))
            except Exception:
                iconic = False
            try:
                rect = tuple(win32gui.GetWindowRect(window))
            except Exception:
                rect = (0, 0, 0, 0)
                iconic = True
        wait_msg = decide_window_wait(window, iconic, rect)
        if wait_msg:
            print(wait_msg)
            time.sleep(5)
            continue

        left, top, right, bottom = rect
        # left, top, right, bottom = (0, 0, 3840, 2160)  # 游戏窗口不打开时后门，测试用
        dpi = read_dpi(window, logpixelsx)
        SCALE = compute_scale(width_r, width_s, dpi)
        print(f'物理桌面{width_r, height_r}  GetSystemMetrics{width_s, height_s}  '
              f'DPI={dpi}  SCALE={SCALE:.4f}  感知={dpi_mode}')
        print(f'原始 GetWindowRect{left, top, right, bottom}')
        client_rect = None
        try:
            client_rect = _client_rect_screen(window)
            print(f'GetClientRect(screen){client_rect}')
        except Exception as exc:
            print(f'GetClientRect 失败: {exc}')

        w_left, w_top, w_width, w_hight, already, src = correct_window_rect(
            left, top, right, bottom, SCALE, width_r, height_r,
            client_rect=client_rect, dpi_aware=dpi_aware)
        print(f'修正后窗口 x,y,w,h{w_left, w_top, w_width, w_hight}  '
              f'already_physical={already}  source={src}')
        if (w_width <= 0 or w_hight <= 0
                or is_minimized_or_invalid_rect(
                    w_left, w_top, w_left + w_width, w_top + w_hight)):
            print(WAIT_MSG_MINIMIZED)
            time.sleep(5)
            continue
        break

    kind, warn, hard_fail, layout, ratio = resolve_layout(
        w_left, w_top, w_width, w_hight)
    aspect_kind = kind
    print(f'宽高比 ratio={ratio:.4f} → {kind}')
    if warn:
        print(warn)
    if hard_fail:
        print('请使用 16:9 或 16:10（窗口 / 无边框，含 4K），然后重启软件')

    for key, value in layout.items():
        globals()[key] = value
    position_A, position_B, xarray_A, yarray_A, xarray_B, yarray_B = build_positions(layout)


if _HAS_WIN32:
    _bootstrap()
