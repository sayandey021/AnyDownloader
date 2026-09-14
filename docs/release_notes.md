# Any Downloader - Release Notes

Welcome to the **Any Downloader** release notes! Below is a comprehensive changelog of all major updates, new features, and bug fixes added to the application over time.

---

## **v1.9.4 - Backend Engine Version Detection & Metadata Packaging Fix** *(Current)*

### 🐛 Bug Fixes
- **Backend Engine Detection on Clean/New PCs**:
  - Fixed an issue where `yt-dlp` and `spotdl` were displayed as `Installed: vNot Installed` on new machines after installing the packaged app or MSIX package.
  - **Root Cause:** In the built application, `importlib.metadata.version()` could not find `.dist-info` directories because PyInstaller does not bundle metadata for `yt-dlp` or `spotdl` by default, and pure metadata lookup lacked static fallbacks.
  - **Fix 1 (Dual-Tier Engine Version Discovery):** Engineered a safe dual-tier engine version resolver in `get_installed_engine_versions()`: fast non-import lookup via `importlib.metadata.version()`, backed by zero-side-effect static fallback resolution (`yt_dlp.version.__version__`, `spotdl._version` file content inspection, and `curl_cffi.__version__`) that never executes package initializers or probes external executables.
  - **Fix 2 (Automatic Metadata Bundling):** Configured PyInstaller packaging via `custom_pack.py`, `build.bat`, and build specs to bundle package metadata (`--copy-metadata yt-dlp --copy-metadata spotdl`), ensuring `.dist-info` is bundled so packaged apps detect engine versions natively on all systems.
  - **Fix 3 (UI Formatting & Cache Refresh):** Fixed version string formatting in Settings to avoid awkward `Installed: vNot Installed` display bugs, and ensured `force_refresh=True` is triggered on manual update checks and post-upgrade events.
- **Taskbar Right-Click Menu Icon (Blue Border / Plate Removal)**:
  - Fixed Windows rendering the taskbar right-click Jump List icon small with a blue background/border box.
  - Generated full set of official unplated, targetsize, and scale variants for `Square44x44Logo` and indexed them into `resources.pri` with `makepri.exe` in `build_msix.ps1`, allowing Windows to display the native transparent icon without plating.
- **Taskbar Menu Blank White "Flet" Window Fix & Single-Instance Activation**:
  - Fixed an issue where clicking "Any Downloader" in the taskbar right-click menu or Jump List launched `flet.exe` directly with no arguments, opening an orphaned blank white window titled "Flet" with a red play icon.
  - **Windows Shell Property Store Binding:** Explicitly configured `PKEY_AppUserModel_ID`, `PKEY_AppUserModel_RelaunchCommand`, and `PKEY_AppUserModel_RelaunchDisplayNameResource` on the Win32 window handle (`HWND`) via Windows Shell Property Store (`SHGetPropertyStoreForWindow`), directing Windows Shell to associate the taskbar shortcut directly with `AnyDownloaderApp.exe`.
  - **Native Smart Launcher Failsafe:** Replaced the raw Flutter runner client with a native C# compiled smart launcher (`flet.exe`) that passes runtime arguments to `flet_bin.exe` during app execution, and intercepts any direct 0-argument launches (from Jump Lists or shortcuts) to instantly un-minimize, restore, and focus the existing Any Downloader window via loopback IPC and Win32 APIs without ever showing a blank window.
  - **Single-Instance Enforcement:** Protected the application with a Windows Named Mutex and local loopback IPC so secondary launches restore and focus the active window and immediately exit.

---

## **v1.9.3 - Build App Console Flash Fix**

### 🐛 Bug Fixes
- **Settings Tab CMD Flash in Built App** (and source mode):
  - Fixed a CMD/terminal window briefly flashing when switching to the Settings tab — both immediately on tab switch and ~1 second later in the background.
  - **Root cause 1 (immediate flash):** `SettingsView._build_ui()` called `get_installed_engine_versions()` synchronously on the main thread during tab initialization, triggering PyInstaller bootloader helper processes visible as an instant CMD flash.
  - **Root cause 2 (delayed flash ~1s):** Direct imports of heavy packages during initialization probed `ffmpeg`/`ffprobe` and spawned visible console processes that bypassed Python's subprocess hook via direct Win32 kernel calls.
  - **Fix 1:** Engine version status is now loaded in a background daemon thread. A lightweight `ProgressRing` placeholder is shown instantly on tab open; real data populates after the frame renders.
  - **Fix 2:** Low-level silent process guards and background execution ensure smooth, silent operation across tab transitions.

---

## **v1.9.2 - History Tab & Settings Quality Fixes**

