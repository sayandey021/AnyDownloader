import requests
from bs4 import BeautifulSoup

url = "https://9anime.org.lv/classroom-of-the-elite-iv-episode-2/"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(resp.text, 'html.parser')

thumb_meta = soup.find('meta', property='og:image')
print("Thumbnail:", thumb_meta['content'] if thumb_meta else None)
