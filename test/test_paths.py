'''Bundled resource paths: source tree vs PyInstaller frozen (_MEIPASS).'''

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_ROOT, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


paths = _load('paths', 'paths.py')


class ResourcePathTests(unittest.TestCase):
    def test_source_run_uses_project_root(self):
        with patch.object(paths.sys, 'frozen', False, create=True):
            got = paths.resource_path('src', 'character.json')
        self.assertEqual(got, os.path.join(_ROOT, 'src', 'character.json'))
        self.assertTrue(os.path.isfile(got))

    def test_frozen_uses_meipass(self):
        meipass = os.path.join(tempfile.gettempdir(), 'keqing-fake-meipass')
        with patch.object(paths.sys, 'frozen', True, create=True), \
             patch.object(paths.sys, '_MEIPASS', meipass, create=True):
            got = paths.resource_path('src', 'character.json')
        self.assertEqual(got, os.path.join(meipass, 'src', 'character.json'))

    def test_frozen_without_meipass_uses_executable_dir(self):
        fake_exe = os.path.join(tempfile.gettempdir(), 'dist', 'keqing.exe')
        orig = getattr(paths.sys, '_MEIPASS', None)
        had = hasattr(paths.sys, '_MEIPASS')
        try:
            if had:
                delattr(paths.sys, '_MEIPASS')
            with patch.object(paths.sys, 'frozen', True, create=True), \
                 patch.object(paths.sys, 'executable', fake_exe):
                got = paths.bundled_root()
        finally:
            if had:
                paths.sys._MEIPASS = orig
        self.assertEqual(got, os.path.dirname(os.path.abspath(fake_exe)))


class OcrCachePathTests(unittest.TestCase):
    def test_cache_under_platform_temp(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(paths.tempfile, 'gettempdir', return_value=td):
                cache = paths.ocr_cache_dir()
                grab = paths.ocr_cache_path('grab.png')
                out = paths.ocr_cache_path('out.png')
            self.assertEqual(cache, os.path.join(td, 'keqing_ocr'))
            self.assertTrue(os.path.isdir(cache))
            self.assertEqual(grab, os.path.join(td, 'keqing_ocr', 'grab.png'))
            self.assertEqual(out, os.path.join(td, 'keqing_ocr', 'out.png'))
            self.assertNotIn(os.path.join('src', 'grab.png'), grab.replace('/', os.sep))


class DocBundledDefaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = _load('doc_paths_test', 'doc.py')

    def test_import_doc_without_cwd_src(self):
        '''Admin/frozen runs often have cwd without src/; must not FileNotFoundError.'''
        with tempfile.TemporaryDirectory() as td:
            old = os.getcwd()
            os.chdir(td)
            try:
                self.assertFalse(os.path.exists('src/character.json'))
                self.doc.ensure_user_data()
            finally:
                os.chdir(old)

    def test_merge_missing_default_keeps_user_file(self):
        with tempfile.TemporaryDirectory() as td:
            user_path = os.path.join(td, 'character.json')
            with open(user_path, 'w', encoding='utf-8') as fp:
                json.dump({'已有角色': {'暴击率': 1}}, fp, ensure_ascii=False)
            missing = os.path.join(td, 'no-such-character.json')
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.doc.merge_new_characters(user_path, src=missing)
            with open(user_path, 'r', encoding='utf-8') as fp:
                user = json.load(fp)
            self.assertEqual(user, {'已有角色': {'暴击率': 1}})
            self.assertIn('未找到默认角色配置', buf.getvalue())

    def test_copy_missing_default_writes_empty_json(self):
        with tempfile.TemporaryDirectory() as td:
            dest = os.path.join(td, 'character.json')
            missing = os.path.join(td, 'no-such.json')
            buf = io.StringIO()
            with redirect_stdout(buf):
                ok = self.doc.copy_default_character(dest, src=missing)
            self.assertFalse(ok)
            with open(dest, 'r', encoding='utf-8') as fp:
                self.assertEqual(json.load(fp), {})
            self.assertIn('未找到默认角色配置', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
