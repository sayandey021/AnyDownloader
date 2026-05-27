<div align="center">
  <img src="assets/icon.png" alt="Logo" width="120" height="120">

  # 📥 Any Downloader

  **A professional, high-performance video and audio downloader.**
  
  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg?logo=python&logoColor=white" alt="Python Version">
    <img src="https://img.shields.io/badge/Flet-UI-orange.svg?logo=flutter&logoColor=white" alt="Flet">
    <img src="https://img.shields.io/badge/yt--dlp-Backend-red.svg?logo=youtube&logoColor=white" alt="yt-dlp">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  </p>
</div>

<br>

Welcome to **Any Downloader**, a sleek, modern desktop application built to fetch high-quality media from thousands of websites with ease. Powered by `yt-dlp` and featuring a beautiful Material 3 interface via `Flet`.

---

## ✨ Features

- 🎨 **Modern UI**: Clean, responsive, and dark-mode focused layout following Material 3 design principles.
- ⚡ **Robust Backend**: Seamlessly extracts video and audio streams across the web using the powerful `yt-dlp` engine.
- 🎯 **Format Selection**: Take control of your downloads—choose the best overall quality, grab audio only (MP3), or specify exact video resolutions.
- 📊 **Real-time Progress**: Stay informed with accurate live updates showing download speed, estimated time of arrival (ETA), and progress bars.
- 🛠️ **Built-in Post-Processing**: Automatically converts and refines media formats utilizing `ffmpeg`.

## 📸 Preview

<div align="center">
  <img src="Screenshots/1.png" alt="Any Downloader Screenshot" width="800">
  <p><i>You can view more images in the <a href="./Screenshots">Screenshots</a> directory.</i></p>
</div>

## 🚀 Getting Started

### 📋 Prerequisites

Before you begin, ensure you have the following installed on your machine:

- 🐍 **Python 3.8** or higher
- 🎵 **[ffmpeg](https://ffmpeg.org/download.html)** (Required for post-processing audio extractions to `.mp3` format. *Make sure it's added to your system's PATH.*)

### ⚙️ Installation

1. **Clone the repository** (or download the source code):
   ```bash
   git clone https://github.com/sayandey021/AnyDownloader.git
   cd AnyDownloader
   ```

2. **Install dependencies**:
   Run the following command to install required packages (`flet`, `yt-dlp`, etc.):
   ```bash
   pip install -r requirements.txt
   ```

### 💻 Usage

Launch the application simply by running:
```bash
python main.py
```

---

<div align="center">
  <i>Developed with ❤️ for seamless media downloading.</i>
</div>
