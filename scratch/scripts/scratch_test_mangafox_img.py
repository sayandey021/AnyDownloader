import requests

url = "https://zjcdn.mangafox.me/store/manga/34225/001.0/compressed/m001.jpg?token=d075094f7bfabce3997eb1e35b931c98e9f7fcd7&ttl=1781596800"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Referer": "https://fanfox.net/manga/maydare_tensei_monogatari/c001/1.html"
}

try:
    r = requests.get(url, headers=headers, timeout=15)
    print("Status code:", r.status_code)
    print("Content length:", len(r.content))
    if r.status_code != 200:
        print("Response text:", r.text[:200])
except Exception as e:
    print("Error:", e)
