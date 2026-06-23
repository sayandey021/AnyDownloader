# Any Downloader - Release Notes

Welcome to the **Any Downloader** release notes! Below is a comprehensive changelog of all major updates, new features, and bug fixes added to the application over time.

---

## **v1.8.0 - The Playlist & Folders Update** *(Current)*
*A massive overhaul to how playlists and multiple files are handled within the app, introducing grouped folders and bulk actions.*

### ✨ New Features
- **Smart Playlist Grouping**: Downloads from a playlist are now cleanly grouped under a native collapsible `PlaylistFolder` in the Downloads tab.
- **Bulk Folder Controls**: Added unified buttons inside folder headers to easily **Pause All**, **Resume All**, **Stop All**, and **Open Folder**.
- **Smart Retry**: Added a **"Retry Errors"** button to automatically requeue only the failed downloads within a playlist folder.
- **Folder Album Art**: Playlists now accurately display the overarching Album Art or Thumbnail on the folder header.
- **Clean Deletion**: Deleting a playlist from storage now successfully cleans up the entire parent directory and temporary files, rather than just the individual files.
- **Target Bitrate Enforcement**: Audio downloads in MP3 or M4A formats now explicitly enforce the exact selected target bitrate (e.g., 96 kbps) via strict CBR transcoding.
- **Instant UI Feedback**: The Fetch Dialog's download buttons now immediately switch to "Starting..." upon click, providing instant confirmation and preventing accidental double-clicks.

### 🐛 Bug Fixes & Polish
- Fixed a bug where the downloads page would scroll to the top automatically upon a download completing.
- Fixed a dynamic scrollbar layout issue by migrating Flet ListView to pre-calculated Columns with protective margins.
- Expanded `yt-dlp` error routing to gracefully display specific error codes (e.g. 403 Forbidden) directly in the UI's log viewer instead of crashing in the terminal.
- Fixed an issue where Apple Podcasts links (`podcasts.apple.com`) were incorrectly parsed as videos instead of pure audio streams.
- Updated audio extraction defaults to offer "Best Available (Original)" quality, bypassing unnecessary re-encoding loss.

---

## **v1.7.0 - The Manga & Image Expansion**
*Expanded the downloader's capabilities far beyond standard video and audio.*

### ✨ New Features
- **Manga Downloading**: Added a dedicated pipeline to fetch image chapters and compile them into pristine `.pdf` documents automatically.
- **Image Extraction**: Added support to scrape raw images (JPG, PNG, WEBP, TIFF) and image galleries from supported sites.
- **Format Intelligence**: The fetch dialogue now automatically detects if a URL contains image codecs and adjusts the available format dropdowns accordingly.

---

## **v1.6.0 - The Aesthetics Update**
*A massive visual upgrade to make the application feel premium.*

### ✨ New Features
- **Dynamic Theming**: Introduced the comprehensive `AppTheme` system, allowing real-time switching between Light and Dark modes.
- **Supported Sites Modal**: Added a beautifully formatted preview of the 1000+ natively supported websites.
- **Responsive Layouts**: Major redesigns to the navigation rail and sidebar layouts.

---

## **v1.5.0 - Personalization & Settings**
*Giving users the tools to configure exactly how they want their media to act.*

### ✨ New Features
- **Settings View**: Created a dedicated settings tab to control application behavior.
- **Subtitles & Metadata**: Added toggles in the settings menu to embed thumbnails directly into MP3 files and download localized subtitles for videos.
- **Custom Directories**: Implemented the ability to define a global custom download folder path.

---

## **v1.4.0 - State Persistence Update**
*Never lose track of your downloads again.*

### ✨ New Features
- **State Persistence**: The application now saves the state of all your downloads (`active`, `paused`, `error`, `completed`) to local storage, allowing you to close the app and resume later.
- **Resume Capabilities**: Automatically reload pending downloads when reopening the application.
- **Log Viewer**: Added a dedicated "Receipt/Log" button to individual download cards to track the exact terminal output of `yt-dlp` for that specific task.

---

## **v1.3.0 - The Search History Update**
*Easily track what you've searched for in the past.*

### ✨ New Features
- **Search History**: Added a brand new "Search History" tab that saves your previous queries, complete with thumbnails and titles, allowing 1-click re-fetching.
- **Clear All Data**: Added safe bulk-deletion buttons to clear your search history or download history securely.

---

## **v1.2.0 - Download Cards & Live Progress**
*Real time monitoring of your downloads.*

### ✨ New Features
- **Live Progress Cards**: Download cards now feature smooth, animated progress bars instead of static statuses.
- **Detailed Telemetry**: Added live ETA parsing, file size tracking, and accurate download speeds.
- **Background Processing**: Heavy downloads now correctly run on detached threads to keep the UI buttery smooth.

---

## **v1.1.0 - The Configurations Update**
*More control over your media.*

### ✨ New Features
- **Advanced Codecs**: Added support for specific audio extraction formats (mp3, m4a, flac, wav, ogg, opus).
- **Video Containers**: Added drop-downs for specifying video wrappers (mp4, mkv, webm).
- **Quality Controls**: Ability to easily select between highest quality, medium, and low to save bandwidth.

---

## **v1.0.0 - Initial Release**
*The birth of Any Downloader!*

### ✨ Features
- Core `yt-dlp` integration for highest-quality video fetching.
- Format selection (Video, Audio).
- Basic input text fields and fetch dialogue box.
- File deletion capabilities.
