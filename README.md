# yt-dlp GUI

A simple graphical user interface for yt-dlp, allowing you to download videos from various websites with a user-friendly interface.

## Features

- Download videos from any supported site (YouTube, Vimeo, etc.)
- Choose between video + audio, audio-only, or video-only downloads
- Select video quality (best, 1080p, 720p, etc.)
- Choose output format (mp4, mp3, mkv, etc.)
- Download entire playlists with scope selection (all, first, last, between, specific items)
- Add custom yt-dlp options
- Load list of links from file
- Filename template customization with help dialog

## Requirements

- [Python 3.x](https://www.python.org/downloads/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://www.ffmpeg.org/download.html)

## Installation

1. Download latest release
2. Unpack archive
3. Run the application

## Usage

1. Run the GUI by executing: `yt-dlp-gui.exe`
2. Enter the video URL in the input field
3. Select your download options:
   - Download type: Video + Audio, Audio Only, or Video Only
   - Quality: Best, 1080p, 720p, etc.
   - Format: mp4, mp3, mkv, etc.
   - Check "Download Playlist" to download entire playlists
   - Select playlist scope if downloading a playlist
4. Select the download path (defaults to ~/Downloads/yt-dlp)
5. Add any additional custom options if needed
6. Click "Download" to start the download
7. View progress in the status bar and detailed log

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
