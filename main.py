import sys
import os
import subprocess
import ctypes
from ctypes import wintypes

# Suppress visible terminal/cmd console flashing for any background subprocesses on Windows
if sys.platform == "win32":
    import _winapi

    _orig_CreateProcess = _winapi.CreateProcess

    def _silent_CreateProcess(app_name, cmd_line, proc_attrs, thread_attrs, inherit_handles, creationflags, env, cwd, startupinfo):
        # Do not force CREATE_NO_WINDOW or SW_HIDE on flet.exe GUI client
        target = (str(app_name or '') + ' ' + str(cmd_line or '')).lower()
        if 'flet.exe' not in target:
            creationflags |= 0x08000000  # CREATE_NO_WINDOW
            if startupinfo is None:
                startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

        return _orig_CreateProcess(app_name, cmd_line, proc_attrs, thread_attrs, inherit_handles, creationflags, env, cwd, startupinfo)

    _winapi.CreateProcess = _silent_CreateProcess
    if hasattr(subprocess, '_winapi'):
        subprocess._winapi.CreateProcess = _silent_CreateProcess

    _orig_popen = subprocess.Popen

    class _SilentPopen(_orig_popen):
        def __init__(self, *args, **kwargs):
            # Do not force CREATE_NO_WINDOW on flet.exe GUI client
            cmd_args = args[0] if args else kwargs.get("args")
            is_flet = False
            if cmd_args:
                first_arg = cmd_args[0] if isinstance(cmd_args, (list, tuple)) else str(cmd_args)
                if "flet.exe" in str(first_arg).lower():
                    is_flet = True

            if not is_flet:
                creationflags = kwargs.get("creationflags", 0)
                creationflags |= subprocess.CREATE_NO_WINDOW
                kwargs["creationflags"] = creationflags

                if "startupinfo" in kwargs and kwargs["startupinfo"] is not None:
                    kwargs["startupinfo"].dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    kwargs["startupinfo"].wShowWindow = 0
                elif len(args) <= 12:
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 0
                    kwargs["startupinfo"] = si

            super().__init__(*args, **kwargs)

    subprocess.Popen = _SilentPopen

def _ensure_dependencies():
    if getattr(sys, 'frozen', False) or getattr(sys, '_any_downloader_deps_checked', False):
        return
    sys._any_downloader_deps_checked = True
    req_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'requirements.txt'))
    if not os.path.exists(req_file):
        return
    try:
        import flet, PIL, pystray, yt_dlp, spotdl, requests, bs4, curl_cffi
    except ImportError:
        print("Missing dependencies detected! Installing automatically...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=True, creationflags=0x08000000 if os.name == 'nt' else 0)
            print("Dependencies installed successfully! Restarting...")
            if os.name == 'nt':
                subprocess.call([sys.executable] + sys.argv, creationflags=0x08000000)
                sys.exit(0)
            else:
                os.execv(sys.executable, [sys.executable] + sys.argv[1:])
        except Exception as e:
            print(f"Failed to install dependencies: {e}")

_ensure_dependencies()

import flet as ft
import threading
from PIL import Image
import pystray

_single_instance_mutex = None
_single_instance_socket = None
_active_page = None

def restore_and_focus_native_window():
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = user32.FindWindowW("FLUTTER_RUNNER_WIN32_WINDOW", "Any Downloader")
        if not hwnd:
            hwnd = user32.FindWindowW(None, "Any Downloader")
        if not hwnd:
            hwnd = user32.FindWindowW("FLUTTER_RUNNER_WIN32_WINDOW", None)

        if hwnd:
            # If minimized (iconic), restore it (SW_RESTORE = 9)
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            else:
                user32.ShowWindow(hwnd, 5)  # SW_SHOW

            # Reliably bring window to foreground across Windows focus-stealing guards
            cur_thread = kernel32.GetCurrentThreadId()
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
            app_thread = user32.GetWindowThreadProcessId(hwnd, None)

            if fg_thread != 0 and fg_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, fg_thread, True)
            if app_thread != 0 and app_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, app_thread, True)

            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.SetFocus(hwnd)

            if app_thread != 0 and app_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, app_thread, False)
            if fg_thread != 0 and fg_thread != cur_thread:
                user32.AttachThreadInput(cur_thread, fg_thread, False)
    except Exception as e:
        print(f"[SingleInstance] Error restoring window: {e}")

