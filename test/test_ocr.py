'''OCR 空白截图 / RapidOCR txts=None：不启动原神、不跑真实引擎。'''

import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_ocr():
    name = 'ocr_blank_helpers'
    if name in sys.modules:
        return sys.modules[name]
    rapid = types.ModuleType('rapidocr')
    rapid.RapidOCR = MagicMock(return_value=MagicMock())
    sys.modules['rapidocr'] = rapid
    spec = importlib.util.spec_from_file_location(name, os.path.join(_ROOT, 'ocr.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules[name] = mod
    return mod


class RequireOcrTextsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocr = _load_ocr()

    def test_none_raises_chinese_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            self.ocr.require_ocr_texts(None)
        self.assertIn('截图空白', str(ctx.exception))
        self.assertIn('原神窗口在最前', str(ctx.exception))

    def test_empty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            self.ocr.require_ocr_texts([])
        self.assertIn('截图空白', str(ctx.exception))

    def test_empty_tuple_raises(self):
        with self.assertRaises(ValueError):
            self.ocr.require_ocr_texts(())

    def test_texts_pass_through(self):
        txts = ['异种的期许', '生之花']
        self.assertIs(self.ocr.require_ocr_texts(txts), txts)


class NearBlankImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocr = _load_ocr()
        from PIL import Image
        cls.Image = Image

    def test_near_white_252_is_blank(self):
        img = self.Image.new('RGB', (80, 40), (252, 252, 252))
        self.assertTrue(self.ocr.is_near_blank_image(img))

    def test_near_black_is_blank(self):
        img = self.Image.new('RGB', (80, 40), (4, 4, 4))
        self.assertTrue(self.ocr.is_near_blank_image(img))

    def test_artifact_like_red_panel_is_not_blank(self):
        img = self.Image.new('RGB', (200, 360), (160, 40, 36))
        for y in range(20, 80):
            for x in range(20, 180):
                img.putpixel((x, y), (255, 240, 230))
        for y in range(120, 140):
            for x in range(30, 160):
                img.putpixel((x, y), (20, 16, 16))
        self.assertFalse(self.ocr.is_near_blank_image(img))

    def test_none_is_blank(self):
        self.assertTrue(self.ocr.is_near_blank_image(None))


class RapidOcrEmptyGrabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocr = _load_ocr()
        from PIL import Image
        cls.Image = Image

    def test_none_txts_no_typeerror(self):
        from PIL import ImageGrab
        white = self.Image.new('RGB', (40, 20), (200, 80, 70))
        self.ocr.ImageGrab = ImageGrab
        orig_grab = ImageGrab.grab
        orig_engine = self.ocr.ocr
        orig_blank = self.ocr.is_near_blank_image
        orig_fg = self.ocr._bring_game_foreground
        orig_save = self.Image.Image.save

        class EmptyResult:
            txts = None

            def vis(self, path):
                raise AssertionError('vis should not run when txts is None')

        try:
            ImageGrab.grab = lambda bbox=None: white
            self.Image.Image.save = lambda *a, **k: None
            self.ocr.is_near_blank_image = lambda img, **k: False
            self.ocr._bring_game_foreground = lambda: True
            self.ocr.ocr = lambda *a, **k: EmptyResult()
            with self.assertRaises(ValueError) as ctx:
                self.ocr.rapid_ocr(10, 10, 40, 20)
            self.assertIn('截图空白', str(ctx.exception))
        finally:
            ImageGrab.grab = orig_grab
            self.ocr.ocr = orig_engine
            self.ocr.is_near_blank_image = orig_blank
            self.ocr._bring_game_foreground = orig_fg
            self.Image.Image.save = orig_save

    def test_white_grab_raises_before_engine(self):
        from PIL import ImageGrab
        white = self.Image.new('RGB', (40, 20), (252, 252, 252))
        orig_grab = ImageGrab.grab
        orig_save = self.Image.Image.save
        called = {'ocr': False}

        def boom(*a, **k):
            called['ocr'] = True
            raise AssertionError('engine should not run on blank grab')

        orig_engine = self.ocr.ocr
        orig_fg = self.ocr._bring_game_foreground
        try:
            ImageGrab.grab = lambda bbox=None: white
            self.Image.Image.save = lambda *a, **k: None
            self.ocr._bring_game_foreground = lambda: True
            self.ocr.ocr = boom
            with self.assertRaises(ValueError) as ctx:
                self.ocr.rapid_ocr(10, 10, 40, 20)
            self.assertIn('截图空白', str(ctx.exception))
            self.assertFalse(called['ocr'])
        finally:
            ImageGrab.grab = orig_grab
            self.ocr.ocr = orig_engine
            self.ocr._bring_game_foreground = orig_fg
            self.Image.Image.save = orig_save

    def test_invalid_bbox_still_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.ocr.rapid_ocr(-32000, -32000, 216, -18)
        self.assertIn('截图区域无效', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
