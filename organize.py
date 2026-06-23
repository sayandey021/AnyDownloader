import os
import shutil

# Files to keep in root
KEEP_FILES = {
    'main.py', 'Any Downloader.spec', 'AnyDownloaderApp.spec', 'AnyDownloaderCert.pfx',
    'README.md', 'requirements.txt', 'settings.json', 'history.json', 'search_history.json',
    'clip.json', 'check_url.py', 'fetch_embed.py', '.gitignore', 'organize.py'
}

# Directories to keep in root
KEEP_DIRS = {
    '.git', 'assets', 'bin', 'dist', 'ffmpeg', 'gallery-dl', 'MsixTemp',
    'Screenshots', 'scripts', 'src', 'scratch', 'docs', '.flet_view'
}

def organize():
    # 1. Ensure docs directory exists
    if not os.path.exists('docs'):
        os.makedirs('docs')
        
    # Move doc files to docs/
    for doc in ['SUPPORTED_SITES.md', 'release_notes.md']:
        if os.path.exists(doc):
            shutil.move(doc, os.path.join('docs', doc))
            print(f"Moved {doc} to docs/")

    # 2. Ensure scratch directories exist
    scratch_dirs = {
        'scripts': os.path.join('scratch', 'scripts'),
        'dumps': os.path.join('scratch', 'dumps'),
        'media': os.path.join('scratch', 'media')
    }
    for path in scratch_dirs.values():
        if not os.path.exists(path):
            os.makedirs(path)

    moved_count = 0

    # 3. Move items from root to scratch subdirectories
    for item in os.listdir('.'):
        if item in KEEP_FILES or item in KEEP_DIRS:
            continue
            
        target_dir = None
        
        # Categorize
        if os.path.isdir(item):
            # Test/temp directories go to scratch/dumps
            if item.startswith('scratch') or item.startswith('test') or item.startswith('temp'):
                target_dir = scratch_dirs['dumps']
        else:
            # Files
            ext = os.path.splitext(item)[1].lower()
            if item.startswith('scratch') and ext == '.py':
                target_dir = scratch_dirs['scripts']
            elif item.startswith('test') and ext == '.py':
                target_dir = scratch_dirs['scripts']
            elif ext in ['.json', '.html', '.txt']:
                target_dir = scratch_dirs['dumps']
            elif ext in ['.mp4', '.mkv', '.webm', '.jpg', '.png', '.pdf']:
                target_dir = scratch_dirs['media']
            else:
                target_dir = scratch_dirs['dumps'] # Fallback
                
        if target_dir:
            try:
                shutil.move(item, os.path.join(target_dir, item))
                moved_count += 1
                print(f"Moved {item} -> {target_dir}/")
            except Exception as e:
                print(f"Failed to move {item}: {e}")

    # 4. Also categorize existing files inside scratch/ (if they are unorganized)
    for item in os.listdir('scratch'):
        item_path = os.path.join('scratch', item)
        # Skip the categorized folders
        if item in ['scripts', 'dumps', 'media'] or not os.path.isfile(item_path):
            continue
            
        ext = os.path.splitext(item)[1].lower()
        target_dir = None
        if ext == '.py':
            target_dir = scratch_dirs['scripts']
        elif ext in ['.json', '.html', '.txt']:
            target_dir = scratch_dirs['dumps']
        elif ext in ['.mp4', '.mkv', '.webm', '.jpg', '.png', '.pdf']:
            target_dir = scratch_dirs['media']
        else:
            target_dir = scratch_dirs['dumps']
            
        if target_dir:
            try:
                shutil.move(item_path, os.path.join(target_dir, item))
                moved_count += 1
                print(f"Moved {item} inside scratch -> {target_dir}/")
            except Exception as e:
                pass

    print(f"\nCleanup complete. Moved {moved_count} items into organized folders.")

if __name__ == '__main__':
    organize()
