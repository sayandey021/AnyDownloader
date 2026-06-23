import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'backend'))
from downloader import DownloaderBackend
backend = DownloaderBackend()
try:
    info = backend.get_video_info("https://gogoanime.com.by/streaming.php?ep=110898&type=sub", None)
    print("SUCCESS")
    print(info.get('url'))
    print(info.get('title'))
except Exception as e:
    print("ERROR", e)
