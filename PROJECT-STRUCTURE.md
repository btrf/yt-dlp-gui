# Project Structure

Here's the complete file structure for yt-dlp GUI:

```
yt-dlp-gui/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── version.py                # Application version
├── yt_dlp_gui_qt.py          # Qt application
├── download_manager.py       # yt-dlp process management
├── yt_dlp_gui.spec           # PyInstaller build specification
├── yt-dlp-gui.json           # Default configuration
├── test_downloader.py
└── bin/                      # Bundled yt-dlp and ffmpeg executables
```

## Description

GUI application for yt-dlp with the following features:

- Download videos from YouTube and other sites
- Choose video quality and format
- Extract audio only
- Download entire playlists with scope options
- Customize filename templates
- Batch download capability