### 🐛 Bug Fixes
- **History Tab Notification Count Badge Removal**:
  - Removed the notification count badge pill next to the "History" tab title for a cleaner, distraction-free header layout.
- **Settings Console Window Flashing Fix**:
  - Completely eliminated the brief black terminal/command prompt window popup when switching to the Settings tab for the first time by:
    - Installing a low-level Win32 `_winapi.CreateProcess` and `subprocess.Popen` silent interceptor on Windows that unconditionally enforces `CREATE_NO_WINDOW` (0x08000000) and `STARTF_USESHOWWINDOW` (`SW_HIDE`) on all background child processes across standard and third-party libraries while preserving the main Flet GUI client.
    - Hardening `YtdlPopen` in `downloader.py` to strictly enforce `CREATE_NO_WINDOW` and hidden window attributes.
    - Optimizing backend engine version discovery with in-memory caching and lightweight `_version` metadata imports, completely avoiding heavy package executions on tab switch.
    - Deferring troubleshoot diagnostics so dependency validation only runs when Developer Mode is active.

---

## **v1.9.1 - Custom Title Bar & History Tab Overhaul**

### ✨ New Features
- **Custom Frameless Title Bar**:
  - Replaced the default Windows OS title bar with a custom, frameless title bar matching the app's dark/light aesthetics.
  - Native window dragging with `WindowDragArea` and double-click to maximize/restore.
  - Custom minimize, maximize/restore, and close buttons featuring smooth Windows 11-style hover animations and red close highlight.
  - Dynamic color integration that immediately updates when switching light/dark themes or accent colors.
- **History Tab 2-Column Grid Redesign**:
  - Completely revamped the History tab from a single list into a modern, responsive 2-column card grid.
  - **16:9 Thumbnail Cards**: Letterboxed thumbnail previews with rounded corners and media-aware fallback icons (music note for audio, video screen for video).
  - **Clean Metadata Line**: Each card displays detailed format, resolution/quality, and size tags (e.g. `MP4 • 480p30 • 13.48 MB` or `YouTube • 2 hours ago`).
  - **Filtering**: Added a segmented filter toggle (**All**, **Downloads**, **Searches**) to seamlessly switch between full history, completed downloads, or search entries.
  - **Direct Card Launch**: Clicking any completed download card directly opens the file in your default media player.
- **Enhanced Context / Options Menu**:
  - Upgraded the 3-dots options menu into an elevated floating card menu with rounded borders (`radius=12`) and shadow separation.
  - Color-coded icons for each action: Green Play for *Open File*, Accent for *Show in Folder*, Primary for *Search Again*, Sky Cyan for *Copy Link*, and Gray for *Open in Browser*.
  - Destructive *Remove from History* action styled in red warning color and separated by a subtle divider.
- **Unified Close Application Dialog Aesthetics**:
  - Modernized the close application popup to match the app's established design system with theme surface background (`AppTheme.SURFACE`), rounded borders (`radius=12`), header icon, styled checkbox, and dynamic runtime theme syncing.
  - Replaced plain text buttons with a prominent filled primary button for *Minimize to Tray*, danger styling for *Exit App*, and clean neutral styling for *Cancel*.
- **Taskbar & App Icon Injection**:
  - Patched packaging scripts (`custom_pack.py`, `patch_flet_exe.py`, `build_msix.ps1`) using `rcedit` to inject `icon.ico` directly into the bundled Flutter `flet.exe` binaries, ensuring the custom app icon displays properly in the Windows Taskbar and Alt+Tab switcher.

### ⚡ Performance Optimizations
- **Instant Tab Switching (< 0.01 ms)**:
  - Implemented dirty tracking (`_history_dirty`) and in-memory pre-rendering so switching between Search, History, and Downloads is instantaneous with zero freeze.
  - Added file size in-memory caching (`_filesize_cache`) to eliminate redundant synchronous disk I/O on repeated views.

### 🐛 Bug Fixes
- **Scrollbar Overlap Fix**: Added dedicated 16px gutter spacing on history cards so the vertical scrollbar no longer overlaps the card border or action buttons.
- **Title Bar Persistence on Theme Change**: Fixed an issue where changing the theme or accent color in Settings caused the custom title bar to disappear.
- **Flet 0.86 Compatibility**: Resolved `ft.Border.all` PascalCase factory requirement, updated `PopupMenuItem` to use `content` instead of `text`, and migrated `ElevatedButton` to `FilledButton`.

---

## **v1.9.0 - SponsorBlock & Backend Engines Update**

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
- **Upgraded Flet UI Framework to v0.86.5**: Migrated Any Downloader to the latest Flet 0.86.5 runtime with modern async window management, refreshed Flutter desktop client runtimes, and updated build tooling.

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
