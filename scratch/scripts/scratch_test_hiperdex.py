from src.backend.downloader import DownloaderBackend
import os

dl = DownloaderBackend()
url = "https://hiperdex.com/manga/im-the-queen-in-this-life/chapter-1/"
info = dl.get_video_info(url)

if not info:
    print("get_video_info returned None!")
    exit(1)

print("Got info!", "entries:" if 'entries' in info else "", len(info.get('entries', [])))

def on_prog(d):
    print("Progress:", d)

def on_err(e):
    print("Error:", e)

def on_log(msg):
    print("Log:", msg)

if info.get('entries'):
    out_dir = "C:\\Users\\sayan\\Documents\\GitHub\\Any Downloader\\test_manga_hiperdex"
    os.makedirs(out_dir, exist_ok=True)
    print("Starting download to", out_dir)
    dl.start_download(
        url=url,
        format_id="best",
        output_path=out_dir,
        is_manga=True,
        selected_entries=info['entries'], # test all entries
        on_progress=on_prog,
        on_error=on_err,
        on_log=on_log
    )
    import time
    time.sleep(5)
