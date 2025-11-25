# yt-dlp GUI

A simple graphical user interface for yt-dlp, allowing you to download videos from various websites (YouTube, Hub, etc.) with a user-friendly interface.

![GUI][def]

## Features

- Download videos from any supported site (YouTube, Vimeo, etc.)
- Choose between video + audio or audio downloads
- Select video quality (best, 1080p, 720p, etc.)
- Choose output format (mp4, mp3, mkv, etc.)
- Download entire playlists with scope selection (all, first, last, between, specific items)
- Add custom yt-dlp options
- Load list of links from file
- Filename template customization with help dialog

## Requirements

- yt-dlp
- ffmpeg

## Installation

1. [Download latest release](https://github.com/btrf/yt-dlp-gui/releases/latest)
2. Unpack archive
3. Run the application by executing: `yt-dlp-gui.exe`

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/btrf)

## Usage

1. Enter the video URL in the input field
2. Select your download options:
   - Download type: Video + Audio or Audio Only
   - Quality: Best, 1080p, 720p, etc.
   - Format: mp4, mp3, mkv, etc.
   - Check "Download Playlist" to download entire playlists
   - Select playlist scope if downloading a playlist
3. Select the download path (defaults to ~/Downloads/yt-dlp)
4. Add any additional custom options if needed
5. Click "Download" to start the download
6. View progress in the status bar and detailed log

## Custom Options

You can add additional yt-dlp options in the "Additional Options" field. Examples:

- `--limit-rate 1M` - Limit download rate to 1MB/s
- `--retries 5` - Retry failed downloads 5 times
- `--username user --password pass` - Authenticate with username/password

## Settings

Access the Settings window via the "File" menu to configure:

- Path to yt-dlp executable (default: yt-dlp)
- Path to ffmpeg executable (default: ffmpeg)
- Default download path (~/Downloads/yt-dlp)

## Batch Downloads

You can download multiple videos from a text file containing one URL per line by selecting "Load Links from File".

## License

This GUI wrapper is provided as-is, and uses yt-dlp under its own license terms.

## Donate

[![YooMoney](https://img.shields.io/badge/Support-YooMoney-orange?style=flat-square&logo=yoomoney)](https://yoomoney.ru/to/41001937179526)  

[def]: GUI.png
