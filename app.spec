# -*- mode: python ; coding: utf-8 -*-


block_cipher = None
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
binaries = collect_dynamic_libs('onnxruntime', destdir='onnxruntime/capi')

datas = [('src', 'src')]
# RapidOCR 模型 / yaml；本机未装 rapidocr 时不阻断 spec 解析
try:
    datas += collect_data_files('rapidocr')
except Exception:
    pass

# Analysis 通常能顺着 app.py → main_page 扫到这些模块；显式列出以免漏打
hiddenimports = [
    'ocr',
    'effective_rolls',
    'equipped',
    'rapidocr',
    'onnxruntime',
    'win32api',
    'win32con',
    'win32gui',
    'win32print',
]


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='keqing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # README 问题反馈需要命令行输出；管理员运行与是否弹控制台无关
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/keqing.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='keqing-1.0.0',
)
