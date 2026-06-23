import subprocess
import tempfile
import os

with tempfile.TemporaryDirectory() as temp_dir:
    cmd = ['gallery-dl', '--directory', temp_dir, "https://hiperdex.com/manga/im-the-queen-in-this-life/chapter-1/"]
    print("Running:", " ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    count = 0
    for line in p.stdout:
        print(line.strip())
        if line.startswith('#'):
            count += 1
    p.wait()
    print("Downloaded files:", count)
    
    # Check what files are there
    for root, dirs, files in os.walk(temp_dir):
        for f in files:
            print("File:", os.path.join(root, f))
