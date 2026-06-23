import requests

domains = ['danbooru.donmai.us', 'ahottie.com', 'bato.to']

services = {
    'google': 'https://www.google.com/s2/favicons?domain={}&sz=128',
    'duck': 'https://icons.duckduckgo.com/ip3/{}.ico',
    'horse': 'https://icon.horse/icon/{}'
}

for d in domains:
    print(f"--- {d} ---")
    for name, url_tmpl in services.items():
        url = url_tmpl.format(d)
        try:
            r = requests.get(url, timeout=5)
            print(f"{name}: {r.status_code}, len: {len(r.content)}")
            if len(r.content) < 500:
                print("  (Probably default/empty icon)")
        except Exception as e:
            print(f"{name}: Error {e}")
