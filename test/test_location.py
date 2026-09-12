'''窗口比例 / DPI SCALE / 4K 坐标：不启动原神。'''

import importlib.util
import os
import sys
import time
import types
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    'location_helpers', os.path.join(_ROOT, 'location.py'))
loc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(loc)

_MINIMIZED_RECT = (-32000, -32000, -31763, -31961)


class ScaleTests(unittest.TestCase):
    def test_unaware_200_percent_uses_metrics(self):
        self.assertEqual(loc.compute_scale(3840, 1920, dpi=96), 2.0)

    def test_dpi_aware_200_percent_does_not_collapse_to_1(self):
        # Per-Monitor 后 SM 已是物理像素，SCALE 应来自 DPI=192
        self.assertEqual(loc.compute_scale(3840, 3840, dpi=192), 2.0)

    def test_dpi_aware_150_percent(self):
        self.assertAlmostEqual(loc.compute_scale(3840, 3840, dpi=144), 1.5)

    def test_100_percent(self):
        self.assertEqual(loc.compute_scale(1920, 1920, dpi=96), 1.0)


class PhysicalRectTests(unittest.TestCase):
    def test_4k_rect_with_scale_2_is_already_physical(self):
        self.assertTrue(loc.rect_already_physical(
            0, 0, 3840, 2160, scale=2.0, desktop_w=3840, desktop_h=2160))

    def test_logical_1080p_on_4k_200pct_is_not_physical(self):
        self.assertFalse(loc.rect_already_physical(
            0, 0, 1920, 1080, scale=2.0, desktop_w=3840, desktop_h=2160))

    def test_dpi_aware_flag(self):
        self.assertTrue(loc.rect_already_physical(
            10, 10, 1930, 1090, scale=2.0, desktop_w=3840, desktop_h=2160,
            dpi_aware=True))


class CorrectRectTests(unittest.TestCase):
    def test_old_double_scale_warps_ratio_off_16_9(self):
        left, top, right, bottom = 0, 0, 3840, 2160
        scale = 2.0
        w = (right - left - 14) * scale
        h = (bottom - top - 38) * scale
        self.assertGreater(w / h, 1.8)

    def test_4k_borderless_physical_no_double_scale(self):
        x, y, w, h, already, src = loc.correct_window_rect(
            0, 0, 3840, 2160, 2.0, 3840, 2160, dpi_aware=True)
        self.assertEqual((x, y, w, h), (0, 0, 3840, 2160))
        self.assertTrue(already)
        self.assertEqual(src, 'borderless')
        self.assertAlmostEqual(w / h, 16 / 9, places=4)

    def test_4k_borderless_via_client_rect(self):
        x, y, w, h, already, src = loc.correct_window_rect(
            -8, -8, 3848, 2168, 2.0, 3840, 2160,
            client_rect=(0, 0, 3840, 2160), dpi_aware=True)
        self.assertEqual((x, y, w, h), (0, 0, 3840, 2160))
        self.assertEqual(src, 'client')
        self.assertAlmostEqual(w / h, 16 / 9, places=4)

    def test_logical_borderless_multiplies_once(self):
        x, y, w, h, already, src = loc.correct_window_rect(
            0, 0, 1920, 1080, 2.0, 3840, 2160, dpi_aware=False)
        self.assertFalse(already)
        self.assertEqual((w, h), (3840.0, 2160.0))
        self.assertAlmostEqual(w / h, 16 / 9, places=4)

    def test_logical_windowed_caption_then_scale(self):
        # 1920x1080 客户区，带 7/31 边框的逻辑 GetWindowRect
        left, top, right, bottom = 100, 100, 100 + 1920 + 14, 100 + 1080 + 38
        x, y, w, h, already, src = loc.correct_window_rect(
            left, top, right, bottom, 2.0, 3840, 2160, dpi_aware=False)
        self.assertEqual(src, 'caption')
        self.assertAlmostEqual(w, 3840.0)
        self.assertAlmostEqual(h, 2160.0)

    def test_150_percent_4k_borderless_physical(self):
        x, y, w, h, already, src = loc.correct_window_rect(
            0, 0, 3840, 2160, 1.5, 3840, 2160, dpi_aware=True)
        self.assertEqual((w, h), (3840, 2160))
        self.assertEqual(src, 'borderless')


