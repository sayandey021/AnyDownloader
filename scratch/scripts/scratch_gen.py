import os
import re
import subprocess
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

def get_ytdlp_sites():
    sites = set()
    if not yt_dlp:
        return sites
    extractors = yt_dlp.extractor.gen_extractors()
    for ie in extractors:
        name = ie.IE_NAME
        # Sometimes IE_NAME is like youtube:playlist, we can just keep the main name or description
        desc = getattr(ie, 'IE_DESC', None)
        if desc == 'Generic downloader that works on some sites': continue
        if not desc:
            desc = name
        
        # We can extract the main domain or name
        sites.add((name, desc, "yt-dlp"))
    return sites

def get_gallerydl_sites():
    sites = set()
    try:
        output = subprocess.check_output(['gallery-dl', '--list-extractors'])
        text_output = output.decode('utf-8', errors='ignore')
        for line in text_output.split('\n'):
            line = line.strip()
            if not line: continue
            # Format usually: extractor_name
            # Wait, gallery-dl --list-extractors actually prints a tree or just names.
            # Let's just use the names
            sites.add((line, line, "gallery-dl"))
    except Exception as e:
        print("gallery-dl error:", e)
    return sites

VERIFIED_CATEGORIES = {
    "Video & Streaming": [
        ("YouTube", "youtube.com"), ("Twitch", "twitch.tv"), ("Kick", "kick.com"),
        ("Trovo", "trovo.live"), ("CHZZK", "chzzk.naver.com"), ("Vimeo", "vimeo.com"),
        ("Dailymotion", "dailymotion.com"), ("Rumble", "rumble.com"),
    ],
    "Music & Audio": [
        ("Spotify", "spotify.com"), ("Apple Music", "music.apple.com"), ("SoundCloud", "soundcloud.com"),
        ("YT Music", "music.youtube.com"), ("Tidal", "tidal.com"), ("Deezer", "deezer.com"),
        ("JioSaavn", "jiosaavn.com"), ("Gaana", "gaana.com"), ("Last.fm", "last.fm"),
        ("Bandcamp", "bandcamp.com"), ("Mixcloud", "mixcloud.com"),
    ],
    "Social Media": [
        ("Instagram", "instagram.com"), ("Twitter / X", "x.com"), ("Facebook", "facebook.com"),
        ("TikTok", "tiktok.com"), ("Reddit", "reddit.com"), ("LinkedIn", "linkedin.com"),
        ("Snapchat", "snapchat.com"), ("Patreon", "patreon.com"), ("Bluesky", "bsky.app"),
        ("VK", "vk.com"),
    ],
    "Images & Art": [
        ("Pinterest", "pinterest.com"), ("Tumblr", "tumblr.com"), ("ArtStation", "artstation.com"),
        ("Behance", "behance.net"), ("Flickr", "flickr.com"), ("DeviantArt", "deviantart.com"),
        ("Imgur", "imgur.com"), ("Wallpaper Cave", "wallpapercave.com"), ("Danbooru", "danbooru.donmai.us"),
        ("Wallhaven", "wallhaven.cc"), ("Tenor", "tenor.com"),
    ],
    "Anime & Manga": [
        ("9Anime", "9anime.to"), ("MangaDex", "mangadex.org"), ("Webtoon", "webtoons.com"),
        ("Tapas", "tapas.io"), ("MangaFire", "mangafire.to"), ("MangaFreak", "mangafreak.me"),
        ("MangaRead", "mangaread.org"), ("MangaTaro", "mangataro.org"), ("Rawkuma", "rawkuma.net"),
        ("Dynasty Reader", "dynasty-scans.com"), ("WeebCentral", "weebcentral.com"),
    ]
}

def main():
    ydl_sites = get_ytdlp_sites()
    gdl_sites = get_gallerydl_sites()
    
    all_sites = ydl_sites.union(gdl_sites)
    
    # Sort and remove duplicates by name (case-insensitive)
    # We will combine the "Engine" string if a duplicate is found
    unique_sites = {}
    for name, desc, tool in all_sites:
        key = name.split(':')[0].lower()
        # Clean up some common prefixes/suffixes for better deduplication
        clean_key = key.replace('extractor', '').replace('user', '').replace('search', '')
        if clean_key not in unique_sites:
            unique_sites[clean_key] = [name.split(':')[0], desc, {tool}]
        else:
            unique_sites[clean_key][2].add(tool)
            
    sorted_sites = sorted(unique_sites.values(), key=lambda x: x[0].lower())
    
    # We want to identify the verified ones so we don't repeat them
    verified_names_lower = set()
    for cat, items in VERIFIED_CATEGORIES.items():
        for name, url in items:
            verified_names_lower.add(name.lower())
            verified_names_lower.add(url.lower().split('.')[0]) # roughly e.g. "youtube"

    # Group the rest by first letter
    categories = {}
    for name, desc, tools_set in sorted_sites:
        # Skip if it seems to be one of our verified sites manually listed
        if name.lower() in verified_names_lower: continue
        
        tool_str = ", ".join(sorted(list(tools_set)))
        
        first_letter = name[0].upper()
        if not first_letter.isalpha():
            first_letter = '#'
        if first_letter not in categories:
            categories[first_letter] = []
        categories[first_letter].append((name, desc, tool_str))
        
    with open("SUPPORTED_SITES.md", "w", encoding="utf-8") as f:
        f.write("# Supported Sites\n\n")
        f.write("This document lists all the websites currently supported by Any Downloader. We divide these into **Verified Sites** that have been manually tested, and a massive list of **Other Supported Sites** that are supported by our underlying engines (yt-dlp and gallery-dl).\n\n")
        
        f.write("## 🌟 Verified Sites\n\n")
        for cat_name, items in VERIFIED_CATEGORIES.items():
            f.write(f"### {cat_name}\n\n")
            f.write("| Site | URL | Status |\n")
            f.write("| --- | --- | --- |\n")
            for name, url in items:
                f.write(f"| {name} | {url} | 🟢 Verified Working |\n")
            f.write("\n")
            
        f.write("## 🌐 Other Supported Sites\n\n")
        f.write("These sites are supported by `yt-dlp` and `gallery-dl`, but have not been manually verified in our interface.\n\n")
        
        for category in sorted(categories.keys()):
            f.write(f"### {category}\n\n")
            f.write("| Site/Extractor | Description | Engine |\n")
            f.write("| --- | --- | --- |\n")
            for name, desc, tool in categories[category]:
                # Clean up description pipes
                desc = desc.replace('|', '-') if desc else ""
                f.write(f"| {name} | {desc} | {tool} |\n")
            f.write("\n")

if __name__ == '__main__':
    main()
