with open('analdin.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'poster' in line.lower() or 'thumb' in line.lower() or 'image' in line.lower() or 'preview' in line.lower() or '.jpg' in line.lower():
        if len(line) < 200:
            print(f"Line {i}: {line.strip()}")
        else:
            print(f"Line {i}: {line[:100]}... (truncated)")
