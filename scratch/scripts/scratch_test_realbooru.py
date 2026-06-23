import sys
sys.path.insert(0, 'c:/Users/sayan/Documents/GitHub/Any Downloader/src')
from backend.downloader import DownloaderBackend
import json

backend = DownloaderBackend()
info = backend.get_video_info("https://realbooru.com/index.php?page=post&s=view&id=996036")
print(json.dumps(info, indent=2))
