import collections
import datetime
import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
import threading
import urllib.parse
from typing import Dict, List, Optional, Tuple

import requests

from src.backend.settings import SettingsManager

# Default recipient email specified by project owner
DEVELOPER_EMAIL = "saayanstudiosoft@gmail.com"
APP_VERSION = "1.9.6"

# Default Google Apps Script Webhook URL (can also be configured via Settings or settings.json)
DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzpwvHeRik869ydQHaAoRvvPN5QV6BKhQTmuGcE8jP4QbYEsHSEzrSHWkF52eSAPUI/exec"


def set_clipboard_text(text: str, page=None) -> bool:
    """Safely copies text to the system clipboard across all Flet versions and platforms."""
    if not isinstance(text, str):
        text = str(text)

    # 1. Native Windows Win32 ctypes (instant, 100% reliable, zero dependencies)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
            kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
            kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalLock.restype = wintypes.LPVOID
            kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalUnlock.restype = wintypes.BOOL
            kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalFree.restype = wintypes.HGLOBAL

            user32.OpenClipboard.argtypes = [wintypes.HWND]
            user32.OpenClipboard.restype = wintypes.BOOL
            user32.EmptyClipboard.argtypes = []
            user32.EmptyClipboard.restype = wintypes.BOOL
            user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
            user32.SetClipboardData.restype = wintypes.HANDLE
            user32.CloseClipboard.argtypes = []
            user32.CloseClipboard.restype = wintypes.BOOL

            data = text.encode("utf-16le") + b"\x00\x00"
            GMEM_MOVEABLE = 0x0002
            CF_UNICODETEXT = 13

            if user32.OpenClipboard(None):
                try:
                    user32.EmptyClipboard()
                    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                    if h_mem:
                        p_mem = kernel32.GlobalLock(h_mem)
                        if p_mem:
                            ctypes.memmove(p_mem, data, len(data))
                            kernel32.GlobalUnlock(h_mem)
                            if user32.SetClipboardData(CF_UNICODETEXT, h_mem):
                                return True
                            else:
                                kernel32.GlobalFree(h_mem)
                finally:
                    user32.CloseClipboard()
        except Exception:
            pass

    # 2. Tkinter fallback
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        pass

    # 3. Flet Page.set_clipboard fallback (for older Flet versions)
    if page and hasattr(page, "set_clipboard") and callable(getattr(page, "set_clipboard")):
        try:
            page.set_clipboard(text)
            return True
        except Exception:
            pass

    return False


# Automatically patch ft.Page.set_clipboard so existing callers across the app never crash
try:
    import flet as ft
    if not hasattr(ft.Page, "set_clipboard"):
        ft.Page.set_clipboard = lambda self, text: set_clipboard_text(text, self)
except Exception:
    pass


class LogCapture:
    """Thread-safe in-memory ring buffer that captures the most recent log lines."""

    _buffer: collections.deque = collections.deque(maxlen=300)
    _lock = threading.Lock()
    _installed = False

    @classmethod
    def write(cls, text: str):
        if not text:
            return
        with cls._lock:
            for line in text.splitlines():
                stripped = line.rstrip()
                if stripped:
                    # Prepend timestamp if not already present
                    if not (stripped.startswith("[") and ":" in stripped[:15]):
                        now_str = datetime.datetime.now().strftime("%H:%M:%S")
                        stripped = f"[{now_str}] {stripped}"
                    cls._buffer.append(stripped)

    @classmethod
    def get_last_lines(cls, n: int = 50) -> List[str]:
        with cls._lock:
            lines = list(cls._buffer)
            return lines[-n:] if len(lines) > n else lines

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._buffer.clear()


class _TeeStream:
    """Wraps an existing stdout/stderr stream and duplicates output to LogCapture."""

    def __init__(self, target):
        self.target = target

    def write(self, s):
        if self.target and hasattr(self.target, "write"):
            try:
                self.target.write(s)
            except Exception:
                pass
        try:
            LogCapture.write(s)
        except Exception:
            pass

    def flush(self):
        if self.target and hasattr(self.target, "flush"):
            try:
                self.target.flush()
            except Exception:
                pass

    def isatty(self):
        return getattr(self.target, "isatty", lambda: False)()


def install_log_capture():
    """Installs the tee logger on sys.stdout and sys.stderr if not already installed."""
    if not LogCapture._installed:
        sys.stdout = _TeeStream(sys.stdout)
        sys.stderr = _TeeStream(sys.stderr)
        LogCapture._installed = True


