# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['kospi200_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('kospi200.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'shiboken6', 'pandas', 'numpy', 'matplotlib', 'scipy', 'PIL', 'IPython', 'selenium', 'pygame', 'tkinter', 'bs4'],
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
    name='코스피200시세판',
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
    icon=['kospi200.ico'],
)
