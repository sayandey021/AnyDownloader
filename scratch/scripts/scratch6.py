from src.backend.downloader import DownloaderBackend
import json

backend = DownloaderBackend()
info = backend.get_video_info("https://www.analdin.xxx/videos/781532/gorgeous-milf-mind-boggling-xxx-story/", settings={})

print("Thumbnail:", info.get('thumbnail'))
print("Thumbnails:", info.get('thumbnails'))
