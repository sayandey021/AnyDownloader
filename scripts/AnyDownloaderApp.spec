# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [('../assets', 'assets'), ('C:/Users/sayan/AppData/Roaming/Python/Python312/site-packages/ytmusicapi/locales', 'ytmusicapi/locales')]
datas += copy_metadata('yt-dlp')
datas += copy_metadata('spotdl')


a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
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
    version='C:/Users/sayan/AppData/Local/Temp/ad0656a4-d118-4953-85eb-55a30b5d7d4b',
    icon=['../assets/icon.ico'],
)
