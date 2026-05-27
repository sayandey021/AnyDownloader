import flet as ft
import sys
import os
import threading
from PIL import Image
import pystray

def kill_child_flet():
    import os
    import subprocess
    try:
        cmd = f'wmic process where "ParentProcessId={os.getpid()} and Name=\'flet.exe\'" get ProcessId'
        output = subprocess.check_output(cmd, shell=True, text=True, creationflags=0x08000000)
        for line in output.splitlines():
            line = line.strip()
            if line.isdigit():
                subprocess.run(["taskkill", "/F", "/PID", line, "/T"], creationflags=0x08000000)
    except Exception:
        pass

# BUST THE WINDOWS TASKBAR CACHE!
# Flet automatically sets FLET_APP_USER_MODEL_ID to the PyInstaller executable path.
# Because you ran it before the metadata was fixed, Windows permanently cached the Flet icon
# for this exact executable path. We will change the AUMID string so Windows thinks this
# is a completely brand new application and re-reads the (now perfect) metadata and icon!
def configure_flet_runtime():
    if getattr(sys, 'frozen', False):
        # 1. Bust the taskbar cache
        new_aumid = os.path.abspath(sys.executable) + "_v3"
        os.environ["FLET_APP_USER_MODEL_ID"] = new_aumid
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(new_aumid)
        except:
            pass
            
        # 2. Force Flet to use our patched bundled flet.exe!
        # The flet pack command compresses the patched flet/ directory into
        # flet-windows.zip inside _MEIPASS/flet_desktop/app/. At runtime,
        # flet falls back to the global ~/.flet/client/ cache which has
        # unpatched Flet branding. We extract the bundled zip ourselves into
        # a writable app-data directory so the patched version is always used.
        import zipfile
        bundled_zip = os.path.join(sys._MEIPASS, "flet_desktop", "app", "flet-windows.zip")
        # Extract to ~/.AnyDownloader instead of LOCALAPPDATA to avoid MSIX VFS bugs
        # where Windows fails to load dependent DLLs (like connectivity_plus_plugin.dll)
        extract_dir = os.path.join(os.path.expanduser("~"), ".AnyDownloader", "flet_view")
        flet_exe = os.path.join(extract_dir, "flet", "flet.exe")
        # Re-extract if the packaged executable is newer (new build) or not yet extracted
        needs_extract = not os.path.isfile(flet_exe)
        version_file = os.path.join(extract_dir, "version.txt")
        current_version = str(os.path.getmtime(sys.executable)) if os.path.isfile(sys.executable) else "unknown"
        
        if not needs_extract:
            cached_version = ""
            if os.path.isfile(version_file):
                try:
                    with open(version_file, "r") as f:
                        cached_version = f.read().strip()
                except Exception:
                    pass
            if current_version != cached_version:
                needs_extract = True
                import shutil
                shutil.rmtree(extract_dir, ignore_errors=True)
        
        if os.path.isfile(bundled_zip) and needs_extract:
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(bundled_zip, 'r') as zf:
                    zf.extractall(extract_dir)
                with open(version_file, "w") as f:
                    f.write(current_version)
            except Exception as e:
                # If extraction fails (e.g. PermissionError because another instance is running),
                # we just continue. The existing flet.exe and DLLs are already there.
                print(f"Warning: Failed to extract flet client (might be in use): {e}")
        
        if os.path.isfile(flet_exe):
            os.environ["FLET_VIEW_PATH"] = os.path.join(extract_dir, "flet")
        else:
            # Fallback: try uncompressed path (shouldn't happen with current build)
            os.environ["FLET_VIEW_PATH"] = os.path.join(sys._MEIPASS, "flet_desktop", "app", "flet")

configure_flet_runtime()

# In development mode, use the patched .flet_view so the taskbar shows
# the correct app icon and name instead of the default Flet branding.
if not getattr(sys, 'frozen', False):
    _local_flet_view = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".flet_view", "flet"
    )
    if os.path.isfile(os.path.join(_local_flet_view, "flet.exe")):
        os.environ.setdefault("FLET_VIEW_PATH", _local_flet_view)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ui.theme import AppTheme
from src.ui.main_view import MainView
from src.backend.settings import SettingsManager

tray_icon = None

