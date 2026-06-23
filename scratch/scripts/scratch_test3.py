import yt_dlp
def _auto_rename_filter(info, *args):
    info['thumbnails'] = [{'url': 'https://via.placeholder.com/300', 'id': 'custom'}]
    info['thumbnail'] = 'https://via.placeholder.com/300'
    return None

ydl=yt_dlp.YoutubeDL({
    'format': 'bestaudio/best', 
    'writethumbnail': True, 
    'match_filter': _auto_rename_filter, 
    'postprocessors': [{'key': 'EmbedThumbnail'}]
})
ydl.download(['https://music.youtube.com/watch?v=kJQP7kiw5Fk'])
