import os
import sys
import json
try:
    from src.backend.downloader import DownloaderBackend
    from src.backend.settings import SettingsManager
    
    db = DownloaderBackend()
    settings = SettingsManager()
    
    url = "https://www.tumblr.com/tiktoksthataregood-ish/819142810870693888?source=share"
    
    info = db.get_video_info(url, settings)
    print("Info fetched.")
    
    print("Is custom fallback?", info.get('id') in ['1', 'direct'] and not info.get('extractor'))
    print("Formats:", json.dumps(info.get('formats', []), indent=2))
    
    output_path = os.path.abspath("temp_tumblr_test")
    os.makedirs(output_path, exist_ok=True)
    
    db.start_download(
        url=url,
        format_id="best",
        output_path=output_path,
        is_audio=False,
        is_image=False,
        video_ext="mp4",
        embed_thumbnail=True,
        info=info,
        settings=settings,
        task_id="test_tumblr",
        on_log=print
    )
    
    import time
    while db.active_tasks.get("test_tumblr", False) is False:
        if "test_tumblr" not in db.active_tasks:
            break
        time.sleep(0.5)
        
    for f in os.listdir(output_path):
        print("Downloaded file:", f)
        
except Exception as e:
    print(f"Error: {e}")
