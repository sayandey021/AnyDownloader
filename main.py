import sys
import os
import subprocess
import ctypes
from ctypes import wintypes
import threading
import time

# Suppress visible terminal/cmd console flashing for any background subprocesses on Windows
if sys.platform == "win32":
    import _winapi

    _orig_CreateProcess = _winapi.CreateProcess

    def _silent_CreateProcess(app_name, cmd_line, proc_attrs, thread_attrs, inherit_handles, creationflags, env, cwd, startupinfo):
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

# Windows AppUserModelID
AUMID = "SwiftGrab.AnyDownloader.App"
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(AUMID)
    except Exception:
        pass

# Single instance enforcement
_single_instance_mutex = None
_single_instance_socket = None
_app_controller_ref = None

def restore_and_focus_native_window():
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = user32.FindWindowW(None, "Any Downloader")
        if hwnd:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            else:
                user32.ShowWindow(hwnd, 5)  # SW_SHOW

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
    global _app_controller_ref
    if _app_controller_ref:
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(_app_controller_ref, "restoreFromTray", Qt.QueuedConnection)
    else:
        restore_and_focus_native_window()

def init_single_instance():
    if sys.platform != "win32":
        return True

    global _single_instance_mutex, _single_instance_socket
    import tempfile
    import socket

    port_file = os.path.join(tempfile.gettempdir(), "any_downloader_pyside6.port")
    MUTEX_NAME = r"Local\AnyDownloader_PySide6_Mutex_2026"
    kernel32 = ctypes.windll.kernel32

    _single_instance_mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()

    if last_error == 183:  # ERROR_ALREADY_EXISTS
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

        restore_and_focus_native_window()
        return False

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


from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl, Qt

from src.controllers.app_controller import AppController
from src.controllers.settings_controller import SettingsController
from src.controllers.history_controller import HistoryController
from src.controllers.downloader_controller import DownloaderController
from src.backend.ffmpeg_manager import is_ffmpeg_available, download_ffmpeg
from src.backend.engine_manager import should_check_for_updates, check_for_engine_updates


def main():
    if not init_single_instance():
        sys.exit(0)

    # Enable High DPI and set application attributes
    app = QApplication(sys.argv)
    app.setApplicationName("Any Downloader")
    app.setOrganizationName("SwiftGrab")
    app.setQuitOnLastWindowClosed(False)

    app_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(app_dir, "assets")
    icon_path = os.path.join(assets_dir, "icon.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(assets_dir, "icon.ico")

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Initialize Controllers
    global _app_controller_ref
    app_controller = AppController()
    _app_controller_ref = app_controller
    settings_controller = SettingsController()
    history_controller = HistoryController()
    downloader_controller = DownloaderController()

    # Setup System Tray
    tray_icon = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon(QIcon(icon_path) if os.path.exists(icon_path) else QIcon(), app)
        tray_menu = QMenu()

        show_action = QAction("Show Any Downloader", app)
        show_action.triggered.connect(app_controller.restoreFromTray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        exit_action = QAction("Exit", app)
        exit_action.triggered.connect(app_controller.exitApp)
        tray_menu.addAction(exit_action)

        tray_icon.setContextMenu(tray_menu)
        tray_icon.setToolTip("Any Downloader")

        def _on_tray_activated(reason):
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
                app_controller.restoreFromTray()

        tray_icon.activated.connect(_on_tray_activated)
        tray_icon.show()
        app_controller.set_tray_icon(tray_icon)

    # Setup QML Application Engine
    engine = QQmlApplicationEngine()

    # Pass context properties to QML
    engine.rootContext().setContextProperty("applicationDirPath", app_dir.replace("\\", "/"))
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty("settingsController", settings_controller)
    engine.rootContext().setContextProperty("historyController", history_controller)
    engine.rootContext().setContextProperty("downloaderController", downloader_controller)

    # Load Main.qml
    main_qml_path = os.path.join(app_dir, "src", "qml", "Main.qml")
    engine.load(QUrl.fromLocalFile(main_qml_path))

    if not engine.rootObjects():
        print("Failed to load QML root object.")
        sys.exit(-1)

    root_window = engine.rootObjects()[0]
    app_controller.set_window(root_window)

    # Check FFmpeg availability
    if not is_ffmpeg_available():
        root_window.setProperty("isSetupMode", True)
        setup_page = root_window.findChild(object, "setupPage")

        def _ffmpeg_download_worker():
            def _prog(percent, status_text):
                if setup_page:
                    setup_page.setProperty("progressPercent", percent)
                    setup_page.setProperty("statusMessage", status_text)

            try:
                download_ffmpeg(_prog)
                if setup_page:
                    setup_page.setProperty("isComplete", True)
            except Exception as e:
                if setup_page:
                    setup_page.setProperty("isError", True)
                    setup_page.setProperty("statusMessage", f"Failed to download FFmpeg: {e}")

        threading.Thread(target=_ffmpeg_download_worker, daemon=True).start()
    else:
        # Background check for backend engines updates
        def _check_engine_updates_startup():
            try:
                time.sleep(3.0)  # Wait for UI to fully mount
                if should_check_for_updates():
                    results = check_for_engine_updates()
                    if results.get('has_updates'):
                        upgrades = [k for k, v in results['engines'].items() if v.get('update_available')]
                        if upgrades:
                            app_controller.showToast(f"Engine update available for {', '.join(upgrades)}! Check Settings > Advanced.", "info")
            except Exception as e:
                print(f"[Main] Engine startup check error: {e}")

        threading.Thread(target=_check_engine_updates_startup, daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
