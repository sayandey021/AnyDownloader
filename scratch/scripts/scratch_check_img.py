import urllib.request
import imghdr
import os

url = "https://44.media.tumblr.com/605b77ca032d25b1d89ba3fc2b63dc22/ea11c5aa6d73eac5-03/s480x852_f1/ced011d3aaa0cac7be3e9faa85058c79fdc89b84.jpg"
out_path = "temp_thumb.jpg"
try:
    urllib.request.urlretrieve(url, out_path)
    with open(out_path, 'rb') as f:
        head = f.read(12)
        print("First 12 bytes:", head)
        if b'WEBP' in head:
            print("FORMAT: WEBP")
        else:
            print("FORMAT:", imghdr.what(out_path))
except Exception as e:
    print(e)
