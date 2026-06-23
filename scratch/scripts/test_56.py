import json
from src.backend.downloader import DownloaderBackend
b = DownloaderBackend(None)
info = b.get_video_info('https://www.56.com/u52/v_MjAyNDAyMTUz.html', {})
if 'entries' in info:
    print('PLAYLIST', len(info['entries']))
    for i, e in enumerate(info['entries'][:5]):
        print(i, e.get('title'), e.get('id'), e.get('url'))
else:
    print('SINGLE VIDEO', info.get('title'), info.get('id'))
