import os
from src.backend.downloader import DownloaderBackend
from src.backend.settings import SettingsManager

url = "https://www.deviantart.com/horrorguy23/art/Horror-OC-James-Mitchel-929740410"

db = DownloaderBackend()
settings = SettingsManager()

try:
    info = db.get_video_info(url, settings)
    if info.get('_type') == 'playlist':
        print(f"Playlist with {len(info.get('entries', []))} entries")
        for i, entry in enumerate(info.get('entries', [])):
            print(f"  [{i+1}] {entry.get('title')}: {entry.get('url')}")
    else:
        print("Single video/image")
        print(f"  Title: {info.get('title')}")
        print(f"  URL: {info.get('url')}")
except Exception as e:
    print("Error:", e)
