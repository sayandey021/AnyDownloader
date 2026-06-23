import yt_dlp
import json
import subprocess

url = "https://www.behance.net/gallery/241795869/Porsche-The-Coded-Love-Letter"

print("--- Testing yt-dlp ---")
try:
    ydl_opts = {'extract_flat': 'in_playlist', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            print(f"Playlist with {len(info['entries'])} entries")
            for e in info['entries']:
                print(f"  - {e.get('url')} (vcodec: {e.get('vcodec')}, ext: {e.get('ext')})")
        else:
            print(f"Single video: {info.get('url')}")
except Exception as e:
    print(f"yt-dlp failed: {e}")

print("\n--- Testing gallery-dl ---")
try:
    out = subprocess.check_output(['gallery-dl', '-j', url], text=True)
    blocks = json.loads('[' + out.replace('][', '],[') + ']')
    for block in blocks:
        if isinstance(block, list):
            for item in block:
                if isinstance(item, list) and len(item) >= 3 and item[0] == 3:
                    print(f"  - {item[1]}")
except Exception as e:
    print(f"gallery-dl failed: {e}")
