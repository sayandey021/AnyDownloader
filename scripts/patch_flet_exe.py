import os
import sys
import subprocess
import shutil
import urllib.request


def kill_existing_flet_processes():
    for exe_name in ("flet.exe", "flet_bin.exe", "AnyDownloaderApp.exe"):
        try:
            subprocess.run(["taskkill", "/F", "/IM", exe_name, "/T"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def patch_flet_exe():
    kill_existing_flet_processes()

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

    # 2. Locate flet directories
    flet_dirs = []
    try:
        from flet_desktop import ensure_client_cached
        global_flet_dir = str(ensure_client_cached())
        if global_flet_dir and os.path.exists(global_flet_dir):
            flet_dirs.append(os.path.join(global_flet_dir, "flet"))

            local_flet_dir = os.path.abspath(os.path.join(base_dir, "..", ".flet_view"))
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

            local_flet_bin_dir = os.path.join(local_flet_dir, "flet")
            if os.path.isdir(local_flet_bin_dir) and local_flet_bin_dir not in flet_dirs:
                flet_dirs.append(local_flet_bin_dir)
    except ImportError:
        print("Warning: flet_desktop import failed.")

    # Always refresh the repo-local cache first so dev launches do not stick to a stale white Flet icon.
    repo_local_dir = os.path.abspath(os.path.join(base_dir, "..", ".flet_view", "flet"))
    if os.path.isdir(repo_local_dir) and repo_local_dir not in flet_dirs:
        flet_dirs.insert(0, repo_local_dir)

    user_extract_dir = os.path.join(os.path.expanduser("~"), ".AnyDownloader", "flet_view", "flet")
    if os.path.isdir(user_extract_dir) and user_extract_dir not in flet_dirs:
        flet_dirs.append(user_extract_dir)

    # 3. Setup flet_bin.exe (Flutter runner) and flet.exe (smart launcher) in each directory
    for f_dir in flet_dirs:
        if not os.path.isdir(f_dir):
            continue
        print(f"Configuring flet binaries in {f_dir}...")
        curr_flet = os.path.join(f_dir, "flet.exe")
        curr_bin = os.path.join(f_dir, "flet_bin.exe")

        # Kill stale processes before replacing the launcher binary.
        if os.path.isfile(curr_flet) or os.path.isfile(curr_bin):
            kill_existing_flet_processes()

        # If flet.exe exists and is the original Flutter runner (> 140KB)
        if os.path.isfile(curr_flet):
            sz = os.path.getsize(curr_flet)
            if sz > 140000 and not os.path.isfile(curr_bin):
                try:
                    shutil.copy2(curr_flet, curr_bin)
                    print(f"Created {curr_bin} from Flutter runner binary.")
                except Exception as e:
                    print(f"Warning copying to flet_bin.exe: {e}")

        if os.path.isfile(curr_bin):
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

        # Install launcher_exe as flet.exe and force a clean replacement to avoid stale white Flet icon caches.
        if os.path.isfile(launcher_exe):
            try:
                if os.path.isfile(curr_flet):
                    backup_flet = curr_flet + ".orig_backup"
                    if not os.path.exists(backup_flet):
                        shutil.copy2(curr_flet, backup_flet)
                    try:
                        os.remove(curr_flet)
                    except Exception:
                        pass
                shutil.copy2(launcher_exe, curr_flet)
                print(f"Installed smart launcher as {curr_flet}")
            except Exception as e:
                print(f"Warning replacing flet.exe: {e}")

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

if __name__ == "__main__":
    patch_flet_exe()