def handle_activate_signal():
    global _active_page
    if _active_page:
        def _do():
            try:
                _active_page.window.visible = True
                _active_page.update()
                _active_page.window.minimized = False
                _active_page.window.focused = True
                _active_page.update()
                try:
                    _active_page.run_task(_active_page.window.to_front)
                except Exception:
                    try:
                        _active_page.window.to_front()
                    except Exception:
                        pass
                _active_page.update()
            except Exception:
                pass
            restore_and_focus_native_window()

        if hasattr(_active_page, 'run_thread') and _active_page.run_thread:
            _active_page.run_thread(_do)
        else:
            _do()
    else:
        restore_and_focus_native_window()

def init_single_instance():
    """
    Enforces a single instance on Windows using a Named Mutex and loopback socket.
    Returns True if primary instance, False if secondary instance (which activates existing window and exits).
    """
    if sys.platform != "win32":
        return True

    global _single_instance_mutex, _single_instance_socket
    import tempfile
    import socket

    port_file = os.path.join(tempfile.gettempdir(), "any_downloader_app.port")
    MUTEX_NAME = r"Local\AnyDownloader_SingleInstance_Mutex_2026"
    kernel32 = ctypes.windll.kernel32

    _single_instance_mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()

    # ERROR_ALREADY_EXISTS = 183
    if last_error == 183:
        print("[SingleInstance] Existing instance detected. Sending activate signal...")
        if os.path.exists(port_file):
            try:
                with open(port_file, "r") as f:
                    port = int(f.read().strip())
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                s.connect(("127.0.0.1", port))
                s.sendall(b"activate\n")
                s.close()
            except Exception as e:
                print(f"[SingleInstance] Socket signal error: {e}")

        # Native fallback: restore and focus existing window handle
        restore_and_focus_native_window()
        return False

    # Primary instance: start background loopback listener
    try:
        _single_instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _single_instance_socket.bind(("127.0.0.1", 0))
        port = _single_instance_socket.getsockname()[1]
        _single_instance_socket.listen(5)

        with open(port_file, "w") as f:
            f.write(str(port))

        def _ipc_server():
            while True:
                try:
                    conn, _ = _single_instance_socket.accept()
                    data = conn.recv(1024)
                    conn.close()
                    if b"activate" in data:
                        handle_activate_signal()
                except Exception:
                    break

        threading.Thread(target=_ipc_server, daemon=True).start()
    except Exception as e:
        print(f"[SingleInstance] Failed to start IPC server: {e}")

    return True

def kill_child_flet():
    try:
        cmd = f'wmic process where "ParentProcessId={os.getpid()} and (Name=\'flet.exe\' or Name=\'flet_bin.exe\')" get ProcessId'
        output = subprocess.check_output(cmd, shell=True, text=True, creationflags=0x08000000)
        for line in output.splitlines():
            line = line.strip()
            if line.isdigit():
                subprocess.run(["taskkill", "/F", "/PID", line, "/T"], creationflags=0x08000000)
    except Exception:
        pass

def get_msix_aumid():
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        length = ctypes.c_uint32(0)
        kernel32.GetCurrentPackageFamilyName(ctypes.byref(length), None)
        if length.value > 0:
            name_buffer = ctypes.create_unicode_buffer(length.value)
            if kernel32.GetCurrentPackageFamilyName(ctypes.byref(length), name_buffer) == 0:
                return f"{name_buffer.value}!AnyDownloader"
    except Exception:
        pass
    return None

def get_app_user_model_id():
    msix_id = get_msix_aumid()
    if msix_id:
        return msix_id
    return "SwiftGrab.AnyDownloader.App"

