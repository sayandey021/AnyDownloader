import yt_dlp
import json

ydl_opts = {'quiet': True}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://trovo.live/s/Trovo/221977930", download=False)
    
    with open('trovo_info.json', 'w') as f:
        json.dump(info, f, indent=2)
        
    print("Formats:")
    has_video = False
    has_audio = False
    for fmt in info.get('formats', []):
        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')
        print(f"format: {fmt.get('format_id')}, vcodec: {vcodec}, acodec: {acodec}")
        if vcodec != 'none' and vcodec != 'images':
            has_video = True
        if acodec != 'none':
            has_audio = True
            
    print(f"Has video: {has_video}")
    print(f"Has audio: {has_audio}")
