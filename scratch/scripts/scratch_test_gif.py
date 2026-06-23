import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from backend.downloader import DownloaderBackend

def test():
    backend = DownloaderBackend()
    url = "https://64.media.tumblr.com/2043a187ac8ddef18e1c22970d3195f5/34f28685c75235df-d3/s99999x99999/ad224ca3f85439b7e75d3169bd993c6c4de3ebf2.gif"
    info = backend.get_video_info(url)
    print("RESULT:", info)

if __name__ == '__main__':
    test()
