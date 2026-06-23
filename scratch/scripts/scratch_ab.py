import yt_dlp, json

ydl_opts = {'quiet': True, 'extract_flat': False}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://audioboom.com/posts/8919178-difficult-decisions-for-ferrari-mercedes-austrian-gp-preview", download=False)
    out = {
        'thumbnail': info.get('thumbnail'),
        'thumbnails': info.get('thumbnails')
    }
    with open('ab_thumb.json', 'w') as f:
        json.dump(out, f, indent=2)
