import yt_dlp
import threading
import os
import uuid
import subprocess
import json
import tempfile
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
import time

_original_os_replace = os.replace
_original_os_rename = os.rename

def _patched_os_replace(src, dst, *args, **kwargs):
    if src == dst:
        return
    for _ in range(30):
        try:
            return _original_os_replace(src, dst, *args, **kwargs)
        except OSError as e:
            if getattr(e, 'winerror', None) == 32:
                time.sleep(0.1)
                continue
            raise
    return _original_os_replace(src, dst, *args, **kwargs)

def _patched_os_rename(src, dst, *args, **kwargs):
    if src == dst:
        return
    for _ in range(30):
        try:
            return _original_os_rename(src, dst, *args, **kwargs)
        except OSError as e:
            if getattr(e, 'winerror', None) == 32:
                time.sleep(0.1)
                continue
            raise
    return _original_os_rename(src, dst, *args, **kwargs)

os.replace = _patched_os_replace
os.rename = _patched_os_rename

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

# Fix for WinError 2 in yt-dlp when thumbnail file is missing
from yt_dlp.postprocessor.ffmpeg import FFmpegThumbnailsConvertorPP
_original_thumbnail_run = FFmpegThumbnailsConvertorPP.run

def _patched_thumbnail_run(self, info):
    thumbnails = info.get('thumbnails')
    if thumbnails:
        valid_thumbnails = []
        for t in thumbnails:
            filepath = t.get('filepath')
            if filepath and os.path.exists(filepath):
                # Fix mismatched extension for images (e.g. JPG data inside .png file)
                try:
                    with open(filepath, 'rb') as f:
                        header = f.read(12)
                    real_ext = None
                    if header.startswith(b'\xff\xd8\xff'):
                        real_ext = '.jpg'
                    elif header.startswith(b'\x89PNG\r\n\x1a\n'):
                        real_ext = '.png'
                    elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
                        real_ext = '.gif'
                    elif header[0:4] == b'RIFF' and header[8:12] == b'WEBP':
                        real_ext = '.webp'
                        
                    if real_ext:
                        current_ext = os.path.splitext(filepath)[1].lower()
                        if current_ext == '.jpeg': current_ext = '.jpg'
                        
                        if real_ext != current_ext:
                            new_filepath = os.path.splitext(filepath)[0] + real_ext
                            import shutil
                            shutil.move(filepath, new_filepath)
                            t['filepath'] = new_filepath
                            try: self.write_debug(f"Fixed mismatched thumbnail extension: {filepath} -> {new_filepath}")
                            except: pass
                except Exception as e:
                    try: self.write_debug(f"Error checking thumbnail header: {e}")
                    except: pass
                    
                valid_thumbnails.append(t)
            else:
                try: self.write_debug(f"Missing thumbnail removed to prevent WinError 2: {filepath}")
                except: pass
        info['thumbnails'] = valid_thumbnails
        
    try:
        return _original_thumbnail_run(self, info)
    except Exception as e:
        try: self.write_debug(f"FFmpegThumbnailsConvertorPP failed but continuing to prevent crash: {e}")
        except: pass
        return [], info

FFmpegThumbnailsConvertorPP.run = _patched_thumbnail_run

# Force yt-dlp to use FFmpeg instead of mutagen for MP4 video thumbnails so Windows File Explorer displays them
from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP
import yt_dlp.postprocessor.embedthumbnail as embedthumbnail_mod

_original_embed_run = EmbedThumbnailPP.run

def _patched_embed_run(self, info):
    is_video = info.get('ext') in ['mp4', 'm4v', 'mov'] and info.get('vcodec') != 'none'
    orig_mutagen = getattr(embedthumbnail_mod, 'mutagen', None)
    
    if is_video and orig_mutagen:
        embedthumbnail_mod.mutagen = None  # Force ffmpeg fallback for video
        
    try:
        return _original_embed_run(self, info)
    finally:
        if is_video and orig_mutagen:
            embedthumbnail_mod.mutagen = orig_mutagen

EmbedThumbnailPP.run = _patched_embed_run

