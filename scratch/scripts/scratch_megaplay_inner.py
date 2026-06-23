import requests

url = "https://megaplay.buzz/stream/s-5/142018/sub"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://megaplay.buzz/stream/s-2/142018/sub"
}
try:
    resp = requests.get(url, headers=headers, timeout=10)
    with open('megaplay_html_inner.txt', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print("Saved HTML to megaplay_html_inner.txt")
except Exception as e:
    print(e)
