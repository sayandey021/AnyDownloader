import os
import sys
import subprocess
import urllib.request

def patch_flet_exe():
    try:
        from flet_cli.__pyinstaller.utils import get_flet_bin_path
        global_flet_dir = get_flet_bin_path()
        if not global_flet_dir:
            print("Error: Could not locate flet bin path.")
            return

        import shutil
        local_flet_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".flet_view")
        
        # Copy to local workspace to avoid modifying the global Flet installation
        if os.path.exists(local_flet_dir):
            shutil.rmtree(local_flet_dir)
        shutil.copytree(global_flet_dir, local_flet_dir)
        
        # flet-desktop-full-x.y.z/flet/flet.exe -> .flet_view/flet/flet.exe
        flet_exe = os.path.join(local_flet_dir, 'flet', 'flet.exe')
        
    except ImportError:
        print("Error: Could not import flet_cli utils.")
        return

    if not os.path.exists(flet_exe):
        print(f"Error: Could not find flet.exe at {flet_exe}")
        return

    rcedit_url = "https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe"
    rcedit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rcedit-x64.exe")

    if not os.path.exists(rcedit_path):
        print("Downloading rcedit-x64.exe...")
        urllib.request.urlretrieve(rcedit_url, rcedit_path)

    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"))
    
    print("Patching flet.exe resources...")
    commands = [
        [rcedit_path, flet_exe, "--set-icon", icon_path],
        [rcedit_path, flet_exe, "--set-version-string", "FileDescription", "Any Downloader"],
        [rcedit_path, flet_exe, "--set-version-string", "ProductName", "Any Downloader"],
        [rcedit_path, flet_exe, "--set-version-string", "CompanyName", "SwiftGrab"],
        [rcedit_path, flet_exe, "--set-version-string", "LegalCopyright", "Copyright (c) 2026 SwiftGrab"]
    ]

    for cmd in commands:
        subprocess.run(cmd, check=True)
        
    print("Successfully patched flet.exe!")

if __name__ == "__main__":
    patch_flet_exe()
