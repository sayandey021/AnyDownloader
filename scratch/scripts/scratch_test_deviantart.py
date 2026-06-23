import json
from src.backend.downloader import DownloaderBackend

def test():
    downloader = DownloaderBackend()
    print("Fetching info...")
    info = downloader.get_video_info("https://www.deviantart.com/anka-kokos/art/Ice-Flower-short-webcomic-1342246955")
    
    print(json.dumps(info, indent=2))

if __name__ == '__main__':
    test()
