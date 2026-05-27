import sys
from flet_cli.commands.pack import Command
import flet_cli.__pyinstaller.win_utils as win_utils

original_update = win_utils.update_flet_view_version_info
original_icon = win_utils.update_flet_view_icon

# The .flet_view/flet/flet.exe is already patched by patch_flet_exe.py using
# rcedit (icon + version info). We intercept both update functions so the
# flet pack command doesn't re-process (and potentially corrupt) the exe
# with win32api calls.

def safe_update(exe_path, product_name, file_description, product_version, file_version, company_name, copyright):
    print("--- INTERCEPTED update_flet_view_version_info ---")
    print("Skipping: .flet_view/flet/flet.exe already has correct version info via rcedit")
    import tempfile, uuid
    from pathlib import Path
    import PyInstaller.utils.win32.versioninfo as versioninfo
    
    vs = versioninfo.VSVersionInfo(
        ffi=versioninfo.FixedFileInfo(
            filevers=(1, 0, 0, 0),
            prodvers=(1, 0, 0, 0),
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0)
        ),
        kids=[
            versioninfo.StringFileInfo([
                versioninfo.StringTable('040904B0', [
                    versioninfo.StringStruct('CompanyName', company_name or ''),
                    versioninfo.StringStruct('FileDescription', file_description or ''),
                    versioninfo.StringStruct('FileVersion', file_version or ''),
                    versioninfo.StringStruct('InternalName', 'AnyDownloaderApp'),
                    versioninfo.StringStruct('LegalCopyright', copyright or ''),
                    versioninfo.StringStruct('OriginalFilename', 'AnyDownloaderApp.exe'),
                    versioninfo.StringStruct('ProductName', product_name or ''),
                    versioninfo.StringStruct('ProductVersion', product_version or '')
                ])
            ]),
            versioninfo.VarFileInfo([versioninfo.VarStruct('Translation', [1033, 1200])])
        ]
    )
    
    version_info_path = str(Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4())))
    with open(version_info_path, "w", encoding="utf-8") as f:
        f.write(str(vs))
        
    return version_info_path

def safe_icon(exe_path, icon_path):
    print("--- INTERCEPTED update_flet_view_icon ---")
    print("Skipping: .flet_view/flet/flet.exe already has correct icon via rcedit")

win_utils.update_flet_view_version_info = safe_update
win_utils.update_flet_view_icon = safe_icon

import argparse
parser = argparse.ArgumentParser()
cmd = Command(parser)
cmd.handle(parser.parse_args())

