import yt_dlp

def _match_filter(info_dict, *args, **kwargs):
    for f in info_dict.get('formats', []):
        f['protocol'] = 'm3u8_native'
        if f.get('ext') == 'unknown_video':
            f['ext'] = 'mp4'
    info_dict['protocol'] = 'm3u8_native'
    return None

ydl_opts = {
    'quiet': False,
    'http_headers': {'Referer': 'https://ok.porn/'},
    'match_filter': _match_filter
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info('https://ok.porn/video/753677/', download=True)
