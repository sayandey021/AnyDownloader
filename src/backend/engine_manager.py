import sys
import os
import shutil
import subprocess
import threading
import time
import json
import urllib.request
from typing import Dict, Any, Optional, Callable

from src.backend.settings import SettingsManager

_cached_engine_versions: Optional[Dict[str, str]] = None


def get_installed_engine_versions(force_refresh: bool = False) -> Dict[str, str]:
    """Retrieve currently installed versions of backend engines safely.

    Uses importlib.metadata first, with lightweight module __version__ attribute
    fallbacks for packaged/frozen environments where dist-info may not be present.
    """
    global _cached_engine_versions
    if not force_refresh and _cached_engine_versions is not None:
        return dict(_cached_engine_versions)

    versions = {
        'yt-dlp': 'Not Installed',
        'spotdl': 'Not Installed',
        'curl_cffi': 'Not Installed',
    }

    # 1. Primary lookup: importlib.metadata (pure filesystem-based dist-info read)
    try:
        import importlib.metadata
        for pkg_name, engine_key in [('yt-dlp', 'yt-dlp'), ('spotdl', 'spotdl'), ('curl-cffi', 'curl_cffi')]:
            try:
                v = importlib.metadata.version(pkg_name)
                if v:
                    versions[engine_key] = v
            except Exception:
                pass
    except Exception:
        pass

    # 2. Safe fallbacks for frozen/packaged binaries where dist-info may not be bundled:
    # yt-dlp fallback: import only yt_dlp.version (pure static string file, no subprocesses)
    if versions['yt-dlp'] in ('Not Installed', 'Unknown'):
        try:
            import yt_dlp.version
            v = getattr(yt_dlp.version, '__version__', None)
            if v:
                versions['yt-dlp'] = str(v)
        except Exception:
            try:
                import yt_dlp
                v = getattr(yt_dlp, '__version__', None) or getattr(getattr(yt_dlp, 'version', None), '__version__', None)
                if v:
                    versions['yt-dlp'] = str(v)
            except Exception:
                pass

    # spotdl fallback: read _version.py text safely or import spotdl._version
    if versions['spotdl'] in ('Not Installed', 'Unknown'):
        try:
            import importlib.resources
            f = importlib.resources.files('spotdl') / '_version.py'
            content = f.read_text(encoding='utf-8')
            for line in content.splitlines():
                if line.strip().startswith('__version__'):
                    versions['spotdl'] = line.split('=')[1].strip().strip('"\'')
                    break
        except Exception:
            try:
                import spotdl._version
                v = getattr(spotdl._version, '__version__', None)
                if v:
                    versions['spotdl'] = str(v)
            except Exception:
                pass

    # curl_cffi fallback: read module __version__
    if versions['curl_cffi'] in ('Not Installed', 'Unknown'):
        try:
            import curl_cffi
            v = getattr(curl_cffi, '__version__', None)
            if v:
                versions['curl_cffi'] = str(v)
        except Exception:
            pass

    _cached_engine_versions = dict(versions)
    return versions


def fetch_latest_pypi_version(package_name: str, timeout: int = 6) -> Optional[str]:
    """Query PyPI JSON API to get the latest release version of a package."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AnyDownloader/1.9.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('info', {}).get('version')
    except Exception as e:
        print(f"[EngineManager] Failed to check PyPI for {package_name}: {e}")
    return None


def _normalize_version(v: str) -> tuple:
    """Helper to convert version string into comparable tuple of ints/strs."""
    clean = v.strip().lstrip('v').replace('-', '.').replace('_', '.')
    parts = []
    for part in clean.split('.'):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part)
    return tuple(parts)


def is_version_newer(latest: str, current: str) -> bool:
    """Compare two version strings."""
    if not latest or not current or current in ('Not Installed', 'Installed', 'Unknown'):
        return False
    try:
        return _normalize_version(latest) > _normalize_version(current)
    except Exception:
        return latest.strip() != current.strip()


def check_for_engine_updates(force_refresh: bool = True) -> Dict[str, Any]:
    """Check PyPI for newer versions of core engines and record check time."""
    current_versions = get_installed_engine_versions(force_refresh=force_refresh)
    results = {
        'engines': {},
        'has_updates': False,
        'check_time': time.time(),
        'error': None
    }

    packages = {
        'yt-dlp': 'yt-dlp',
        'spotdl': 'spotdl',
        'curl_cffi': 'curl-cffi',
    }

    has_updates = False
    for engine_key, pypi_name in packages.items():
        curr_v = current_versions.get(engine_key, 'Unknown')
        latest_v = fetch_latest_pypi_version(pypi_name)
        update_avail = False

        if latest_v and curr_v not in ('Not Installed', 'Unknown'):
            update_avail = is_version_newer(latest_v, curr_v)
            if update_avail:
                has_updates = True

        results['engines'][engine_key] = {
            'current': curr_v,
            'latest': latest_v or curr_v,
            'update_available': update_avail,
        }

    results['has_updates'] = has_updates

    # Persist last check timestamp
    try:
        settings = SettingsManager()
        settings.set('engine_last_check_time', results['check_time'])
        settings.save()
    except Exception:
        pass

    return results


def should_check_for_updates() -> bool:
    """Check if the user's scheduled interval (daily, weekly, monthly) has elapsed."""
    settings = SettingsManager()
    interval = settings.get('engine_update_interval', 'weekly').lower()
    if interval == 'never':
        return False

    last_check = float(settings.get('engine_last_check_time', 0))
    now = time.time()
    elapsed = now - last_check

    intervals = {
        'daily': 86400,        # 24 hours
        'weekly': 604800,      # 7 days
        'monthly': 2592000,    # 30 days
    }
    required_elapsed = intervals.get(interval, 604800)
    return elapsed >= required_elapsed


def update_engines(
    packages: Optional[list] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> tuple[bool, str]:
    """
    Run pip upgrade for specified packages in background.
    Returns (success: bool, message: str).
    """
    if packages is None:
        packages = ['yt-dlp', 'spotdl', 'curl_cffi']

    # Locate a valid python/pip runner
    python_cmd = None
    if not getattr(sys, 'frozen', False):
        python_cmd = [sys.executable, "-m", "pip"]
    else:
        # If running inside a packaged binary, attempt to find system python/pip
        sys_py = shutil.which("python") or shutil.which("python3") or shutil.which("py")
        if sys_py:
            python_cmd = [sys_py, "-m", "pip"]
        elif shutil.which("pip"):
            python_cmd = [shutil.which("pip")]

    if not python_cmd:
        msg = "Python pip was not found on this system. Please update engines manually using 'pip install -U yt-dlp spotdl'."
        if progress_callback:
            progress_callback(msg)
        return False, msg

    cmd = [*python_cmd, "install", "--upgrade", *packages]
    if progress_callback:
        progress_callback(f"Running upgrade for {', '.join(packages)}...")

    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            creationflags=creation_flags
        )

        if proc.returncode == 0:
            msg = f"Successfully updated engines: {', '.join(packages)}"
            if progress_callback:
                progress_callback(msg)
            return True, msg
        else:
            err = proc.stderr.strip() or proc.stdout.strip() or "Unknown pip error"
            msg = f"Update failed: {err[:200]}"
            if progress_callback:
                progress_callback(msg)
            return False, msg
    except Exception as e:
        msg = f"Update error: {e}"
        if progress_callback:
            progress_callback(msg)
        return False, msg
