# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('..\\assets', 'assets'), ('C:\\Users\\sayan\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\ytmusicapi\\locales', 'ytmusicapi/locales')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='AnyDownloaderApp',
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
    version='C:\\Users\\sayan\\AppData\\Local\\Temp\\c7ad77f6-ade5-4e6f-9728-aac3a486429c',
    icon=['..\\assets\\icon.ico'],
)
