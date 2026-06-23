from src.backend.downloader import DownloaderBackend
import os
import json

backend = DownloaderBackend()
url = "https://www.behance.net/gallery/241795869/Porsche-The-Coded-Love-Letter?tracking_source=search_projects&l=1"

# Step 1: get_video_info
info = backend.get_video_info(url)
print("Info type:", info.get('_type'))
print("Info entries:", len(info.get('entries', [])))

# Step 2: start_download
output_path = os.path.abspath("./scratch_downloads")
os.makedirs(output_path, exist_ok=True)

def on_log(msg):
    print("[YTDLP]", msg)

settings = {
    'embed_thumbnail': True,
    'filename_template': '%(title)s.%(ext)s',
    'playlist_filename_template': '%(playlist_index)s - %(title)s.%(ext)s',
}

# The UI passes is_image=False and video_ext=None for Mixed Media
task_id = backend.start_download(
    url=url,
    format_id="best",
    output_path=output_path,
    is_audio=False,
    video_ext=None,
    settings=settings,
    info=info,
    is_image=False,
    on_log=on_log
)

import time
while task_id in backend.active_tasks:
    time.sleep(1)

print("Finished download!")
# List downloaded files
for f in os.listdir(output_path):
    print("Downloaded:", f)