def configure_flet_runtime():
    if sys.platform == "win32":
        aumid = get_app_user_model_id()
        os.environ["FLET_APP_USER_MODEL_ID"] = aumid
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(aumid)
        except Exception:
            pass

    if getattr(sys, 'frozen', False):
        # Force Flet to use our patched bundled flet.exe!
        import zipfile
        bundled_zip = os.path.join(sys._MEIPASS, "flet_desktop", "app", "flet-windows.zip")
        extract_dir = os.path.join(os.path.expanduser("~"), ".AnyDownloader", "flet_view")
        flet_exe = os.path.join(extract_dir, "flet", "flet.exe")
        flet_bin = os.path.join(extract_dir, "flet", "flet_bin.exe")
        version_file = os.path.join(extract_dir, "version.txt")
        current_version = str(os.path.getmtime(sys.executable)) if os.path.isfile(sys.executable) else "unknown"
        
        needs_extract = not os.path.isfile(flet_exe) or not os.path.isfile(flet_bin)
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
                print(f"Warning: Failed to extract flet client (might be in use): {e}")

        # Ensure flet_bin.exe exists if flet.exe is the raw Flutter binary
        if os.path.isfile(flet_exe) and not os.path.isfile(flet_bin):
            if os.path.getsize(flet_exe) > 140000:
                try:
                    import shutil
                    shutil.copy2(flet_exe, flet_bin)
                except Exception:
                    pass
        
        if os.path.isfile(flet_exe):
            os.environ["FLET_VIEW_PATH"] = os.path.join(extract_dir, "flet")
        else:
            os.environ["FLET_VIEW_PATH"] = os.path.join(sys._MEIPASS, "flet_desktop", "app", "flet")

# COM / Shell Property Store for Taskbar grouping and Jump List relaunch
class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]

class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [
        ("fmtid", _GUID),
        ("pid", wintypes.DWORD)
    ]

_IID_IPropertyStore = _GUID(
    0x886d8eeb, 0x8cf2, 0x4446,
    (wintypes.BYTE * 8)(0x8d, 0x02, 0xcd, 0xba, 0x1d, 0xbd, 0xcf, 0x99)
)

_PKEY_FMTID = _GUID(
    0x9f4c2855, 0x9f79, 0x4b39,
    (wintypes.BYTE * 8)(0xa8, 0xd0, 0xe1, 0xd4, 0x2d, 0xe1, 0xd5, 0xf3)
)

_PKEY_AppUserModel_ID = _PROPERTYKEY(_PKEY_FMTID, 5)
_PKEY_AppUserModel_RelaunchCommand = _PROPERTYKEY(_PKEY_FMTID, 2)
_PKEY_AppUserModel_RelaunchDisplayNameResource = _PROPERTYKEY(_PKEY_FMTID, 4)
_PKEY_AppUserModel_RelaunchIconResource = _PROPERTYKEY(_PKEY_FMTID, 3)

class _PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", wintypes.WORD),
        ("wReserved2", wintypes.WORD),
        ("wReserved3", wintypes.WORD),
        ("pwszVal", wintypes.LPWSTR),
        ("padding", wintypes.DWORD * 2)
    ]

class _IPropertyStoreVtbl(ctypes.Structure):
    pass

class _IPropertyStore(ctypes.Structure):
    _fields_ = [("lpVtbl", ctypes.POINTER(_IPropertyStoreVtbl))]

_STDMETHOD = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
_SETVALUEMETHOD = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(_PROPERTYKEY), ctypes.c_void_p)

_IPropertyStoreVtbl._fields_ = [
    ("QueryInterface", _STDMETHOD),
    ("AddRef", _STDMETHOD),
    ("Release", _STDMETHOD),
    ("GetCount", _STDMETHOD),
    ("GetAt", _STDMETHOD),
    ("GetValue", _STDMETHOD),
    ("SetValue", _SETVALUEMETHOD),
    ("Commit", _STDMETHOD),
]

