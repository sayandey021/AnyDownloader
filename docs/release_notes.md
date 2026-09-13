# Any Downloader - Release Notes

Welcome to the **Any Downloader** release notes! Below is a comprehensive changelog of all major updates, new features, and bug fixes added to the application over time.

---

## **v1.9.0 - SponsorBlock & Backend Engines Update** *(Current)*

### ✨ New Features
- **SponsorBlock Integration**: Integrated native SponsorBlock support for YouTube video and audio downloads. Automatically detects and handles sponsored segments, self-promotions, interaction reminders, intros, outros, previews, and music off-topic sections.
- **Configurable SponsorBlock Actions**: Choose between:
  - **Remove Segments**: Cleanly cut out unwanted sponsor segments from the downloaded media using FFmpeg post-processing.
  - **Mark as Chapters**: Keep the full video intact but label sponsor sections with descriptive chapter markers for easy navigation.
  - **Remove & Save with Chapters**: Remove sponsored segments while embedding all remaining standard video chapters.
- **Granular Category Selection & Presets**: Dedicated settings section allowing custom category filtering alongside quick presets (**Default**, **All**, **Minimal**).
- **Save with Chapters (Chapter Embedding)**: Added a master switch under *Media & Processing* settings to preserve and embed video/audio chapter markers directly into output containers (MKV, MP4, M4A, etc.).
- **Per-Download SponsorBlock Toggle**: Added an inline SponsorBlock switch directly inside the Fetch Dialog when inspecting YouTube media, allowing on-the-fly toggling per download without changing global settings.
- **New General Settings Tab**: Added a dedicated *General* tab in Settings for everyday configuration (app close behavior, download speed limits, auto-delete history, metadata/thumbnail/chapter/subtitle embedding, and SponsorBlock), keeping the *Advanced* tab cleanly focused on technical controls (Hardware Acceleration, Browser Cookies, Web Login bypasses, and Developer options).
- **Multi-Subtitle Embedding**: Added support for embedding multiple subtitle tracks into a single video file. Users can now specify comma-separated language codes (e.g., `en, es, ja, hi`) or `'all'` in Settings or the Fetch Dialog to download and embed multiple soft-coded subtitle streams with proper language metadata tags.
- **Backend Engines & Dependencies Updater**: Added an integrated engine update manager under *Advanced* settings to keep core download engines (`yt-dlp`, `spotdl`, and `curl_cffi`) up to date directly from inside the app without needing manual terminal commands.
- **Configurable Engine Update Schedules**: Choose how frequently Any Downloader checks PyPI for engine updates: **Daily**, **Weekly**, **Monthly**, or **Never (Manual Only)**. Checks run unobtrusively in a background thread on startup and notify you when new engine versions are ready.
- **Manual Engine Check & One-Click Upgrade**: Added status card displaying installed vs latest PyPI versions for each engine, along with a "Check for Updates" button and a one-click "Update Engines Now" pip updater.
- **Modern Fluent UI & Dropdown Redesign**: Completely overhauled dropdown menus with modern rounded shapes, surface hover animations, and improved contrast.
- **Expanded Filename & Playlist Template Guides**: Added real-world examples, explanations of dynamic format tags, and one-click preset apply cards inside the Settings template guide modals.

---

## **v1.8.3 - Stability & Compatibility Hotfixes**

### 🐛 Bug Fixes & Polish
- **Python Path Handling**: Fixed a critical startup restart bug where Python executables located in paths with spaces (such as `C:\Program Files\...`) failed to launch with `can't open file 'C:\Program'`. Switched to safe subprocess handling.
- **SpotDL / Curl-Cffi Compatibility**: Updated `curl_cffi` requirements (`>=0.7.0`) to resolve dependency conflicts with `spotapi` and Spotify audio metadata extraction.
- **Flet UI Compatibility**: Pinned `flet>=0.22.0,<=0.85.3` in `requirements.txt` and adjusted checkbox styling properties to prevent breaking socket protocol mismatches with bundled desktop runtimes.

---

## **v1.8.2 - Hotfixes & Stability Improvements**

### 🐛 Bug Fixes
- **YouTube 403 Errors**: Fixed an issue where downloading from YouTube resulted in an `HTTP Error 403: Forbidden`. The underlying `yt-dlp` package has been updated to bypass the latest bot detection mechanisms.
- **UI Dialog Crashes**: Fixed a `RuntimeError: Dialog is already opened` crash that occurred when spamming the fetch button or failing to dismiss the loading dialog properly in the Flet UI.

---

## **v1.8.0 - The Playlist & Folders Update**
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