class AspectTests(unittest.TestCase):
    def test_exact_16_9(self):
        kind, warn, hard = loc.classify_aspect(3840 / 2160, 3840, 2160)
        self.assertEqual(kind, '16:9')
        self.assertFalse(hard)
        self.assertIsNone(warn)

    def test_exact_16_10(self):
        kind, warn, hard = loc.classify_aspect(2560 / 1600, 2560, 1600)
        self.assertEqual(kind, '16:10')
        self.assertFalse(hard)

    def test_old_warped_1_803_still_16_9(self):
        kind, warn, hard = loc.classify_aspect(7652 / 4244, 7652, 4244)
        self.assertEqual(kind, '16:9')
        self.assertFalse(hard)

    def test_ultrawide_hard_fail(self):
        kind, warn, hard = loc.classify_aspect(3440 / 1440, 3440, 1440)
        self.assertEqual(kind, 'unsupported')
        self.assertTrue(hard)
        self.assertIn('暂不支持', warn)
        self.assertNotIn('1920*1080', warn)
        self.assertNotIn('1920×1080', warn)

    def test_large_near_16_9_fallback(self):
        kind, warn, hard = loc.classify_aspect(1.90, 3840, 2020)
        self.assertEqual(kind, '16:9')
        self.assertFalse(hard)
        self.assertIsNotNone(warn)


class Layout4kTests(unittest.TestCase):
    def test_4k_16_9_uses_1080_fractions(self):
        kind, warn, hard, layout, ratio = loc.resolve_layout(0, 0, 3840, 2160)
        self.assertEqual(kind, '16:9')
        self.assertFalse(hard)
        self.assertAlmostEqual(ratio, 16 / 9, places=4)
        flower = layout['slot_click_B'][0]
        self.assertAlmostEqual(flower[0], 84 / 1920 * 3840)
        self.assertAlmostEqual(flower[1], 44 / 1080 * 2160)
        self.assertAlmostEqual(layout['x_grab_A'], 1331 / 1920 * 3840)

    def test_4k_16_10(self):
        kind, warn, hard, layout, ratio = loc.resolve_layout(0, 0, 3840, 2400)
        self.assertEqual(kind, '16:10')
        self.assertAlmostEqual(layout['slot_click_B'][0][0], 112 / 2560 * 3840)

    def test_else_no_longer_forces_1080_message_for_4k(self):
        kind, warn, hard, layout, ratio = loc.resolve_layout(0, 0, 3840, 2160)
        self.assertEqual(kind, '16:9')
        self.assertIsNone(warn)
        text = (warn or '') + kind
        self.assertNotIn('1920*1080', text)


class OverlayLayoutTests(unittest.TestCase):
    '''合计贴图须在部位数字下方，不能盖住 24px 参考框。'''

    def _assert_total_below_slots(self, layout, w_width):
        slot_h = loc.slot_paste_height(w_width)
        slot_bottom = max(y for _, y in layout['slot_overlay_B']) + slot_h
        total_y = layout['total_overlay_B'][1]
        self.assertGreaterEqual(total_y, slot_bottom)

    def test_16_9_1080_total_below_slots(self):
        _, _, _, layout, _ = loc.resolve_layout(0, 0, 1920, 1080)
        self._assert_total_below_slots(layout, 1920)
        self.assertAlmostEqual(layout['slot_overlay_B'][0][1], 62)
        # 旧坐标 y=82 会盖住 62+36 的部位框
        self.assertGreaterEqual(layout['total_overlay_B'][1], 62 + 36)

    def test_16_9_4k_total_below_slots(self):
        _, _, _, layout, _ = loc.resolve_layout(0, 0, 3840, 2160)
        self._assert_total_below_slots(layout, 3840)

    def test_16_10_total_below_slots(self):
        _, _, _, layout, _ = loc.resolve_layout(0, 0, 2560, 1600)
        self._assert_total_below_slots(layout, 2560)

    def test_16_10_4k_total_below_slots(self):
        _, _, _, layout, _ = loc.resolve_layout(0, 0, 3840, 2400)
        self._assert_total_below_slots(layout, 3840)


