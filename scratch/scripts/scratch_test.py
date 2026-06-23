import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backend.downloader import DownloaderBackend
backend = DownloaderBackend(None)
info = backend.get_video_info("https://speakerdeck.com/slideist/free-powerpoint-presentation-template-3?slide=2", {})

import json
print(json.dumps(info, indent=2)[:5000])
