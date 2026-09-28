# yt-dlp GUI

A simple graphical user interface for yt-dlp, allowing you to download videos from various websites (YouTube, PronHub, etc.) with a user-friendly interface.

![GUI][def]

## Features

- Download videos from any supported site (YouTube, Vimeo, etc.)
- Choose between video or audio downloads
- Select video quality (best, 1080p, 720p, etc.)
- Choose output format (mp4, mkv, mp3, etc.)
- Download entire playlists with scope selection (all, first, last, between, specific items)
- Filename template customization
- Add custom yt-dlp options
- Batch processing: load list of links from file

## Installation

1. [Download latest release](https://github.com/btrf/yt-dlp-gui/releases/latest)
2. Run the portable application

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/btrf)

## Usage

1. Enter the video URL in the input field
2. Select your download options:
   - Download type: Video + Audio or Audio Only
   - Quality: Best, 1080p, 720p, etc.
   - Format: mp4, mp3, mkv, etc.
   - Check "Download Playlist" to download entire playlists
   - Select playlist scope if downloading a playlist
3. Select the download path
4. Click "Download" to start the download
5. View progress in the status bar and detailed log

## Custom Options

You can add additional yt-dlp options in the "Additional Options" field. Examples:

- `--limit-rate 1M` - Limit download rate to 1MB/s
- `--retries 5` - Retry failed downloads 5 times
- `--username user --password pass` - Authenticate with username/password

## Batch Downloads

You can download multiple videos from a text file containing one URL per line by selecting "Load Links from File".

## ToDo

Ideas, suggestions and proposals for the further development of this project are welcome. Please describe them in an issue: https://github.com/btrf/yt-dlp-gui/issues

## License

This GUI wrapper is provided as-is, and uses yt-dlp under its own license terms.

## Donate

[![YooMoney](https://img.shields.io/badge/Support-YooMoney-orange?style=flat-square&logo=yoomoney)](https://yoomoney.ru/to/41001937179526)  

![QR Code for Donations](qr.png)

[def]: yt-dlp-gui-portable-v2.0.3.gif
