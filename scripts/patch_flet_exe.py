import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import tempfile

def is_flet_launcher(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as f:
            chunk = f.read(65536)
            return b"FletLauncher" in chunk or b"_CorExeMain" in chunk
    except Exception:
        return False

def is_flutter_runner(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as f:
            content = f.read()
            return b"flutter" in content.lower() and b"FletLauncher" not in content and b"_CorExeMain" not in content
    except Exception:
        return False

def patch_flet_exe():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.abspath(os.path.join(base_dir, "..", "assets"))
    icon_path = os.path.join(assets_dir, "icon.ico")
    rcedit_path = os.path.join(base_dir, "rcedit-x64.exe")

    if not os.path.exists(rcedit_path):
        rcedit_url = "https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe"
        print("Downloading rcedit-x64.exe...")
        urllib.request.urlretrieve(rcedit_url, rcedit_path)

    # 1. Compile C# flet_launcher.exe
    csc_path = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if not os.path.isfile(csc_path):
        csc_path = r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"

    launcher_cs = os.path.join(base_dir, "flet_launcher.cs")
    launcher_exe = os.path.join(base_dir, "flet_launcher.exe")

    if os.path.isfile(csc_path) and os.path.isfile(launcher_cs):
        print("Compiling flet_launcher.exe...")
        compile_cmd = [
            csc_path,
            "/nologo",
            "/target:winexe",
            f"/win32icon:{icon_path}",
            f"/out:{launcher_exe}",
            launcher_cs
        ]
        try:
            subprocess.run(compile_cmd, check=True)
            print("Compiled flet_launcher.exe successfully!")
        except Exception as e:
            print(f"Warning: Failed to compile flet_launcher.cs: {e}")

    # Patch metadata on launcher_exe
    if os.path.isfile(launcher_exe) and os.path.isfile(rcedit_path):
        meta_cmds = [
            [rcedit_path, launcher_exe, "--set-icon", icon_path],
            [rcedit_path, launcher_exe, "--set-version-string", "FileDescription", "Any Downloader"],
            [rcedit_path, launcher_exe, "--set-version-string", "ProductName", "Any Downloader"],
            [rcedit_path, launcher_exe, "--set-version-string", "CompanyName", "SwiftGrab"],
            [rcedit_path, launcher_exe, "--set-version-string", "LegalCopyright", "Copyright (c) 2026 SwiftGrab"]
        ]
        for cmd in meta_cmds:
            try:
                subprocess.run(cmd, check=True)
            except Exception:
                pass

    # 2. Locate and sanitize global Flet cache
    from flet_desktop import ensure_client_cached, version as flet_ver
    global_flet_dir = str(ensure_client_cached())
    global_flet_exe = os.path.join(global_flet_dir, "flet", "flet.exe")
    global_flet_bin = os.path.join(global_flet_dir, "flet", "flet_bin.exe")

    # If the global cache was poisoned previously with flet_launcher, restore clean client
    if is_flet_launcher(global_flet_exe):
        print("Detected poisoned flet.exe in global cache. Restoring pristine Flutter client...")
        clean_found = False
        if is_flutter_runner(global_flet_bin):
            shutil.copy2(global_flet_bin, global_flet_exe)
            clean_found = True
        
        if not clean_found:
            clean_zip = os.path.join(tempfile.gettempdir(), 'flet-windows-clean.zip')
            if not os.path.isfile(clean_zip):
                ver = flet_ver.version
                url = f"https://github.com/flet-dev/flet/releases/download/v{ver}/flet-windows.zip"
                print(f"Downloading clean Flet {ver} client...")
                urllib.request.urlretrieve(url, clean_zip)
            
            with zipfile.ZipFile(clean_zip, 'r') as zf:
                zf.extractall(global_flet_dir)
            print("Pristine Flet client restored to global cache.")

    # Remove flet_bin.exe from global cache to ensure global cache stays standard
    if os.path.isfile(global_flet_bin):
        try:
            os.remove(global_flet_bin)
        except Exception:
            pass

    # 3. Setup local .flet_view directory
    local_flet_dir = os.path.abspath(os.path.join(base_dir, "..", ".flet_view"))
    version_marker = os.path.join(local_flet_dir, "flet_version.txt")
    current_global_tag = os.path.basename(os.path.normpath(global_flet_dir))

    curr_flet = os.path.join(local_flet_dir, "flet", "flet.exe")
    curr_bin = os.path.join(local_flet_dir, "flet", "flet_bin.exe")

    needs_refresh = (
        not os.path.exists(local_flet_dir)
        or not os.path.isfile(curr_bin)
        or not is_flutter_runner(curr_bin)
        or is_flet_launcher(curr_bin)
    )

    if not needs_refresh:
        cached_tag = ""
        if os.path.isfile(version_marker):
            try:
                with open(version_marker, "r", encoding="utf-8") as vf:
                    cached_tag = vf.read().strip()
            except Exception:
                pass
        if cached_tag != current_global_tag:
            needs_refresh = True

    if needs_refresh:
        print(f"Refreshing local .flet_view from pristine global cache...")
        if os.path.exists(local_flet_dir):
            shutil.rmtree(local_flet_dir, ignore_errors=True)
        shutil.copytree(global_flet_dir, local_flet_dir)
        try:
            with open(version_marker, "w", encoding="utf-8") as vf:
                vf.write(current_global_tag)
        except Exception:
            pass

    # In local_flet_dir, ensure curr_bin is the Flutter runner
    if not is_flutter_runner(curr_bin):
        if is_flutter_runner(curr_flet):
            shutil.copy2(curr_flet, curr_bin)
            print(f"Created {curr_bin} from pristine Flutter runner.")
        elif is_flutter_runner(global_flet_exe):
            shutil.copy2(global_flet_exe, curr_bin)
            print(f"Restored {curr_bin} directly from global Flutter runner.")
        else:
            raise RuntimeError("CRITICAL: Failed to locate pristine Flutter runner binary!")

    # Strict check: curr_bin must be a genuine Flutter runner
    if not is_flutter_runner(curr_bin) or is_flet_launcher(curr_bin):
        raise RuntimeError(f"CRITICAL: {curr_bin} is corrupted or is a flet_launcher! Aborting build.")

    # Patch curr_bin (Flutter runner) with app branding
    if os.path.isfile(curr_bin) and os.path.isfile(rcedit_path):
        for cmd in [
            [rcedit_path, curr_bin, "--set-icon", icon_path],
            [rcedit_path, curr_bin, "--set-version-string", "FileDescription", "Any Downloader"],
            [rcedit_path, curr_bin, "--set-version-string", "ProductName", "Any Downloader"],
            [rcedit_path, curr_bin, "--set-version-string", "CompanyName", "SwiftGrab"],
            [rcedit_path, curr_bin, "--set-version-string", "LegalCopyright", "Copyright (c) 2026 SwiftGrab"]
        ]:
            try:
                subprocess.run(cmd, check=True)
            except Exception:
                pass

    # Install launcher_exe as curr_flet (flet.exe)
    if os.path.isfile(launcher_exe):
        shutil.copy2(launcher_exe, curr_flet)
        print(f"Installed smart launcher as {curr_flet}")

        if not is_flet_launcher(curr_flet):
            raise RuntimeError("CRITICAL: flet.exe did not match flet_launcher signature!")

        for cmd in [
            [rcedit_path, curr_flet, "--set-icon", icon_path],
            [rcedit_path, curr_flet, "--set-version-string", "FileDescription", "Any Downloader"],
            [rcedit_path, curr_flet, "--set-version-string", "ProductName", "Any Downloader"],
            [rcedit_path, curr_flet, "--set-version-string", "CompanyName", "SwiftGrab"],
            [rcedit_path, curr_flet, "--set-version-string", "LegalCopyright", "Copyright (c) 2026 SwiftGrab"]
        ]:
            try:
                subprocess.run(cmd, check=True)
            except Exception:
                pass

    print("Successfully configured and patched all flet executables!")
    print(f"  flet.exe:     {curr_flet} (is_launcher={is_flet_launcher(curr_flet)})")
    print(f"  flet_bin.exe: {curr_bin} (is_flutter={is_flutter_runner(curr_bin)})")

    # Clean any corrupted user extract dir in ~/.AnyDownloader if present
    user_bin = os.path.join(os.path.expanduser("~"), ".AnyDownloader", "flet_view", "flet", "flet_bin.exe")
    if os.path.isfile(user_bin) and is_flet_launcher(user_bin):
        print(f"Cleaning corrupted user cache at {user_bin}...")
        try:
            shutil.rmtree(os.path.join(os.path.expanduser("~"), ".AnyDownloader", "flet_view"), ignore_errors=True)
            print("Successfully cleared corrupted user cache.")
        except Exception:
            pass

if __name__ == "__main__":
    patch_flet_exe()
