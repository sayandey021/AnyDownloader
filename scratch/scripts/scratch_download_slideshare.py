import urllib.request

url = "https://raw.githubusercontent.com/Neelfrost/slideshare-dl/main/slideshare_dl/__main__.py"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    code = response.read().decode('utf-8')
    with open('scratch_slideshare_code.txt', 'w', encoding='utf-8') as f:
        f.write(code)
