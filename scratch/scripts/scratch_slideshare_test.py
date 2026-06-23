import requests
from bs4 import BeautifulSoup
import json

url = "https://www.slideshare.net/slideshow/all-about-vlsi-in-ppt/236598976"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
r = requests.get(url, headers=headers)
print("Status Code:", r.status_code)

soup = BeautifulSoup(r.text, 'html.parser')
# SlideShare usually puts images in `<picture>` or `<img>` tags inside a container
# Let's search for some images
imgs = soup.find_all('img')
slide_urls = []
for img in imgs:
    src = img.get('src') or img.get('srcset') or img.get('data-full')
    if src and ('slide' in src or 'ss_thumbnails' in src):
        slide_urls.append(src)

print("Found slide URLs:", len(slide_urls))
for i, u in enumerate(slide_urls[:5]):
    print(f"[{i}] {u}")
