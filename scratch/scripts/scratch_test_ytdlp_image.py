import yt_dlp

ydl_opts = {
    'outtmpl': 'scratch_test_ytdlp_image.%(ext)s',
    'format': 'best',
    'postprocessors': [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4'
    }],
    'quiet': False
}

url = "https://via.placeholder.com/150.png"

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
