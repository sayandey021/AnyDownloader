import sys
import os
import re

def main():
    if len(sys.argv) < 2:
        print("Usage: python update_version.py <new_version>")
        print("Example: python update_version.py 1.1")
        sys.exit(1)

    new_version = sys.argv[1].strip()
    
    # Ensure standard windows 4-part version (e.g. 1.1 -> 1.1.0.0)
    parts = new_version.split('.')
    while len(parts) < 4:
        parts.append('0')
    win_version = '.'.join(parts[:4])
    
    # Format for UI (e.g., just "1.1" or whatever was passed)
    ui_version = new_version

    print(f"Updating version to UI: {ui_version}, Windows: {win_version}")
    
    # Use absolute paths so the script can be run from anywhere
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, '..'))

    # 1. Update src/ui/about_view.py
    about_path = os.path.join(repo_root, 'src', 'ui', 'about_view.py')
    if os.path.exists(about_path):
        with open(about_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = re.sub(r'version = ft\.Text\("Version [^"]+",', f'version = ft.Text("Version {ui_version}",', content)
        
        with open(about_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {about_path}")
    else:
        print(f"Warning: Could not find {about_path}")

    # 2. Update build_msix.ps1
    msix_path = os.path.join(script_dir, 'build_msix.ps1')
    if os.path.exists(msix_path):
        with open(msix_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = re.sub(r'\$Version\s*=\s*"[^"]+"', f'$Version = "{win_version}"', content)
        
        with open(msix_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {msix_path}")
    else:
        print(f"Warning: Could not find {msix_path}")

    # 3. Update build.bat
    bat_path = os.path.join(script_dir, 'build.bat')
    if os.path.exists(bat_path):
        with open(bat_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = re.sub(r'--product-version\s+"[^"]+"', f'--product-version "{win_version}"', content)
        content = re.sub(r'--file-version\s+"[^"]+"', f'--file-version "{win_version}"', content)
        
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {bat_path}")
    else:
        print(f"Warning: Could not find {bat_path}")

    print("Version update complete!")

if __name__ == '__main__':
    main()