class MinimizedRectTests(unittest.TestCase):
    # 用户日志：GetWindowRect(-32000, -32000, -31763, -31961) → 宽高比 -12、OCR 负高度崩溃
    _BUG_RECT = (-32000, -32000, -31763, -31961)

    def test_bug_screenshot_rect_is_invalid(self):
        self.assertTrue(loc.is_minimized_or_invalid_rect(*self._BUG_RECT))

    def test_iconic_flag_invalid_even_if_rect_looks_normal(self):
        self.assertTrue(loc.is_minimized_or_invalid_rect(
            0, 0, 3840, 2160, iconic=True))

    def test_restored_4k_rect_is_valid(self):
        self.assertFalse(loc.is_minimized_or_invalid_rect(0, 0, 3840, 2160))

    def test_multimonitor_negative_origin_is_valid(self):
        self.assertFalse(loc.is_minimized_or_invalid_rect(-1920, 0, 0, 1080))

    def test_non_positive_size_is_invalid(self):
        self.assertTrue(loc.is_minimized_or_invalid_rect(10, 10, 10, 100))
        self.assertTrue(loc.is_minimized_or_invalid_rect(0, 100, 100, 50))

    def test_caption_correction_of_minimized_still_unusable(self):
        x, y, w, h, already, src = loc.correct_window_rect(
            *self._BUG_RECT, 1.5, 3840, 2160, dpi_aware=True)
        self.assertAlmostEqual(x, -31989.5)
        self.assertAlmostEqual(y, -31953.5)
        self.assertAlmostEqual(w, 216.0)
        self.assertAlmostEqual(h, -18.0)
        self.assertTrue(w <= 0 or h <= 0)
        self.assertTrue(loc.is_invalid_grab_bbox(x, y, w, h))

    def test_wait_message_minimized(self):
        msg = loc.decide_window_wait(1, False, self._BUG_RECT)
        self.assertEqual(msg, loc.WAIT_MSG_MINIMIZED)
        self.assertIn('最小化', msg)
        self.assertEqual(loc.decide_window_wait(1, True, (0, 0, 3840, 2160)),
                         loc.WAIT_MSG_MINIMIZED)
        self.assertEqual(loc.decide_window_wait(0, False, (0, 0, 0, 0)),
                         loc.WAIT_MSG_MISSING)

    def test_wait_none_when_restored(self):
        self.assertIsNone(loc.decide_window_wait(42, False, (0, 0, 3840, 2160)))

    def test_invalid_grab_bbox_negative_height(self):
        self.assertTrue(loc.is_invalid_grab_bbox(-31989.5, -31953.5, 216.0, -18.0))
        self.assertFalse(loc.is_invalid_grab_bbox(100, 100, 400, 500))

    def test_restored_4k_still_16_9(self):
        kind, warn, hard, layout, ratio = loc.resolve_layout(0, 0, 3840, 2160)
        self.assertEqual(kind, '16:9')
        self.assertFalse(hard)
        self.assertAlmostEqual(ratio, 16 / 9, places=2)
        self.assertAlmostEqual(ratio, 1.78, places=2)


class FakeForegroundApi:
    def __init__(self, hwnd=42, fg=99, iconic=False, set_fails=0, raise_on_set=True):
        self.hwnd = hwnd
        self.fg = fg
        self.iconic = iconic
        self.set_fails = set_fails
        self.raise_on_set = raise_on_set
        self.calls = []

    def is_iconic(self, hwnd):
        return self.iconic

    def show_window(self, hwnd, cmd):
        self.calls.append(('show', cmd))
        self.iconic = False

    def set_foreground(self, hwnd):
        self.calls.append(('set', hwnd))
        if self.set_fails > 0:
            self.set_fails -= 1
            if self.raise_on_set:
                raise OSError('SetForegroundWindow denied')
            return
        self.fg = hwnd

    def get_foreground(self):
        return self.fg

    def alt_down(self):
        self.calls.append('alt_down')

    def alt_up(self):
        self.calls.append('alt_up')