def set_window_relaunch_properties(hwnd, aumid, relaunch_cmd, display_name="Any Downloader", icon_res=None):
    if sys.platform != "win32":
        return False
    try:
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
        shlwapi = ctypes.windll.shlwapi

        ole32.CoInitialize(None)

        pps = ctypes.POINTER(_IPropertyStore)()
        hr = shell32.SHGetPropertyStoreForWindow(hwnd, ctypes.byref(_IID_IPropertyStore), ctypes.byref(pps))
        if hr != 0 or not pps:
            return False

        store = pps.contents
        vtbl = store.lpVtbl.contents

        def _make_prop(val):
            pv = _PROPVARIANT()
            p_str = wintypes.LPWSTR()
            if shlwapi.SHStrDupW(str(val), ctypes.byref(p_str)) == 0:
                pv.vt = 31  # VT_LPWSTR
                pv.pwszVal = p_str
            return pv

        try:
            if relaunch_cmd:
                pv = _make_prop(relaunch_cmd)
                vtbl.SetValue(pps, ctypes.byref(_PKEY_AppUserModel_RelaunchCommand), ctypes.byref(pv))
                ole32.PropVariantClear(ctypes.byref(pv))

            if display_name:
                pv = _make_prop(display_name)
                vtbl.SetValue(pps, ctypes.byref(_PKEY_AppUserModel_RelaunchDisplayNameResource), ctypes.byref(pv))
                ole32.PropVariantClear(ctypes.byref(pv))

            if icon_res:
                pv = _make_prop(icon_res)
                vtbl.SetValue(pps, ctypes.byref(_PKEY_AppUserModel_RelaunchIconResource), ctypes.byref(pv))
                ole32.PropVariantClear(ctypes.byref(pv))

            if aumid:
                pv = _make_prop(aumid)
                vtbl.SetValue(pps, ctypes.byref(_PKEY_AppUserModel_ID), ctypes.byref(pv))
                ole32.PropVariantClear(ctypes.byref(pv))

            vtbl.Commit(pps)
            return True
        finally:
            vtbl.Release(pps)
    except Exception as e:
        print(f"[PropertyStore] Error: {e}")
        return False

def apply_native_window_styling(window_title="Any Downloader", icon_path=None, dark=True):
    if sys.platform != "win32":
        return

    def _worker():
        import time
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi
        
        hwnd = None
        for _ in range(50):
            hwnd = user32.FindWindowW("FLUTTER_RUNNER_WIN32_WINDOW", window_title)
            if not hwnd:
                hwnd = user32.FindWindowW(None, window_title)
            if not hwnd:
                hwnd = user32.FindWindowW("FLUTTER_RUNNER_WIN32_WINDOW", None)
            if hwnd:
                break
            time.sleep(0.08)

        if not hwnd:
            return

        try:
            user32.SetWindowTextW(hwnd, window_title)
        except Exception:
            pass

        # 1. Windows 10/11 title bar dark mode
        try:
            val = ctypes.c_int(1 if dark else 0)
            if dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val)) != 0:
                dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

        # 2. Native Win32 window icons (Titlebar small icon + Taskbar big icon)
        if icon_path and os.path.exists(icon_path):
            try:
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x0010

                h_sm = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if h_sm:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_sm)
                    try:
                        user32.SetClassLongPtrW(hwnd, -34, h_sm)  # GCLP_HICONSM
                    except Exception:
                        pass

                h_bg = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                if h_bg:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_bg)
                    try:
                        user32.SetClassLongPtrW(hwnd, -14, h_bg)  # GCLP_HICON
                    except Exception:
                        pass
            except Exception:
                pass

        # 3. Taskbar Jump List & AppUserModelID properties
        try:
            aumid = get_app_user_model_id()
            relaunch_cmd = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            set_window_relaunch_properties(
                hwnd,
                aumid=aumid,
                relaunch_cmd=relaunch_cmd,
                display_name=window_title,
                icon_res=icon_path
            )
        except Exception as e:
            print(f"[NativeStyling] Property store error: {e}")

    threading.Thread(target=_worker, daemon=True).start()

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
from src.ui.title_bar import CustomTitleBar
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

