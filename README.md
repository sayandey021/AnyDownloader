# Any Downloader

A professional, high-performance video downloader powered by `yt-dlp` and `Flet`.

## Features
- **Modern UI**: Clean, dark-mode focused, Material 3 design.
- **Robust Backend**: Uses `yt-dlp` to extract video and audio streams from thousands of websites.
- **Format Selection**: Allows downloading best quality, audio-only, or specific video resolutions.
- **Real-time Progress**: Displays download speed, ETA, and progress accurately.

## Requirements
- Python 3.8+
- `flet`
- `yt-dlp`
- `ffmpeg` (Required for post-processing audio extractions to `.mp3` format)

## Installation & Running

1. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python main.py
   ```

*Note: For the best experience (e.g. extracting audio to mp3), make sure `ffmpeg` is installed on your system and added to your system's PATH.*
