import webview
import sys
import os

def run_browser(url, output_file):
    def on_closed():
        cookies = window.get_cookies()
        lines = []
        domain = ''
        for c in cookies:
            for key, morsel in c.items():
                domain = morsel['domain'] or ''
                if not domain:
                    if 'instagram' in url:
                        domain = '.instagram.com'
                    elif 'facebook' in url:
                        domain = '.facebook.com'
                    elif 'x.com' in url or 'twitter.com' in url:
                        domain = '.x.com'
                    elif 'youtube.com' in url:
                        domain = '.youtube.com'
                    else:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url)
                        domain = '.' + parsed.netloc.split(':')[0].replace('www.', '')
                        
                include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = morsel['path'] or '/'
                secure = 'TRUE' if morsel['secure'] else 'FALSE'
                expires = '2147483647'
                name = key
                value = morsel.value
                
                lines.append(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
                
        # To avoid duplicates, we read existing lines and filter out the ones for this domain
        existing_lines = []
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
                
        # filter out old cookies for this domain
        new_existing = []
        target_domain = ''
        if lines and domain:
            target_domain = domain.lstrip('.')
            
        for line in existing_lines:
            if line.startswith('#') or not line.strip():
                new_existing.append(line)
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 7 and target_domain:
                line_domain = parts[0].lstrip('.')
                if target_domain in line_domain or line_domain in target_domain:
                    # skip old cookie for this domain
                    continue
            new_existing.append(line)

        # Write merged
        with open(output_file, 'w', encoding='utf-8') as f:
            if not any(l.startswith('# Netscape') for l in new_existing):
                f.write("# Netscape HTTP Cookie File\n")
            for line in new_existing:
                f.write(line)
            for line in lines:
                f.write(line)

    window = webview.create_window('Login (Close window when done)', url, width=800, height=600)
    window.events.closed += on_closed
    webview.start(private_mode=False)

if __name__ == '__main__':
    if len(sys.argv) > 2:
        run_browser(sys.argv[1], sys.argv[2])
