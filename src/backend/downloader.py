import yt_dlp
import threading
import os
import uuid
import subprocess
import json
import tempfile
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

thread_local = threading.local()

# Patch yt_dlp Popen to capture FFmpeg progress
from yt_dlp.utils import Popen as YtdlPopen

_original_communicate_or_kill = YtdlPopen.communicate_or_kill
_original_communicate = YtdlPopen.communicate
_original_wait = YtdlPopen.wait
_original_init = YtdlPopen.__init__

def _is_ffmpeg_conversion(args_list):
    """Check if a command is an ffmpeg conversion (not ffprobe or other tools).
    Uses the executable basename to avoid false positives from directory names containing 'ffmpeg'."""
    try:
        if not args_list or not isinstance(args_list[0], str):
            return False
        exe_basename = os.path.basename(args_list[0]).lower()
        # Match ffmpeg/ffmpeg.exe but NOT ffprobe/ffprobe.exe
        return exe_basename in ('ffmpeg', 'ffmpeg.exe') and 'ffprobe' not in exe_basename
    except Exception:
        return False

def patched_init(self, *args, **kwargs):
    if args and len(args) > 0 and isinstance(args[0], list):
        cmd = args[0]
        if _is_ffmpeg_conversion(cmd):
            if 'stderr' not in kwargs or kwargs['stderr'] is None:
                kwargs['stderr'] = subprocess.PIPE
    _original_init(self, *args, **kwargs)

def patched_wait(self, timeout=None):
    is_ffmpeg = False
    try:
        is_ffmpeg = _is_ffmpeg_conversion(self.args)
    except:
        pass
        
    if is_ffmpeg and getattr(self, 'stderr', None) is not None:
        cb = getattr(thread_local, 'ffmpeg_progress_cb', None)
        
        # Prevent deadlock if ffmpeg writes to stdout while wait() is called
        stdout_drain_thread = None
        if getattr(self, 'stdout', None) is not None:
            def drain_stdout():
                try:
                    while self.stdout.read(4096):
                        pass
                except:
                    pass
            stdout_drain_thread = threading.Thread(target=drain_stdout)
            stdout_drain_thread.daemon = True
            stdout_drain_thread.start()

        buffer = []
        while True:
            if getattr(self.stderr, 'closed', True): break
            try:
                char = self.stderr.read(1)
            except ValueError:
                break
            if not char: break
            
            if char in (b'\r', b'\n', '\r', '\n'):
                if isinstance(char, bytes):
                    line = b''.join(buffer).decode('utf-8', errors='ignore')
                else:
                    line = ''.join(buffer)
                buffer = []
                
                if cb:
                    m = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                    if m:
                        secs = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                        
                        size_bytes = 0
                        m_size = re.search(r'size=\s*(\d+)(kB|mB|B|k|m|g)?', line, re.IGNORECASE)
                        if m_size:
                            val = int(m_size.group(1))
                            unit = m_size.group(2)
                            if unit:
                                unit = unit.lower()
                                if unit == 'k' or unit == 'kb': val *= 1024
                                elif unit == 'm' or unit == 'mb': val *= 1024 * 1024
                                elif unit == 'g' or unit == 'gb': val *= 1024 * 1024 * 1024
                            size_bytes = val
                            
                        speed_str = ""
                        m_speed = re.search(r'speed=\s*([0-9.]+x)', line)
                        if m_speed:
                            speed_str = m_speed.group(1)
                            
                        try: cb(secs, size_bytes, speed_str, line.strip())
                        except Exception as e:
                            if str(e) == "Download cancelled by user":
                                self.kill()
                                break
                            try: cb(secs)
                            except TypeError: pass
                    else:
                        if ('frame=' in line or 'size=' in line or 'speed=' in line):
                            try: cb(None, None, None, line.strip())
                            except Exception as e:
                                if str(e) == "Download cancelled by user":
                                    self.kill()
                                    break
            else:
                buffer.append(char)
                
    return _original_wait(self, timeout)

def patched_communicate(self, *args, **kwargs):
    is_ffmpeg = False
    try:
        is_ffmpeg = _is_ffmpeg_conversion(self.args)
    except:
        pass
    if is_ffmpeg and getattr(self, 'stderr', None) is not None:
        stdout_output = []
        stderr_output = []
        cb = getattr(thread_local, 'ffmpeg_progress_cb', None)
        
        input_data = kwargs.get('input')
        if len(args) > 0:
            input_data = args[0]
            
        def read_stderr():
            buffer = []
            while True:
                try:
                    char = self.stderr.read(1)
                except ValueError:
                    break
                if not char:
                    if buffer:
                        if isinstance(buffer[0], bytes): line = b''.join(buffer)
                        else: line = ''.join(buffer)
                        if isinstance(line, bytes):
                            try: line = line.decode('utf-8', errors='ignore')
                            except: line = str(line)
                        stderr_output.append(line)
                    break
                buffer.append(char)
                if char in (b'\r', b'\n', '\r', '\n'):
                    if isinstance(char, bytes): line = b''.join(buffer)
                    else: line = ''.join(buffer)
                    buffer = []
                    
                    if isinstance(line, bytes):
                        try: line = line.decode('utf-8', errors='ignore')
                        except: line = str(line)
                    stderr_output.append(line)
                    
                    if cb:
                        m = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                        if m:
                            secs = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                            size_bytes = 0
                            m_size = re.search(r'size=\s*(\d+)(kB|mB|B|k|m|g)?', line, re.IGNORECASE)
                            if m_size:
                                val = int(m_size.group(1))
                                unit = (m_size.group(2) or '').lower()
                                if 'g' in unit: val *= 1024*1024*1024
                                elif 'm' in unit: val *= 1024*1024
                                elif 'k' in unit: val *= 1024
                                size_bytes = val
                            speed_str = ""
                            m_speed = re.search(r'speed=\s*([\d\.]+x)', line)
                            if m_speed: speed_str = m_speed.group(1)
                            try:
                                cb(secs, size_bytes, speed_str, line.strip())
                            except TypeError:
                                try: cb(secs, size_bytes, speed_str)
                                except TypeError: cb(secs)
                            except Exception as e:
                                if str(e) == "Download cancelled by user":
                                    self.kill()
                                    break
                        else:
                            if ('frame=' in line or 'size=' in line or 'speed=' in line):
                                try: cb(None, None, None, line.strip())
                                except TypeError: pass
                                except Exception as e:
                                    if str(e) == "Download cancelled by user":
                                        self.kill()
                                        break

        def read_stdout():
            if getattr(self, 'stdout', None) is not None:
                try:
                    out = self.stdout.read()
                    if out:
                        if isinstance(out, str):
                            out = out.encode('utf-8', errors='ignore')
                        stdout_output.append(out)
                except ValueError:
                    pass

        t_err = threading.Thread(target=read_stderr)
        t_out = threading.Thread(target=read_stdout)
        
        t_err.start()
        t_out.start()
        
        if input_data and getattr(self, 'stdin', None):
            try:
                is_text_mode = getattr(self, 'universal_newlines', False) or getattr(self, 'text_mode', False)
                if is_text_mode and isinstance(input_data, bytes):
                    input_data = input_data.decode('utf-8', errors='ignore')
                elif not is_text_mode and isinstance(input_data, str):
                    input_data = input_data.encode('utf-8', errors='ignore')
                self.stdin.write(input_data)
            except Exception:
                pass
        if getattr(self, 'stdin', None):
            try:
                self.stdin.close()
            except Exception:
                pass
                
        t_err.join()
        t_out.join()
        self.wait()
        
        out = stdout_output[0] if stdout_output else b''
        err_str = "".join(stderr_output)
        
        # Respect Popen text mode settings
        is_text_mode = getattr(self, 'universal_newlines', False) or getattr(self, 'text_mode', False)
        
        if is_text_mode:
            if isinstance(out, bytes):
                out = out.decode('utf-8', errors='ignore')
            return out, err_str
        else:
            if isinstance(out, str):
                out = out.encode('utf-8', errors='ignore')
            return out, err_str.encode('utf-8', errors='ignore')
    else:
        if kwargs.get('is_communicate_or_kill'):
            kwargs.pop('is_communicate_or_kill', None)
            return _original_communicate_or_kill(self, *args, **kwargs)
        kwargs.pop('is_communicate_or_kill', None)
        return _original_communicate(self, *args, **kwargs)

def patched_communicate_wrapper(self, *args, **kwargs):
    kwargs['is_communicate_or_kill'] = False
    return patched_communicate(self, *args, **kwargs)

def patched_communicate_or_kill_wrapper(self, *args, **kwargs):
    kwargs['is_communicate_or_kill'] = True
    return patched_communicate(self, *args, **kwargs)

YtdlPopen.__init__ = patched_init
YtdlPopen.communicate = patched_communicate_wrapper
YtdlPopen.communicate_or_kill = patched_communicate_or_kill_wrapper
YtdlPopen.wait = patched_wait

