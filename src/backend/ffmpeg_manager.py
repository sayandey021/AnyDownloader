import os
import shutil
import urllib.request
import zipfile
import threading
import sys

import requests

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def get_local_ffmpeg_dir():
    """Returns the local directory where FFmpeg should be installed."""
    return os.path.join(os.path.expanduser('~'), '.AnyDownloader', 'bin', 'ffmpeg')

def get_local_ffmpeg_exe():
    """Returns the expected path of the local ffmpeg.exe or the system ffmpeg if available."""
    # First, check if ffmpeg is in the system PATH
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        return system_ffmpeg
        
    ffmpeg_dir = get_local_ffmpeg_dir()
    if not os.path.exists(ffmpeg_dir):
        return None
        
    for root, dirs, files in os.walk(ffmpeg_dir):
        if 'ffmpeg.exe' in files:
            return os.path.join(root, 'ffmpeg.exe')
            
    return None

def is_ffmpeg_available():
    """Checks if our local ffmpeg is available."""
    if get_local_ffmpeg_exe():
        return True
    return False

def get_ffmpeg_path():
    """Returns the path to the local ffmpeg directory to pass to yt-dlp."""
    local_exe = get_local_ffmpeg_exe()
    if local_exe:
        return os.path.dirname(local_exe)
    return None

def download_ffmpeg(progress_callback=None):
    """Downloads and extracts FFmpeg to the local directory.
    progress_callback should accept (progress_percent, status_text)
    """
    ffmpeg_dir = get_local_ffmpeg_dir()
    os.makedirs(ffmpeg_dir, exist_ok=True)
    zip_path = os.path.join(ffmpeg_dir, 'ffmpeg.zip')
    
    try:
        # Download
        if progress_callback:
            progress_callback(0, "Connecting to FFmpeg server...")
            
        with requests.get(FFMPEG_URL, stream=True, timeout=30) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0 and progress_callback:
                            percent = (downloaded / total_size) * 100
                            progress_callback(percent, f"Downloading FFmpeg... {downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB")
        
        # Extract
        if progress_callback:
            progress_callback(100, "Extracting FFmpeg... This may take a moment.")
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
            
        # Clean up zip
        try:
            os.remove(zip_path)
        except Exception:
            pass
            
        if progress_callback:
            progress_callback(100, "FFmpeg setup complete!")
            
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(0, f"Error: {str(e)}")
        # Clean up partial downloads
        if os.path.exists(zip_path):
            try: os.remove(zip_path)
            except: pass
        raise e
