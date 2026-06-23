import os
import sys
import json
try:
    from src.backend.downloader import DownloaderBackend
    from src.backend.settings import SettingsManager
    
    db = DownloaderBackend()
    settings = SettingsManager()
    
    url = "https://www.tumblr.com/tiktoksthataregood-ish/819142810870693888?source=share"
    
    info = db.get_video_info(url, settings)
    
    print("KEYS:", list(info.keys()))
    print("ID:", info.get('id'))
    print("EXTRACTOR:", info.get('extractor'))
    
except Exception as e:
    print(f"Error: {e}")