class ForegroundTests(unittest.TestCase):
    def test_already_foreground_skips_alt(self):
        api = FakeForegroundApi(hwnd=7, fg=7)
        self.assertTrue(loc.try_set_foreground(7, api))
        self.assertNotIn('alt_down', api.calls)
        self.assertNotIn(('set', 7), api.calls)

    def test_iconic_restores_then_sets(self):
        api = FakeForegroundApi(hwnd=7, fg=1, iconic=True)
        self.assertTrue(loc.try_set_foreground(7, api))
        self.assertIn(('show', 'restore'), api.calls)
        self.assertIn(('set', 7), api.calls)
        self.assertFalse(api.iconic)
        self.assertEqual(api.fg, 7)

    def test_set_denied_uses_alt_trick(self):
        api = FakeForegroundApi(hwnd=7, fg=1, set_fails=1)
        self.assertTrue(loc.try_set_foreground(7, api))
        self.assertIn('alt_down', api.calls)
        self.assertIn('alt_up', api.calls)
        self.assertEqual(api.fg, 7)

    def test_alt_fail_then_restore_retry(self):
        api = FakeForegroundApi(hwnd=7, fg=1, set_fails=2)
        self.assertTrue(loc.try_set_foreground(7, api))
        shows = [c for c in api.calls if c[0] == 'show']
        self.assertTrue(any(c[1] == 'restore' for c in shows))
        self.assertEqual(api.fg, 7)

    def test_missing_hwnd_false(self):
        api = FakeForegroundApi()
        self.assertFalse(loc.try_set_foreground(0, api))
        self.assertFalse(loc.try_set_foreground(None, api))

    def test_find_game_window_without_win32(self):
        self.assertFalse(loc._HAS_WIN32)
        self.assertEqual(loc.find_game_window(), 0)
        self.assertFalse(loc.bring_game_to_foreground())


class FakeLayoutApi:
    def __init__(self, hwnd=1, iconic=False, rect=(0, 0, 3840, 2160),
                 client_rect=None, desktop=(3840, 2160), sm=None,
                 logpixelsx=144, dpi_mode='Per-Monitor-V2'):
        self.hwnd = hwnd
        self.iconic = iconic
        self.rect = rect
        self.client_rect = client_rect if client_rect is not None else rect
        self.desktop = desktop
        self.sm = sm or desktop
        self.logpixelsx = logpixelsx
        self.dpi_mode = dpi_mode

    def find_window(self):
        return self.hwnd

    def is_iconic(self, hwnd):
        return self.iconic

    def get_window_rect(self, hwnd):
        return self.rect

    def get_client_rect_screen(self, hwnd):
        if self.client_rect is None:
            raise OSError('no client')
        return self.client_rect

    def desktop_metrics(self):
        return dict(
            dpi_mode=self.dpi_mode,
            width_r=self.desktop[0],
            height_r=self.desktop[1],
            logpixelsx=self.logpixelsx,
            width_s=self.sm[0],
            height_s=self.sm[1],
        )


def _sleep_bomb(seconds):
    raise AssertionError('bootstrap slept %.3fs; must not wait-loop' % seconds)


