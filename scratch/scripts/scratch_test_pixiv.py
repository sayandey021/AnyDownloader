import yt_dlp

url = "https://comic.pixiv.net/viewer/stories/113777"
ydl_opts = {'quiet': False, 'verbose': True}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        print("Success! Title:", info.get('title'))
    except Exception as e:
        print("Error:", e)
