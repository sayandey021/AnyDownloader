import json
from yt_dlp import YoutubeDL
import sys

url = "https://pornstars.tube/videos/688136/"

ydl_opts = {
    'quiet': False,
    'no_warnings': False,
    'nocheckcertificate': True
}

try:
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    with open("scratch.json", "w") as f:
        json.dump(info, f, indent=2)
    print("SUCCESS, keys:", info.keys())
except Exception as e:
    print(f"FAILED: {e}")
