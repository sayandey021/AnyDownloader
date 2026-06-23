import yt_dlp

ydl_opts = {'quiet': False, 'extract_flat': False}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info('ytsearch1:Promise (Official Audio) K Jai Gharsane Aala | Dev Next Level | Latest Punjabi Songs 2023', download=False)
    if 'entries' in info:
        info = info['entries'][0]
    
    format_id = 'bestvideo[height<=1080][ext=webm]+bestaudio[ext=webm]/best[height<=1080][ext=webm]/best'
    print("\nFormat string:", format_id)
    
    ydl_opts_test = {'format': format_id, 'quiet': False}
    with yt_dlp.YoutubeDL(ydl_opts_test) as ydl2:
        info2 = ydl2.extract_info(info['webpage_url'], download=False)
        print("Matched:", info2.get('format_id'), info2.get('vcodec'), info2.get('acodec'), info2.get('ext'))

if __name__ == '__main__':
    test()