def setup_tray(page: ft.Page):
    import pystray
    from PIL import Image
    import os
    import threading
    
    def on_show(icon, item):
        page.pubsub.send_all("show_window")
        
    def on_exit(icon, item):
        page.pubsub.send_all("exit_app")
        def _cleanup():
            try:
                icon.stop()
            except:
                pass
        threading.Thread(target=_cleanup, daemon=True).start()
        
    menu = pystray.Menu(
        pystray.MenuItem('Show Any Downloader', on_show, default=True),
        pystray.MenuItem('Exit', on_exit)
    )
    
    image = Image.new('RGB', (64, 64), color='red')
    
    # Resolve assets dir for PyInstaller
    if getattr(sys, 'frozen', False):
        assets_dir = os.path.join(sys._MEIPASS, "assets")
    else:
        assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
        
    icon_path = os.path.join(assets_dir, "icon.png")
    if os.path.exists(icon_path):
        image = Image.open(icon_path)
        
    global tray_icon
    tray_icon = pystray.Icon("any_downloader", image, "Any Downloader", menu)
    tray_icon.run()

def minimize_to_tray(page: ft.Page):
    page.window.visible = False
    page.update()

def main(page: ft.Page):
    # Setup thread-safe pubsub receiver for tray events
    def on_tray_message(msg):
        if msg == "show_window":
            page.window.visible = True
            page.update()
            page.window.minimized = False
            page.window.to_front()
            page.window.focus()
            page.update()
        elif msg == "exit_app":
            page.window.on_event = None
            page.window.prevent_close = False
            try:
                page.window.destroy()
            except Exception:
                pass
            
            # Allow time for Flet to gracefully close flet.exe process
            def _fallback():
                import time
                time.sleep(1.0)
                kill_child_flet()
                import os
                os._exit(0)
            threading.Thread(target=_fallback, daemon=True).start()
            
    page.pubsub.subscribe(on_tray_message)
    settings = SettingsManager()
    AppTheme.apply()  # Load saved theme (dark/light) before building UI

    page.title = "Any Downloader"
    page.window.icon = "icon.ico"
    page.width = 900
    page.height = 700
    page.theme = AppTheme.get_theme()
    page.theme_mode = ft.ThemeMode.LIGHT if AppTheme.MODE == 'light' else ft.ThemeMode.DARK
    page.bgcolor = AppTheme.BACKGROUND
    page.padding = 0
    page.window.prevent_close = True

    # Start tray icon immediately
    threading.Thread(target=setup_tray, args=(page,), daemon=True).start()

    def force_exit_app():
        def _cleanup():
            global tray_icon
            if tray_icon:
                try:
                    tray_icon.stop()
                except Exception:
                    pass
            try:
                page.window.destroy()
            except Exception:
                pass
            import time
            time.sleep(1.0)  # Wait for flet.exe to gracefully exit
            kill_child_flet()
            import os
            os._exit(0)
        threading.Thread(target=_cleanup, daemon=True).start()

    def handle_close_action(action, remember):
        if remember:
            settings.set('ask_on_close', False)
            settings.set('close_behavior', action)
            settings.save()
            
            # Force the SettingsView to update immediately if it's currently open
            for ctrl in page.controls:
                if hasattr(ctrl, 'settings_view') and getattr(ctrl, 'settings_view', None):
                    ctrl.settings_view.sync_from_settings()
            
        if action == "tray":
            minimize_to_tray(page)
        elif action == "exit":
            page.window.on_event = None
            page.window.prevent_close = False
            page.window.visible = False
            page.update()
            force_exit_app()

    remember_checkbox = ft.Checkbox(label="Remember my choice", value=False)
    
    def on_minimize(e):
        close_dialog.open = False
        page.update()
        import time
        time.sleep(0.1)  # allow dialog to close before hiding window
        handle_close_action("tray", remember_checkbox.value)
        
    def on_exit(e):
        close_dialog.open = False
        page.update()
        handle_close_action("exit", remember_checkbox.value)
        
    def on_cancel(e):
        close_dialog.open = False
        page.update()

    close_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Close Application"),
        content=ft.Column([
            ft.Text("Do you want to minimize to the system tray or exit the application?"),
            remember_checkbox
        ], tight=True),
        actions=[
            ft.TextButton("Minimize to Tray", on_click=on_minimize),
            ft.TextButton("Exit App", on_click=on_exit, style=ft.ButtonStyle(color=ft.Colors.ERROR)),
            ft.TextButton("Cancel", on_click=on_cancel)
        ]
    )
    
    page.overlay.append(close_dialog)

    def window_event(e):
        # Handle different Flet versions event data
        event_val = getattr(e, "type", getattr(e, "data", ""))
        print(f"[WINDOW EVENT] data={getattr(e, 'data', None)} type={getattr(e, 'type', None)} event_val={event_val}")
        
        if str(event_val) == "close" or "close" in str(event_val).lower():
            ask_on_close = settings.get('ask_on_close', True)
            close_behavior = settings.get('close_behavior', 'prompt')
            
            if not ask_on_close:
                if close_behavior == 'tray':
                    minimize_to_tray(page)
                else:
                    page.window.on_event = None
                    page.window.prevent_close = False
                    page.window.visible = False
                    page.update()
                    force_exit_app()
                return
                
            print("Showing close dialog...")
            remember_checkbox.value = False
            close_dialog.open = True
            page.update()

    page.window.on_event = window_event
    page.update()


    from src.backend.ffmpeg_manager import is_ffmpeg_available, download_ffmpeg

    if is_ffmpeg_available():
        main_view = MainView(page)
        page.add(main_view)
    else:
        progress_bar = ft.ProgressBar(width=400, color=AppTheme.PRIMARY, bgcolor=AppTheme.SURFACE_VARIANT, value=0)
        status_text = ft.Text("Checking dependencies...", size=14, color=AppTheme.TEXT_SECONDARY)
        
        loading_view = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(width=48, height=48, color=AppTheme.PRIMARY, stroke_width=4),
                    ft.Text("First Time Setup", size=24, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
                    ft.Text("Downloading media conversion tools (FFmpeg).\nThis is a one-time process and keeps the app lightweight.", 
                            text_align=ft.TextAlign.CENTER, color=AppTheme.TEXT_SECONDARY),
                    ft.Container(height=20),
                    progress_bar,
                    status_text
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
        )
        page.add(loading_view)
        
        def update_progress(percent, text):
            progress_bar.value = percent / 100.0 if percent > 0 else None
            status_text.value = text
            page.update()
            
        def download_task():
            try:
                download_ffmpeg(update_progress)
                page.controls.clear()
                main_view = MainView(page)
                page.add(main_view)
                page.update()
            except Exception as e:
                status_text.value = f"Failed to download FFmpeg: {e}\nPlease restart the app or install FFmpeg manually."
                status_text.color = ft.Colors.ERROR
                progress_bar.color = ft.Colors.ERROR
                progress_bar.value = 1.0
                page.update()
                
        threading.Thread(target=download_task, daemon=True).start()