async def main(page: ft.Page):
    global _active_page
    _active_page = page

    def _safe_destroy_window():
        try:
            page.run_task(page.window.destroy)
        except Exception:
            try:
                page.window.destroy()
            except Exception:
                pass

    # Setup thread-safe pubsub receiver for tray events
    def on_tray_message(msg):
        if msg == "show_window":
            page.window.visible = True
            page.update()
            page.window.minimized = False
            page.window.focused = True
            try:
                page.run_task(page.window.to_front)
            except Exception:
                pass
            page.update()
        elif msg == "exit_app":
            page.window.on_event = None
            page.window.prevent_close = False
            _safe_destroy_window()
            
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

    if getattr(sys, 'frozen', False):
        assets_dir = os.path.join(sys._MEIPASS, "assets")
    else:
        assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
    icon_ico_path = os.path.join(assets_dir, "icon.ico")

    page.title = "Any Downloader"
    page.window.icon = icon_ico_path if os.path.exists(icon_ico_path) else "icon.ico"
    page.window.brightness = ft.Brightness.DARK if AppTheme.MODE == 'dark' else ft.Brightness.LIGHT
    page.width = 900
    page.height = 700
    page.theme = AppTheme.get_theme()
    page.theme_mode = ft.ThemeMode.LIGHT if AppTheme.MODE == 'light' else ft.ThemeMode.DARK
    page.bgcolor = AppTheme.BACKGROUND
    page.window.bgcolor = AppTheme.BACKGROUND
    page.padding = 0
    page.window.prevent_close = True
    page.window.title_bar_hidden = True
    page.window.visible = False

    apply_native_window_styling("Any Downloader", icon_ico_path, dark=(AppTheme.MODE == 'dark'))

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
            _safe_destroy_window()
            import time
            time.sleep(1.0)  # Wait for flet.exe to gracefully exit
            kill_child_flet()
            try:
                import tempfile
                pf = os.path.join(tempfile.gettempdir(), "any_downloader_app.port")
                if os.path.exists(pf):
                    os.remove(pf)
            except Exception:
                pass
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

    close_icon = ft.Icon(ft.Icons.EXIT_TO_APP_ROUNDED, color=AppTheme.PRIMARY, size=22)
    close_title_text = ft.Text("Close Application", weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY, size=18)
    prompt_text = ft.Text("Do you want to minimize to the system tray or exit the application?", color=AppTheme.TEXT_SECONDARY, size=14)

    remember_checkbox = ft.Checkbox(
        label="Remember my choice",
        value=False,
        active_color=AppTheme.PRIMARY,
        check_color=ft.Colors.WHITE,
        label_style=ft.TextStyle(color=AppTheme.TEXT_SECONDARY, size=13),
    )
    
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

    cancel_btn = ft.TextButton("Cancel", on_click=on_cancel, style=ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY))
    exit_btn = ft.TextButton("Exit App", on_click=on_exit, icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED, style=ft.ButtonStyle(color=AppTheme.ERROR))
    minimize_btn = ft.FilledButton(
        "Minimize to Tray",
        icon=ft.Icons.MOVE_TO_INBOX_ROUNDED,
        style=ft.ButtonStyle(
            bgcolor=AppTheme.PRIMARY,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=on_minimize,
    )

    close_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([close_icon, close_title_text], spacing=10),
        content=ft.Container(
            content=ft.Column([
                prompt_text,
                ft.Container(height=4),
                remember_checkbox
            ], tight=True, spacing=10),
            width=460,
        ),
        bgcolor=AppTheme.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
        actions=[
            cancel_btn,
            exit_btn,
            minimize_btn,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    
    page.overlay.append(close_dialog)

    def request_close(e=None):
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
        close_dialog.bgcolor = AppTheme.SURFACE
        close_icon.color = AppTheme.PRIMARY
        close_title_text.color = AppTheme.TEXT_PRIMARY
        prompt_text.color = AppTheme.TEXT_SECONDARY
        remember_checkbox.active_color = AppTheme.PRIMARY
        remember_checkbox.label_style = ft.TextStyle(color=AppTheme.TEXT_SECONDARY, size=13)
        cancel_btn.style = ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY)
        exit_btn.style = ft.ButtonStyle(color=AppTheme.ERROR)
        minimize_btn.style = ft.ButtonStyle(
            bgcolor=AppTheme.PRIMARY,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
        )
        remember_checkbox.value = False
        close_dialog.open = True
        page.update()

    title_bar = CustomTitleBar(page, on_close_click=request_close)
    page.custom_title_bar = title_bar

    def window_event(e):
        event_val = str(getattr(e, "type", getattr(e, "data", ""))).lower()
        print(f"[WINDOW EVENT] data={getattr(e, 'data', None)} type={getattr(e, 'type', None)} event_val={event_val}")
        
        if "close" in event_val:
            request_close()
            return
        elif any(k in event_val for k in ("max", "restore", "unmax")):
            title_bar.update_maximize_state(page.window.maximized)
            page.update()

    page.window.on_event = window_event

    from src.backend.ffmpeg_manager import is_ffmpeg_available, download_ffmpeg

    if is_ffmpeg_available():
        main_view = MainView(page)
        page.add(ft.Column([title_bar, main_view], spacing=0, expand=True))

        # Scheduled backend engine update check (daily, weekly, monthly)
        def _check_engine_updates_startup():
            try:
                import time
                from src.backend.engine_manager import should_check_for_updates, check_for_engine_updates
                if should_check_for_updates():
                    results = check_for_engine_updates()
                    if results.get('has_updates'):
                        time.sleep(2.5)  # Wait for UI to fully mount
                        def show_banner():
                            upgrades = [k for k, v in results['engines'].items() if v.get('update_available')]
                            sb = ft.SnackBar(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.UPGRADE_ROUNDED, color=AppTheme.PRIMARY),
                                    ft.Text(f"Engine update available for {', '.join(upgrades)}! Check Settings > Advanced.", color=AppTheme.TEXT_PRIMARY),
                                ], spacing=10),
                                bgcolor=AppTheme.SURFACE_VARIANT,
                                duration=6000,
                            )
                            page.overlay.append(sb)
                            sb.open = True
                            page.update()
                        if hasattr(page, 'run_thread') and page.run_thread:
                            page.run_thread(show_banner)
                        else:
                            show_banner()
            except Exception as e:
                print(f"[Main] Engine startup check error: {e}")

        threading.Thread(target=_check_engine_updates_startup, daemon=True).start()
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
        page.add(ft.Column([title_bar, loading_view], spacing=0, expand=True))
        
        def update_progress(percent, text):
            progress_bar.value = percent / 100.0 if percent > 0 else None
            status_text.value = text
            page.update()
            
        def download_task():
            try:
                download_ffmpeg(update_progress)
                
                def exit_app(e):
                    force_exit_app()
                    
                restart_btn = ft.ElevatedButton(
                    "Exit Application",
                    icon=ft.Icons.EXIT_TO_APP_ROUNDED,
                    bgcolor=AppTheme.PRIMARY,
                    color=ft.Colors.WHITE,
                    on_click=exit_app,
                    height=45
                )
                
                page.controls.clear()
                restart_view = ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=AppTheme.SUCCESS, size=64),
                            ft.Text("Setup Complete!", size=28, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
                            ft.Text("FFmpeg has been installed successfully.\nPlease manually restart the application to apply the changes.", 
                                    text_align=ft.TextAlign.CENTER, color=AppTheme.TEXT_SECONDARY, size=16),
                            ft.Container(height=20),
                            restart_btn
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    expand=True,
                )
                page.add(ft.Column([title_bar, restart_view], spacing=0, expand=True))
                page.update()
            except Exception as e:
                status_text.value = f"Failed to download FFmpeg: {e}\nPlease restart the app or install FFmpeg manually."
                status_text.color = ft.Colors.ERROR
                progress_bar.color = ft.Colors.ERROR
                progress_bar.value = 1.0
                page.update()
                
        threading.Thread(target=download_task, daemon=True).start()

    try:
        await page.window.wait_until_ready_to_show()
    except Exception:
        pass
    page.window.visible = True
    page.update()
if __name__ == "__main__":
    if not init_single_instance():
        sys.exit(0)

    # Redirect stdout/stderr to log file ONLY when packaged as an executable.
    # In development mode (python main.py), print everything directly to the terminal.
    if getattr(sys, 'frozen', False):
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
    
    ft.run(main, assets_dir=assets_dir, view=ft.AppView.FLET_APP_HIDDEN)
