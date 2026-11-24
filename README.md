# yt-dlp GUI

A portable Windows download manager for video hostings: paste a link, pick options, get the file. No installation required.

![Portable Download Manager][def]

## Features

- Download video or audio from any site supported by yt-dlp (YouTube, VK, TikTok, X, Vimeo, Reddit and thousands more)
- MKV by default, with MP4/WebM and MP3/M4A/WAV available
- Quality presets from 360p to 4K, picked through yt-dlp format sorting so video and audio always match
- Playlists: all items, first, last, a range or selected numbers
- Filename templates: a curated list of the most useful ones, with descriptions, copy and one-click apply
- Ad-free video: sponsor segments are cut out via SponsorBlock (on by default, one checkbox to disable)
- Extra yt-dlp arguments for anything the UI does not cover
- Batch downloads from a `.txt` list, with a per-URL result summary and "retry failed"
- Batch archive and "skip existing" so repeated runs do not download twice
- `--cookies-from-browser` support for sites that require a login
- One-click yt-dlp update; the installed yt-dlp version is shown in the About dialog
- Portable: all settings and the download path live in one `yt-dlp-gui.json` next to the executable
- Russian and English interface (switches on the fly)
- Live progress, speed and ETA, rotating log file, desktop notifications
- Recent downloads submenu: the last ten attempted videos by title, one click to reuse
- Drag and drop links or a link file onto the window

## Installation

1. [Download the latest release](https://github.com/btrf/yt-dlp-gui/releases/latest)
2. Grab `yt-dlp-gui-portable-vX.Y.Z.exe` - a single file, easiest to move around
3. Run the `.exe`. Nothing is installed into the system.

## Usage

1. Paste a video link (the field is filled automatically from the clipboard when it contains a URL)
2. Select the download folder
3. Choose type (video/audio), quality, format and filename template
4. For playlists tick "Download playlist" and pick a scope
5. Press "Download" and watch progress, speed and ETA in the status bar

## Custom options

The "Extra args" field accepts any yt-dlp flags:

- `--limit-rate 1M` - limit the download rate
- `--retries 5` - retry failed downloads
- `--username user --password pass` - authenticate
- `--no-part` - do not use `.part` files

Quoted values are supported: `--cookies "C:\my folder\cookies.txt"`.

## Batch downloads

Use "Load links from file" (or drop a `.txt` file onto the window): one URL per line, `#`, `;` and `//` lines are ignored, UTF-8 and cp1251 files both work. The result dialog lists every URL and offers to retry the failed ones.

## Troubleshooting

The full log is written to `%TEMP%\yt-dlp-gui\yt-dlp-gui.log` (button "Open log file" in the status section) and is rotated automatically.

The app checks at startup that `yt-dlp.exe`, `ffmpeg.exe` and `ffprobe.exe` are present:
`ffmpeg` is needed for merging and converting, `ffprobe` for metadata/thumbnail post-processing.

## Bundled binaries

Release builds ship working binaries, so nothing has to be installed:

| Binary | Version | Source |
|---|---|---|
| `yt-dlp.exe` | 2026.11.23 | [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases) |
| `ffmpeg.exe`, `ffprobe.exe` | 9.1 (essentials) | [gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/) |

FFmpeg is distributed under the GPLv3; the license text is bundled as `bin/FFMPEG-LICENSE.txt`.

## Development

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python -m pytest
.venv\Scripts\python yt_dlp_gui_qt.py
```

Project layout:

```
yt_dlp_gui_qt.py        entry point (also supports --self-test)
core/command_builder.py yt-dlp argv construction (pure, unit-tested)
core/progress.py        parsing of yt-dlp progress output
core/runner.py          QProcess-based, non-blocking download runner
core/config.py          portable config loading/saving
ui/main_window.py       the window
ui/dialogs.py           about / templates / batch summary
ui/i18n.py              Russian and English strings
ui/settings.py          UI settings in the same portable JSON config (migrates old INI)
tools/bump_version.py   single-command version bump + consistency check
```

Build the portable exe with `build.ps1`; `yt-dlp.exe`, `ffmpeg.exe` and `ffprobe.exe` go into `bin/`. Each local build bumps the patch version (`3.2.0` -> `3.2.1`) and updates `version.py`, the exe resource and the docs. Use `build.ps1 -NoVersionBump` to build without changing the version (the CI and release workflows do this).

Release workflow: bump the version with `python tools/bump_version.py X.Y.Z`, tag `vX.Y.Z` and push the tag - GitHub Actions builds and publishes the artifacts.

## License

This GUI wrapper is provided as-is. It bundles yt-dlp (Unlicense) and FFmpeg (GPLv3 - see `bin/FFMPEG-LICENSE.txt`), each under its own license terms.

## Donate

[![Support YooMoney](https://img.shields.io/badge/Support-YooMoney-orange?style=flat-square&logo=yoomoney)](https://yoomoney.ru/to/41001937179526)  
![QR Code for Donations](docs/qr.png)

[def]: docs/demo-light.png
