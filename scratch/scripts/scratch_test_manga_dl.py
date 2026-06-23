from src.backend.downloader import DownloaderBackend
import tempfile
import os

dl = DownloaderBackend()
info = dl.get_video_info("https://fanfox.net/manga/maydare_tensei_monogatari/c001/1.html")
if not info or not info.get('entries'):
    print("Failed to get info")
    exit(1)

def on_prog(d):
    print("Progress:", d)

def on_err(e):
    print("Error:", e)

def on_log(msg):
    print("Log:", msg)

out_dir = "C:\\Users\\sayan\\Documents\\GitHub\\Any Downloader\\test_manga"
os.makedirs(out_dir, exist_ok=True)
print("Starting download to", out_dir)
dl.start_download(
    url="https://fanfox.net/manga/maydare_tensei_monogatari/c001/1.html",
    format_id="best",
    output_path=out_dir,
    is_manga=True,
    selected_entries=info['entries'][:2], # test with 2 entries
    on_progress=on_prog,
    on_error=on_err,
    on_log=on_log
)
import time
time.sleep(5)
