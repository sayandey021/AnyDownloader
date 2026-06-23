import os
import shutil
import glob

# Files to keep in root
KEEP_FILES = {
    'main.py', 'Any Downloader.spec', 'AnyDownloaderApp.spec', 'AnyDownloaderCert.pfx',
    'README.md', 'SUPPORTED_SITES.md', 'release_notes.md', 'requirements.txt',
    'settings.json', 'history.json', 'search_history.json', 'clip.json',
    'check_url.py', 'fetch_embed.py', '.gitignore'
}

# Directories to keep in root
KEEP_DIRS = {
    '.git', 'assets', 'bin', 'dist', 'ffmpeg', 'gallery-dl', 'MsixTemp', 'Screenshots', 'scripts', 'src', 'scratch'
}

def organize():
    if not os.path.exists('scratch'):
        os.makedirs('scratch')

    moved_count = 0
    for item in os.listdir('.'):
        if item in KEEP_FILES or item in KEEP_DIRS:
            continue
            
        if os.path.isdir(item):
            # Move test directories to scratch
            if item.startswith('scratch_') or item.startswith('test_') or item.startswith('temp'):
                try:
                    shutil.move(item, os.path.join('scratch', item))
                    moved_count += 1
                    print(f"Moved directory {item} -> scratch/")
                except Exception as e:
                    print(f"Failed to move {item}: {e}")
        else:
            # Move files to scratch
            try:
                shutil.move(item, os.path.join('scratch', item))
                moved_count += 1
                print(f"Moved file {item} -> scratch/")
            except Exception as e:
                print(f"Failed to move {item}: {e}")
                
    print(f"\nCleanup complete. Moved {moved_count} items to the 'scratch' folder.")

if __name__ == '__main__':
    organize()
