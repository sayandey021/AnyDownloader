import yt_dlp

url = "https://www.bilibili.com/video/BV1gzJ56rEFG/"

ydl_opts = {'quiet': False, 'verbose': True, 'extractor_args': {'bilibili': {'player_client': ['web']}}}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        print("Success! Title:", info.get('title'))
    except Exception as e:
        print("Error extracting:", e)