class DownloaderBackend:
    def __init__(self, run_thread=None):
        self.run_thread = run_thread
        # active_tasks maps task_id -> cancel_flag (boolean)
        self.active_tasks = {}

    @staticmethod
    def is_spotify_url(url):
        return 'open.spotify.com' in url or 'spotify.com' in url

    @staticmethod
    def is_applemusic_url(url):
        return 'music.apple.com' in url

    @staticmethod
    def is_tidal_url(url):
        import re
        return bool(re.search(r'tidal\.com', url))

    @staticmethod
    def is_deezer_url(url):
        import re
        return bool(re.search(r'deezer\.com', url))



    @staticmethod
    def is_gaana_url(url):
        import re
        return bool(re.search(r'gaana\.com', url))

    @staticmethod
    def is_lastfm_url(url):
        import re
        return bool(re.search(r'last\.fm', url))

    def get_video_info(self, url, settings=None):
        if self.is_spotify_url(url):
            return self._get_spotify_info(url)
        if self.is_applemusic_url(url):
            return self._get_applemusic_info(url)
        if self.is_tidal_url(url):
            return self._get_tidal_info(url)
        if self.is_deezer_url(url):
            return self._get_deezer_info(url)
        import re
        if bool(re.search(r'music\.amazon\.[a-z.]+', url)):
            raise Exception("Link not supported")
        if self.is_gaana_url(url):
            return self._get_gaana_info(url)
        if self.is_lastfm_url(url):
            return self._get_lastfm_info(url)

        class DummyLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
            def error(self, msg): pass

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'logger': DummyLogger(),
            'extract_flat': 'in_playlist',
            'nocheckcertificate': True,
            'source_address': '0.0.0.0',
            'extractor_args': {
                'youtube': ['player_skip=webpage,configs']
            },
            'js_runtimes': {
                'node': {},
                'deno': {},
                'bun': {},
                'quickjs': {},
            },
            'remote_components': ['ejs:github'],
        }

        cookies_path = settings.get('cookies_path') if settings else None
        browser_cookies = settings.get('browser_cookies', 'none') if settings else 'none'
        
        if cookies_path and os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
        elif browser_cookies and browser_cookies != 'none':
            ydl_opts['cookiesfrombrowser'] = (browser_cookies, )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Pre-download thumbnail for kick.com or twitch (0x0 fixes)
                if info and info.get('thumbnail'):
                    thumb_url = info['thumbnail']
                    b64_data = None
                    try:
                        if 'vimeocdn.com' in thumb_url and '?' in thumb_url:
                            # Clean up Vimeo thumbnails which have invalid `?&...` params
                            thumb_url = thumb_url.split('?')[0]
                            info['thumbnail'] = thumb_url

                        if 'kick.com' in thumb_url or 'kick' in url.lower():
                            from curl_cffi import requests as cffi_requests
                            import base64
                            resp = cffi_requests.get(thumb_url, impersonate="chrome", timeout=10)
                            if resp.status_code == 200:
                                b64_data = base64.b64encode(resp.content).decode('utf-8')
                        elif 'static-cdn.jtvnw.net' in thumb_url and '0x0' in thumb_url:
                            # Fix twitch 0x0 thumbnails just in case
                            import requests
                            import base64
                            fixed_url = thumb_url.replace('0x0', '320x180')
                            resp = requests.get(fixed_url, timeout=10)
                            if resp.status_code == 200:
                                b64_data = base64.b64encode(resp.content).decode('utf-8')
                                info['thumbnail'] = fixed_url # Also update the url
                    except Exception:
                        pass
                        
                    if b64_data:
                        info['thumbnail_base64'] = b64_data

                if info and info.get('_type') == 'playlist' and not info.get('entries'):
                    raise Exception("Empty playlist returned by yt-dlp, fallback to gallery-dl")

                return info
        except Exception as yt_e:
            yt_err_str = str(yt_e).lower()
            if "cookie" in yt_err_str and ("could not copy" in yt_err_str or "permission" in yt_err_str or "locked" in yt_err_str):
                raise Exception(f"Failed to access {browser_cookies} cookies. Please close your browser completely and try again, or export a cookies.txt file instead.")
            
            # Fallback to gallery-dl if yt-dlp fails (for image galleries, Pinterest, etc.)
            try:
                import subprocess
                import json
                
                out = None
                
                cmd = ['gallery-dl', '-j']
                if cookies_path and os.path.exists(cookies_path):
                    cmd.extend(['--cookies', cookies_path])
                cmd.append(url)
                
                try:
                    out = subprocess.check_output(
                        cmd,
                        stderr=subprocess.DEVNULL,
                        text=True
                    )
                except subprocess.CalledProcessError:
                    pass
                    
                # If out is None or contains "login page", try with cookies
                if not out or '"HTTP redirect to login page' in out or '"error":' in out:
                    for browser in ['chrome', 'edge', 'firefox', 'brave']:
                        try:
                            out = subprocess.check_output(
                                ['gallery-dl', '-j', '--cookies-from-browser', browser, url],
                                stderr=subprocess.DEVNULL,
                                text=True
                            )
                            if '"HTTP redirect to login page' not in out and '"error":' not in out:
                                break
                        except:
                            pass
                
                if not out or '"HTTP redirect to login page' in out or '"error":' in out:
                    if 'instagram.com' in url:
                        raise Exception("Instagram blocks multi-image posts without cookies. Go to Settings and click 'Login to Browser (Export Cookies)' to link your account.")
                    return None
                
                # gallery-dl outputs JSON arrays. There might be multiple arrays separated by newlines.
                out = out.strip()
                import re
                # Ensure all top-level arrays are wrapped in one giant array
                out_wrapped = '[' + re.sub(r'\]\s*\[', '],[', out) + ']'
                try:
                    blocks = json.loads(out_wrapped)
                except json.JSONDecodeError:
                    return None
                
                data = []
                for block in blocks:
                    if isinstance(block, list):
                        if len(block) > 0 and isinstance(block[0], int):
                            data.append(block)
                        else:
                            data.extend(block)
                
                if not data:
                    if 'instagram.com' in url or 'facebook.com' in url:
                        raise Exception("Failed to fetch from Instagram/Facebook. Please ensure you have imported a valid cookies.txt file in Settings -> Advanced.")
                    return None
                    
                entries = []
                last_metadata = {}
                for item in data:
                    if isinstance(item, list) and len(item) == 2:
                        status, info_dict = item
                        
                        if status == 2 and isinstance(info_dict, dict):
                            last_metadata = info_dict
                            
                        if status != -1:
                            img_url = None
                            if isinstance(info_dict, dict):
                                img_url = info_dict.get('url') or info_dict.get('file_url')
                                if not img_url and 'images' in info_dict and isinstance(info_dict['images'], dict):
                                    orig = info_dict['images'].get('orig')
                                    if orig and isinstance(orig, dict):
                                        img_url = orig.get('url')
                                if not img_url:
                                    img_url = info_dict.get('image_medium_url')
                            elif isinstance(info_dict, str) and info_dict.startswith('http'):
                                img_url = info_dict
                                info_dict = last_metadata # Use previous metadata for title/id
                                
                            if img_url:
                                ext = img_url.split('.')[-1][:4].lower() if '.' in img_url else 'jpg'
                                if '?' in ext: ext = ext.split('?')[0]
                                if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                                    ext = 'jpg'
                                
                                title = str(info_dict.get('title', info_dict.get('description', 'Image'))).strip() or "Image"
                                # Append unique index/id to title to prevent overwriting
                                img_id = str(info_dict.get('id', info_dict.get('tweet_id', str(len(entries)+1))))
                                title = f"{title}_{img_id}"
                                
                                entry = {
                                    '_type': 'video', # Fake as video to satisfy UI
                                    'id': img_id,
                                    'title': title,
                                    'url': img_url,
                                    'thumbnail': img_url,
                                    'duration': 0,
                                    'formats': [{'url': img_url, 'ext': ext, 'vcodec': 'image', 'acodec': 'none'}],
                                }
                                entries.append(entry)
                
                if entries:
                    if len(entries) == 1:
                        return entries[0]
                    else:
                        # Construct a fake playlist for the UI
                        return {
                            '_type': 'playlist',
                            'id': 'gallery',
                            'title': entries[0]['title'] if entries else 'Image Gallery',
                            'entries': entries,
                            'thumbnail': entries[0]['thumbnail'] if entries else None,
                        }
            except Exception as g_e:
                if "Instagram blocks" in str(g_e) or "Browser cookie extraction" in str(g_e):
                    raise g_e
                pass
            
            import traceback
            traceback.print_exc()
            return None

    # ──────────────────────────────────────────────────────────────
    #  SPOTIFY WEB API — metadata fetching
    # ──────────────────────────────────────────────────────────────
    _spotify_token = None
    _spotify_token_expires = 0
    _spotify_session = None
    _spotify_session_lock = threading.Lock()

    @classmethod
    def _get_spotify_session(cls):
        """Return a reusable requests.Session for HTTP keep-alive / connection pooling."""
        if cls._spotify_session is None:
            with cls._spotify_session_lock:
                if cls._spotify_session is None:
                    import requests
                    s = requests.Session()
                    adapter = requests.adapters.HTTPAdapter(
                        pool_connections=4, pool_maxsize=10, max_retries=0,
                    )
                    s.mount("https://", adapter)
                    cls._spotify_session = s
        return cls._spotify_session

    @classmethod
    def _get_spotify_token(cls):
        """Get a valid Spotify Web API access token, refreshing if needed."""
        import time as _time
        import base64

        if cls._spotify_token and _time.time() < cls._spotify_token_expires - 60:
            return cls._spotify_token

        # Use spotdl's default Spotify app credentials
        try:
            from spotdl.utils.config import DEFAULT_CONFIG
            client_id = DEFAULT_CONFIG["client_id"]
            client_secret = DEFAULT_CONFIG["client_secret"]
        except Exception:
            client_id = "5f573c9620494bae87890c0f08a60293"
            client_secret = "212476d9b0f3472eaa762d90b19b0ba8"

        auth_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        session = cls._get_spotify_session()
        resp = session.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {auth_b64}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        cls._spotify_token = data["access_token"]
        cls._spotify_token_expires = _time.time() + data.get("expires_in", 3600)
        return cls._spotify_token

    @classmethod
    def _spotify_api_get(cls, endpoint, params=None):
        """Make a GET request to the Spotify Web API with automatic retry on 429."""
        import time as _time

        session = cls._get_spotify_session()
        max_retries = 4
        for attempt in range(max_retries):
            token = cls._get_spotify_token()
            resp = session.get(
                f"https://api.spotify.com/v1/{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2))
                if retry_after > 10:
                    print(f"[SPOTIFY API] Rate limited for {retry_after}s, falling back immediately.")
                    return None
                print(f"[SPOTIFY API] Rate limited, retrying in {retry_after}s (attempt {attempt+1}/{max_retries})")
                _time.sleep(retry_after)
            elif resp.status_code == 401:
                # Token expired, force refresh
                cls._spotify_token = None
                continue
            else:
                print(f"[SPOTIFY API] Error {resp.status_code}: {resp.text[:200]}")
                return None
        print("[SPOTIFY API] Max retries exceeded")
        return None

    @classmethod
    def _spotify_api_get_url(cls, full_url):
        """GET a full Spotify API URL (used for pagination 'next' links)."""
        import time as _time

        session = cls._get_spotify_session()
        max_retries = 4
        for attempt in range(max_retries):
            token = cls._get_spotify_token()
            resp = session.get(
                full_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2))
                print(f"[SPOTIFY API] Rate limited on pagination, retrying in {retry_after}s")
                _time.sleep(retry_after)
            elif resp.status_code == 401:
                cls._spotify_token = None
                continue
            else:
                print(f"[SPOTIFY API] Pagination error {resp.status_code}: {resp.text[:200]}")
                return None
        return None

    @staticmethod
    def _parse_spotify_url(url):
        """Extract (type, id) from a Spotify URL or URI."""
        import re
        patterns = [
            r'open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)',
            r'spotify:(track|album|playlist):([a-zA-Z0-9]+)',
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1), m.group(2)
        return None, None

    def _get_spotify_info(self, url):
        """Fetch Spotify track/album/playlist metadata via the Spotify Web API with HTML fallback."""
        try:
            stype, sid = self._parse_spotify_url(url)
            if not stype or not sid:
                print(f"[SPOTIFY] Could not parse URL: {url}")
                return None

            info = None
            if stype == 'track':
                info = self._fetch_spotify_track(sid, url)
            elif stype == 'album':
                info = self._fetch_spotify_album(sid, url)
            elif stype == 'playlist':
                info = self._fetch_spotify_playlist(sid, url)
            else:
                print(f"[SPOTIFY] Unsupported type: {stype}")

            # Fallback to HTML scraping if API fails (e.g., due to rate limiting)
            if not info:
                print(f"[SPOTIFY] API failed or rate-limited. Falling back to HTML scrape for {url}")
                info = self._scrape_spotify_html(url, stype)

            return info

        except Exception as e:
            import traceback
            print(f"[SPOTIFY API ERROR] {e}")
            traceback.print_exc()
            return None

    def _scrape_spotify_html(self, url, stype):
        """Fallback method to extract basic metadata directly from Spotify HTML."""
        import requests
        import re

        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                return None

            html = resp.text

            # Extract basic Open Graph metadata
            def get_og(prop):
                m = re.search(rf'<meta property="og:{prop}" content="([^"]+)"', html)
                return m.group(1) if m else ''

            title = get_og("title") or "Unknown Title"
            thumbnail = get_og("image")
            description = get_og("description") or ""

            # Attempt to extract artist/uploader from description
            uploader = "Spotify"
            if description:
                # e.g., "Rick Astley · Whenever You Need Somebody · Song · 1987"
                # or "Playlist · Today's Top Hits · 50 items · 34.3M saves"
                parts = [p.strip() for p in description.split('·')]
                if parts:
                    if stype == 'playlist' and len(parts) > 1:
                        # For playlists, description usually starts with "Playlist"
                        uploader = "Spotify"
                    else:
                        # For tracks/albums, artist is usually the first part
                        uploader = parts[0]

            is_playlist = (stype in ['playlist', 'album'])

            if is_playlist:
                entries = []
                # Extract track URLs from the playlist HTML
                track_urls = re.findall(r'https://open.spotify.com/track/[a-zA-Z0-9]+', html)
                
                # De-duplicate while preserving order
                seen = set()
                unique_urls = []
                for tu in track_urls:
                    if tu not in seen:
                        seen.add(tu)
                        unique_urls.append(tu)
                        
                if unique_urls:
                    # Fetch basic track metadata concurrently so UI shows names
                    import concurrent.futures
                    def fetch_track_info(t_url):
                        # Use the same scrape method for individual tracks
                        t_info = self._scrape_spotify_html(t_url, 'track')
                        if t_info:
                            return t_info
                        # Absolute fallback if scrape fails
                        return {'url': t_url, 'webpage_url': t_url, 'title': t_url.split('/')[-1]}

                    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                        entries = list(executor.map(fetch_track_info, unique_urls))

                return {
                    '_type': 'playlist',
                    'title': title,
                    'uploader': uploader,
                    'thumbnail': thumbnail,
                    'webpage_url': url,
                    'entries': entries,
                    '_spotify': True,
                }
            else:
                return {
                    'title': f"{uploader} - {title}",
                    'fulltitle': title,
                    'uploader': uploader,
                    'creator': uploader,
                    'channel': uploader,
                    'duration': 0,
                    'thumbnail': thumbnail,
                    'webpage_url': url,
                    'url': url,
                    'album': '',
                    'artist': uploader,
                    'extractor_key': 'Spotify',
                    '_spotify': True,
                }
        except Exception as e:
            print(f"[SPOTIFY SCRAPE ERROR] {e}")
            return None

    def _fetch_spotify_track(self, track_id, original_url):
        """Fetch a single Spotify track."""
        data = self._spotify_api_get(f"tracks/{track_id}")
        if not data:
            return None
        return self._spotify_api_track_to_info(data, original_url)

    def _collect_all_pages(self, first_page_items, next_url):
        """Collect all paginated items, using concurrent requests when total/offset are known."""
        all_items = list(first_page_items)
        if not next_url:
            return all_items

        # Fetch first extra page to learn total/offset/limit for concurrent pre-computation
        remaining_url = next_url
        while remaining_url:
            page = self._spotify_api_get_url(remaining_url)
            if not page:
                break
            all_items.extend(page.get('items', []))
            remaining_url = page.get('next')

            # Pre-compute remaining page URLs for concurrent fetch
            if remaining_url:
                total = page.get('total', 0)
                limit = page.get('limit', 50)
                offset = page.get('offset', 0) + limit
                if total and offset < total:
                    import urllib.parse
                    concurrent_urls = []
                    while offset < total:
                        parsed = urllib.parse.urlparse(remaining_url)
                        params = urllib.parse.parse_qs(parsed.query)
                        params['offset'] = [str(offset)]
                        new_query = urllib.parse.urlencode(params, doseq=True)
                        new_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
                        concurrent_urls.append(new_url)
                        offset += limit

                    if concurrent_urls:
                        with ThreadPoolExecutor(max_workers=min(6, len(concurrent_urls))) as pool:
                            futures = {pool.submit(self._spotify_api_get_url, u): u for u in concurrent_urls}
                            for future in as_completed(futures):
                                try:
                                    p = future.result()
                                    if p:
                                        all_items.extend(p.get('items', []))
                                except Exception as ex:
                                    print(f"[SPOTIFY] Concurrent page fetch error: {ex}")
                    remaining_url = None  # All done

        return all_items

    def _fetch_spotify_album(self, album_id, original_url):
        """Fetch a Spotify album with all tracks (with concurrent pagination)."""
        data = self._spotify_api_get(f"albums/{album_id}")
        if not data:
            return None

        album_name = data.get('name', 'Unknown Album')
        album_artist = ', '.join(a['name'] for a in data.get('artists', []))
        cover_url = data['images'][0]['url'] if data.get('images') else ''
        release_year = data.get('release_date', '')[:4]

        # Collect all tracks (concurrent pagination for large albums)
        first_items = data.get('tracks', {}).get('items', [])
        next_url = data.get('tracks', {}).get('next')
        all_track_items = self._collect_all_pages(first_items, next_url)

        entries = []
        for track in all_track_items:
            entries.append(self._spotify_api_album_track_to_info(
                track, album_name, album_artist, cover_url, release_year, original_url
            ))

        if len(entries) == 1:
            return entries[0]

        return {
            '_type': 'playlist',
            'title': album_name,
            'uploader': album_artist or 'Spotify',
            'thumbnail': cover_url,
            'webpage_url': original_url,
            'entries': entries,
            '_spotify': True,
        }

    def _fetch_spotify_playlist(self, playlist_id, original_url):
        """Fetch a Spotify playlist with all tracks (with concurrent pagination)."""
        # Request extra fields to avoid needing separate track lookups
        data = self._spotify_api_get(
            f"playlists/{playlist_id}",
            params={'fields': 'name,owner,images,tracks(items(track(name,artists,album,duration_ms,external_urls)),next,total,limit,offset)'}
        )
        if not data:
            return None

        playlist_name = data.get('name', 'Unknown Playlist')
        owner = data.get('owner', {}).get('display_name', 'Spotify')
        cover_url = data['images'][0]['url'] if data.get('images') else ''

        # Collect all page items (concurrent pagination for large playlists)
        first_items = data.get('tracks', {}).get('items', [])
        next_url = data.get('tracks', {}).get('next')
        all_playlist_items = self._collect_all_pages(first_items, next_url)

        entries = []
        for item in all_playlist_items:
            track = item.get('track')
            if not track:
                continue
            entries.append(self._spotify_api_track_to_info(track, original_url))

        if not entries:
            return None

        if len(entries) == 1:
            return entries[0]

        return {
            '_type': 'playlist',
            'title': playlist_name,
            'uploader': owner or 'Spotify',
            'thumbnail': cover_url,
            'webpage_url': original_url,
            'entries': entries,
            '_spotify': True,
        }

    @staticmethod
    def _spotify_api_track_to_info(track_data, original_url=''):
        """Convert a Spotify Web API track object into a yt-dlp-like info dict."""
        name = track_data.get('name', 'Unknown Track')
        artists = ', '.join(a['name'] for a in track_data.get('artists', []))
        artist = artists or 'Unknown Artist'
        album = track_data.get('album', {})
        album_name = album.get('name', '')
        album_artist = ', '.join(a['name'] for a in album.get('artists', []))
        cover_url = album.get('images', [{}])[0].get('url', '') if album.get('images') else ''
        duration_ms = track_data.get('duration_ms', 0)
        duration_s = duration_ms / 1000 if duration_ms else 0
        release_date = album.get('release_date', '')
        year = release_date[:4] if release_date else None
        track_url = track_data.get('external_urls', {}).get('spotify', original_url)

        return {
            'title': f"{artist} - {name}",
            'fulltitle': name,
            'uploader': artist,
            'creator': artist,
            'channel': artist,
            'duration': duration_s,
            'thumbnail': cover_url,
            'webpage_url': track_url,
            'url': track_url,
            'album': album_name,
            'album_artist': album_artist,
            'track': name,
            'artist': artist,
            'year': int(year) if year and year.isdigit() else None,
            'extractor_key': 'Spotify',
            '_spotify': True,
        }

    @staticmethod
    def _spotify_api_album_track_to_info(track_data, album_name, album_artist, cover_url, year, original_url=''):
        """Convert a Spotify album track item (which lacks album info) into a yt-dlp-like info dict."""
        name = track_data.get('name', 'Unknown Track')
        artists = ', '.join(a['name'] for a in track_data.get('artists', []))
        artist = artists or 'Unknown Artist'
        duration_ms = track_data.get('duration_ms', 0)
        duration_s = duration_ms / 1000 if duration_ms else 0
        track_url = track_data.get('external_urls', {}).get('spotify', original_url)

        return {
            'title': f"{artist} - {name}",
            'fulltitle': name,
            'uploader': artist,
            'creator': artist,
            'channel': artist,
            'duration': duration_s,
            'thumbnail': cover_url,
            'webpage_url': track_url,
            'url': track_url,
            'album': album_name,
            'album_artist': album_artist,
            'track': name,
            'artist': artist,
            'year': int(year) if year and str(year).isdigit() else None,
            'extractor_key': 'Spotify',
            '_spotify': True,
        }

    # ──────────────────────────────────────────────────────────────
    #  APPLE MUSIC WEB API — metadata fetching
    # ──────────────────────────────────────────────────────────────
    def _get_applemusic_info(self, url):
        """Fetch Apple Music track/album/playlist metadata. Uses AppleMusicMP3 PyPI package with a runtime patch to fix Apple's new JSON schema, and adds single track/album support."""
        import requests
        import bs4
        import json
        import traceback
        
        # We will attempt to use our fixed parser to find tracks in the Apple Music JSON.
        def find_tracks_in_apple_json(node, tracks_list):
            if isinstance(node, dict):
                # Look for track signatures
                if 'title' in node and 'subtitleLinks' in node:
                    title = node.get('title')
                    if isinstance(title, str):
                        artists = []
                        subtitle_links = node.get('subtitleLinks')
                        if isinstance(subtitle_links, list):
                            for link in subtitle_links:
                                if isinstance(link, dict) and 'title' in link:
                                    artists.append(link['title'])
                        if artists:
                            tracks_list.append({"title": title, "artist": " & ".join(artists)})
                for key, value in node.items():
                    find_tracks_in_apple_json(value, tracks_list)
            elif isinstance(node, list):
                for item in node:
                    find_tracks_in_apple_json(item, tracks_list)
                    
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"[APPLE MUSIC] HTTP Error {resp.status_code}")
                return None
                
            soup = bs4.BeautifulSoup(resp.text, 'html.parser')
            
            # Extract basic Open Graph metadata
            def get_og(prop):
                import re
                m = re.search(rf'<meta (?:name|property)="og:{prop}" content="([^"]+)"', resp.text)
                if not m:
                    m = re.search(rf'<meta (?:name|property)="apple:{prop}" content="([^"]+)"', resp.text)
                return m.group(1) if m else ''
                
            import html
            page_title = html.unescape(get_og('title') or 'Unknown Apple Music Item').replace('\xc2\xa0', ' ').replace('\u00a0', ' ')
            page_image = get_og('image') or ''
            
            # Remove " - Apple Music" or " - Single by ..."
            clean_title = page_title.split(' - Apple Music')[0].split(' on Apple Music')[0].split(' - Single by')[0].split(' - EP by')[0]
            
            # Try to get tracks
            script_tag = soup.find('script', id='serialized-server-data')
            raw_tracks = []
            if script_tag:
                data = json.loads(script_tag.get_text())
                find_tracks_in_apple_json(data, raw_tracks)
                
            # Filter and deduplicate
            seen = set()
            unique_tracks = []
            for t in raw_tracks:
                if 'Listen to' in t['title'] or t['title'] == page_title: continue
                key = f"{t['title']}_{t['artist']}"
                if key not in seen:
                    seen.add(key)
                    unique_tracks.append(t)
                    
            # If no tracks found, maybe it's a single track and we can use the page title
            if not unique_tracks:
                # "TrackName by Artist" is a common format in OpenGraph description
                desc = html.unescape(get_og('description') or '').replace('\xc2\xa0', ' ').replace('\u00a0', ' ')
                artist = 'Unknown Artist'
                if ' by ' in clean_title:
                    parts = clean_title.split(' by ')
                    clean_title = parts[0]
                    artist = parts[1]
                elif ' by ' in desc:
                    # Listen to X by Y on Apple Music.
                    parts = desc.split(' by ')
                    if len(parts) > 1:
                        artist = parts[1].split(' on Apple')[0].split('.')[0]
                
                unique_tracks.append({"title": clean_title.strip(), "artist": artist.strip()})
                
            entries = []
            for t in unique_tracks:
                entries.append({
                    'title': f"{t['artist']} - {t['title']}",
                    'fulltitle': t['title'],
                    'uploader': t['artist'],
                    'creator': t['artist'],
                    'channel': t['artist'],
                    'duration': 0,
                    'thumbnail': page_image,
                    'webpage_url': url,
                    'url': url,
                    'track': t['title'],
                    'artist': t['artist'],
                    'extractor_key': 'AppleMusic',
                    '_spotify': True,  # Treat as Spotify for 1:1 UI layout
                })
                
            if len(entries) == 0:
                return None
                
            if len(entries) == 1:
                return entries[0]
                
            return {
                '_type': 'playlist',
                'title': clean_title,
                'uploader': 'Apple Music',
                'thumbnail': page_image,
                'webpage_url': url,
                'entries': entries,
                '_spotify': True,
            }
            
        except Exception as e:
            print(f"[APPLE MUSIC ERROR] {e}")
            traceback.print_exc()
            return None

    def _get_tidal_info(self, url):
        try:
            import sys, os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scratch', 'SpotiFLAC'))
            from SpotiFLAC.providers.tidal_metadata import TidalMetadataClient
            client = TidalMetadataClient()
            collection_name, tracks = client.get_url(url)
            if not tracks:
                return None
            
            if len(tracks) == 1 and ('track' in url or 'track' in getattr(tracks[0], 'url', '')):
                t = tracks[0]
                return {
                    "id": getattr(t, 'track_id', getattr(t, 'id', '')),
                    "title": t.title,
                    "uploader": t.artists,
                    "thumbnail": t.cover_url,
                    "duration": getattr(t, 'duration', 0),
                    "is_audio_only": True,
                    "webpage_url": url,
                    "is_spotify": True
                }
            
            entries = []
            for t in tracks:
                entries.append({
                    "id": getattr(t, 'track_id', getattr(t, 'id', '')),
                    "title": t.title,
                    "uploader": t.artists,
                    "thumbnail": t.cover_url,
                    "duration": getattr(t, 'duration', 0),
                    "url": getattr(t, 'url', url),
                    "is_audio_only": True
                })
                
            return {
                "type": "playlist",
                "title": collection_name,
                "uploader": entries[0]["uploader"] if entries else "Tidal",
                "thumbnail": entries[0]["thumbnail"] if entries else None,
                "entries": entries,
                "webpage_url": url,
                "is_spotify": True
            }
        except Exception as e:
            print(f"[TIDAL] Error fetching info: {e}")
            return None

    def _get_deezer_info(self, url):
        import re
        import requests
        try:
            m = re.search(r'deezer\.com/(?:\w+/)?track/(\d+)', url)
            if m:
                tid = m.group(1)
                r = requests.get(f'https://api.deezer.com/track/{tid}').json()
                if 'error' in r: return None
                return {
                    "id": str(r.get('id', '')),
                    "title": r.get('title', 'Unknown'),
                    "uploader": r.get('artist', {}).get('name', 'Unknown'),
                    "thumbnail": r.get('album', {}).get('cover_xl', ''),
                    "duration": r.get('duration', 0),
                    "is_audio_only": True,
                    "webpage_url": url,
                    "is_spotify": True
                }
                
            m = re.search(r'deezer\.com/(?:\w+/)?album/(\d+)', url)
            if m:
                aid = m.group(1)
                r = requests.get(f'https://api.deezer.com/album/{aid}').json()
                if 'error' in r: return None
                entries = []
                for t in r.get('tracks', {}).get('data', []):
                    entries.append({
                        "id": str(t.get('id', '')),
                        "title": t.get('title', 'Unknown'),
                        "uploader": t.get('artist', {}).get('name', 'Unknown'),
                        "thumbnail": r.get('cover_xl', ''),
                        "duration": t.get('duration', 0),
                        "url": t.get('link', url),
                        "is_audio_only": True
                    })
                return {
                    "type": "playlist",
                    "title": r.get('title', 'Unknown'),
                    "uploader": r.get('artist', {}).get('name', 'Unknown'),
                    "thumbnail": r.get('cover_xl', ''),
                    "entries": entries,
                    "webpage_url": url,
                    "is_spotify": True
                }
                
            m = re.search(r'deezer\.com/(?:\w+/)?playlist/(\d+)', url)
            if m:
                pid = m.group(1)
                r = requests.get(f'https://api.deezer.com/playlist/{pid}').json()
                if 'error' in r: return None
                entries = []
                for t in r.get('tracks', {}).get('data', []):
                    entries.append({
                        "id": str(t.get('id', '')),
                        "title": t.get('title', 'Unknown'),
                        "uploader": t.get('artist', {}).get('name', 'Unknown'),
                        "thumbnail": t.get('album', {}).get('cover_xl', ''),
                        "duration": t.get('duration', 0),
                        "url": t.get('link', url),
                        "is_audio_only": True
                    })
                return {
                    "type": "playlist",
                    "title": r.get('title', 'Unknown'),
                    "uploader": r.get('creator', {}).get('name', 'Unknown'),
                    "thumbnail": r.get('picture_xl', ''),
                    "entries": entries,
                    "webpage_url": url,
                    "is_spotify": True
                }
        except Exception as e:
            print(f"[DEEZER] Error fetching info: {e}")
            return None
        return None



    def _get_gaana_info(self, url):
        import re
        import requests
        import json
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None

            m = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', resp.text)
            if not m:
                return None
            
            data = json.loads(m.group(1))
            
            entries = []
            playlist_title = "Gaana Playlist"
            playlist_thumbnail = None
            
            # Extract from different possible structures depending on URL type
            if 'song' in url and data.get('song'):
                song_data = data['song'].get('songDetail', {})
                tracks = song_data.get('tracks', [])
                if tracks and len(tracks) > 0:
                    t = tracks[0]
                    playlist_title = t.get('track_title', 'Gaana Track')
                    playlist_thumbnail = t.get('artwork_web') or t.get('artwork')
                    entries = [t]
            elif 'playlist' in url and data.get('playlist'):
                playlist_data = data['playlist'].get('playlistDetail', {})
                inner_playlist = playlist_data.get('playlist', {})
                playlist_title = inner_playlist.get('title') or playlist_data.get('title', 'Gaana Playlist')
                playlist_thumbnail = inner_playlist.get('artwork_web') or inner_playlist.get('artwork') or playlist_data.get('artwork_web') or playlist_data.get('artwork')
                entries = playlist_data.get('tracks', [])
            elif 'album' in url and data.get('album'):
                album_data = data['album'].get('albumDetail', {})
                inner_album = album_data.get('album', {})
                playlist_title = inner_album.get('title') or album_data.get('title', 'Gaana Album')
                playlist_thumbnail = inner_album.get('artwork_web') or inner_album.get('artwork') or album_data.get('artwork_web') or album_data.get('artwork')
                entries = album_data.get('tracks', [])
                if not entries:
                    entries = []

            results = []
            for t in entries:
                track_title = t.get('track_title')
                if not track_title:
                    continue
                
                artist = "Unknown Artist"
                if isinstance(t.get('artist'), list) and len(t['artist']) > 0:
                    artist = ", ".join([a.get('name', '') for a in t['artist']])
                elif isinstance(t.get('artist'), str):
                    artist = t['artist']
                    
                thumb = t.get('artwork_web') or t.get('artwork') or playlist_thumbnail
                duration = 0
                if t.get('duration'):
                    try: duration = int(t['duration'])
                    except: pass
                
                track_id = t.get('track_id', '')
                
                results.append({
                    "title": f"{artist} - {track_title}",
                    "fulltitle": track_title,
                    "uploader": artist,
                    "creator": artist,
                    "channel": artist,
                    "thumbnail": thumb,
                    "duration": duration,
                    "webpage_url": url,
                    "url": url,
                    "track": track_title,
                    "artist": artist,
                    "extractor_key": 'Gaana',
                    "_spotify": True, # Treat as Spotify to trigger Youtube search
                    "id": str(track_id)
                })
            
            if not results:
                return None
                
            if len(results) == 1:
                return results[0]
                
            return {
                '_type': 'playlist',
                'title': playlist_title,
                'uploader': 'Gaana',
                'thumbnail': playlist_thumbnail,
                'webpage_url': url,
                'entries': results,
                '_spotify': True,
            }
        except Exception as e:
            print(f"[GAANA] Error: {e}")
            return None

    def _get_lastfm_info(self, url):
        import requests
        import bs4
        import urllib.parse
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None

            soup = bs4.BeautifulSoup(resp.text, 'html.parser')
            
            # Extract common metadata
            title_el = soup.find('h1')
            main_title = title_el.text.strip() if title_el else "Last.fm Playlist"
            
            artist_el = soup.select('.header-new-crumb') or soup.select('.header-title a') or soup.select('.header-title')
            main_artist = artist_el[0].text.strip() if artist_el else "Unknown Artist"
            
            thumb_el = soup.select_one('.cover-art img')
            main_thumb = thumb_el['src'] if thumb_el and thumb_el.has_attr('src') else "https://via.placeholder.com/300"
            if main_thumb.startswith('/'):
                main_thumb = "https://www.last.fm" + main_thumb
            
            entries = []
            
            # Check for playlist/album tracks
            for row in soup.select('tr.chartlist-row'):
                playlink = row.select_one('.js-playlink')
                if playlink and playlink.get('data-track-name'):
                    track_name = playlink.get('data-track-name')
                    artist_name = playlink.get('data-artist-name') or main_artist
                    # Check for thumbnail inside row
                    row_img = row.select_one('img.cover-art') or row.select_one('img')
                    row_thumb = row_img['src'] if row_img and row_img.has_attr('src') else main_thumb
                    if row_thumb.startswith('/'):
                        row_thumb = "https://www.last.fm" + row_thumb
                    
                    entries.append({
                        "title": f"{artist_name} - {track_name}",
                        "fulltitle": track_name,
                        "uploader": artist_name,
                        "creator": artist_name,
                        "channel": artist_name,
                        "thumbnail": row_thumb,
                        "duration": 0,
                        "webpage_url": url,
                        "url": url,
                        "track": track_name,
                        "artist": artist_name,
                        "extractor_key": 'LastFM',
                        "_spotify": True,
                        "id": track_name
                    })
                    
            if entries:
                return {
                    '_type': 'playlist',
                    'title': main_title,
                    'uploader': main_artist,
                    'thumbnail': main_thumb,
                    'webpage_url': url,
                    'entries': entries,
                    '_spotify': True,
                }
            
            # Single track fallback
            return {
                "title": f"{main_artist} - {main_title}",
                "fulltitle": main_title,
                "uploader": main_artist,
                "creator": main_artist,
                "channel": main_artist,
                "thumbnail": main_thumb,
                "duration": 0,
                "webpage_url": url,
                "url": url,
                "track": main_title,
                "artist": main_artist,
                "extractor_key": 'LastFM',
                "_spotify": True,
                "id": main_title
            }
        except Exception as e:
            print(f"[LASTFM] Error: {e}")
            return None

    # ──────────────────────────────────────────────────────────────
    #  YouTube Music search (replaces spotdl)
    # ──────────────────────────────────────────────────────────────
    _ytmusic_instance = None
    _ytmusic_lock = threading.Lock()

    @classmethod
    def _get_ytmusic(cls):
        """Lazy-initialise a single YTMusic instance (thread-safe)."""
        if cls._ytmusic_instance is None:
            with cls._ytmusic_lock:
                if cls._ytmusic_instance is None:
                    from ytmusicapi import YTMusic
                    cls._ytmusic_instance = YTMusic()
        return cls._ytmusic_instance

    @classmethod
    def _search_ytmusic(cls, track_name, artist, duration_s=None):
        """Search YouTube Music for a matching track. Returns a youtube URL or None."""
        ytm = cls._get_ytmusic()
        query = f"{artist} - {track_name}"
        try:
            results = ytm.search(query, filter="songs", limit=5)
        except Exception:
            # Fallback: unfiltered search
            try:
                results = ytm.search(query, limit=10)
            except Exception as ex:
                print(f"[YTM SEARCH] Failed for '{query}': {ex}")
                return None

        if not results:
            return None

        # Pick best match — prefer close duration if available
        best = None
        best_diff = float('inf')
        for r in results:
            vid = r.get('videoId')
            if not vid:
                continue
            if duration_s and r.get('duration_seconds'):
                diff = abs(r['duration_seconds'] - duration_s)
                if diff < best_diff:
                    best_diff = diff
                    best = vid
            elif not best:
                best = vid

        if best:
            return f"https://music.youtube.com/watch?v={best}"
        return None

    def start_download(self, url, format_id, output_path, is_audio=False, 
                       video_ext=None, audio_codec=None, audio_quality=None,
                       settings=None, on_progress=None, on_finish=None, on_error=None,
                       embed_thumbnail=None, embed_subtitles=None, subtitle_lang=None,
                       custom_filename=None, info=None, is_image=False, image_ext=None, is_thumbnail=False, on_log=None):
        task_id = str(uuid.uuid4())
        self.active_tasks[task_id] = False
        final_downloaded_file = None

        final_downloaded_file = None

        if is_thumbnail:
            def download_thumb_task():
                import requests
                import re
                try:
                    if self.active_tasks.get(task_id, False):
                        if on_error: on_error("Cancelled")
                        return

                    thumb_url = info.get('thumbnail') if info else None
                    if not thumb_url and info and info.get('thumbnails'):
                        thumb_url = info['thumbnails'][0]['url']
                    
                    if not thumb_url:
                        if on_error: on_error("No thumbnail found")
                        return

                    title = info.get('title', 'Thumbnail') if info else 'Thumbnail'
                    title = re.sub(r'[\\/*?:"<>|]', "", title)
                    
                    if custom_filename:
                        ext = thumb_url.split('.')[-1].split('?')[0]
                        if len(ext) > 4 or not ext.isalnum(): ext = 'jpg'
                        final_name = custom_filename.replace('%(ext)s', ext).replace('%(title)s', title)
                    else:
                        ext = thumb_url.split('.')[-1].split('?')[0]
                        if len(ext) > 4 or not ext.isalnum(): ext = 'jpg'
                        
                        # Settings template fallback
                        tmpl = settings.get('filename_template', '%(title)s.%(ext)s') if settings else '%(title)s.%(ext)s'
                        final_name = tmpl.replace('%(title)s', title).replace('%(ext)s', ext)

                    final_path = os.path.join(output_path, final_name)
                    
                    if on_progress:
                        on_progress({'percent': 50, 'speed': '', 'eta': '', 'downloaded_bytes': 0, 'total_bytes': 0, 'filename': final_name, 'status': 'downloading'})
                    
                    r = requests.get(thumb_url, timeout=15)
                    r.raise_for_status()
                    
                    if self.active_tasks.get(task_id, False):
                        if on_error: on_error("Cancelled")
                        return
                        
                    with open(final_path, 'wb') as f:
                        f.write(r.content)
                        
                    if on_progress:
                        on_progress({'percent': 100, 'speed': '', 'eta': '', 'downloaded_bytes': len(r.content), 'total_bytes': len(r.content), 'filename': final_name, 'status': 'finished'})
                        
                    if on_finish:
                        on_finish(final_path)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    if on_error: on_error(str(e))
                finally:
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
                        
            if self.run_thread:
                self.run_thread(download_thumb_task)
            else:
                threading.Thread(target=download_thumb_task, daemon=True).start()
            return task_id

        # Route Spotify, Apple Music, Tidal, Deezer, Gaana, Last.fm to ytmusicapi fallback
        if (self.is_spotify_url(url) or self.is_applemusic_url(url) or 
            self.is_tidal_url(url) or self.is_deezer_url(url) or
            self.is_gaana_url(url) or self.is_lastfm_url(url)):
            def audio_fallback_task():
                self._download_audio_fallback(
                    task_id, url, output_path, audio_codec, audio_quality,
                    settings, on_progress, on_finish, on_error,
                    embed_thumbnail=embed_thumbnail, custom_filename=custom_filename,
                    info=info, on_log=on_log
                )
            if self.run_thread:
                self.run_thread(audio_fallback_task)
            else:
                threading.Thread(target=audio_fallback_task, daemon=True).start()
            return task_id
            

        def _progress_hook(d):
            nonlocal final_downloaded_file
            if self.active_tasks.get(task_id, False):
                raise Exception("Download cancelled by user")
                
            if d['status'] == 'downloading':
                import re
                ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
                percent_str = ansi_escape.sub('', d.get('_percent_str', '0.0%')).replace('%', '').strip()
                try:
                    percent = float(percent_str)
                except:
                    percent = 0.0
                    
                speed_str = ansi_escape.sub('', d.get('_speed_str', 'N/A')).strip()
                if len(speed_str) > 50 or '\\n' in speed_str or ' -i ' in speed_str or 'Sec-Fetch-Mode' in speed_str:
                    speed_str = 'Recording...'
                    
                eta_str = ansi_escape.sub('', d.get('_eta_str', 'N/A')).strip()
                if len(eta_str) > 50 or '\\n' in eta_str or ' -i ' in eta_str or 'Sec-Fetch-Mode' in eta_str:
                    eta_str = 'Live'
                try: downloaded_bytes = int(d.get('downloaded_bytes') or 0)
                except: downloaded_bytes = 0
                
                # Fallback: Check physical file size if yt-dlp/ffmpeg didn't report it
                if downloaded_bytes == 0 and d.get('filename'):
                    try:
                        import os
                        if os.path.exists(d['filename']):
                            downloaded_bytes = os.path.getsize(d['filename'])
                    except:
                        pass
                        
                try: total_bytes = int(d.get('total_bytes') or d.get('total_bytes_estimate') or 0)
                except: total_bytes = 0
                
                if on_progress:
                    on_progress({
                        'percent': percent,
                        'speed': speed_str,
                        'eta': eta_str,
                        'downloaded_bytes': downloaded_bytes,
                        'total_bytes': total_bytes,
                        'filename': d.get('filename', '')
                    })
            elif d['status'] == 'finished':
                # Capture the final filename (may be overridden by postprocessor hook)
                nonlocal final_downloaded_file
                if d.get('info_dict', {}).get('_filename'):
                    final_downloaded_file = d['info_dict']['_filename']
                elif d.get('filename'):
                    final_downloaded_file = d['filename']
                
        def _pp_hook(d):
            nonlocal final_downloaded_file
            if d['status'] in ['started', 'processing']:
                if on_progress:
                    on_progress({
                        'percent': 100,
                        'speed': '',
                        'eta': '',
                        'downloaded_bytes': 0,
                        'total_bytes': 0,
                        'filename': '',
                        'status': 'processing'
                    })
            elif d['status'] == 'finished':
                if d.get('info_dict', {}).get('filepath'):
                    final_downloaded_file = d['info_dict']['filepath']
                elif d.get('info_dict', {}).get('_filename'):
                    final_downloaded_file = d['info_dict']['_filename']
                elif d.get('filepath'):
                    final_downloaded_file = d['filepath']
                
        def download_task():
            thread_local.task_id = task_id
            
            def ffmpeg_cb(secs=None, size_bytes=0, speed_str="", raw_line=None):
                if self.active_tasks.get(task_id, False):
                    raise Exception("Download cancelled by user")
                    
                if raw_line and on_log and ('frame=' in raw_line or 'size=' in raw_line or 'speed=' in raw_line):
                    # Filter out the Sec-Fetch-Mode garbage just in case it slips in
                    if 'Sec-Fetch-Mode' not in raw_line and len(raw_line) < 200:
                        on_log(raw_line)
                
                if on_progress:
                    # If size is 0, try to check the physical .part file
                    if size_bytes == 0:
                        try:
                            # We don't have the exact part filename easily accessible here, 
                            # but we can try the final filename + .part
                            if final_downloaded_file and os.path.exists(final_downloaded_file + '.part'):
                                size_bytes = os.path.getsize(final_downloaded_file + '.part')
                            # Also check output_path for .part files matching the title
                            elif info and info.get('title'):
                                title = info['title']
                                for f in os.listdir(output_path):
                                    if f.endswith('.part') and title[:10] in f:
                                        size_bytes = os.path.getsize(os.path.join(output_path, f))
                                        break
                        except: pass
                        
                    duration = info.get('duration', 0) if info else 0
                    if duration > 0 and secs is not None:
                        pct = min(100.0, (secs / duration) * 100.0)
                        on_progress({
                            'percent': round(pct, 1),
                            'speed': speed_str,
                            'eta': '',
                            'downloaded_bytes': size_bytes,
                            'total_bytes': 100,
                            'filename': '',
                            'status': 'processing',
                            'elapsed_secs': secs
                        })
                    else:
                        on_progress({
                            'percent': 0,
                            'speed': speed_str,
                            'eta': 'Live',
                            'downloaded_bytes': size_bytes,
                            'total_bytes': 0,
                            'filename': '',
                            'status': 'downloading',
                            'elapsed_secs': secs
                        })
            thread_local.ffmpeg_progress_cb = ffmpeg_cb

            # Build filename template — per-download custom_filename overrides settings
            if custom_filename:
                filename_template = custom_filename
            else:
                filename_template = '%(title)s.%(ext)s'
                if settings:
                    filename_template = settings.get('filename_template', filename_template)

            nonlocal final_downloaded_file
            final_downloaded_file = None

            class YtdlLogger:
                def debug(self, msg):
                    if on_log: on_log(msg)
                def warning(self, msg):
                    if on_log: on_log(f"WARNING: {msg}")
                def error(self, msg):
                    if on_log: on_log(f"ERROR: {msg}")

            from src.backend.ffmpeg_manager import get_ffmpeg_path
            
            ydl_opts = {
                'format': format_id,
                'outtmpl': {'default': filename_template},
                'paths': {'home': output_path},
                'progress_hooks': [_progress_hook],
                'postprocessor_hooks': [_pp_hook],
                'logger': YtdlLogger(),
                'quiet': True,
                'verbose': True,
                'noprogress': False,
                'no_warnings': False,
                'noplaylist': True,
                'ffmpeg_location': get_ffmpeg_path(),
                'js_runtimes': {
                    'node': {},
                    'deno': {},
                    'bun': {},
                    'quickjs': {},
                },
                'remote_components': ['ejs:github'],
            }

            if settings:
                temp_path = settings.get('temp_download_path')
                if temp_path and os.path.exists(temp_path):
                    ydl_opts['paths']['temp'] = temp_path
                    
                cookies_path = settings.get('cookies_path')
                browser_cookies = settings.get('browser_cookies', 'none')
                
                if cookies_path and os.path.exists(cookies_path):
                    ydl_opts['cookiefile'] = cookies_path
                elif browser_cookies and browser_cookies != 'none':
                    ydl_opts['cookiesfrombrowser'] = (browser_cookies, )

            if video_ext and not is_audio and not is_image:
                ydl_opts['merge_output_format'] = video_ext

            # Speed limit
            if settings:
                speed_limit = settings.get('speed_limit', 0)
                if speed_limit and speed_limit > 0:
                    ydl_opts['ratelimit'] = speed_limit

            postprocessors = []

            if is_audio:
                final_audio_codec = audio_codec or (settings.get('audio_codec', 'mp3') if settings else 'mp3')
                final_audio_quality = audio_quality or (settings.get('audio_quality', '192') if settings else '192')
                
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': final_audio_codec,
                    'preferredquality': final_audio_quality,
                })

            # Embed thumbnail — per-download override takes priority over settings
            should_embed_thumb = embed_thumbnail if embed_thumbnail is not None else (
                settings.get('embed_thumbnail', False) if settings else False
            )
            
            # Disable thumbnail embedding for WAV since ffmpeg doesn't support it
            if should_embed_thumb and is_audio and final_audio_codec == 'wav':
                should_embed_thumb = False
                
            if should_embed_thumb:
                ydl_opts['writethumbnail'] = True
                if not is_audio:
                    # Only force MKV for formats that don't support thumbnail embedding (webm)
                    # MP4, MKV, etc. natively support embedded thumbnails
                    current_format = ydl_opts.get('merge_output_format', video_ext or '').lower()
                    if current_format in ('webm', '') or not current_format:
                        ydl_opts['merge_output_format'] = 'mkv'
                        postprocessors.append({
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': 'mkv',
                        })
                postprocessors.append({'key': 'EmbedThumbnail'})

            # Embed subtitles — per-download override takes priority over settings
            should_embed_subs = embed_subtitles if embed_subtitles is not None else (
                settings.get('embed_subtitles', False) if settings else False
            )
            if should_embed_subs:
                lang = subtitle_lang or (settings.get('auto_subtitle_lang', 'en') if settings else 'en')
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = [lang]
                postprocessors.append({'key': 'FFmpegEmbedSubtitle'})

            # Embed metadata
            should_embed_metadata = settings.get('embed_metadata', True) if settings else True
            ydl_opts.setdefault('external_downloader_args', {})
            if 'ffmpeg' not in ydl_opts['external_downloader_args']:
                ydl_opts['external_downloader_args']['ffmpeg'] = []
            ydl_opts['external_downloader_args']['ffmpeg'].extend(['-loglevel', 'info'])

            if should_embed_metadata:
                postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                
                ydl_opts.setdefault('postprocessor_args', {})
                if 'ffmpeg' not in ydl_opts['postprocessor_args']:
                    ydl_opts['postprocessor_args']['ffmpeg'] = []
                
                # Windows File Explorer doesn't support the default ID3v2.4 tags for mp3s, so we force ID3v2.3
                if is_audio and final_audio_codec == 'mp3':
                    ydl_opts['postprocessor_args']['ffmpeg'].extend(['-id3v2_version', '3'])
                
                # If part of a playlist, inject the track number manually since it's a standalone download
                if info and info.get('playlist_index'):
                    ydl_opts['postprocessor_args']['ffmpeg'].extend(['-metadata', f'track={info["playlist_index"]}'])

            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors

            try:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        error_code = ydl.download([url])
                except Exception as e:
                    yt_err_str = str(e).lower()
                    if "cookie" in yt_err_str and ("could not copy" in yt_err_str or "permission" in yt_err_str or "locked" in yt_err_str):
                        raise Exception(f"Failed to access {browser_cookies} cookies. Please close your browser completely and try again, or export a cookies.txt file.")
                    raise e
                    
                if is_image and image_ext and final_downloaded_file and os.path.exists(final_downloaded_file):
                    # Convert image using FFmpeg if needed
                    import subprocess
                    
                    downloaded_file = final_downloaded_file
                    current_ext = os.path.splitext(downloaded_file)[1].lstrip('.').lower()
                    
                    if current_ext != image_ext:
                        base_path = os.path.splitext(downloaded_file)[0]
                        target_file = f"{base_path}.{image_ext}"
                        try:
                            ffmpeg_exe = 'ffmpeg'
                            local_dir = get_ffmpeg_path()
                            if local_dir:
                                ffmpeg_exe = os.path.join(local_dir, 'ffmpeg.exe')
                            
                            subprocess.run([
                                ffmpeg_exe, '-y', '-i', downloaded_file, target_file
                            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                            os.remove(downloaded_file)
                        except Exception as ex:
                            print(f"[IMAGE CONVERT ERROR] {ex}")

                if on_finish:
                    on_finish(final_downloaded_file)
            except Exception as e:
                if str(e) == "Download cancelled by user" or self.active_tasks.get(task_id, False):
                    if on_error:
                        on_error("Cancelled")
                else:
                    import traceback
                    traceback.print_exc()
                    if on_error:
                        on_error(str(e))
            finally:
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                        
        if self.run_thread:
            self.run_thread(download_task)
        else:
            threading.Thread(target=download_task, daemon=True).start()
            
        return task_id

    def _download_audio_fallback(self, task_id, url, output_path, audio_codec, audio_quality,
                          settings, on_progress, on_finish, on_error,
                          embed_thumbnail=None, custom_filename=None, info=None, on_log=None):
        """Download a Spotify/Apple Music track via ytmusicapi search + yt-dlp."""
        try:
            # Check for cancellation
            if self.active_tasks.get(task_id, False):
                if on_error:
                    on_error("Cancelled")
                return

            # ── Step 1: Resolve track metadata ──
            track_name = None
            artist = None
            duration_s = None
            if info:
                track_name = info.get('track') or info.get('fulltitle') or info.get('title')
                artist = info.get('artist') or info.get('uploader') or info.get('creator', '')
                duration_s = info.get('duration')
            
            if not track_name or not artist:
                # Fallback: fetch metadata from Spotify/Apple Music
                if self.is_spotify_url(url):
                    stype, sid = self._parse_spotify_url(url)
                    if stype == 'track' and sid:
                        data = self._spotify_api_get(f"tracks/{sid}")
                        if data:
                            track_name = data.get('name', '')
                            artist = ', '.join(a['name'] for a in data.get('artists', []))
                            duration_s = (data.get('duration_ms', 0) / 1000) if data.get('duration_ms') else None
                elif self.is_applemusic_url(url):
                    apple_info = self._get_applemusic_info(url)
                    if apple_info:
                        if apple_info.get('_type') == 'playlist':
                            apple_info = apple_info.get('entries', [{}])[0]
                        track_name = apple_info.get('track') or apple_info.get('fulltitle') or apple_info.get('title')
                        artist = apple_info.get('artist') or apple_info.get('uploader', '')
                elif self.is_tidal_url(url):
                    tidal_info = self._get_tidal_info(url)
                    if tidal_info:
                        if tidal_info.get('type') == 'playlist':
                            tidal_info = tidal_info.get('entries', [{}])[0]
                        track_name = tidal_info.get('title')
                        artist = tidal_info.get('uploader')
                        duration_s = tidal_info.get('duration')
                elif self.is_deezer_url(url):
                    deezer_info = self._get_deezer_info(url)
                    if deezer_info:
                        if deezer_info.get('type') == 'playlist':
                            deezer_info = deezer_info.get('entries', [{}])[0]
                        track_name = deezer_info.get('title')
                        artist = deezer_info.get('uploader')
                        duration_s = deezer_info.get('duration')

            if not track_name:
                if on_error:
                    on_error("Could not resolve audio track metadata")
                return

            # ── Step 2: Search YouTube Music ──
            if on_progress:
                on_progress({
                    'percent': 5,
                    'speed': '',
                    'eta': 'Searching YouTube Music...',
                    'downloaded_bytes': 0,
                    'total_bytes': 0,
                    'filename': ''
                })

            yt_url = self._search_ytmusic(track_name, artist, duration_s)
            if not yt_url:
                if on_error:
                    on_error(f"No YouTube Music match for '{artist} - {track_name}'")
                return

            if self.active_tasks.get(task_id, False):
                if on_error:
                    on_error("Cancelled")
                return

            if on_progress:
                on_progress({
                    'percent': 15,
                    'speed': '',
                    'eta': 'Match found, downloading...',
                    'downloaded_bytes': 0,
                    'total_bytes': 0,
                    'filename': ''
                })

            thread_local.task_id = task_id
            def ffmpeg_cb(secs):
                if on_progress:
                    duration = duration_s or 0
                    if duration > 0:
                        pct = min(100.0, (secs / duration) * 100.0)
                        on_progress({
                            'percent': round(pct, 1),
                            'speed': '',
                            'eta': '',
                            'downloaded_bytes': 0,
                            'total_bytes': 100,
                            'filename': '',
                            'status': 'processing'
                        })
            thread_local.ffmpeg_progress_cb = ffmpeg_cb

            # ── Step 3: Download via yt-dlp ──
            fmt = audio_codec or (settings.get('audio_codec', 'mp3') if settings else 'mp3')
            bitrate = audio_quality or (settings.get('audio_quality', '192') if settings else '192')

            # Build filename — use Spotify metadata for a clean name
            if custom_filename:
                filename_template = custom_filename
            else:
                filename_template = settings.get('filename_template', '%(title)s.%(ext)s') if settings else '%(title)s.%(ext)s'

            final_downloaded_file = None

            def _progress_hook(d):
                nonlocal final_downloaded_file
                if self.active_tasks.get(task_id, False):
                    raise Exception("Download cancelled by user")
                if d['status'] == 'finished':
                    if d.get('info_dict', {}).get('_filename'):
                        final_downloaded_file = d['info_dict']['_filename']
                    elif d.get('filename'):
                        final_downloaded_file = d['filename']
                elif d['status'] == 'downloading':
                    import re
                    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
                    percent_str = ansi_escape.sub('', d.get('_percent_str', '0.0%')).replace('%', '').strip()
                    try:
                        percent = float(percent_str)
                    except:
                        percent = 0.0
                    # Scale to 15-95 range (first 15% was search)
                    scaled = 15 + percent * 0.80
                    speed_str = ansi_escape.sub('', d.get('_speed_str', 'N/A')).strip()
                    eta_str = ansi_escape.sub('', d.get('_eta_str', 'N/A')).strip()
                    if on_progress:
                        on_progress({
                            'percent': round(scaled, 1),
                            'speed': speed_str,
                            'eta': eta_str,
                            'downloaded_bytes': d.get('downloaded_bytes', 0),
                            'total_bytes': d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0),
                            'filename': d.get('filename', '')
                        })
                        
            def _pp_hook(d):
                nonlocal final_downloaded_file
                if d['status'] in ['started', 'processing']:
                    if on_progress:
                        on_progress({
                            'percent': 100,
                            'speed': '',
                            'eta': '',
                            'downloaded_bytes': 0,
                            'total_bytes': 0,
                            'filename': '',
                            'status': 'processing'
                        })
                elif d['status'] == 'finished':
                    if d.get('info_dict', {}).get('filepath'):
                        final_downloaded_file = d['info_dict']['filepath']
                    elif d.get('info_dict', {}).get('_filename'):
                        final_downloaded_file = d['info_dict']['_filename']
                    elif d.get('filepath'):
                        final_downloaded_file = d['filepath']

            class YtdlLogger:
                def debug(self, msg):
                    if on_log: on_log(msg)
                def warning(self, msg):
                    if on_log: on_log(f"WARNING: {msg}")
                def error(self, msg):
                    if on_log: on_log(f"ERROR: {msg}")

            from src.backend.ffmpeg_manager import get_ffmpeg_path
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': {'default': filename_template},
                'paths': {'home': output_path},
                'progress_hooks': [_progress_hook],
                'postprocessor_hooks': [_pp_hook],
                'logger': YtdlLogger(),
                'quiet': True,
                'verbose': True,
                'noprogress': False,
                'no_warnings': False,
                'nocheckcertificate': True,
                'noplaylist': True,
                'ffmpeg_location': get_ffmpeg_path(),
                'js_runtimes': {
                    'node': {},
                    'deno': {},
                    'bun': {},
                    'quickjs': {},
                },
                'remote_components': ['ejs:github'],
            }

            if settings:
                temp_path = settings.get('temp_download_path')
                if temp_path and os.path.exists(temp_path):
                    ydl_opts['paths']['temp'] = temp_path
                    
                cookies_path = settings.get('cookies_path')
                browser_cookies = settings.get('browser_cookies', 'none')
                
                if cookies_path and os.path.exists(cookies_path):
                    ydl_opts['cookiefile'] = cookies_path
                elif browser_cookies and browser_cookies != 'none':
                    ydl_opts['cookiesfrombrowser'] = (browser_cookies, )

            # Speed limit
            if settings:
                speed_limit = settings.get('speed_limit', 0)
                if speed_limit and speed_limit > 0:
                    ydl_opts['ratelimit'] = speed_limit

            postprocessors = []
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': fmt,
                'preferredquality': bitrate,
            })

            # Embed thumbnail
            should_embed_thumb = embed_thumbnail if embed_thumbnail is not None else (
                settings.get('embed_thumbnail', False) if settings else False
            )
            
            # Disable thumbnail embedding for WAV since ffmpeg doesn't support it
            if should_embed_thumb and fmt == 'wav':
                should_embed_thumb = False
                
            if should_embed_thumb:
                ydl_opts['writethumbnail'] = True
                postprocessors.append({'key': 'EmbedThumbnail'})

            ydl_opts['postprocessors'] = postprocessors

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
            except Exception as e:
                yt_err_str = str(e).lower()
                if "cookie" in yt_err_str and ("could not copy" in yt_err_str or "permission" in yt_err_str or "locked" in yt_err_str):
                    raise Exception(f"Failed to access {browser_cookies} cookies. Please close your browser completely and try again, or export a cookies.txt file.")
                raise e

            if on_finish:
                on_finish(final_downloaded_file)

        except Exception as e:
            if str(e) == "Download cancelled by user":
                if on_error:
                    on_error("Cancelled")
            else:
                import traceback
                traceback.print_exc()
                if on_error:
                    on_error(str(e))
        finally:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def _download_amazon_spotiflac(self, task_id, url, output_path, settings, 
                                   on_progress, on_finish, on_error, custom_filename=None, info=None, on_log=None):
        try:
            if self.active_tasks.get(task_id, False):
                if on_error:
                    on_error("Cancelled")
                return

            import sys
            import os
            import re
            
            spotiflac_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scratch', 'SpotiFLAC')
            if spotiflac_path not in sys.path:
                sys.path.append(spotiflac_path)
                
            from SpotiFLAC.providers.amazon import AmazonProvider

            provider = AmazonProvider()

            def progress_cb(downloaded, total):
                if self.active_tasks.get(task_id, False):
                    raise Exception("Download cancelled by user")
                if on_progress:
                    percent = (downloaded / total * 100) if total else 0
                    on_progress({
                        'percent': round(percent, 1),
                        'speed': '',
                        'eta': '',
                        'downloaded_bytes': downloaded,
                        'total_bytes': total,
                        'filename': 'Downloading from Amazon...'
                    })
            
            provider.set_progress_callback(progress_cb)

            if on_progress:
                on_progress({
                    'percent': 5,
                    'speed': '',
                    'eta': 'Starting Amazon download via SpotiFLAC...',
                    'downloaded_bytes': 0,
                    'total_bytes': 0,
                    'filename': ''
                })

            quality = settings.get('audio_quality', 'flac') if settings else 'flac'
            
            downloaded_file, api_meta = provider._download_from_api(url, output_path, quality)
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                if on_error:
                    on_error("Failed to download from Amazon API.")
                return

            if custom_filename or info:
                ext = os.path.splitext(downloaded_file)[1]
                
                if custom_filename:
                    final_name = custom_filename.replace('%(ext)s', ext[1:])
                else:
                    title = info.get('title') if info else 'Amazon Music Track'
                    # clean title for filename
                    title = re.sub(r'[\\/*?:"<>|]', "", title)
                    final_name = f"{title}{ext}"
                    
                new_path = os.path.join(output_path, final_name)
                
                if os.path.abspath(downloaded_file) != os.path.abspath(new_path):
                    if os.path.exists(new_path):
                        os.remove(new_path)
                    os.rename(downloaded_file, new_path)
                    downloaded_file = new_path

            if on_finish:
                on_finish(downloaded_file)

        except Exception as e:
            if str(e) == "Download cancelled by user":
                if on_error:
                    on_error("Cancelled")
            else:
                import traceback
                traceback.print_exc()
                if on_error:
                    on_error(str(e))
        finally:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def cancel_download(self, task_id):
        if task_id in self.active_tasks:
            self.active_tasks[task_id] = True
