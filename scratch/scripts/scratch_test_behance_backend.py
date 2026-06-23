import sys
from src.backend.downloader import DownloaderBackend

def test():
    backend = DownloaderBackend()
    url = "https://www.behance.net/gallery/241795869/Porsche-The-Coded-Love-Letter?tracking_source=search_projects&l=1"
    
    settings = {'cookies_path': '', 'browser_cookies': 'none'}
    print(f"Fetching info for: {url}")
    try:
        info = backend.get_video_info(url, settings)
        print("Success!")
        
        if info.get('_type') == 'playlist':
            print(f"Playlist found with {len(info.get('entries', []))} entries.")
            for e in info.get('entries', []):
                formats = e.get('formats', [])
                if formats:
                    f = formats[0]
                    print(f"  - [{e.get('id')}] {f.get('ext')} | {f.get('vcodec')} | {f.get('url')[:60]}...")
                else:
                    print(f"  - [{e.get('id')}] No formats found.")
        else:
            print(f"Single video: {info.get('title')}")
            formats = info.get('formats', [])
            if formats:
                f = formats[0]
                print(f"  - {f.get('ext')} | {f.get('vcodec')} | {f.get('url')[:60]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test()
