import subprocess

url = "https://fanfox.net/manga/maydare_tensei_monogatari/c001/1.html"
out = subprocess.check_output(['gallery-dl', '-j', url], text=True)

if '"error":' in out:
    print('Found "error": in out!')
else:
    print('Did not find "error": in out.')
