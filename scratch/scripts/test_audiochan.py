import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from backend.downloader import DownloaderBackend

url = "https://audiochan.com/a/Bsiokgvf9YJ4FoNO4D"

def test():
    backend = DownloaderBackend()
    try:
        info = backend.get_video_info(url)
        print(json.dumps(info, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
