import os
import sys
import subprocess
import urllib.request

def patch_flet_exe():
    try:
        from flet_desktop import ensure_client_cached
        global_flet_dir = str(ensure_client_cached())
        if not global_flet_dir or not os.path.exists(global_flet_dir):
            print("Error: Could not locate flet desktop client.")
            return

        import shutil
        local_flet_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".flet_view"))
        version_marker = os.path.join(local_flet_dir, "flet_version.txt")
        current_global_tag = os.path.basename(os.path.normpath(global_flet_dir))
        
        needs_copy = not os.path.exists(local_flet_dir)
        if not needs_copy:
            cached_tag = ""
            if os.path.isfile(version_marker):
                try:
                    with open(version_marker, "r", encoding="utf-8") as vf:
                        cached_tag = vf.read().strip()
                except Exception:
                    pass
            if cached_tag != current_global_tag or not os.path.exists(os.path.join(local_flet_dir, 'flet', 'flet.exe')):
                needs_copy = True
                try:
                    shutil.rmtree(local_flet_dir)
                except Exception as e:
                    print(f"Warning: Could not remove old .flet_view ({e})")
        
        if needs_copy and not os.path.exists(local_flet_dir):
            print(f"Updating local .flet_view to {current_global_tag}...")
            shutil.copytree(global_flet_dir, local_flet_dir)
            try:
                with open(version_marker, "w", encoding="utf-8") as vf:
                    vf.write(current_global_tag)
            except Exception:
                pass
        
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
    
    targets = [flet_exe]
    global_exe = os.path.join(global_flet_dir, 'flet', 'flet.exe')
    if os.path.exists(global_exe) and global_exe not in targets:
        targets.append(global_exe)
    
    user_extract_exe = os.path.join(os.path.expanduser("~"), ".AnyDownloader", "flet_view", "flet", "flet.exe")
    if os.path.exists(user_extract_exe) and user_extract_exe not in targets:
        targets.append(user_extract_exe)

    for target in targets:
        print(f"Patching resources on {target}...")
        commands = [
            [rcedit_path, target, "--set-icon", icon_path],
            [rcedit_path, target, "--set-version-string", "FileDescription", "Any Downloader"],
            [rcedit_path, target, "--set-version-string", "ProductName", "Any Downloader"],
            [rcedit_path, target, "--set-version-string", "CompanyName", "SwiftGrab"],
            [rcedit_path, target, "--set-version-string", "LegalCopyright", "Copyright (c) 2026 SwiftGrab"]
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, check=True)
            except Exception as e:
                print(f"Warning: Failed to patch {target}: {e}")
        
    print("Successfully patched flet executables!")

if __name__ == "__main__":
    patch_flet_exe()