class BootstrapOnceTests(unittest.TestCase):
    def setUp(self):
        loc.install_default_layout()
        self._orig_sleep = loc.time.sleep
        loc.time.sleep = _sleep_bomb

    def tearDown(self):
        loc.time.sleep = self._orig_sleep
        loc.install_default_layout()

    def test_default_layout_is_1080p(self):
        geo = loc.scan_geometry()
        self.assertEqual(geo['SCALE'], 1.0)
        self.assertEqual(geo['w_width'], 1920)
        self.assertEqual(geo['w_hight'], 1080)
        self.assertEqual(geo['aspect_kind'], '16:9')

    def test_missing_window_returns_wait_msg_without_sleep(self):
        api = FakeLayoutApi(hwnd=0, rect=(0, 0, 0, 0))
        ok, msg = loc.bootstrap_once(api=api, verbose=False)
        self.assertFalse(ok)
        self.assertEqual(msg, loc.WAIT_MSG_MISSING)

    def test_minimized_returns_wait_msg_without_sleep(self):
        api = FakeLayoutApi(hwnd=1, iconic=True, rect=_MINIMIZED_RECT)
        ok, msg = loc.bootstrap_once(api=api, verbose=False)
        self.assertFalse(ok)
        self.assertEqual(msg, loc.WAIT_MSG_MINIMIZED)
        self.assertIn('最小化', msg)

    def test_minimized_sentinel_rect_without_iconic_flag(self):
        api = FakeLayoutApi(hwnd=1, iconic=False, rect=_MINIMIZED_RECT)
        ok, msg = loc.refresh_layout(api=api, verbose=False)
        self.assertFalse(ok)
        self.assertEqual(msg, loc.WAIT_MSG_MINIMIZED)

    def test_minimized_many_calls_finish_quickly(self):
        api = FakeLayoutApi(hwnd=1, iconic=True, rect=_MINIMIZED_RECT)
        start = time.monotonic()
        for _ in range(40):
            ok, msg = loc.bootstrap_once(api=api, verbose=False)
            self.assertFalse(ok)
            self.assertEqual(msg, loc.WAIT_MSG_MINIMIZED)
        self.assertLess(time.monotonic() - start, 1.0)

    def test_failed_bootstrap_does_not_clobber_valid_layout(self):
        api4k = FakeLayoutApi(
            rect=(0, 0, 3840, 2160), client_rect=(0, 0, 3840, 2160),
            desktop=(3840, 2160), logpixelsx=144)
        ok, msg = loc.bootstrap_once(api=api4k, verbose=False)
        self.assertTrue(ok)
        self.assertIsNone(msg)
        flower = loc.slot_click_B[0]
        grab_w = loc.w_grab_B
        api_min = FakeLayoutApi(iconic=True, rect=_MINIMIZED_RECT)
        ok, msg = loc.bootstrap_once(api=api_min, verbose=False)
        self.assertFalse(ok)
        self.assertAlmostEqual(loc.slot_click_B[0][0], flower[0])
        self.assertAlmostEqual(loc.w_grab_B, grab_w)

    def test_refresh_after_fake_size_change_1440_to_4k(self):
        api1440 = FakeLayoutApi(
            rect=(0, 0, 2560, 1440), client_rect=(0, 0, 2560, 1440),
            desktop=(2560, 1440), logpixelsx=96)
        ok, _ = loc.refresh_layout(api=api1440, verbose=False)
        self.assertTrue(ok)
        geo1440 = loc.scan_geometry()
        self.assertAlmostEqual(geo1440['slot_click'][0][0], 84 / 1920 * 2560)
        self.assertAlmostEqual(geo1440['w_width'], 2560)
        self.assertAlmostEqual(geo1440['x_grab'], 1461 / 1920 * 2560)

        api4k = FakeLayoutApi(
            rect=(0, 0, 3840, 2160), client_rect=(0, 0, 3840, 2160),
            desktop=(3840, 2160), logpixelsx=144)
        ok, _ = loc.refresh_layout(api=api4k, verbose=False)
        self.assertTrue(ok)
        geo4k = loc.scan_geometry()
        self.assertAlmostEqual(geo4k['slot_click'][0][0], 84 / 1920 * 3840)
        self.assertAlmostEqual(geo4k['slot_click'][0][1], 44 / 1080 * 2160)
        self.assertAlmostEqual(geo4k['w_width'], 3840)
        self.assertAlmostEqual(geo4k['h_grab'], 378 / 1080 * 2160)
        self.assertNotAlmostEqual(geo4k['slot_click'][0][0], geo1440['slot_click'][0][0])
        self.assertNotAlmostEqual(geo4k['x_grab'], geo1440['x_grab'])
        self.assertAlmostEqual(geo4k['SCALE'], 1.5)
        self.assertEqual(geo4k['aspect_kind'], '16:9')

    def test_prepare_scan_restores_then_refreshes(self):
        api = FakeLayoutApi(hwnd=7, iconic=True, rect=_MINIMIZED_RECT)
        calls = []

        def restore():
            calls.append('restore')
            api.iconic = False
            api.rect = (0, 0, 3840, 2160)
            api.client_rect = (0, 0, 3840, 2160)

        ok, msg = loc.prepare_scan_layout(
            api=api, restore_fn=restore, verbose=False)
        self.assertEqual(calls, ['restore'])
        self.assertTrue(ok)
        self.assertIsNone(msg)
        self.assertAlmostEqual(loc.w_width, 3840)

    def test_prepare_scan_still_invalid_aborts_with_wait_msg(self):
        api = FakeLayoutApi(hwnd=7, iconic=True, rect=_MINIMIZED_RECT)
        ok, msg = loc.prepare_scan_layout(
            api=api, restore_fn=lambda: None, verbose=False)
        self.assertFalse(ok)
        self.assertEqual(msg, loc.WAIT_MSG_MINIMIZED)

    def test_paste_qt_scale_uses_current_width(self):
        api4k = FakeLayoutApi(
            rect=(0, 0, 3840, 2160), client_rect=(0, 0, 3840, 2160),
            desktop=(3840, 2160), logpixelsx=144)
        loc.refresh_layout(api=api4k, verbose=False)
        self.assertAlmostEqual(loc.paste_qt_scale(), 3840 / 1280 / 1.5)


