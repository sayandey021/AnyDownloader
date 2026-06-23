import requests
import re
url = "https://realbooru.com//images/a7/d2/a7d2dcf503ffa8572ecfd83c545ea62b.jpeg"
headers = {'User-Agent': 'Mozilla/5.0'}
for u in [url, url.replace("//images", "/images"), "https://realbooru.com/thumbnails/a7/d2/thumbnails_a7d2dcf503ffa8572ecfd83c545ea62b.jpg"]:
    r = requests.get(u, headers=headers, timeout=5, allow_redirects=True)
    print(r.status_code, len(r.content), u)
