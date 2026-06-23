from src.backend.downloader import DownloaderBackend

dl = DownloaderBackend()
info = dl.get_video_info("https://fanfox.net/manga/maydare_tensei_monogatari/c001/1.html")

if info:
    print("Success! Got info with entries:", len(info.get('entries', [])) if 'entries' in info else 0)
    print(info.get('title'))
else:
    print("Returned None!")
