'''窗口比例 / DPI SCALE / 4K 坐标：不启动原神。'''

import importlib.util
import os
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    'location_helpers', os.path.join(_ROOT, 'location.py'))
loc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(loc)


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


if __name__ == '__main__':
    unittest.main()
