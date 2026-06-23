import requests

url = "https://www.slideshare.net/slideshow/all-about-vlsi-in-ppt/236598976"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
r = requests.get(url, headers=headers)
with open('scratch_slideshare_html.txt', 'w', encoding='utf-8') as f:
    f.write(r.text)

import re
slides = re.findall(r'https://image.slidesharecdn.com/[^"]+-2048\.jpg', r.text)
slides = list(set(slides))
print(f"Found {len(slides)} 2048.jpg slides in HTML")

# Also find __NEXT_DATA__
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
if m:
    with open('scratch_slideshare_next_data.json', 'w', encoding='utf-8') as f:
        f.write(m.group(1))
    print("Found __NEXT_DATA__")
