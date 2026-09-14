import sys
from flet_cli.commands.pack import Command
import flet_cli.__pyinstaller.win_utils as win_utils

original_update = win_utils.update_flet_view_version_info
original_icon = win_utils.update_flet_view_icon

# The .flet_view/flet/flet.exe is already patched by patch_flet_exe.py using
# rcedit (icon + version info). We intercept both update functions so the
# flet pack command doesn't re-process (and potentially corrupt) the exe
# with win32api calls.

import os
import subprocess
import tempfile
import uuid
from pathlib import Path

# Path to rcedit helper
rcedit_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "rcedit-x64.exe"))

def safe_update(exe_path, product_name, file_description, product_version, file_version, company_name, copyright):
    print(f"--- INTERCEPTED update_flet_view_version_info for {exe_path} ---")
    if os.path.exists(rcedit_path) and os.path.isfile(exe_path):
        print(f"Applying metadata via rcedit to: {exe_path}")
        commands = [
            [rcedit_path, exe_path, "--set-version-string", "FileDescription", file_description or "Any Downloader"],
            [rcedit_path, exe_path, "--set-version-string", "ProductName", product_name or "Any Downloader"],
            [rcedit_path, exe_path, "--set-version-string", "CompanyName", company_name or "SwiftGrab"],
            [rcedit_path, exe_path, "--set-version-string", "LegalCopyright", copyright or "Copyright (c) 2026 SwiftGrab"],
        ]
        if file_version:
            commands.append([rcedit_path, exe_path, "--set-file-version", str(file_version)])
        if product_version:
            commands.append([rcedit_path, exe_path, "--set-product-version", str(product_version)])
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True)
            except Exception as err:
                print(f"Warning: rcedit version string failed: {err}")

    import PyInstaller.utils.win32.versioninfo as versioninfo
    
    # Parse version strings to 4-tuples for FixedFileInfo
    def _parse_version(v_str):
        try:
            parts = [int(p) for p in str(v_str).split('.')[:4]]
            while len(parts) < 4:
                parts.append(0)
            return tuple(parts)
        except Exception:
            return (1, 0, 0, 0)

    f_vers = _parse_version(file_version)
    p_vers = _parse_version(product_version)

    vs = versioninfo.VSVersionInfo(
        ffi=versioninfo.FixedFileInfo(
            filevers=f_vers,
            prodvers=p_vers,
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
    print(f"--- INTERCEPTED update_flet_view_icon for {exe_path} ---")
    if os.path.exists(rcedit_path) and os.path.isfile(exe_path) and os.path.isfile(icon_path):
        print(f"Applying icon via rcedit to: {exe_path} from {icon_path}")
        try:
            subprocess.run([rcedit_path, exe_path, "--set-icon", icon_path], check=True)
            print("Successfully patched icon on temporary flet.exe!")
        except Exception as err:
            print(f"Warning: rcedit set-icon failed: {err}")
    else:
        print(f"Warning: rcedit ({os.path.exists(rcedit_path)}), exe ({os.path.exists(exe_path)}), or icon ({os.path.exists(icon_path)}) not found")

win_utils.update_flet_view_version_info = safe_update
win_utils.update_flet_view_icon = safe_icon

import argparse
parser = argparse.ArgumentParser()
cmd = Command(parser)
cmd.handle(parser.parse_args())


