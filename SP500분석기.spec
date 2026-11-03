# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['sp500_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('sp500.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'shiboken6', 'scipy', 'IPython', 'seaborn', 'selenium', 'pygame', 'tkinter', 'bs4', 'openpyxl'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SP500분석기',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['sp500.ico'],
)