if __name__ == "__main__":
    import ctypes
    def get_msix_aumid():
        try:
            kernel32 = ctypes.windll.kernel32
            length = ctypes.c_uint32(0)
            kernel32.GetCurrentPackageFamilyName(ctypes.byref(length), None)
            if length.value > 0:
                name_buffer = ctypes.create_unicode_buffer(length.value)
                if kernel32.GetCurrentPackageFamilyName(ctypes.byref(length), name_buffer) == 0:
                    # Append the Application Id defined in AppxManifest.xml
                    return f"{name_buffer.value}!AnyDownloader"
        except Exception:
            pass
        return None

    try:
        msix_aumid = get_msix_aumid()
        # If running from MSIX, use a slightly modified AUMID to break cache.
        # If running raw EXE, use a hardcoded AUMID to break path-based cache.
        final_aumid = f"{msix_aumid}_v1" if msix_aumid else "SwiftGrab.AnyDownloader.App.v1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(final_aumid)
    except Exception:
        pass

    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    log_path = os.path.join(temp_dir, "any_downloader_debug.log")
    sys.stdout = open(log_path, "w", encoding="utf-8", buffering=1)
    sys.stderr = sys.stdout
    print("Any Downloader Debug Log Started")
    
    # Resolve assets dir for PyInstaller
    if getattr(sys, 'frozen', False):
        assets_dir = os.path.join(sys._MEIPASS, "assets")
    else:
        assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
        
    print(f"Assets dir resolved to: {assets_dir}")
    print(f"Does icon.png exist? {os.path.exists(os.path.join(assets_dir, 'icon.png'))}")
    
    ft.app(target=main, assets_dir=assets_dir)
