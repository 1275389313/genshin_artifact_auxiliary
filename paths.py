'''Resolve bundled resource paths for source and PyInstaller frozen runs.'''

import os
import sys
import tempfile


def bundled_root():
    '''Directory that contains packed `src/` (project root, or sys._MEIPASS).'''
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            return os.path.abspath(meipass)
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    '''Absolute path to a file shipped with the app, e.g. resource_path('src', 'character.json').

    Does not depend on the process working directory. User data stays in ~/Documents/keqing/.
    '''
    return os.path.join(bundled_root(), *parts)


def ocr_cache_dir():
    '''Writable folder for OCR debug dumps. Frozen `src/` is often missing or read-only.'''
    path = os.path.join(tempfile.gettempdir(), 'keqing_ocr')
    os.makedirs(path, exist_ok=True)
    return path


def ocr_cache_path(*parts):
    '''Path under %TEMP%/keqing_ocr/ (or the platform temp dir).'''
    return os.path.join(ocr_cache_dir(), *parts)
