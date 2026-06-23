import requests
from bs4 import BeautifulSoup

url = "https://www.analdin.xxx/videos/781532/gorgeous-milf-mind-boggling-xxx-story/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
}

r = requests.get(url, headers=headers)
with open('analdin.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