def patched_init(self, *args, **kwargs):
    if args and len(args) > 0 and isinstance(args[0], list):
        cmd = args[0]
        if _is_ffmpeg_conversion(cmd):
            if 'stderr' not in kwargs or kwargs['stderr'] is None:
                kwargs['stderr'] = subprocess.PIPE
    if sys.platform == "win32":
        creationflags = kwargs.get('creationflags', 0)
        creationflags |= subprocess.CREATE_NO_WINDOW
        kwargs['creationflags'] = creationflags
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

    @staticmethod
    def is_9anime_url(url):
        import re
        return bool(re.search(r'9anime\.', url))

    @staticmethod
    def is_anime8_url(url):
        import re
        return bool(re.search(r'anime8\.', url))

    @staticmethod
    def is_animeflv_url(url):
        import re
        return bool(re.search(r'animeflv\.', url))

    @staticmethod
    def is_kissanime_url(url):
        import re
        return bool(re.search(r'kissanime\.', url))

    @staticmethod
    def is_zorotv_url(url):
        import re
        return bool(re.search(r'zorotv\.', url))

    @staticmethod
    def is_yummyani_url(url):
        import re
        return bool(re.search(r'yummyani\.me', url))

    def _get_yummyani_info(self, url, settings=None):
        import re
        import json
        from bs4 import BeautifulSoup
        try:
            from curl_cffi import requests as crequests
            req_kwargs = {"impersonate": "chrome120"}
        except ImportError:
            import requests as crequests
            req_kwargs = {}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://old.yummyani.me/"
        }

        print(f"[YummyAnime] Fetching {url}")
        res = crequests.get(url, headers=headers, **req_kwargs)
        soup = BeautifulSoup(res.text, 'html.parser')

        title_tag = soup.find('h1')
        title = title_tag.text.strip() if title_tag else "YummyAnime Video"

        poster = soup.find('img', class_='big-poster')
        thumbnail = poster.get('src') if poster else None
        if thumbnail and thumbnail.startswith('//'):
            thumbnail = 'https:' + thumbnail

        page_id_meta = soup.find('meta', {'id': 'page_id'})
        page_id = page_id_meta.get('content') if page_id_meta else None

        if not page_id:
            rating_div = soup.find(class_='rating-info')
            if rating_div:
                page_id = rating_div.get('data-id')

        if not page_id:
            print("[YummyAnime] Error: Could not find page_id")
            raise Exception("Could not find page_id on YummyAnime")

        print(f"[YummyAnime] Found title: {title}, page_id: {page_id}")

        domain = re.search(r'(https?://[^/]+)', url).group(1)
        player_html = None

        # Probing common AnimeGo / YummyAnime AJAX endpoints
        endpoints_to_try = [
            f"{domain}/api/anime/video?id={page_id}",
            f"{domain}/ajax/anime/video?id={page_id}",
            f"{domain}/anime/{page_id}/player?_allow=true",
            f"{domain}/api/video/{page_id}",
        ]

        for ep_url in endpoints_to_try:
            try:
                print(f"[YummyAnime] Probing {ep_url}")
                ep_res = crequests.get(ep_url, headers=headers, **req_kwargs)
                if ep_res.status_code == 200:
                    if 'json' in ep_res.headers.get('content-type', '').lower():
                        data = ep_res.json()
                        if 'content' in data:
                            player_html = data['content']
                            break
                    elif '<iframe' in ep_res.text or 'player' in ep_res.text:
                        player_html = ep_res.text
                        break
            except Exception as e:
                print(f"[YummyAnime] Probe failed: {e}")

        if not player_html:
            print("[YummyAnime] YUMMYANIME_DEBUG: Failed to fetch player API. Need exact endpoint.")
            raise Exception("Failed to fetch YummyAnime player data. API endpoint unknown.")

        psoup = BeautifulSoup(player_html, 'html.parser')
        iframe = psoup.find('iframe')
        
        embed_url = iframe.get('src') if iframe else None
        if not embed_url:
            print("[YummyAnime] YUMMYANIME_DEBUG: No iframe found in player_html:", player_html[:200])
            raise Exception("Could not extract iframe from YummyAnime player.")

        if embed_url.startswith('//'):
            embed_url = 'https:' + embed_url

        print(f"[YummyAnime] Extracted embed URL: {embed_url}")
        
        # Now we delegate the actual video extraction to the router
        info = self.get_video_info(embed_url, settings)
        if info:
            info['title'] = title
            if thumbnail:
                info['thumbnails'] = [{'url': thumbnail}]
            return info

        raise Exception("Failed to resolve YummyAnime embed link.")

    @staticmethod
    def is_speakerdeck_url(url):
        import re
        return bool(re.search(r'speakerdeck\.com/[^/]+/[^/]+', url))

    def _get_speakerdeck_info(self, url, settings=None):
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        title = soup.find('meta', property='og:title')
        title = title['content'] if title else 'Speaker Deck Presentation'
        
        thumbnail = soup.find('meta', property='og:image')
        thumbnail_url = thumbnail['content'] if thumbnail else None
        
        pdf_link = soup.select_one('a[title="Download PDF"]')
        if not pdf_link or 'href' not in pdf_link.attrs:
            raise Exception("Could not find PDF download link on Speaker Deck. The author may have disabled downloads.")
            
        pdf_url = pdf_link['href']
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = 'https://speakerdeck.com' + pdf_url
            
        info = {
            '_type': 'video',
            'id': url.split('/')[-1].split('?')[0],
            'title': title,
            'original_url': url,
            'url': pdf_url,
            'ext': 'pdf',
            'vcodec': 'none',
            'acodec': 'none'
        }
        
        if thumbnail_url:
            info['thumbnails'] = [{'url': thumbnail_url}]
            info['thumbnail'] = thumbnail_url
            
        return info

    @staticmethod
    def is_scribd_url(url):
        import re
        return bool(re.search(r'scribd\.com/(?:doc|document)/', url))

    def _get_scribd_info(self, url, settings=None):
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        title = soup.find('meta', property='og:title')
        title = title['content'] if title else 'Scribd Document'
        
        thumbnail = soup.find('meta', property='og:image')
        thumbnail_url = thumbnail['content'] if thumbnail else None
        
        # Scribd doesn't allow direct PDF downloads without an account.
        # We will use an external API like scribd.vdownloaders.com as a fallback
        # However, to maintain compatibility with yt-dlp's format structure:
        
        info = {
            '_type': 'video',
            'id': url.split('/')[-2] if len(url.split('/')) > 4 else 'scribd_doc',
            'title': title,
            'original_url': url,
            'url': url,
            'thumbnail': thumbnail_url,
            'duration': 0,
            'ext': 'pdf',
        }
        
        if thumbnail_url:
            info['thumbnails'] = [{'url': thumbnail_url}]
            
        try:
            # Attempt to use a third-party API to get the download link
            from curl_cffi import requests as cffi_requests
            api_url = "https://scribd.vdownloaders.com/api/generate"
            api_resp = cffi_requests.post(api_url, json={'url': url}, headers=headers, impersonate="chrome", timeout=15)
            if api_resp.status_code == 200:
                data = api_resp.json()
                if data.get('url'):
                    info['formats'] = [{'url': data['url'], 'ext': 'pdf', 'vcodec': 'none', 'acodec': 'none'}]
                    return info
            raise Exception(f"API Error: {api_resp.status_code} {api_resp.text}")
        except Exception as e:
            raise Exception("Failed to bypass Scribd. The external downloader service might be offline or blocked by Cloudflare. You may need to use 'Browser Cookies' to download directly with a premium account.")
        
        return info

    def _get_slideshare_info(self, url):
        """Extract all slide images from a SlideShare presentation."""
        import requests
        import re
        from bs4 import BeautifulSoup
        import json
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        title = soup.find('meta', property='og:title')
        title = title['content'] if title else 'SlideShare Presentation'
        
        thumbnail = soup.find('meta', property='og:image')
        thumbnail_url = thumbnail['content'] if thumbnail else None
        
        slides = []
        
        # Parse JSON state or HTML
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text)
        if m:
            try:
                urls = re.findall(r'(https://image\.slidesharecdn\.com/[^"\']+-\d+-(?:2048|1024|768)\.jpg)', m.group(1))
                slides.extend(urls)
            except:
                pass
                
        # Also parse from HTML directly
        urls = re.findall(r'(https://image\.slidesharecdn\.com/[^"\'?\s]+-\d+-(?:2048|1024|768)\.jpg)', resp.text)
        slides.extend(urls)
        
        # SlideShare might lazy load images, try to find total slide count
        total_slides = 0
        total_match = re.search(r'"totalSlides":(\d+)', resp.text) or re.search(r'"total_slides":(\d+)', resp.text) or re.search(r'data-total-slides="(\d+)"', resp.text)
        if total_match:
            total_slides = int(total_match.group(1))
            
        first_img_match = re.search(r'(https://image\.slidesharecdn\.com/[^"\'?\s]+)-1-(?:2048|1024|768)\.jpg', resp.text)
        if first_img_match and total_slides > 0:
            base_url = first_img_match.group(1)
            res = "2048" if "2048" in first_img_match.group(0) else ("1024" if "1024" in first_img_match.group(0) else "768")
            for i in range(1, total_slides + 1):
                slides.append(f"{base_url}-{i}-{res}.jpg")
                
        # Remove duplicates while prioritizing higher resolution
        unique_slides = {}
        for s in slides:
            s = s.replace('\\/', '/')
            num_match = re.search(r'-(\d+)-(?:2048|1024|768)\.jpg', s)
            if num_match:
                num = int(num_match.group(1))
                if num not in unique_slides or ('2048' in s and '1024' in unique_slides[num]):
                    unique_slides[num] = s
                    
        sorted_slides = [unique_slides[k] for k in sorted(unique_slides.keys())]
        
        if not sorted_slides:
            raise Exception("Could not extract any slides from this SlideShare presentation.")
            
        entries = []
        for i, slide_url in enumerate(sorted_slides):
            entries.append({
                '_type': 'video',
                'id': f'slide_{i+1}',
                'title': f'{title} - Slide {i+1}',
                'url': slide_url,
                'thumbnail': slide_url,
                'ext': 'jpg',
                'vcodec': 'none',
                'acodec': 'none'
            })
            
        return {
            '_type': 'playlist',
            'id': url.split('/')[-1] if '/' in url else 'slideshare',
            'title': title,
            'original_url': url,
            'webpage_url': url,
            'entries': entries,
            'thumbnail': thumbnail_url or (sorted_slides[0] if sorted_slides else None)
        }

    def get_video_info(self, url, settings=None):
        import re
        if 'idolcomplex.com' in url:
            m = re.search(r'idolcomplex\.com(?:/[a-z]{2})?/posts/([A-Za-z0-9_-]+)', url)
            if m:
                url = f"https://idol.sankakucomplex.com/post/show/{m.group(1)}"

        if 'slideshare.net/' in url:
            return self._get_slideshare_info(url)

        if self.is_speakerdeck_url(url):
            return self._get_speakerdeck_info(url, settings)

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
        if self.is_9anime_url(url):
            return self._get_9anime_info(url, settings)
        if self.is_anime8_url(url):
            return self._get_anime8_info(url, settings)
        if self.is_animeflv_url(url):
            return self._get_animeflv_info(url, settings)
        if self.is_kissanime_url(url):
            return self._get_kissanime_info(url, settings)
        if self.is_zorotv_url(url):
            return self._get_zorotv_info(url, settings)
        if self.is_yummyani_url(url):
            return self._get_yummyani_info(url, settings)
        if self.is_scribd_url(url):
            return self._get_scribd_info(url, settings)

        class DummyLogger:
            def debug(self, msg): pass
            def warning(self, msg): pass
            def error(self, msg): print(msg)

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

        if '56.com' in url.lower():
            ydl_opts['noplaylist'] = True
            ydl_opts['extract_flat'] = False

        try:
            if 'speakerdeck.com' in url.lower():
                import requests
                from bs4 import BeautifulSoup
                
                resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    embed_div = soup.find('div', class_='speakerdeck-embed')
                    if embed_div and embed_div.get('data-id'):
                        presentation_id = embed_div.get('data-id')
                        player_url = f"https://speakerdeck.com/player/{presentation_id}"
                        player_resp = requests.get(player_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                        
                        if player_resp.status_code == 200:
                            player_soup = BeautifulSoup(player_resp.text, 'html.parser')
                            title_el = player_soup.find(class_='sd-player-title-name')
                            title = title_el.text.strip() if title_el else "Speaker Deck Presentation"
                            author_el = player_soup.find(class_='sd-player-title-author')
                            author = author_el.text.strip().replace('by ', '') if author_el else "Unknown"
                            
                            slides = player_soup.find_all('div', class_='sd-player-slide js-sd-slide')
                            entries = []
                            for i, slide in enumerate(slides):
                                img_url = slide.get('data-url')
                                if img_url:
                                    entries.append({
                                        '_type': 'video',
                                        'id': f"{presentation_id}_slide_{i+1}",
                                        'title': f"{title} - Slide {i+1}",
                                        'url': img_url,
                                        'thumbnail': slide.get('data-preview-url') or img_url,
                                        'uploader': author,
                                        'formats': [{'format_id': 'best', 'url': img_url, 'ext': 'jpg', 'vcodec': 'image', 'acodec': 'none'}]
                                    })
                            
                            if entries:
                                return {
                                    '_type': 'playlist',
                                    'id': presentation_id,
                                    'title': title,
                                    'uploader': author,
                                    'extractor': 'speakerdeck',
                                    'extractor_key': 'SpeakerDeck',
                                    'entries': entries
                                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info and info.get('ext') == 'unknown_video':
                    try:
                        import requests
                        r = requests.get(url, timeout=5, allow_redirects=True, stream=True, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                            'Accept': 'image/*,*/*;q=0.8'
                        })
                        
                        img_ext = None
                        clean_title = None
                        
                        # 1. Check Content-Disposition for the real filename
                        cd = r.headers.get('content-disposition', '')
                        if 'filename' in cd:
                            import re
                            m = re.search(r'filename[*]?=["\']?([^"\';\r\n]+)', cd)
                            if m:
                                cd_filename = m.group(1).strip().strip('"').strip("'")
                                if '.' in cd_filename:
                                    cd_ext = cd_filename.rsplit('.', 1)[-1].lower()
                                    if cd_ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'svg', 'pdf'):
                                        img_ext = 'jpg' if cd_ext == 'jpeg' else cd_ext
                                    # Extract a clean title from the filename
                                    cd_name = cd_filename.rsplit('.', 1)[0]
                                    cd_name = cd_name.replace('-', ' ').replace('_', ' ').strip()
                                    if cd_name:
                                        clean_title = cd_name.title()
                        
                        # 2. Check Content-Type
                        if not img_ext:
                            ctype = r.headers.get('content-type', '').lower()
                            if ctype.startswith('image/'):
                                ct_ext = ctype.split('/')[-1].split(';')[0].strip()
                                if ct_ext == 'jpeg': ct_ext = 'jpg'
                                img_ext = ct_ext
                        
                        # 3. Check magic bytes as final fallback
                        if not img_ext:
                            first_bytes = next(r.iter_content(chunk_size=16), b'')
                            if first_bytes[:3] == b'\xff\xd8\xff':
                                img_ext = 'jpg'
                            elif first_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                                img_ext = 'png'
                            elif first_bytes[:4] == b'RIFF' and first_bytes[8:12] == b'WEBP':
                                img_ext = 'webp'
                            elif first_bytes[:6] in (b'GIF87a', b'GIF89a'):
                                img_ext = 'gif'
                        
                        r.close()
                        
                        if img_ext:
                            info['ext'] = img_ext
                            info['vcodec'] = 'image'
                            if clean_title:
                                info['title'] = clean_title
                                info['fulltitle'] = clean_title
                            if not info.get('formats'):
                                info['formats'] = [{'url': url, 'ext': img_ext, 'vcodec': 'image', 'acodec': 'none'}]
                            else:
                                for f in info['formats']:
                                    f['ext'] = img_ext
                                    f['vcodec'] = 'image'
                    except:
                        pass
                
                if info and 'linkedin.com' in url.lower():
                    try:
                        import requests
                        from bs4 import BeautifulSoup
                        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, timeout=10)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            video_tag = soup.find('video')
                            if video_tag:
                                if video_tag.get('data-poster-url'):
                                    src = video_tag.get('data-poster-url')
                                    info['thumbnail'] = src
                                    if 'thumbnails' in info:
                                        info['thumbnails'] = [{'url': src}]
                                
                                if not info.get('duration'):
                                    import json
                                    sources_str = video_tag.get('data-sources')
                                    if sources_str:
                                        try:
                                            sources = json.loads(sources_str)
                                            if sources and isinstance(sources, list):
                                                for src_info in sources:
                                                    v_url = src_info.get('src')
                                                    v_bitrate = src_info.get('data-bitrate')
                                                    if v_url and v_bitrate:
                                                        head_r = requests.head(v_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                                                        if head_r.status_code == 200 and 'Content-Length' in head_r.headers:
                                                            c_len = int(head_r.headers['Content-Length'])
                                                            info['duration'] = (c_len * 8) / v_bitrate
                                                            break
                                        except:
                                            pass
                            else:
                                for img in soup.find_all('img'):
                                    src = img.get('src', '')
                                    if 'media.licdn.com' in src and ('image-scale' in src or 'cover' in src.lower()):
                                        info['thumbnail'] = src
                                        if 'thumbnails' in info:
                                            info['thumbnails'] = [{'url': src}]
                                        break
                    except Exception:
                        pass
                        
                if info and not info.get('thumbnail') and 'analdin.' in url.lower():
                    try:
                        import requests
                        import re
                        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                        if resp.status_code == 200:
                            m = re.search(r"preview_url:\s*'([^']+)'", resp.text)
                            if m:
                                info['thumbnail'] = m.group(1)
                                if 'thumbnails' not in info:
                                    info['thumbnails'] = []
                                info['thumbnails'].append({'url': m.group(1)})
                    except Exception:
                        pass
                        
                # Pre-download thumbnail for kick.com or twitch (0x0 fixes)
                thumb_url = info.get('thumbnail')
                if not thumb_url and info.get('thumbnails'):
                    thumb_url = info['thumbnails'][-1]['url']

                if thumb_url:
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
                        elif 'audioboom' in url.lower():
                            import requests
                            import base64
                            resp = requests.get(thumb_url, timeout=10)
                            if resp.status_code == 200:
                                b64_data = base64.b64encode(resp.content).decode('utf-8')
                        elif 'bcbits.com' in thumb_url or 'bandcamp' in url.lower():
                            import requests
                            import base64
                            resp = requests.get(thumb_url, timeout=10)
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
            
            if "bilibili.com" in url.lower() and ("412" in yt_err_str or "precondition failed" in yt_err_str or "login" in yt_err_str):
                raise Exception("Bilibili is blocking the request (HTTP 412). To fix this, please go to Settings -> Advanced, select your web browser in 'Browser Cookies' (where you are logged into Bilibili), and try again.")
            
            # Fallback for direct media links (like .gif or .jpg) that yt-dlp's generic extractor rejects
            is_unsupported = "unsupported url" in yt_err_str or "unable to download webpage" in yt_err_str or "403: forbidden" in yt_err_str
            if is_unsupported and any(url.lower().split('?')[0].endswith(x) for x in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf', '.mp4', '.webm', '.mov', '.mp3', '.wav', '.flac', '.m4a', '.ogg']):
                ext = url.split('.')[-1].split('?')[0].lower()
                if len(ext) > 4 or not ext.isalnum(): ext = 'jpg'
                is_video = ext in ['mp4', 'webm', 'mov', 'mkv', 'avi']
                is_audio = ext in ['mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac']
                
                if is_audio:
                    vcodec = 'none'
                    acodec = 'audio'
                else:
                    vcodec = 'video' if is_video else 'image'
                    acodec = 'none'
                
                import urllib.parse
                title = urllib.parse.unquote(url.split('/')[-1].split('?')[0]) or "Media"
                
                return {
                    '_type': 'video',
                    'id': 'direct',
                    'title': title,
                    'original_url': url,
                    'url': url,
                    'thumbnail': url if not is_audio else None,
                    'duration': 0,
                    'formats': [{'url': url, 'ext': ext, 'vcodec': vcodec, 'acodec': acodec}],
                }

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
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                except subprocess.CalledProcessError:
                    pass
                    
                # If out is None or contains "login page", try with cookies
                if not out or '"HTTP redirect to login page' in out or '"error":' in out or 'blocked by network security' in out:
                    for browser in ['chrome', 'edge', 'firefox', 'brave']:
                        try:
                            out = subprocess.check_output(
                                ['gallery-dl', '-j', '--cookies-from-browser', browser, url],
                                stderr=subprocess.DEVNULL,
                                text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                            )
                            if '"HTTP redirect to login page' not in out and '"error":' not in out and 'blocked by network security' not in out:
                                break
                        except:
                            pass
                
                if not out or '"HTTP redirect to login page' in out or '"error":' in out or 'blocked by network security' in out:
                    if 'instagram.com' in url:
                        raise Exception("Instagram blocks multi-image posts without cookies. Go to Settings and click 'Login to Browser (Export Cookies)' to link your account.")
                    if 'reddit.com' in url and 'blocked by network security' in out:
                        raise Exception("Reddit is blocking the request. To fix this, go to Settings -> Advanced and select your browser in the 'Browser Cookies' dropdown, or use a cookies.txt file.")
                    if 'tumblr.com' in url:
                        raise Exception("Tumblr is blocking the request. To fix this, go to Settings -> Advanced and select your browser in the 'Browser Cookies' dropdown, or use a cookies.txt file.")
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
                    
                print("GALLERY-DL DATA:", json.dumps(data, indent=2)[:2000])
                    
                seen_urls = set()
                entries = []
                last_metadata = {}
                for item in data:
                    if isinstance(item, list) and len(item) >= 2:
                        status = item[0]
                        info_dict = item[1]
                        
                        if status == 6 and isinstance(info_dict, str) and info_dict.startswith('http'):
                            # Redirect/Delegate URL
                            return self.get_video_info(info_dict, settings)
                        
                        if status == 2 and isinstance(info_dict, dict):
                            last_metadata = info_dict
                            
                        img_url = None
                        if status == 3 and len(item) >= 3 and isinstance(item[1], str):
                            img_url = item[1]
                            info_dict = item[2] if isinstance(item[2], dict) else last_metadata
                        elif status not in (1, 2, 4, 6, -1):
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
                                
                        if img_url and img_url not in seen_urls:
                            seen_urls.add(img_url)
                            if img_url.startswith('ytdl:'):
                                img_url = img_url[5:]

                            import urllib.parse
                            parsed_url = urllib.parse.urlparse(img_url)
                            path = parsed_url.path
                            
                            ext = path.split('.')[-1].lower() if '.' in path else ''
                            
                            query_params = urllib.parse.parse_qs(parsed_url.query)
                            ct = query_params.get('ct', [''])[0]
                            
                            is_audio = False
                            if not ext or len(ext) > 5 or '/' in ext:
                                if 'audio/' in ct:
                                    ext = ct.split('/')[-1]
                                    if ext == 'mpeg': ext = 'mp3'
                                    is_audio = True
                                elif 'image/' in ct:
                                    ext = ct.split('/')[-1]
                                    if ext == 'jpeg': ext = 'jpg'
                                elif 'video/' in ct:
                                    ext = ct.split('/')[-1]
                                elif 'audioFile' in info_dict and isinstance(info_dict['audioFile'], dict):
                                    ext = 'mp3'
                                    is_audio = True
                                elif 'audio' in info_dict.get('mime_type', '') or 'audio' in img_url.lower():
                                    ext = 'mp3'
                                    is_audio = True

                            is_video = ext in ['mp4', 'webm', 'mov', 'mkv', 'avi', 'm3u8']
                            if not is_audio:
                                is_audio = ext in ['mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac']
                            
                            if not is_video and not is_audio and ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf']:
                                ext = 'jpg'
                            
                            raw_title = str(info_dict.get('title') or info_dict.get('description') or info_dict.get('filename') or "Media").strip() or "Media"
                            
                            # For boorus, tags are more useful as title
                            booru_tags = info_dict.get('tags_general') or info_dict.get('tags')
                            if booru_tags and isinstance(booru_tags, str):
                                raw_title = booru_tags.strip()
                                if len(raw_title) > 80:
                                    raw_title = raw_title[:77] + "..."
                            
                            title = raw_title
                            # Append unique index/id to title to prevent overwriting
                            img_id = str(info_dict.get('id') or info_dict.get('tweet_id') or str(len(entries)+1))
                            if img_id not in title:
                                title = f"{title}_{img_id}"
                            
                            if is_audio:
                                vcodec = 'none'
                                acodec = 'audio'
                            else:
                                vcodec = 'video' if is_video else 'image'
                                acodec = 'none'
                                
                            thumb = img_url
                            
                            # Clean up // in URLs
                            if thumb and '://' in thumb:
                                parts = thumb.split('://')
                                thumb = parts[0] + '://' + parts[1].replace('//', '/')
                                
                                # Use thumbnail URL instead of full size for realbooru/gelbooru style
                                if '/images/' in thumb and not is_video:
                                    try:
                                        t_parts = thumb.split('/images/')
                                        t_filename = t_parts[-1].split('/')[-1]
                                        t_filename_noext = t_filename.rsplit('.', 1)[0]
                                        t_path = t_parts[-1].rsplit('/', 1)[0] + '/' if '/' in t_parts[-1] else ''
                                        thumb = f"{t_parts[0]}/thumbnails/{t_path}thumbnails_{t_filename_noext}.jpg"
                                    except:
                                        pass
                            
                            # If it's a video, try to find a thumbnail from metadata
                            if is_video:
                                thumb = info_dict.get('thumbnail') or info_dict.get('image_medium_url') or info_dict.get('thumbnail_url') or thumb
                                
                                # Fallback for Tumblr video posters embedded in 'body' HTML
                                if thumb == img_url and 'body' in info_dict:
                                    import re
                                    match = re.search(r'poster="([^"]+)"', info_dict['body'])
                                    if match:
                                        thumb = match.group(1)
                                        
                                # Fallback for Behance video covers
                                if thumb == img_url and 'covers' in info_dict and isinstance(info_dict['covers'], dict):
                                    all_avail = info_dict['covers'].get('allAvailable', [])
                                    if all_avail and isinstance(all_avail, list):
                                        thumb = all_avail[-1].get('url') or thumb

                                if thumb == img_url:
                                    thumb = None
                            
                            format_ext = 'mp4' if ext == 'm3u8' else ext
                            format_protocol = 'm3u8' if ext == 'm3u8' else 'https'
                            
                            author_obj = info_dict.get('author') or info_dict.get('user') or {}
                            author_name = info_dict.get('username')
                            if isinstance(author_obj, dict):
                                author_name = author_obj.get('username') or author_obj.get('name') or author_name
                            elif isinstance(author_obj, str):
                                author_name = author_obj

                            entry = {
                                '_type': 'video', # Fake as video to satisfy UI
                                'id': img_id,
                                'title': title,
                                'original_url': url,
                                'webpage_url': url,
                                'url': img_url,
                                'thumbnail': thumb,
                                'duration': 0,
                                'uploader': author_name,
                                'artist': author_name,
                                'description': info_dict.get('description') or info_dict.get('caption'),
                                'formats': [{'format_id': 'best', 'url': img_url, 'ext': format_ext, 'protocol': format_protocol, 'vcodec': vcodec, 'acodec': acodec}],
                            }
                            entries.append(entry)
                
                if entries:
                    if len(entries) == 1:
                        return entries[0]
                    else:
                        playlist_title = last_metadata.get('comic_name') or last_metadata.get('manga') or last_metadata.get('comic') or last_metadata.get('title')
                        if not playlist_title or str(playlist_title).strip() == "":
                            playlist_title = entries[0]['title'] if entries else 'Image Gallery'
                            
                        # Construct a fake playlist for the UI
                        return {
                            '_type': 'playlist',
                            'id': 'gallery',
                            'title': playlist_title,
                            'original_url': url,
                            'webpage_url': url,
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
            result = client.get_url(url)
            collection_name = result[0]
            tracks = result[1]
            if not tracks:
                return None
            
            if len(tracks) == 1 and ('track' in url or 'track' in getattr(tracks[0], 'url', '')):
                t = tracks[0]
                return {
                    "id": getattr(t, 'track_id', getattr(t, 'id', '')),
                    "title": t.title,
                    "uploader": t.artists,
                    "thumbnail": t.cover_url,
                    "duration": getattr(t, 'duration_seconds', 0),
                    "is_audio_only": True,
                    "webpage_url": url,
                    "_spotify": True
                }
            
            entries = []
            for t in tracks:
                entries.append({
                    "id": getattr(t, 'track_id', getattr(t, 'id', '')),
                    "title": t.title,
                    "uploader": t.artists,
                    "thumbnail": t.cover_url,
                    "duration": getattr(t, 'duration_seconds', 0),
                    "url": getattr(t, 'url', url),
                    "is_audio_only": True
                })
                
            return {
                "_type": "playlist",
                "title": collection_name,
                "uploader": entries[0]["uploader"] if entries else "Tidal",
                "thumbnail": entries[0]["thumbnail"] if entries else None,
                "entries": entries,
                "webpage_url": url,
                "_spotify": True
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



    @staticmethod
    def decode9AnimeString(encoded_str):
        import urllib.parse
        str1 = encoded_str[0:9]
        str2 = encoded_str[9:]

        encodedNum = 0
        counter = 0
        part1 = ""

        for char in str2:
            encodedNum <<= 6
            try:
                letterNum = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'.index(char)
                encodedNum |= letterNum
            except ValueError:
                pass
            counter += 1

            if counter == 4:
                part1 += chr((16711680 & encodedNum) >> 16)
                part1 += chr((65280 & encodedNum) >> 8)
                part1 += chr(255 & encodedNum)
                encodedNum = 0
                counter = 0

        if counter == 2:
            encodedNum >>= 4
            part1 += chr(encodedNum)
        elif counter == 3:
            encodedNum >>= 2
            part1 += chr((65280 & encodedNum) >> 8)
            part1 += chr(255 & encodedNum)

        try:
            part1 = urllib.parse.unquote(part1)
        except Exception:
            pass

        arr = {}
        byteSize = 256
        final = ""

        for c in range(byteSize):
            arr[c] = c

        x = 0
        for c in range(byteSize):
            x = (x + arr[c] + ord(str1[c % len(str1)])) % byteSize
            i = arr[c]
            arr[c] = arr[x]
            arr[x] = i

        x = 0
        d = 0

        for s in range(len(part1)):
            d = (d + 1) % byteSize
            x = (x + arr[d]) % byteSize

            i = arr[d]
            arr[d] = arr[x]
            arr[x] = i

            final += chr(ord(part1[s]) ^ arr[(arr[d] + arr[x]) % byteSize])

        return final

    def _get_kissanime_info(self, url, settings=None, is_sample=False):
        import re
        import json
        import base64
        from bs4 import BeautifulSoup
        try:
            try:
                from curl_cffi import requests as crequests
                resp = crequests.get(url, impersonate="chrome", timeout=15)
            except ImportError:
                import requests
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code != 200:
                print(f"[KISSANIME] Failed to fetch {url}")
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            title_el = soup.select_one('h1.entry-title') or soup.select_one('h1.title')
            anime_title = title_el.text.strip() if title_el else "KissAnime Video"
            
            is_single = '?single=1' in url or is_sample
            
            clean_url = url.split('?')[0]

            thumb_meta = soup.find('meta', property='og:image')
            anime_thumbnail = thumb_meta['content'] if thumb_meta and thumb_meta.has_attr('content') else None

            servers_list = soup.select('.server-item a.btn')
            episodes_ul = soup.select('div.episodes-ul a.ep-item')
            if not episodes_ul:
                eplist = soup.find('div', class_='eplister')
                if eplist:
                    episodes_ul = eplist.find_all('a')
                    
            if not is_single and episodes_ul:
                if ' Episode ' in anime_title:
                    anime_title = anime_title.split(' Episode ')[0].strip()
                    
                entries = []
                ep_data = []
                for ep in episodes_ul:
                    href = ep.get('href')
                    if not href: continue
                    
                    if href.startswith('/'):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                        
                    href = href.split('?')[0]
                    
                    num_text = ep.get('data-number')
                    if not num_text:
                        order_div = ep.select_one('.order')
                        if order_div:
                            num_text = order_div.text.strip()
                        else:
                            m = re.search(r'-episode-(\d+)', href)
                            if m: num_text = m.group(1)
                            else: num_text = str(len(ep_data) + 1)
                            
                    try:
                        num = float(num_text)
                    except:
                        num = 0
                        
                    ep_data.append({'url': href, 'num': num})
                
                seen = set()
                unique_eps = []
                for e in ep_data:
                    if e['url'] not in seen:
                        seen.add(e['url'])
                        unique_eps.append(e)
                        
                unique_eps.sort(key=lambda x: x['num'])
                
                for e in unique_eps:
                    num_str = str(int(e['num'])) if e['num'].is_integer() else str(e['num'])
                    entries.append({
                        '_type': 'url',
                        'url': e['url'] + "?single=1",
                        'title': f"{anime_title} - Episode {num_str}",
                        'thumbnail': anime_thumbnail,
                        'thumbnails': [{'url': anime_thumbnail, 'id': 'kissanime'}] if anime_thumbnail else []
                    })
                    
                if entries:
                    playlist_info = {
                        '_type': 'playlist',
                        'title': anime_title,
                        'thumbnail': anime_thumbnail,
                        'entries': entries,
                        'webpage_url': clean_url,
                        '_is_kissanime': True
                    }
                    
                    try:
                        sample_ep_info = self._get_kissanime_info(entries[-1]['url'], settings, is_sample=True)
                        if not sample_ep_info or 'formats' not in sample_ep_info:
                            if len(entries) > 1:
                                sample_ep_info = self._get_kissanime_info(entries[0]['url'], settings, is_sample=True)

                        if sample_ep_info and 'formats' in sample_ep_info:
                            playlist_info['formats'] = sample_ep_info['formats']
                            playlist_info['duration'] = sample_ep_info.get('duration')
                            
                            sample_duration = sample_ep_info.get('duration')
                            for entry in entries:
                                entry['formats'] = sample_ep_info['formats']
                                if sample_duration:
                                    entry['duration'] = sample_duration
                    except Exception as e:
                        print(f"[KISSANIME] Failed to fetch sample episode formats: {e}")
                        
                    return playlist_info
                    
            if servers_list:
                for server in servers_list:
                    hash_data = server.get('data-hash')
                    if not hash_data: continue
                    
                    try:
                        decoded_html = base64.b64decode(hash_data).decode('utf-8')
                        iframe_m = re.search(r'src=["\']([^"\']+)["\']', decoded_html)
                        if iframe_m:
                            embed_url = iframe_m.group(1)
                            if embed_url.startswith('//'):
                                embed_url = "https:" + embed_url
                                
                            info = self.get_video_info(embed_url, settings)
                            
                            # Fallback: extract inner iframe (e.g., megaplay.buzz) and find m3u8
                            if not info and 'gogoanime' in embed_url and 'streaming.php' in embed_url:
                                try:
                                    try:
                                        from curl_cffi import requests as crequests
                                        w_resp = crequests.get(embed_url, impersonate="chrome", headers={'Referer': clean_url}, timeout=15)
                                    except ImportError:
                                        import requests
                                        w_resp = requests.get(embed_url, headers={'Referer': clean_url, 'User-Agent': 'Mozilla/5.0'}, timeout=15)
                                        
                                    inner_iframe_m = re.search(r'iframe\s+src=["\']([^"\']+)["\']', w_resp.text)
                                    if inner_iframe_m:
                                        inner_url = inner_iframe_m.group(1)
                                        if inner_url.startswith('//'):
                                            inner_url = "https:" + inner_url
                                            
                                        info = self.get_video_info(inner_url, settings)
                                        
                                        if not info and 'megaplay' in inner_url:
                                            try:
                                                from curl_cffi import requests as crequests
                                                m_resp = crequests.get(inner_url, impersonate="chrome", headers={'Referer': embed_url}, timeout=15)
                                            except ImportError:
                                                import requests
                                                m_resp = requests.get(inner_url, headers={'Referer': embed_url, 'User-Agent': 'Mozilla/5.0'}, timeout=15)
                                                
                                            m3u8_m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', m_resp.text)
                                            if m3u8_m:
                                                m3u8_url = m3u8_m.group(1).replace('\\/', '/')
                                                info = self.get_video_info(m3u8_url, settings)
                                            else:
                                                file_m = re.search(r'file\s*:\s*["\'](https?://[^"\']+)["\']', m_resp.text)
                                                if file_m:
                                                    f_url = file_m.group(1).replace('\\/', '/')
                                                    info = self.get_video_info(f_url, settings)
                                except Exception as e:
                                    print(f"[KISSANIME] Inner iframe extraction failed: {e}")
                                    
                            if info:
                                info['title'] = anime_title
                                info['_is_kissanime'] = True
                                if anime_thumbnail:
                                    info['thumbnail'] = anime_thumbnail
                                    info['thumbnails'] = [{'url': anime_thumbnail, 'id': 'kissanime'}]
                                return info
                    except Exception as e:
                        print(f"[KISSANIME] Error parsing server: {e}")
                        continue
                        
            return None
        except Exception as e:
            print(f"[KISSANIME] Error fetching info: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_animeflv_info(self, url, settings=None):
        import re
        import json
        from bs4 import BeautifulSoup
        try:
            try:
                from curl_cffi import requests as crequests
                resp = crequests.get(url, impersonate="chrome", timeout=15)
            except ImportError:
                import requests
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code != 200:
                print(f"[ANIMEFLV] Failed to fetch {url}")
                with open('animeflv_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(f"STATUS CODE: {resp.status_code}\nURL: {url}\n\n{resp.text}")
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}/"

            if '/ver/' not in url:
                # Series page
                anime_info_m = re.search(r'anime_info\s*=\s*(\[.*?\]);', resp.text, re.DOTALL)
                episodes_m = re.search(r'episodes\s*=\s*(\[.*?\]);', resp.text, re.DOTALL)
                
                if not anime_info_m or not episodes_m:
                    print("[ANIMEFLV] Could not find anime_info or episodes")
                    return None
                    
                anime_info = json.loads(anime_info_m.group(1))
                episodes = json.loads(episodes_m.group(1))
                
                title_el = soup.select_one('h1.Title')
                anime_title = title_el.text.strip() if title_el else (anime_info[1] if len(anime_info) > 1 else "AnimeFLV Video")
                
                og_img = soup.find('meta', property='og:image')
                anime_thumbnail = og_img['content'] if og_img and og_img.has_attr('content') else None
                
                entries = []
                # Episodes list is usually reversed, so reverse it back to chronological order
                for epi in reversed(episodes):
                    # epi = [episode_number, id]
                    ep_url = f"{base_url}ver/{epi[1]}/{anime_info[2]}-{epi[0]}"
                    entries.append({
                        '_type': 'url',
                        'url': ep_url,
                        'title': f"{anime_title} - Episode {epi[0]}",
                        'thumbnail': anime_thumbnail
                    })
                    
                if not entries:
                    return None
                    
                playlist_info = {
                    '_type': 'playlist',
                    'title': anime_title,
                    'thumbnail': anime_thumbnail,
                    'entries': entries,
                    'webpage_url': url,
                    '_is_animeflv': True
                }
                
                try:
                    sample_ep_info = self._get_animeflv_info(entries[0]['url'], settings)
                    if sample_ep_info and 'formats' in sample_ep_info:
                        playlist_info['formats'] = sample_ep_info['formats']
                        sample_duration = sample_ep_info.get('duration')
                        for entry in entries:
                            entry['formats'] = sample_ep_info['formats']
                            if sample_duration:
                                entry['duration'] = sample_duration
                except Exception as e:
                    print(f"[ANIMEFLV] Failed to fetch sample episode formats: {e}")
                    
                return playlist_info
                
            else:
                # Watch page
                title_el = soup.select_one('h1.Title') or soup.select_one('h2.Title')
                anime_title = title_el.text.strip() if title_el else "AnimeFLV Episode"
                
                og_img = soup.find('meta', property='og:image')
                anime_thumbnail = og_img['content'] if og_img and og_img.has_attr('content') else None
                
                videos_m = re.search(r'videos\s*=\s*(\{.*?\});', resp.text, re.DOTALL)
                if not videos_m:
                    print("[ANIMEFLV] Could not find videos data")
                    with open('animeflv_debug.txt', 'w', encoding='utf-8') as f:
                        f.write("COULD NOT FIND VIDEOS DATA\n\n" + resp.text)
                    return None
                    
                videos_data = json.loads(videos_m.group(1))
                video_list = videos_data.get('SUB') or videos_data.get('LAT') or []
                
                with open('animeflv_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(f"FOUND VIDEOS: {json.dumps(video_list)}\n")
                
                # Order servers by yt-dlp compatibility
                supported_servers = ['stape', 'yu', 'fembed', 'gocdn', 'natsuki']
                sorted_videos = sorted(video_list, key=lambda x: supported_servers.index(x['server'].lower()) if x['server'].lower() in supported_servers else 999)
                
                for v in sorted_videos:
                    embed_url = v.get('code')
                    if not embed_url:
                        continue
                        
                    if v['server'].lower() == 'natsuki':
                        # The template says natsuki requires an extra API call to get the real file
                        try:
                            from curl_cffi import requests as crequests
                            api_url = embed_url.replace('embed', 'check')
                            api_resp = crequests.get(api_url, impersonate="chrome", timeout=10)
                            embed_url = api_resp.json().get('file', embed_url)
                        except:
                            pass
                            
                    try:
                        info = self.get_video_info(embed_url, settings)
                        if info:
                            info['title'] = anime_title
                            info['_is_animeflv'] = True
                            if anime_thumbnail:
                                info['thumbnail'] = anime_thumbnail
                                info['thumbnails'] = [{'url': anime_thumbnail, 'id': 'animeflv'}]
                            return info
                    except Exception as e:
                        print(f"[ANIMEFLV] Error fetching embed from server {v['server']}: {e}")
                        continue
                        
                with open('animeflv_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(f"ALL SERVERS FAILED OR EMPTY. Sorted videos: {json.dumps(sorted_videos)}\n")
                return None
                
        except Exception as e:
            print(f"[ANIMEFLV] Error fetching info: {e}")
            import traceback
            traceback.print_exc()
            with open('animeflv_debug.txt', 'w', encoding='utf-8') as f:
                f.write(f"EXCEPTION: {e}\n{traceback.format_exc()}")
            return None

    def _get_anime8_info(self, url, settings=None):
        import re
        from bs4 import BeautifulSoup
        try:
            try:
                from curl_cffi import requests as crequests
                resp = crequests.get(url, impersonate="chrome", timeout=15)
            except ImportError:
                import requests
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code != 200:
                print(f"[ANIME8] Failed to fetch {url}")
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            is_watch_page = 'ctk =' in resp.text and 'episode_id =' in resp.text
            
            domain_match = re.search(r'anime8\.([a-zA-Z0-9.]+)', url)
            extension = domain_match.group(1) if domain_match else 'ru'
            base_url = f"https://anime8.{extension}"

            if not is_watch_page:
                thumb_img = soup.select_one('div.thumb.mvic-thumb img')
                anime_title = thumb_img['alt'] if thumb_img and thumb_img.has_attr('alt') else "Anime8 Video"
                anime_thumbnail = thumb_img['src'] if thumb_img and thumb_img.has_attr('src') else None
                
                watch_link = soup.select_one('div#mv-info > a')
                if not watch_link or not watch_link.has_attr('href'):
                    print("[ANIME8] Could not find watch link on series page")
                    return None
                    
                watch_url = watch_link['href']
                if watch_url.startswith('/'):
                    watch_url = base_url + watch_url
                    
                try:
                    from curl_cffi import requests as crequests
                    w_resp = crequests.get(watch_url, impersonate="chrome", timeout=15)
                except ImportError:
                    import requests
                    w_resp = requests.get(watch_url, headers=headers, timeout=15)
                    
                w_soup = BeautifulSoup(w_resp.text, 'html.parser')
                eps = w_soup.select('a[class*="btn-eps"]')
                
                entries = []
                for idx, ep in enumerate(eps):
                    href = ep.get('href')
                    if not href: continue
                    if href.startswith('/'): href = base_url + href
                    entries.append({
                        '_type': 'url',
                        'url': href,
                        'title': f"{anime_title} - Episode {idx + 1}",
                        'thumbnail': anime_thumbnail
                    })
                    
                if not entries:
                    return None
                    
                playlist_info = {
                    '_type': 'playlist',
                    'title': anime_title,
                    'thumbnail': anime_thumbnail,
                    'entries': entries,
                    'webpage_url': url,
                    '_is_anime8': True
                }
                
                try:
                    sample_ep_info = self._get_anime8_info(entries[0]['url'], settings)
                    if sample_ep_info and 'formats' in sample_ep_info:
                        playlist_info['formats'] = sample_ep_info['formats']
                        sample_duration = sample_ep_info.get('duration')
                        for entry in entries:
                            entry['formats'] = sample_ep_info['formats']
                            if sample_duration:
                                entry['duration'] = sample_duration
                except Exception as e:
                    print(f"[ANIME8] Failed to fetch sample episode formats: {e}")
                    
                return playlist_info
                
            else:
                title_el = soup.select_one('div.mvic-desc h3') or soup.select_one('h1')
                anime_title = title_el.text.strip() if title_el else "Anime8 Episode"
                
                thumb_img = soup.select_one('div.thumb.mvic-thumb img')
                anime_thumbnail = thumb_img['src'] if thumb_img and thumb_img.has_attr('src') else None
                
                ctk_m = re.search(r"ctk\s*=\s*'([^']*)'", resp.text)
                id_m = re.search(r"episode_id\s*=\s*['\"]?([^;'\"]*)", resp.text)
                
                if not ctk_m or not id_m:
                    print("[ANIME8] Missing ctk or episode_id")
                    return None
                    
                ctk = ctk_m.group(1)
                ep_id = id_m.group(1)
                
                # Prioritize mp4upload since yt-dlp parses its qualities perfectly. 
                # streamx often falls back to a generic extractor missing height metadata.
                servers = ['mp4upload', 'vidcdn', 'streamtape', 'streamx']
                
                for server in servers:
                    ajax_url = f"{base_url}/ajax/anime/load_episodes_v2?s={server}"
                    try:
                        try:
                            from curl_cffi import requests as crequests
                            ajax_resp = crequests.post(ajax_url, data={"episode_id": ep_id, "ctk": ctk}, impersonate="chrome", timeout=10)
                        except ImportError:
                            import requests
                            ajax_resp = requests.post(ajax_url, data={"episode_id": ep_id, "ctk": ctk}, headers=headers, timeout=10)
                            
                        json_data = ajax_resp.json()
                        if not json_data.get('status') or not json_data.get('value'):
                            continue
                            
                        html_val = json_data.get('value', '')
                        iframe_m = re.search(r'iframe\s*src.*?["\']([^"\']+)["\']', html_val.replace('\\', ''))
                        if not iframe_m:
                            continue
                            
                        embed_url = iframe_m.group(1)
                        if embed_url.startswith('//'):
                            embed_url = "https:" + embed_url
                            
                        info = self.get_video_info(embed_url, settings)
                        if info:
                            info['title'] = anime_title
                            info['_is_anime8'] = True
                            if anime_thumbnail:
                                info['thumbnail'] = anime_thumbnail
                                info['thumbnails'] = [{'url': anime_thumbnail, 'id': 'anime8'}]
                            return info
                            
                    except Exception as e:
                        print(f"[ANIME8] Error fetching embed from server {server}: {e}")
                        continue
                        
                return None
                
        except Exception as e:
            print(f"[ANIME8] Error fetching info: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_9anime_info(self, url, settings=None):
        import re
        import json
        import base64
        from bs4 import BeautifulSoup
        try:
            try:
                from curl_cffi import requests as crequests
                resp = crequests.get(url, impersonate="chrome", timeout=15)
            except ImportError:
                import requests
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code != 200:
                print(f"[9ANIME] Failed to fetch {url} (status {resp.status_code})")
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            title_el = soup.select_one('h1.entry-title') or soup.select_one('h1.title')
            anime_title = title_el.text.strip() if title_el else "9Anime Video"

            thumb_meta = soup.find('meta', property='og:image')
            anime_thumbnail = thumb_meta['content'] if thumb_meta and thumb_meta.get('content') else None

            # Check if this is a show/series page by looking for an episode list
            ep_links = []
            
            eplist = soup.find('div', class_='eplister')
            if eplist:
                for a in eplist.find_all('a'):
                    if a.get('href') and ('/episode' in a.get('href') or '-episode-' in a.get('href')):
                        ep_links.append(a.get('href'))
                        
            ul_list = soup.find('ul', class_='episodes-ul') or soup.find('ul', id='episodes')
            if ul_list and not ep_links:
                for a in ul_list.find_all('a'):
                    if a.get('href'):
                        ep_links.append(a.get('href'))
                        
            # Generic fallback for series pages
            if not ep_links and ('/anime/' in url or '/series/' in url):
                for a in soup.find_all('a'):
                    href = a.get('href')
                    if href and '-episode-' in href and href not in ep_links:
                        ep_links.append(href)
                        
            if ep_links:
                # Deduplicate while preserving order
                seen = set()
                unique_eps = []
                for link in ep_links:
                    if link.startswith('/'):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        link = f"{parsed.scheme}://{parsed.netloc}{link}"
                    if link not in seen:
                        seen.add(link)
                        unique_eps.append(link)
                        
                entries = []
                # Often listed latest-first on Animestream, check first/last
                is_reversed = False
                if unique_eps and '-episode-1/' in unique_eps[-1] and '-episode-1/' not in unique_eps[0]:
                    is_reversed = True
                    unique_eps.reverse()
                    
                for idx, ep_url in enumerate(unique_eps):
                    entries.append({
                        '_type': 'url',
                        'url': ep_url,
                        'title': f"{anime_title} - Episode {idx + 1}",
                        'thumbnail': anime_thumbnail,
                        'thumbnails': [{'url': anime_thumbnail, 'id': '9anime'}] if anime_thumbnail else []
                    })
                    
                if entries:
                    playlist_info = {
                        '_type': 'playlist',
                        'title': anime_title,
                        'thumbnail': anime_thumbnail,
                        'entries': entries,
                        'webpage_url': url,
                        '_is_9anime': True
                    }
                    
                    # Fetch formats from the latest episode (last in the list) to give the user accurate modern quality/size estimates
                    try:
                        sample_ep_info = self._get_9anime_info(entries[-1]['url'], settings)
                        
                        # Fallback to the first episode if the last one fails
                        if not sample_ep_info or 'formats' not in sample_ep_info:
                            if len(entries) > 1:
                                sample_ep_info = self._get_9anime_info(entries[0]['url'], settings)

                        if sample_ep_info and 'formats' in sample_ep_info:
                            playlist_info['formats'] = sample_ep_info['formats']
                            playlist_info['duration'] = sample_ep_info.get('duration')
                            
                            # Copy the formats and duration to all entries to allow accurate UI size estimations
                            sample_duration = sample_ep_info.get('duration')
                            for entry in entries:
                                entry['formats'] = sample_ep_info['formats']
                                if sample_duration:
                                    entry['duration'] = sample_duration
                    except Exception as e:
                        print(f"Failed to fetch sample episode formats: {e}")
                        
                    return playlist_info

            # Check if it's an Animestream clone (e.g. 9anime.org.lv)
            mirror_select = soup.select_one('select.mirror')
            if mirror_select:
                options = mirror_select.select('option[value]')
                for opt in options:
                    val = opt.get('value', '')
                    if not val: continue
                    try:
                        decoded_html = base64.b64decode(val).decode('utf-8')
                        iframe_m = re.search(r'src=["\']([^"\']+)["\']', decoded_html)
                        if iframe_m:
                            iframe_url = iframe_m.group(1)
                            # yt-dlp supports vidmoly, streamtape, mp4upload, streamwish, etc.
                            if any(x in iframe_url for x in ['vidmoly', 'streamtape', 'mp4upload', 'streamwish', 'dood']):
                                info = self.get_video_info(iframe_url, settings)
                                if info:
                                    info['title'] = f"{anime_title} ({opt.text.strip()})"
                                    info['_is_9anime'] = True
                                    
                                    # Assign 9anime thumbnail if available
                                    if anime_thumbnail:
                                        info['thumbnail'] = anime_thumbnail
                                        info['thumbnails'] = [{'url': anime_thumbnail, 'id': '9anime'}]
                                    else:
                                        # Sanitize empty thumbnails to prevent yt-dlp EmbedThumbnail crash
                                        if info.get('thumbnail') == "":
                                            info['thumbnail'] = None
                                        if 'thumbnails' in info and isinstance(info['thumbnails'], list):
                                            valid_thumbs = [t for t in info['thumbnails'] if t.get('url')]
                                            if valid_thumbs:
                                                info['thumbnails'] = valid_thumbs
                                            else:
                                                del info['thumbnails']
                                    return info
                    except Exception:
                        pass

            # Fallback to the real 9anime API logic
            player_wrapper = soup.select_one("div.player-wrapper")
            if not player_wrapper:
                print("[9ANIME] No valid player wrappers or mirrors found.")
                return None
            
            title_id = player_wrapper.get('data-id')
            if not title_id:
                print("[9ANIME] No data-id on player-wrapper.")
                return None
                
            domain_match = re.search(r'9anime\.([a-zA-Z0-9.]+)', url)
            extension = domain_match.group(1) if domain_match else 'org.lv'
            
            try:
                from curl_cffi import requests as crequests
                servers_resp = crequests.get(f"https://9anime.{extension}/ajax/anime/servers?id={title_id}", impersonate="chrome", timeout=10)
            except ImportError:
                servers_resp = requests.get(f"https://9anime.{extension}/ajax/anime/servers?id={title_id}", headers=headers, timeout=10)
                
            episode_html = servers_resp.text
            streamtape_regex = r'data-sources=[\'"](.*?"40".*?".*?".*?\})'
            streamtape_episodes = re.findall(streamtape_regex, episode_html)
            
            if not streamtape_episodes:
                print("[9ANIME] Unable to find streamtape server")
                return None
                
            entries = []
            for ep_data_str in streamtape_episodes:
                import html
                ep_data_str = html.unescape(ep_data_str)
                try:
                    ep_data = json.loads(ep_data_str)
                    ep_id = ep_data.get('40')
                    if not ep_id: continue
                        
                    try:
                        from curl_cffi import requests as crequests
                        ep_resp = crequests.get(f"https://9anime.{extension}/ajax/anime/episode?id={ep_id}", impersonate="chrome", timeout=10)
                    except ImportError:
                        ep_resp = requests.get(f"https://9anime.{extension}/ajax/anime/episode?id={ep_id}", headers=headers, timeout=10)
                        
                    encoded_url = ep_resp.json().get('url', '')
                    if not encoded_url: continue
                        
                    streamtape_url = self.decode9AnimeString(encoded_url)
                    if not streamtape_url: continue
                        
                    info = self.get_video_info(streamtape_url, settings)
                    if info:
                        info['title'] = anime_title
                        info['_is_9anime'] = True
                        if anime_thumbnail:
                            info['thumbnail'] = anime_thumbnail
                            info['thumbnails'] = [{'url': anime_thumbnail, 'id': '9anime'}]
                        else:
                            if info.get('thumbnail') == "":
                                info['thumbnail'] = None
                            if 'thumbnails' in info and isinstance(info['thumbnails'], list):
                                valid_thumbs = [t for t in info['thumbnails'] if t.get('url')]
                                if valid_thumbs:
                                    info['thumbnails'] = valid_thumbs
                                else:
                                    del info['thumbnails']
                        entries.append(info)
                except Exception as e:
                    print(f"[9ANIME] Error parsing episode data: {e}")
            
            if not entries:
                print("[9ANIME] No valid streamtape links successfully extracted")
                return None
                
            if len(entries) == 1:
                entries[0]['_is_9anime'] = True
                return entries[0]
            else:
                return {
                    "_type": "playlist",
                    "title": anime_title,
                    "entries": entries,
                    "webpage_url": url,
                    "_is_9anime": True
                }

        except Exception as e:
            print(f"[9ANIME] Error fetching info: {e}")
            import traceback
            traceback.print_exc()
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
                       custom_filename=None, info=None, is_image=False, image_ext=None, 
                       is_thumbnail=False, is_manga=False, selected_entries=None,
                       on_log=None, task_id=None, enable_sponsorblock=None):
        import json
        import re
        if 'idolcomplex.com' in url:
            m = re.search(r'idolcomplex\.com(?:/[a-z]{2})?/posts/([A-Za-z0-9_-]+)', url)
            if m:
                url = f"https://idol.sankakucomplex.com/post/show/{m.group(1)}"
        try:
            with open("C:/Users/sayan/Documents/GitHub/Any Downloader/debug_dl.json", "w", encoding="utf-8") as f:
                json.dump({
                    "url": url,
                    "format_id": format_id,
                    "is_image": is_image,
                    "image_ext": image_ext,
                    "info_ext": info.get('ext') if info else None,
                    "info_vcodec": info.get('vcodec') if info else None,
                    "info_extractor": info.get('extractor') if info else None,
                    "info_title": info.get('title') if info else None
                }, f, indent=2)
        except: pass
        
        # Ensure 9anime URLs are fully resolved before starting (fixes playlist episode downloads)
        if hasattr(self, 'is_9anime_url') and self.is_9anime_url(url):
            if not info or info.get('_type') == 'url' or not info.get('extractor'):
                resolved_info = self._get_9anime_info(url, settings)
                if resolved_info:
                    if info and info.get('title'):
                        resolved_info['title'] = info['title']
                    info = resolved_info
                    
        if not task_id:
            task_id = str(uuid.uuid4())
        self.active_tasks[task_id] = False
        final_downloaded_file = None

        final_downloaded_file = None
        
        if is_manga and selected_entries:
            def download_manga_task():
                import os
                import tempfile
                import requests as req_module
                req_kwargs = {}
                from PIL import Image
                import traceback
                try:
                    if on_progress:
                        on_progress({'percent': 0, 'status': 'Starting batch download...'})
                        
                    total = len(selected_entries)
                    downloaded_images = []
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        idx = 0
                        while idx < len(selected_entries):
                            entry = selected_entries[idx]
                            if self.active_tasks.get(task_id, False):
                                if on_error: on_error("Cancelled")
                                return
                            
                            entry_url = entry.get('url')
                            if not entry_url:
                                idx += 1
                                continue
                                
                            if on_progress:
                                on_progress({'percent': (idx / total) * 80, 'status': f'Downloading page {idx+1}/{total}...', 'filename': f'Page {idx+1}'})
                                
                            headers = {
                                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                                "Referer": url
                            }
                            if not req_kwargs.get('impersonate'):
                                headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            
                            try:
                                r = req_module.get(entry_url, headers=headers, timeout=15, **req_kwargs)
                                r.raise_for_status()
                                
                                temp_img_path = os.path.join(temp_dir, f"page_{idx:04d}.jpg")
                                with open(temp_img_path, 'wb') as f:
                                    f.write(r.content)
                                downloaded_images.append(temp_img_path)
                            except Exception as e:
                                if "404" in str(e) and idx == 0:
                                    if on_log: on_log(f"Links expired (404). Refreshing metadata...")
                                    try:
                                        new_info = self.get_video_info(url, settings)
                                        if new_info and new_info.get('entries'):
                                            # Update the list in-place so len(selected_entries) updates
                                            selected_entries[:] = new_info['entries']
                                            total = len(selected_entries)
                                            # Don't increment idx, just let the while loop retry idx 0
                                            continue
                                    except Exception as refetch_e:
                                        if on_log: on_log(f"Failed to refresh metadata: {refetch_e}")
                                        
                                if on_log: on_log(f"Failed to download page {idx+1}: {e}")
                            
                            idx += 1
                                
                        if not downloaded_images:
                            if on_error: on_error("No images could be downloaded.")
                            return
                            
                        # Format check
                        manga_ext = image_ext or 'pdf'
                        
                        if manga_ext == 'pdf':
                            if on_progress:
                                on_progress({'percent': 85, 'status': 'Generating PDF...'})
                                
                            # Merge images to PDF
                            pil_images = []
                            first_image = None
                            
                            for img_path in downloaded_images:
                                try:
                                    img = Image.open(img_path)
                                    if img.mode != 'RGB':
                                        img = img.convert('RGB')
                                    if not first_image:
                                        first_image = img
                                    else:
                                        pil_images.append(img)
                                except Exception as e:
                                    if on_log: on_log(f"Failed to process image {img_path}: {e}")
                                    
                            if not first_image:
                                if on_error: on_error("Failed to process downloaded images.")
                                return
                                
                            base_name = custom_filename or "Manga.pdf"
                            if base_name.lower().endswith('.pdf'):
                                base_no_ext = base_name[:-4]
                            else:
                                base_no_ext = base_name
                                base_name = f"{base_no_ext}.pdf"
                                
                            final_path = os.path.join(output_path, base_name)
                            counter = 1
                            while os.path.exists(final_path):
                                final_path = os.path.join(output_path, f"{base_no_ext} ({counter}).pdf")
                                counter += 1
                                
                            first_image.save(final_path, "PDF", resolution=100.0, save_all=True, append_images=pil_images)
                        elif manga_ext == 'epub':
                            if on_progress:
                                on_progress({'percent': 85, 'status': 'Generating EPUB...'})
                                
                            import zipfile
                            
                            base_name = custom_filename or "Manga.epub"
                            if base_name.lower().endswith('.epub'):
                                base_no_ext = base_name[:-5]
                            else:
                                base_no_ext = base_name
                                base_name = f"{base_no_ext}.epub"
                                
                            final_path = os.path.join(output_path, base_name)
                            counter = 1
                            while os.path.exists(final_path):
                                final_path = os.path.join(output_path, f"{base_no_ext} ({counter}).epub")
                                counter += 1
                                
                            with zipfile.ZipFile(final_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                                epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                                epub.writestr('META-INF/container.xml', '<?xml version="1.0"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n  </rootfiles>\n</container>')
                                
                                manifest_items = ""
                                spine_items = ""
                                for idx, img_path in enumerate(downloaded_images):
                                    page_id = f"page_{idx+1:04d}"
                                    img_name = f"{page_id}.jpg"
                                    html_name = f"{page_id}.xhtml"
                                    
                                    epub.write(img_path, f"OEBPS/{img_name}")
                                    
                                    html_content = f'<?xml version="1.0" encoding="UTF-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml">\n<head><title>Page {idx+1}</title></head>\n<body style="margin:0;padding:0;text-align:center;">\n<img src="{img_name}" style="max-width:100%;height:auto;"/>\n</body>\n</html>'
                                    epub.writestr(f"OEBPS/{html_name}", html_content)
                                    
                                    manifest_items += f'    <item id="img_{page_id}" href="{img_name}" media-type="image/jpeg"/>\n'
                                    manifest_items += f'    <item id="html_{page_id}" href="{html_name}" media-type="application/xhtml+xml"/>\n'
                                    spine_items += f'    <itemref idref="html_{page_id}"/>\n'
                                    
                                content_opf = f'<?xml version="1.0" encoding="UTF-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">\n  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n    <dc:title>{base_no_ext}</dc:title>\n    <dc:language>en</dc:language>\n  </metadata>\n  <manifest>\n{manifest_items}  </manifest>\n  <spine>\n{spine_items}  </spine>\n</package>'
                                epub.writestr('OEBPS/content.opf', content_opf)
                        else:
                            if on_progress:
                                on_progress({'percent': 85, 'status': 'Processing images...'})
                                
                            # Save as individual images in a folder
                            folder_name = custom_filename or "Manga Batch"
                            base_final_path = os.path.join(output_path, folder_name)
                            final_path = base_final_path
                            counter = 1
                            while os.path.exists(final_path):
                                final_path = f"{base_final_path} ({counter})"
                                counter += 1
                                
                            os.makedirs(final_path)
                                
                            for idx, img_path in enumerate(downloaded_images):
                                try:
                                    if manga_ext == 'gif':
                                        import shutil
                                        out_img_path = os.path.join(final_path, f"page_{idx+1:04d}.{manga_ext}")
                                        shutil.move(img_path, out_img_path)
                                    else:
                                        img = Image.open(img_path)
                                        if img.mode != 'RGB' and manga_ext == 'jpg':
                                            img = img.convert('RGB')
                                        out_img_path = os.path.join(final_path, f"page_{idx+1:04d}.{manga_ext}")
                                        img.save(out_img_path, format=manga_ext.upper() if manga_ext != 'jpg' else 'JPEG')
                                except Exception as e:
                                    if on_log: on_log(f"Failed to save image {img_path}: {e}")
                        
                        if on_progress:
                            on_progress({'percent': 100, 'status': 'finished', 'filename': os.path.basename(final_path)})
                            
                        if on_finish:
                            on_finish(final_path)
                            
                except Exception as e:
                    traceback.print_exc()
                    if on_error: on_error(str(e))
                finally:
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
                        
            if self.run_thread:
                self.run_thread(download_manga_task)
            else:
                threading.Thread(target=download_manga_task, daemon=True).start()
            return task_id

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
                        
                    # Fallback for playlists without a top-level thumbnail
                    if not thumb_url and info and info.get('_type') == 'playlist':
                        entries = info.get('entries', [])
                        if entries:
                            first = entries[0]
                            thumb_url = first.get('thumbnail') or (first.get('thumbnails', [{}])[0].get('url', '') if first.get('thumbnails') else '')
                    
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
                if d.get('info_dict', {}).get('_filename'):
                    final_downloaded_file = d['info_dict']['_filename']
                elif d.get('filename'):
                    final_downloaded_file = d['filename']
                
        def _pp_hook(d):
            nonlocal final_downloaded_file
            print(f"[DEBUG] _pp_hook status: {d.get('status')}, postprocessor: {d.get('postprocessor')}")
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
                if d.get('postprocessor') in ['ThumbnailsConvertor', 'Metadata', 'EmbedThumbnail']:
                    pass # Don't update final path for these side-effects
                elif d.get('postprocessor') == 'MoveFiles':
                    if d.get('info_dict', {}).get('_filename'):
                        final_downloaded_file = d['info_dict']['_filename']
                else:
                    if d.get('info_dict', {}).get('filepath'):
                        final_downloaded_file = d['info_dict']['filepath']
                    elif d.get('info_dict', {}).get('_filename'):
                        final_downloaded_file = d['info_dict']['_filename']
                    elif d.get('filepath'):
                        final_downloaded_file = d['filepath']
                
        def download_task():
            nonlocal info
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
                    print(msg)
                    if on_log: on_log(f"ERROR: {msg}")

            from src.backend.ffmpeg_manager import get_ffmpeg_path
            
            local_format_id = format_id
            if local_format_id == 'best' and not is_image and not is_audio and not is_manga:
                local_format_id = 'bestvideo+bestaudio/best'
            if video_ext in ['mp4', 'mov']:
                # Prefer h264/h265 codecs for mp4 and mov to avoid container incompatibility (e.g. AV1 in MOV)
                if local_format_id and 'bestvideo' in local_format_id and '[vcodec' not in local_format_id:
                    local_format_id = local_format_id.replace('bestvideo', 'bestvideo[vcodec~="^((he|a)vc|h26[45])"]')
                # Also prefer m4a (AAC) audio over opus for mov container
                if local_format_id and '+bestaudio' in local_format_id and '[ext' not in local_format_id.split('+bestaudio')[1]:
                    local_format_id = local_format_id.replace('+bestaudio', '+bestaudio[ext=m4a]')
            elif video_ext == 'webm':
                # Force yt-dlp to pick WebM-compatible native formats (VP9/AV1) to avoid transcoding
                if local_format_id and 'bestvideo' in local_format_id and '[ext' not in local_format_id:
                    local_format_id = local_format_id.replace('bestvideo', 'bestvideo[ext=webm]')
                if local_format_id and '+bestaudio' in local_format_id and 'ext=webm' not in local_format_id.split('+bestaudio')[1]:
                    local_format_id = local_format_id.replace('+bestaudio', '+bestaudio[ext=webm]')
                if '/best' in local_format_id and '/best[' not in local_format_id:
                    local_format_id = local_format_id.replace('/best', '/best[ext=webm]')
            
            ydl_opts = {
                'format': local_format_id,
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
                'file_access_retries': 30,
                'trim_file_name': 150,
                'js_runtimes': {
                    'node': {},
                    'deno': {},
                    'bun': {},
                    'quickjs': {},
                },
                'remote_components': ['ejs:github'],
            }
            
            if is_image:
                ydl_opts['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Dest': 'image'
                }
            elif info and info.get('original_url') and (not info.get('extractor') or info.get('extractor') == 'generic'):
                # For direct stream links and generic extractor,
                # provide a Referer and standard User-Agent to bypass CDN hotlink protection
                import urllib.parse
                parsed = urllib.parse.urlparse(info['original_url'])
                origin = f"{parsed.scheme}://{parsed.netloc}/"
                ydl_opts['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': origin
                }

            if settings:
                temp_path = settings.get('temp_download_path')
                if temp_path and os.path.exists(temp_path):
                    unique_temp = os.path.join(temp_path, task_id)
                    os.makedirs(unique_temp, exist_ok=True)
                    ydl_opts['paths']['temp'] = unique_temp
                    
                cookies_path = settings.get('cookies_path')
                browser_cookies = settings.get('browser_cookies', 'none')
                
                if cookies_path and os.path.exists(cookies_path):
                    ydl_opts['cookiefile'] = cookies_path
                elif browser_cookies and browser_cookies != 'none':
                    ydl_opts['cookiesfrombrowser'] = (browser_cookies, )

            if video_ext and not is_audio and not is_image:
                ydl_opts['merge_output_format'] = video_ext
                if 'postprocessors' not in ydl_opts:
                    ydl_opts['postprocessors'] = []
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': video_ext,
                })

            # Speed limit
            if settings:
                speed_limit = settings.get('speed_limit', 0)
                if speed_limit and speed_limit > 0:
                    ydl_opts['ratelimit'] = speed_limit

                hw_accel = settings.get('hw_accel', 'auto')
                if hw_accel and hw_accel != 'none':
                    for arg_dict_name in ('postprocessor_args', 'external_downloader_args'):
                        ydl_opts.setdefault(arg_dict_name, {})
                        if 'ffmpeg_i' not in ydl_opts[arg_dict_name]:
                            ydl_opts[arg_dict_name]['ffmpeg_i'] = []
                        if hw_accel == 'cuda':
                            ydl_opts[arg_dict_name]['ffmpeg_i'].extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
                        else:
                            ydl_opts[arg_dict_name]['ffmpeg_i'].extend(['-hwaccel', hw_accel])

            postprocessors = []

            is_playlist = info and info.get('_type') in ['playlist', 'album']
            if video_ext and not is_audio and not is_image and not is_playlist:
                postprocessors.append({
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': video_ext,
                })

            if is_audio:
                final_audio_codec = audio_codec or (settings.get('audio_codec', 'mp3') if settings else 'mp3')
                final_audio_quality = audio_quality or (settings.get('audio_quality', '192') if settings else '192')
                
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': final_audio_codec,
                    'preferredquality': final_audio_quality,
                })
                
                if final_audio_codec in ['mp3', 'm4a'] and final_audio_quality and final_audio_quality not in ['0', 'best']:
                    ydl_opts.setdefault('postprocessor_args', {})
                    if 'ExtractAudio' not in ydl_opts['postprocessor_args']:
                        ydl_opts['postprocessor_args']['ExtractAudio'] = []
                    ydl_opts['postprocessor_args']['ExtractAudio'].extend(['-b:a', f'{final_audio_quality}k'])

            # Embed subtitles — per-download override takes priority over settings
            should_embed_subs = embed_subtitles if embed_subtitles is not None else (
                settings.get('embed_subtitles', False) if settings else False
            )
            if should_embed_subs:
                raw_lang = subtitle_lang or (settings.get('auto_subtitle_lang', 'en') if settings else 'en')
                if isinstance(raw_lang, str):
                    langs = [l.strip() for l in raw_lang.replace(';', ',').split(',') if l.strip()]
                elif isinstance(raw_lang, (list, tuple)):
                    langs = [str(l).strip() for l in raw_lang if str(l).strip()]
                else:
                    langs = ['en']

                if not langs:
                    langs = ['en']

                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = langs
                postprocessors.append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})
                postprocessors.append({'key': 'FFmpegEmbedSubtitle'})

            # SponsorBlock (YouTube)
            should_sponsorblock = enable_sponsorblock if enable_sponsorblock is not None else (
                settings.get('enable_sponsorblock', False) if settings else False
            )
            if should_sponsorblock and not is_image:
                sb_action = settings.get('sponsorblock_action', 'remove') if settings else 'remove'
                raw_cats = settings.get('sponsorblock_categories', ['sponsor', 'selfpromo', 'interaction', 'intro', 'outro']) if settings else ['sponsor']
                sb_cats = set(raw_cats) if raw_cats else {'sponsor'}

                postprocessors.append({
                    'key': 'SponsorBlock',
                    'categories': sb_cats,
                    'when': 'after_filter'
                })

                if sb_action == 'remove':
                    removable_cats = sb_cats - {'poi_highlight', 'chapter'}
                    if removable_cats:
                        postprocessors.append({
                            'key': 'ModifyChapters',
                            'remove_sponsor_segments': removable_cats,
                            'force_keyframes': False
                        })
                elif sb_action == 'remove_and_mark':
                    removable_cats = sb_cats - {'poi_highlight', 'chapter'}
                    postprocessors.append({
                        'key': 'ModifyChapters',
                        'remove_sponsor_segments': removable_cats,
                        'sponsorblock_chapter_title': '[SponsorBlock]: %(category_names)l',
                        'force_keyframes': False
                    })
                else:
                    postprocessors.append({
                        'key': 'ModifyChapters',
                        'sponsorblock_chapter_title': '[SponsorBlock]: %(category_names)l',
                    })

            # Embed chapters
            should_embed_chapters = settings.get('embed_chapters', True) if settings else True
            if is_image:
                should_embed_chapters = False
            ydl_opts['addchapters'] = should_embed_chapters

            # Embed metadata
            should_embed_metadata = settings.get('embed_metadata', True) if settings else True
            if is_image:
                should_embed_metadata = False
            ydl_opts.setdefault('external_downloader_args', {})
            if 'ffmpeg' not in ydl_opts['external_downloader_args']:
                ydl_opts['external_downloader_args']['ffmpeg'] = []
            ydl_opts['external_downloader_args']['ffmpeg'].extend(['-loglevel', 'info'])

            if should_embed_metadata or should_embed_chapters:
                postprocessors.append({
                    'key': 'FFmpegMetadata',
                    'add_metadata': should_embed_metadata,
                    'add_chapters': should_embed_chapters
                })
                
                ydl_opts.setdefault('postprocessor_args', {})
                if 'ffmpeg' not in ydl_opts['postprocessor_args']:
                    ydl_opts['postprocessor_args']['ffmpeg'] = []
                
                # Windows File Explorer doesn't support the default ID3v2.4 tags for mp3s, so we force ID3v2.3
                if is_audio and final_audio_codec == 'mp3':
                    ydl_opts['postprocessor_args']['ffmpeg'].extend(['-id3v2_version', '3'])
                
                # If part of a playlist, inject the track number manually since it's a standalone download
                if info and info.get('playlist_index'):
                    ydl_opts['postprocessor_args']['ffmpeg'].extend(['-metadata', f'track={info["playlist_index"]}'])

            # Embed thumbnail — must be AFTER metadata so ffmpeg doesn't strip the mutagen thumbnail
            should_embed_thumb = embed_thumbnail if embed_thumbnail is not None else (
                settings.get('embed_thumbnail', True) if settings else True
            )
            
            # Disable thumbnail embedding for WAV since ffmpeg doesn't support it
            if should_embed_thumb and is_audio and final_audio_codec == 'wav':
                should_embed_thumb = False
                
            # Disable thumbnail embedding for WebM since ffmpeg doesn't support it without massive transcoding to mp4/mkv
            if should_embed_thumb and not is_audio and video_ext == 'webm':
                should_embed_thumb = False

            # Disable thumbnail embedding for images, since they are already images
            if is_image:
                should_embed_thumb = False
                
            # Disable thumbnail embedding if we already know there's no thumbnail AND it's not a playlist
            if info and not is_playlist and not info.get('thumbnail'):
                should_embed_thumb = False
                
            # Disable thumbnail embedding for 9anime so Windows can auto-generate a frame from the video
            is_9anime = info.get('_is_9anime') if info else False
            if hasattr(self, 'is_9anime_url') and self.is_9anime_url(url):
                is_9anime = True
                
            is_anime8 = info.get('_is_anime8') if info else False
            if hasattr(self, 'is_anime8_url') and self.is_anime8_url(url):
                is_anime8 = True
                
            if is_9anime or is_anime8:
                should_embed_thumb = False
                
            if should_embed_thumb:
                ydl_opts['writethumbnail'] = True
                postprocessors.append({
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                })
                postprocessors.append({'key': 'EmbedThumbnail'})

            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors

            try:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        def _auto_rename_filter(info_dict, *args, **kwargs):
                            if info_dict.get('extractor') in ['generic', 'html5'] and ('ok.porn' in info_dict.get('webpage_url', '') or 'pornstars.tube' in info_dict.get('webpage_url', '')):
                                for f in info_dict.get('formats', []):
                                    f_url = f.get('url', '')
                                    if '.mp4/' in f_url or f_url.endswith('.mp4'):
                                        f['protocol'] = 'm3u8_native'
                                if '.mp4/' in info_dict.get('url', '') or info_dict.get('url', '').endswith('.mp4'):
                                    info_dict['protocol'] = 'm3u8_native'
                                    
                            # Sanitize empty string thumbnails extracted natively by yt-dlp to prevent EmbedThumbnail crash
                            if info_dict.get('thumbnail') == "":
                                info_dict['thumbnail'] = None
                                
                            if info:
                                # Ensure thumbnail array exists so yt-dlp downloads it for embedding
                                thumb = info.get('thumbnail')
                                if not thumb and info.get('original_url') and 'archive.org/details/' in info.get('original_url'):
                                    import re
                                    m = re.search(r'archive\.org/details/([^/?#&]+)', info.get('original_url'))
                                    if m:
                                        thumb = f"https://archive.org/services/img/{m.group(1)}"
                                        
                                if thumb:
                                    info_dict['thumbnail'] = thumb
                                    info_dict['thumbnails'] = [{'url': thumb, 'id': 'custom'}]
                                    
                            if 'thumbnails' in info_dict and isinstance(info_dict['thumbnails'], list):
                                valid_thumbs = [t for t in info_dict['thumbnails'] if t.get('url')]
                                for t in valid_thumbs:
                                    if 'jamendo.com' in t.get('url', '').lower() or t.get('ext') == 'com':
                                        t['ext'] = 'jpg'
                                if valid_thumbs:
                                    info_dict['thumbnails'] = valid_thumbs
                                else:
                                    del info_dict['thumbnails']
                                

                                # Ensure metadata fields are propagated for FFmpegMetadata
                                for key in ['uploader', 'artist', 'album', 'description']:
                                    if info.get(key) and not info_dict.get(key):
                                        info_dict[key] = info[key]
                            original_title = info_dict.get('title')
                            if not original_title:
                                return None
                            target_ext = info_dict.get('ext')
                            if is_audio:
                                target_ext = final_audio_codec
                                # Windows File Explorer requires an album tag to display m4a thumbnails
                                if target_ext == 'm4a' and not info_dict.get('album'):
                                    info_dict['album'] = original_title or 'Unknown Album'
                            elif video_ext and not is_image:
                                target_ext = ydl.params.get('merge_output_format') or video_ext
                                
                            for i in range(1, 1000):
                                temp_info = info_dict.copy()
                                if target_ext:
                                    temp_info['ext'] = target_ext
                                if i > 1:
                                    temp_info['title'] = f"{original_title} ({i})"
                                
                                final_path = ydl.prepare_filename(temp_info)
                                if not os.path.exists(final_path):
                                    if i > 1:
                                        info_dict['title'] = temp_info['title']
                                    break
                                    
                            try:
                                if on_log:
                                    d_type = "Image" if is_image else ("Audio" if is_audio else "Video")
                                    if is_audio:
                                        q = f"{audio_quality}kbps" if audio_quality else "best"
                                    else:
                                        q = info_dict.get('resolution') or info_dict.get('format_note') or "best"
                                    file_name = os.path.basename(final_path)
                                    on_log(f"--- Download Info ---")
                                    on_log(f"Type: {d_type}")
                                    on_log(f"Format: {target_ext}")
                                    on_log(f"Quality: {q}")
                                    on_log(f"File Name: {file_name}")
                                    on_log(f"Location: {final_path}")
                                    on_log(f"---------------------")
                            except Exception: pass
                            
                            return None
                            
                        ydl.params['match_filter'] = _auto_rename_filter
                        
                        if info and info.get('_type') == 'url':
                            # Resolve custom URLs that yt-dlp cannot extract natively
                            target_url = info.get('url', url)
                            if (hasattr(self, 'is_9anime_url') and self.is_9anime_url(target_url)) or \
                               (hasattr(self, 'is_anime8_url') and self.is_anime8_url(target_url)) or \
                               (hasattr(self, 'is_animeflv_url') and self.is_animeflv_url(target_url)):
                                resolved_info = self.get_video_info(target_url, settings)
                                if resolved_info:
                                    # Preserve custom playlist title and thumbnail
                                    if info.get('title'):
                                        resolved_info['title'] = info['title']
                                    if info.get('thumbnail'):
                                        resolved_info['thumbnail'] = info['thumbnail']
                                    info = resolved_info
                        
                        use_info = False
                        if info:
                            is_generic = info.get('extractor') == 'generic'
                            is_custom = not info.get('extractor')
                            is_gallery_dl = info.get('extractor') == 'gallery-dl'
                            is_speakerdeck = info.get('extractor') == 'speakerdeck'
                            is_playlist_entry = info.get('playlist_index') is not None
                            
                            if is_playlist_entry or is_custom or is_gallery_dl or is_speakerdeck or (is_image and is_generic) or (hasattr(self, 'is_9anime_url') and self.is_9anime_url(url)) or (hasattr(self, 'is_anime8_url') and self.is_anime8_url(url)) or (hasattr(self, 'is_animeflv_url') and self.is_animeflv_url(url)):
                                use_info = True

                        if use_info:
                            def _ensure_extractor(d, ext, ext_key):
                                if isinstance(d, dict):
                                    if 'extractor' not in d:
                                        d['extractor'] = ext
                                    if 'extractor_key' not in d:
                                        d['extractor_key'] = ext_key
                                    if d.get('_type') == 'playlist' and 'entries' in d:
                                        for e in d['entries']:
                                            if e: _ensure_extractor(e, ext, ext_key)
                            
                            _ensure_extractor(info, info.get('extractor', 'generic'), info.get('extractor_key', 'Generic'))
                            error_code = ydl.process_ie_result(info, download=True)
                        else:
                            error_code = ydl.download([url])
                except Exception as e:
                    yt_err_str = str(e).lower()
                    if "cookie" in yt_err_str and ("could not copy" in yt_err_str or "permission" in yt_err_str or "locked" in yt_err_str):
                        raise Exception(f"Failed to access {browser_cookies} cookies. Please close your browser completely and try again, or export a cookies.txt file.")
                    
                    # Fallback for direct media links (like .gif or .jpg) that yt-dlp's generic extractor rejects
                    is_unsupported = "unsupported url" in yt_err_str or "unable to download webpage" in yt_err_str or "403: forbidden" in yt_err_str
                    if is_unsupported and any(url.lower().split('?')[0].endswith(x) for x in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf', '.mp4', '.webm', '.mov']):
                        try:
                            from curl_cffi import requests as crequests
                            req_module = crequests
                            req_kwargs = {'impersonate': 'chrome110'}
                        except ImportError:
                            import requests as crequests
                            req_module = crequests
                            req_kwargs = {}
                            
                        import re
                        if on_log: on_log(f"yt-dlp rejected URL. Falling back to direct download for {url}")
                        
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                            "Referer": url
                        }
                        
                        r = req_module.get(url, stream=True, headers=headers, timeout=15, **req_kwargs)
                        r.raise_for_status()
                        total_size = int(r.headers.get('content-length', 0))
                        
                        ext = url.split('.')[-1].split('?')[0]
                        if len(ext) > 4 or not ext.isalnum(): ext = 'jpg'
                        
                        title = info.get('title', 'Media') if info else 'Media'
                        title = re.sub(r'[\\/*?:"<>|]', "", title)
                        
                        if custom_filename:
                            final_name = custom_filename.replace('%(ext)s', ext).replace('%(title)s', title)
                        else:
                            tmpl = filename_template if filename_template else '%(title)s.%(ext)s'
                            final_name = tmpl.replace('%(title)s', title).replace('%(ext)s', ext)
                            
                        final_path = os.path.join(output_path, final_name)
                        
                        downloaded = 0
                        with open(final_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if self.active_tasks.get(task_id, False):
                                    raise Exception("Download cancelled by user")
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if on_progress and total_size > 0:
                                        on_progress({
                                            'percent': (downloaded / total_size) * 100,
                                            'speed': '',
                                            'eta': '',
                                            'downloaded_bytes': downloaded,
                                            'total_bytes': total_size,
                                            'filename': final_name,
                                            'status': 'downloading'
                                        })
                        
                        final_downloaded_file = final_path
                        if on_progress:
                            on_progress({
                                'percent': 100,
                                'speed': '',
                                'eta': '',
                                'downloaded_bytes': downloaded,
                                'total_bytes': total_size,
                                'filename': final_name,
                                'status': 'finished'
                            })
                    elif "unable to embed using ffprobe" in yt_err_str:
                        if on_log: on_log("WARNING: Thumbnail embedding failed, but the download succeeded.")
                        import shutil
                        if final_downloaded_file and not os.path.exists(final_downloaded_file):
                            base_path = os.path.splitext(final_downloaded_file)[0]
                            for ext in ['.mp4', '.mkv', '.webm', '.mov']:
                                if os.path.exists(base_path + ext):
                                    final_downloaded_file = base_path + ext
                                    break
                        
                        if final_downloaded_file and os.path.exists(final_downloaded_file):
                            try:
                                file_name = os.path.basename(final_downloaded_file)
                                dest_path = os.path.join(output_path, file_name)
                                if os.path.abspath(final_downloaded_file) != os.path.abspath(dest_path):
                                    if os.path.exists(dest_path):
                                        os.remove(dest_path)
                                    shutil.move(final_downloaded_file, dest_path)
                                    final_downloaded_file = dest_path
                                    if on_log: on_log(f"Moved final file to: {dest_path}")
                            except Exception as move_ex:
                                if on_log: on_log(f"WARNING: Failed to move file to destination: {move_ex}")
                        pass # Ignore error as file is downloaded
                    else:
                        raise e
                    
                if is_image and final_downloaded_file and os.path.exists(final_downloaded_file):
                    import subprocess
                    
                    downloaded_file = final_downloaded_file
                    current_ext = os.path.splitext(downloaded_file)[1].lstrip('.').lower()
                    
                    # Detect actual image format from magic bytes
                    detected_ext = None
                    try:
                        with open(downloaded_file, 'rb') as bf:
                            header = bf.read(16)
                        if header[:3] == b'\xff\xd8\xff':
                            detected_ext = 'jpg'
                        elif header[:8] == b'\x89PNG\r\n\x1a\n':
                            detected_ext = 'png'
                        elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                            detected_ext = 'webp'
                        elif header[:6] in (b'GIF87a', b'GIF89a'):
                            detected_ext = 'gif'
                        elif header[:2] == b'BM':
                            detected_ext = 'bmp'
                    except:
                        pass
                    
                    target_ext = image_ext or detected_ext or 'jpg'
                    
                    # If current extension is wrong/unknown, rename or convert
                    if current_ext != target_ext:
                        base_path = os.path.splitext(downloaded_file)[0]
                        target_file = f"{base_path}.{target_ext}"
                        
                        # Simple rename when actual format matches target or extension is just wrong
                        if detected_ext and (detected_ext == target_ext or current_ext in ('unknown_video', '')):
                            try:
                                os.rename(downloaded_file, target_file)
                                final_downloaded_file = target_file
                            except Exception as ex:
                                print(f"[IMAGE RENAME ERROR] {ex}")
                        else:
                            # Genuine format conversion needed
                            try:
                                if target_ext == 'pdf':
                                    from PIL import Image
                                    with Image.open(downloaded_file) as img:
                                        if img.mode != 'RGB':
                                            img = img.convert('RGB')
                                        img.save(target_file, "PDF", resolution=100.0)
                                    os.remove(downloaded_file)
                                    final_downloaded_file = target_file
                                else:
                                    ffmpeg_exe = 'ffmpeg'
                                    local_dir = get_ffmpeg_path()
                                    if local_dir:
                                        ffmpeg_exe = os.path.join(local_dir, 'ffmpeg.exe')
                                    
                                    subprocess.run([
                                        ffmpeg_exe, '-y', '-i', downloaded_file, target_file
                                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                                    os.remove(downloaded_file)
                                    final_downloaded_file = target_file
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
                if final_downloaded_file:
                    try:
                        import time
                        time.sleep(0.5)
                        base = os.path.splitext(final_downloaded_file)[0]
                        print("[DEBUG] base path:", base)
                        for ext in ['.temp.mp4', '.temp.mkv', '.temp.webm', '.temp.mov']:
                            if os.path.exists(base + ext):
                                print("[DEBUG] deleting:", base + ext)
                                try:
                                    os.remove(base + ext)
                                except Exception as d_e:
                                    print("Delete error:", d_e)
                    except: pass
                
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                    
                # Clean up unique temp directory
                if 'unique_temp' in locals() and unique_temp and os.path.exists(unique_temp):
                    try:
                        import shutil
                        shutil.rmtree(unique_temp, ignore_errors=True)
                    except Exception:
                        pass
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
            original_thumbnail_url = None
            album_name = None
            if info:
                track_name = info.get('track') or info.get('fulltitle') or info.get('title')
                artist = info.get('artist') or info.get('uploader') or info.get('creator', '')
                duration_s = info.get('duration')
                original_thumbnail_url = info.get('thumbnail') or (info.get('thumbnails', [{}])[0].get('url') if info.get('thumbnails') else None)
                album_name = info.get('album')
            
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
                            if data.get('album') and data['album'].get('images'): original_thumbnail_url = data['album']['images'][0]['url']
                            if data.get('album'): album_name = data['album'].get('name')
                elif self.is_applemusic_url(url):
                    apple_info = self._get_applemusic_info(url)
                    if apple_info:
                        if apple_info.get('_type') == 'playlist':
                            apple_info = apple_info.get('entries', [{}])[0]
                        track_name = apple_info.get('track') or apple_info.get('fulltitle') or apple_info.get('title')
                        artist = apple_info.get('artist') or apple_info.get('uploader', '')
                        if apple_info.get('thumbnail'): original_thumbnail_url = apple_info.get('thumbnail')
                        if apple_info.get('album'): album_name = apple_info.get('album')
                elif self.is_tidal_url(url):
                    tidal_info = self._get_tidal_info(url)
                    if tidal_info:
                        if tidal_info.get('_type') == 'playlist' or tidal_info.get('type') == 'playlist':
                            tidal_info = tidal_info.get('entries', [{}])[0]
                        track_name = tidal_info.get('title')
                        artist = tidal_info.get('uploader')
                        duration_s = tidal_info.get('duration')
                        if tidal_info.get('thumbnail'): original_thumbnail_url = tidal_info.get('thumbnail')
                        if tidal_info.get('album'): album_name = tidal_info.get('album')
                elif self.is_deezer_url(url):
                    deezer_info = self._get_deezer_info(url)
                    if deezer_info:
                        if deezer_info.get('type') == 'playlist':
                            deezer_info = deezer_info.get('entries', [{}])[0]
                        track_name = deezer_info.get('title')
                        artist = deezer_info.get('uploader')
                        duration_s = deezer_info.get('duration')
                        if deezer_info.get('thumbnail'): original_thumbnail_url = deezer_info.get('thumbnail')
                        if deezer_info.get('album'): album_name = deezer_info.get('album')

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
                'file_access_retries': 30,
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

                hw_accel = settings.get('hw_accel', 'auto')
                if hw_accel and hw_accel != 'none':
                    for arg_dict_name in ('postprocessor_args', 'external_downloader_args'):
                        ydl_opts.setdefault(arg_dict_name, {})
                        if 'ffmpeg_i' not in ydl_opts[arg_dict_name]:
                            ydl_opts[arg_dict_name]['ffmpeg_i'] = []
                        if hw_accel == 'cuda':
                            ydl_opts[arg_dict_name]['ffmpeg_i'].extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
                        else:
                            ydl_opts[arg_dict_name]['ffmpeg_i'].extend(['-hwaccel', hw_accel])

            postprocessors = []
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': fmt,
                'preferredquality': bitrate,
            })
            
            if fmt in ['mp3', 'm4a'] and bitrate and bitrate not in ['0', 'best']:
                ydl_opts.setdefault('postprocessor_args', {})
                if 'ExtractAudio' not in ydl_opts['postprocessor_args']:
                    ydl_opts['postprocessor_args']['ExtractAudio'] = []
                ydl_opts['postprocessor_args']['ExtractAudio'].extend(['-b:a', f'{bitrate}k'])

            # Embed metadata
            should_embed_metadata = settings.get('embed_metadata', True) if settings else True
            if should_embed_metadata:
                postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                ydl_opts.setdefault('postprocessor_args', {})
                if 'ffmpeg' not in ydl_opts['postprocessor_args']:
                    ydl_opts['postprocessor_args']['ffmpeg'] = []
                if fmt == 'mp3':
                    ydl_opts['postprocessor_args']['ffmpeg'].extend(['-id3v2_version', '3'])

            # SponsorBlock (YouTube fallback)
            should_sponsorblock = settings.get('enable_sponsorblock', False) if settings else False
            if should_sponsorblock:
                sb_action = settings.get('sponsorblock_action', 'remove') if settings else 'remove'
                raw_cats = settings.get('sponsorblock_categories', ['sponsor', 'selfpromo', 'interaction', 'intro', 'outro']) if settings else ['sponsor']
                sb_cats = set(raw_cats) if raw_cats else {'sponsor'}

                postprocessors.append({
                    'key': 'SponsorBlock',
                    'categories': sb_cats,
                    'when': 'after_filter'
                })

                if sb_action == 'remove':
                    removable_cats = sb_cats - {'poi_highlight', 'chapter'}
                    if removable_cats:
                        postprocessors.append({
                            'key': 'ModifyChapters',
                            'remove_sponsor_segments': removable_cats,
                            'force_keyframes': False
                        })
                elif sb_action == 'remove_and_mark':
                    removable_cats = sb_cats - {'poi_highlight', 'chapter'}
                    postprocessors.append({
                        'key': 'ModifyChapters',
                        'remove_sponsor_segments': removable_cats,
                        'sponsorblock_chapter_title': '[SponsorBlock]: %(category_names)l',
                        'force_keyframes': False
                    })
                else:
                    postprocessors.append({
                        'key': 'ModifyChapters',
                        'sponsorblock_chapter_title': '[SponsorBlock]: %(category_names)l',
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
                postprocessors.append({
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                })
                postprocessors.append({'key': 'EmbedThumbnail'})

            ydl_opts['postprocessors'] = postprocessors

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    def _auto_rename_filter(info_dict, *args, **kwargs):
                        if original_thumbnail_url:
                            info_dict['thumbnails'] = [{'url': original_thumbnail_url, 'id': 'custom_original'}]
                            info_dict['thumbnail'] = original_thumbnail_url
                        if track_name:
                            info_dict['title'] = track_name
                        if artist:
                            info_dict['artist'] = artist
                            info_dict['uploader'] = artist
                            info_dict['creator'] = artist
                        if album_name:
                            info_dict['album'] = album_name
                            
                        original_title = info_dict.get('title')
                        if not original_title:
                            return None
                        target_ext = fmt
                        # Windows File Explorer requires an album tag to display m4a thumbnails
                        if target_ext == 'm4a' and not info_dict.get('album'):
                            info_dict['album'] = original_title or 'Unknown Album'
                            
                        for i in range(1, 1000):
                            temp_info = info_dict.copy()
                            if target_ext:
                                temp_info['ext'] = target_ext
                            if i > 1:
                                temp_info['title'] = f"{original_title} ({i})"
                            
                            final_path = ydl.prepare_filename(temp_info)
                            if not os.path.exists(final_path):
                                if i > 1:
                                    info_dict['title'] = temp_info['title']
                                break
                                
                        try:
                            if on_log:
                                q = f"{bitrate}kbps" if bitrate else "best"
                                file_name = os.path.basename(final_path)
                                on_log(f"--- Download Info ---")
                                on_log(f"Type: Audio")
                                on_log(f"Format: {target_ext}")
                                on_log(f"Quality: {q}")
                                on_log(f"File Name: {file_name}")
                                on_log(f"Location: {final_path}")
                                on_log(f"---------------------")
                        except Exception: pass
                        
                        return None
                        
                    ydl.params['match_filter'] = _auto_rename_filter
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
