import json
try:
    with open('sc_hydration.json', 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    with open('sc_hydration.json', 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    # Try to clean the JSON string
    import re
    # Just in case there are some unescaped quotes or something
    print("JSON Decode Error, trying regex extraction")
    data = []
    matches = re.finditer(r'\{"hydratable":"([a-zA-Z]+)","data":(\{.*?\})\}(?:,|\])', text)
    for m in matches:
        try:
            data.append({"hydratable": m.group(1), "data": json.loads(m.group(2))})
        except:
            pass

types = [item.get('hydratable') for item in data]
print("Types:", types)
playlist_item = next((i for i in data if i.get('hydratable') == 'playlist'), None)
if playlist_item:
    print('Playlist found:', playlist_item is not None)
    tracks = playlist_item['data'].get('tracks', [])
    print('Tracks count:', len(tracks))
    for i, t in enumerate(tracks[:3]):
        print(f"Track {i}: {t.get('title')} - {t.get('permalink_url')}")
else:
    print("No playlist item found.")
    sound_items = [i for i in data if i.get('hydratable') == 'sound']
    print(f"Found {len(sound_items)} sound items")
    for i, item in enumerate(sound_items[:3]):
        print(f"Sound {i}: {item['data'].get('title')} - {item['data'].get('permalink_url')}")