def get_candidate_log_files() -> List[str]:
    """Returns a list of possible filesystem paths for any_downloader_debug.log."""
    paths = []
    # 1. Inside temp subdirectory of executable or script
    base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    paths.append(os.path.join(base_dir, "temp", "any_downloader_debug.log"))
    paths.append(os.path.join(base_dir, "..", "..", "temp", "any_downloader_debug.log"))
    
    # 2. Inside user's ~/.AnyDownloader directory
    user_app_dir = os.path.join(os.path.expanduser("~"), ".AnyDownloader")
    paths.append(os.path.join(user_app_dir, "any_downloader_debug.log"))
    
    # 3. Inside system temp directory
    import tempfile
    paths.append(os.path.join(tempfile.gettempdir(), "Any Downloader", "any_downloader_debug.log"))
    paths.append(os.path.join(tempfile.gettempdir(), "any_downloader_debug.log"))
    
    # Return normalized paths that exist or valid candidates
    normalized = []
    for p in paths:
        norm = os.path.abspath(p)
        if norm not in normalized:
            normalized.append(norm)
    return normalized


def get_recent_debug_logs(n_lines: int = 50) -> str:
    """Retrieves the last N lines of debug logs from file or in-memory capture buffer."""
    lines: List[str] = []
    
    # Check filesystem log files first
    for path in get_candidate_log_files():
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    file_lines = [line.rstrip() for line in f if line.strip()]
                    if file_lines:
                        lines = file_lines[-n_lines:]
                        break
            except Exception:
                pass

    # If log file yielded fewer lines, augment or fallback to in-memory LogCapture
    memory_lines = LogCapture.get_last_lines(n_lines)
    if memory_lines:
        if not lines:
            lines = memory_lines
        else:
            # Merge while keeping ordering
            seen = set(lines)
            for m in memory_lines:
                if m not in seen:
                    lines.append(m)
            lines = lines[-n_lines:]

    if not lines:
        return "[No recent debug logs recorded. Application running normally.]"

    return "\n".join(lines)


