import yt_dlp

def test_download():
    def _auto_rename_filter(info_dict, *args, **kwargs):
        if info_dict.get('extractor') in ['generic', 'html5'] and ('ok.porn' in info_dict.get('webpage_url', '') or 'pornstars.tube' in info_dict.get('webpage_url', '')):
            for f in info_dict.get('formats', []):
                f_url = f.get('url', '')
                if '.mp4/' in f_url or f_url.endswith('.mp4'):
                    f['protocol'] = 'm3u8_native'
            if '.mp4/' in info_dict.get('url', '') or info_dict.get('url', '').endswith('.mp4'):
                info_dict['protocol'] = 'm3u8_native'
        return None

    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'outtmpl': 'test_download_height.%(ext)s',
        'match_filter': _auto_rename_filter,
        'quiet': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(['https://pornstars.tube/videos/688136/'])
    except Exception as e:
        print("Error:", e)

test_download()
