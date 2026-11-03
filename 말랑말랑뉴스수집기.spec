# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['naver_news_crawler.py'],
    pathex=[],
    binaries=[],
    datas=[('news_bunny.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'shiboken6', 'pandas', 'numpy', 'matplotlib', 'scipy', 'PIL', 'IPython', 'selenium', 'pygame', 'tkinter'],
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
    name='말랑말랑뉴스수집기',
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
    icon=['news_bunny.ico'],
)
