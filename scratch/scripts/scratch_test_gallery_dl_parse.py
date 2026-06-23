import subprocess
import json
import re

url = "https://fanfox.net/manga/maydare_tensei_monogatari/c001/1.html"

print("Running gallery-dl...")
try:
    out = subprocess.check_output(['gallery-dl', '-j', url], text=True)
except Exception as e:
    print("Error running gallery-dl:", e)
    exit(1)

print(f"Raw output length: {len(out)}")

out = out.strip()
out_wrapped = '[' + re.sub(r'\]\s*\[', '],[', out) + ']'
try:
    blocks = json.loads(out_wrapped)
    print("Parsed JSON correctly. Number of blocks:", len(blocks))
except Exception as e:
    print("JSON Error:", e)
    exit(1)

data = []
for block in blocks:
    if isinstance(block, list):
        if len(block) > 0 and isinstance(block[0], int):
            data.append(block)
        else:
            data.extend(block)

print("Number of data items:", len(data))
if data:
    print("First item:", data[0])