def _install_fake_win32(hwnd=1, iconic=True, rect=_MINIMIZED_RECT):
    win32con = types.ModuleType('win32con')
    win32con.DESKTOPHORZRES = 118
    win32con.DESKTOPVERTRES = 117
    win32con.LOGPIXELSX = 88
    win32con.SW_RESTORE = 9
    win32con.SW_SHOW = 5
    win32con.VK_MENU = 18
    win32con.KEYEVENTF_KEYUP = 2

    win32api = types.ModuleType('win32api')
    win32api.GetSystemMetrics = lambda i: 3840 if i == 0 else 2160
    win32api.keybd_event = lambda *a, **k: None

    win32gui = types.ModuleType('win32gui')
    win32gui.FindWindow = lambda *a, **k: hwnd
    win32gui.IsIconic = lambda h: iconic
    win32gui.GetWindowRect = lambda h: rect
    win32gui.GetDC = lambda h: 1
    win32gui.ReleaseDC = lambda *a, **k: None
    win32gui.GetClientRect = lambda h: (0, 0, 0, 0)
    win32gui.ClientToScreen = lambda h, p: (rect[0], rect[1])
    win32gui.BringWindowToTop = lambda h: None
    win32gui.SetForegroundWindow = lambda h: None
    win32gui.GetForegroundWindow = lambda: 0
    win32gui.ShowWindow = lambda h, c: None

    win32print = types.ModuleType('win32print')
    caps = {118: 3840, 117: 2160, 88: 144}
    win32print.GetDeviceCaps = lambda hdc, idx: caps.get(idx, 96)

    sys.modules['win32con'] = win32con
    sys.modules['win32api'] = win32api
    sys.modules['win32gui'] = win32gui
    sys.modules['win32print'] = win32print


def _clear_fake_win32():
    for key in ('win32con', 'win32api', 'win32gui', 'win32print'):
        sys.modules.pop(key, None)


class ImportDoesNotHangTests(unittest.TestCase):
    def test_import_with_minimized_win32_does_not_loop(self):
        name = 'location_fake_win32_minimized'
        sys.modules.pop(name, None)
        _install_fake_win32(iconic=True, rect=_MINIMIZED_RECT)
        orig_sleep = time.sleep
        time.sleep = _sleep_bomb
        try:
            spec = importlib.util.spec_from_file_location(
                name, os.path.join(_ROOT, 'location.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertTrue(mod._HAS_WIN32)
            self.assertEqual(mod.w_width, 1920)
            self.assertEqual(mod.SCALE, 1.0)
            ok, msg = mod.bootstrap_once(verbose=False)
            self.assertFalse(ok)
            self.assertEqual(msg, mod.WAIT_MSG_MINIMIZED)
        finally:
            time.sleep = orig_sleep
            _clear_fake_win32()
            sys.modules.pop(name, None)

    def test_import_with_missing_window_keeps_default_layout(self):
        name = 'location_fake_win32_missing'
        sys.modules.pop(name, None)
        _install_fake_win32(hwnd=0, iconic=False, rect=(0, 0, 0, 0))
        orig_sleep = time.sleep
        time.sleep = _sleep_bomb
        try:
            spec = importlib.util.spec_from_file_location(
                name, os.path.join(_ROOT, 'location.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        finally:
            time.sleep = orig_sleep
            _clear_fake_win32()
            sys.modules.pop(name, None)
        self.assertEqual(mod.w_width, 1920)
        self.assertAlmostEqual(mod.slot_click_B[0][0], 84)


if __name__ == '__main__':
    unittest.main()
