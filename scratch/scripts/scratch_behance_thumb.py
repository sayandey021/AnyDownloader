import json
import subprocess

url = "https://www.behance.net/gallery/241795869/Porsche-The-Coded-Love-Letter"
out = subprocess.check_output(['gallery-dl', '-j', url], text=True)
blocks = json.loads('[' + out.replace('][', '],[') + ']')

for block in blocks:
    if isinstance(block, list):
        last_metadata = {}
        for item in block:
            if isinstance(item, list) and len(item) >= 2:
                status = item[0]
                if status == 2 and isinstance(item[1], dict):
                    last_metadata = item[1]
                elif status == 3:
                    img_url = item[1]
                    info_dict = item[2] if len(item) >= 3 and isinstance(item[2], dict) else last_metadata
                    
                    if "ytdl:" in img_url:
                        print(f"Covers: {info_dict.get('covers')}")
                        print(f"Colors: {info_dict.get('colors')}")
                        break