def get_system_diagnostics() -> Dict[str, str]:
    """Collects comprehensive, safe diagnostic information without any private data."""
    diagnostics: Dict[str, str] = {
        "App Version": APP_VERSION,
        "Package Mode": "Packaged Executable (Frozen)" if getattr(sys, "frozen", False) else "Development (Python Source)",
        "Operating System": f"{platform.system()} {platform.release()} (Build {platform.version()})",
        "OS Architecture": platform.machine(),
        "Python Runtime": f"{platform.python_version()} ({platform.architecture()[0]})",
    }

    # Flet version
    try:
        import flet as ft
        diagnostics["Flet Version"] = getattr(ft, "__version__", "Unknown")
    except Exception:
        diagnostics["Flet Version"] = "Not found"

    # Engine versions (yt-dlp, spotdl, curl_cffi)
    try:
        from src.backend.engine_manager import get_installed_engine_versions
        engine_versions = get_installed_engine_versions()
        diagnostics["yt-dlp Engine"] = engine_versions.get("yt-dlp", "Unknown")
        diagnostics["spotdl Engine"] = engine_versions.get("spotdl", "Unknown")
        diagnostics["curl_cffi Engine"] = engine_versions.get("curl_cffi", "Unknown")
    except Exception as e:
        diagnostics["Engines"] = f"Error reading versions: {e}"

    # FFmpeg status
    try:
        from src.backend.ffmpeg_manager import is_ffmpeg_available, get_local_ffmpeg_exe
        ffmpeg_available = is_ffmpeg_available()
        ffmpeg_path = get_local_ffmpeg_exe() or "Not found in PATH or .AnyDownloader"
        diagnostics["FFmpeg Available"] = "Yes" if ffmpeg_available else "No"
        diagnostics["FFmpeg Path"] = ffmpeg_path
    except Exception as e:
        diagnostics["FFmpeg"] = f"Error checking FFmpeg: {e}"

    # App Settings & UI Mode
    try:
        settings = SettingsManager()
        diagnostics["Theme Mode"] = settings.get("theme", "dark")
        diagnostics["Accent Color"] = settings.get("accent_color", "Rose")
        diagnostics["Max Concurrent Downloads"] = str(settings.get("max_concurrent_downloads", 3))
        diagnostics["SponsorBlock Enabled"] = str(settings.get("enable_sponsorblock", False))
        diagnostics["Browser Cookies Config"] = settings.get("browser_cookies", "none")
    except Exception:
        pass

    diagnostics["Report Timestamp (UTC)"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return diagnostics


def format_system_diagnostics_markdown(diag: Dict[str, str]) -> str:
    """Formats system diagnostics as clean markdown bullet points."""
    return "\n".join([f"- **{k}**: `{v}`" for k, v in diag.items()])


def build_full_report_markdown(
    category: str,
    title: str,
    description: str,
    user_email: str = "",
    include_diagnostics: bool = True,
    system_info: Optional[Dict[str, str]] = None,
    logs: Optional[str] = None,
) -> str:
    """Generates a complete, markdown-formatted bug report."""
    if system_info is None:
        system_info = get_system_diagnostics() if include_diagnostics else {}
    if logs is None:
        logs = get_recent_debug_logs(50) if include_diagnostics else ""

    contact = user_email.strip() if user_email and user_email.strip() else "Not provided"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = [
        f"# [Any Downloader v{APP_VERSION}] Bug Report",
        "",
        "### 📌 Overview",
        f"- **Category:** {category}",
        f"- **Title:** {title}",
        f"- **Contact Email:** {contact}",
        f"- **Target Developer:** {DEVELOPER_EMAIL}",
        f"- **Generated At:** {now_str}",
        "",
        "### 📝 Description",
        description.strip() if description.strip() else "*(No description provided)*",
        "",
    ]

    if include_diagnostics:
        md.append("### 💻 System Diagnostics")
        md.append(format_system_diagnostics_markdown(system_info))
        md.append("")
        md.append("### 📋 Recent Debug Logs (Last 50 Lines)")
        md.append("```text")
        md.append(logs if logs else "[No logs]")
        md.append("```")
        md.append("")

    return "\n".join(md)


def get_active_webhook_url() -> str:
    """Returns the currently active Webhook URL from settings or default constant."""
    try:
        settings = SettingsManager()
        configured = settings.get("bug_report_webhook_url", "")
        if configured and configured.strip():
            return configured.strip()
    except Exception:
        pass
    return DEFAULT_WEBHOOK_URL.strip()


def send_bug_report(
    category: str,
    title: str,
    description: str,
    user_email: str = "",
    include_diagnostics: bool = True,
    webhook_url: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """Sends a bug report via HTTP POST to the serverless webhook (Google Apps Script).

    Returns:
        (success: bool, status_message: str, markdown_report: str)
    """
    sys_info = get_system_diagnostics() if include_diagnostics else {}
    debug_logs = get_recent_debug_logs(50) if include_diagnostics else ""
    full_markdown = build_full_report_markdown(
        category=category,
        title=title,
        description=description,
        user_email=user_email,
        include_diagnostics=include_diagnostics,
        system_info=sys_info,
        logs=debug_logs,
    )

    url = (webhook_url or get_active_webhook_url()).strip()

    if not url:
        return (
            False,
            "NO_WEBHOOK_URL",
            full_markdown,
        )

    payload = {
        "recipient": DEVELOPER_EMAIL,
        "type": "bug_report",
        "app_name": "Any Downloader",
        "app_version": APP_VERSION,
        "category": category,
        "title": title,
        "user_email": user_email.strip(),
        "description": description.strip(),
        "include_diagnostics": include_diagnostics,
        "system_info": sys_info,
        "logs": debug_logs,
        "report_markdown": full_markdown,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"AnyDownloader/{APP_VERSION}",
            },
            timeout=35,
            allow_redirects=True,
        )

        if response.status_code in (200, 201):
            try:
                data = response.json()
                if data.get("status") == "error":
                    return (
                        False,
                        data.get("message", "Webhook returned an error response."),
                        full_markdown,
                    )
            except Exception:
                # If non-JSON but 200 OK (Google Apps Script redirection sometimes returns text/html)
                pass

            return (
                True,
                "Bug report successfully delivered to saayanstudiosoft@gmail.com!",
                full_markdown,
            )
        else:
            return (
                False,
                f"Server returned status {response.status_code}: {response.text[:150]}",
                full_markdown,
            )
    except requests.exceptions.Timeout:
        return (
            False,
            "Request timed out. Please check your internet connection.",
            full_markdown,
        )
    except requests.exceptions.ConnectionError:
        return (
            False,
            "Could not connect to the bug report server. Check your internet connection.",
            full_markdown,
        )
    except Exception as e:
        return (
            False,
            f"Unexpected error: {str(e)}",
            full_markdown,
        )


def build_mailto_url(category: str, title: str, description: str, system_info: Optional[Dict[str, str]] = None) -> str:
    """Builds a mailto URL directed to saayanstudiosoft@gmail.com with pre-filled content."""
    subject = f"[Any Downloader Bug Report] [{category}] {title}"
    body = f"Description:\n{description}\n\n"
    if system_info:
        body += "System Diagnostics:\n"
        for k, v in system_info.items():
            body += f"{k}: {v}\n"
    # URL encode
    return f"mailto:{DEVELOPER_EMAIL}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
