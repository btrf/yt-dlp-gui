"""Build yt-dlp command lines.

This module is pure Python (no Qt), so the whole download configuration is
covered by fast unit tests.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass

VIDEO_FORMATS = ("mkv", "mp4", "webm", "flv", "avi", "mov")
AUDIO_FORMATS = ("mp3", "m4a", "wav")
DEFAULT_VIDEO_FORMAT = "mkv"
DEFAULT_AUDIO_FORMAT = "mp3"
DEFAULT_TEMPLATE = "%(upload_date)s - %(title)s.%(ext)s"

# Prefixed to every progress line so the runner can tell machine-readable
# progress apart from ordinary yt-dlp output. The video title is emitted in
# front of the JSON payload, separated by a unit separator (U+001F), which is
# practically impossible to find in a real title.
PROGRESS_MARKER = "__YTDLP_PROGRESS__"
TITLE_SEPARATOR = "\x1f"
PROGRESS_TEMPLATE = (
    f"download:{PROGRESS_MARKER}%(info.title)s{TITLE_SEPARATOR}%(progress)j"
)

# Quality preset -> yt-dlp ``-S`` (format sorting) expression.
# Using ``-S`` instead of hand-written ``-f`` strings keeps audio and video
# paired correctly and avoids failing merges for VP9/AV1 sources.
VIDEO_QUALITY_SORTS = {
    "best": "",
    "2160p": "res:2160",
    "1440p": "res:1440",
    "1080p": "res:1080",
    "720p": "res:720",
    "480p": "res:480",
    "360p": "res:360",
}
AUDIO_QUALITY_FORMAT = "bestaudio/best"

VIDEO_QUALITY_CHOICES = tuple(VIDEO_QUALITY_SORTS)
AUDIO_QUALITY_CHOICES = ("bestaudio",)

DEFAULT_VIDEO_QUALITY = "1080p"
DEFAULT_AUDIO_QUALITY = "bestaudio"


class ExtraOptionsError(ValueError):
    """Raised when the user-supplied extra arguments cannot be parsed."""


@dataclass(frozen=True)
class DownloadRequest:
    """Everything needed to turn UI state into a yt-dlp command line."""

    url: str
    output_dir: str = ""
    filename_template: str = DEFAULT_TEMPLATE
    download_type: str = "video"
    quality: str = DEFAULT_VIDEO_QUALITY
    output_format: str = DEFAULT_VIDEO_FORMAT
    playlist_enabled: bool = False
    playlist_items: str = ""
    extra_options: str = ""
    cookies_from_browser: str = ""
    archive_path: str = ""
    skip_existing: bool = False
    remove_ads: bool = True


def split_extra_options(raw: str) -> list[str]:
    """Split user arguments while keeping quoted values with spaces intact."""
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        tokens = shlex.split(raw, posix=False)
    except ValueError as exc:  # unbalanced quotes
        raise ExtraOptionsError(str(exc)) from exc

    result: list[str] = []
    for token in tokens:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
            token = token[1:-1]
        if token:
            result.append(token)
    return result


def normalize_format(download_type: str, output_format: str) -> str:
    """Clamp the requested container to the formats allowed for the media type."""
    if download_type == "audio":
        return output_format if output_format in AUDIO_FORMATS else DEFAULT_AUDIO_FORMAT
    return output_format if output_format in VIDEO_FORMATS else DEFAULT_VIDEO_FORMAT


def normalize_quality(download_type: str, quality: str) -> str:
    if download_type == "audio":
        return quality if quality in AUDIO_QUALITY_CHOICES else DEFAULT_AUDIO_QUALITY
    return quality if quality else DEFAULT_VIDEO_QUALITY


def build_command(
    request: DownloadRequest,
    *,
    yt_dlp_path: str,
    ffmpeg_path: str = "",
) -> list[str]:
    """Return the full yt-dlp argv for ``request``."""
    cmd: list[str] = [
        yt_dlp_path,
        "--newline",
        "--no-color",
        # Without this, yt-dlp writes Russian titles in the Windows ANSI
        # codepage and the log shows mojibake.
        "--encoding",
        "utf-8",
        "--progress-template",
        PROGRESS_TEMPLATE,
    ]

    template = (request.filename_template or DEFAULT_TEMPLATE).strip() or DEFAULT_TEMPLATE
    output_dir = (request.output_dir or "").strip()
    cmd.extend(["-o", os.path.join(output_dir, template) if output_dir else template])

    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir:
            cmd.extend(["--ffmpeg-location", ffmpeg_dir])

    download_type = "audio" if request.download_type == "audio" else "video"
    output_format = normalize_format(download_type, request.output_format)
    quality = normalize_quality(download_type, request.quality)

    if download_type == "audio":
        cmd.extend(["-x", "--audio-format", output_format])
        cmd.extend(["-f", AUDIO_QUALITY_FORMAT])
    else:
        sort = VIDEO_QUALITY_SORTS.get(quality, "")
        if quality in VIDEO_QUALITY_SORTS:
            if sort:
                cmd.extend(["-S", sort])
        else:
            # Raw yt-dlp format expression (power users / config file).
            cmd.extend(["-f", quality])
        cmd.extend(["--merge-output-format", output_format])

    cmd.append("--embed-metadata")

    if request.remove_ads:
        # SponsorBlock cuts paid-promotion segments out of the downloaded file
        # (classic YouTube ad breaks are never part of the stream itself).
        cmd.extend(["--sponsorblock-remove", "sponsor"])

    if request.playlist_enabled:
        spec = (request.playlist_items or "").strip()
        if spec == "first":
            spec = "1"
        elif spec == "last":
            spec = "-1"
        if spec in ("", "all"):
            cmd.append("--yes-playlist")
        else:
            cmd.extend(["--playlist-items", spec])
    else:
        # Without this a playlist URL silently downloads the whole playlist.
        cmd.append("--no-playlist")

    if request.archive_path:
        cmd.extend(["--download-archive", request.archive_path])
    if request.skip_existing:
        cmd.append("--no-overwrites")
    if request.cookies_from_browser:
        cmd.extend(["--cookies-from-browser", request.cookies_from_browser])

    cmd.extend(split_extra_options(request.extra_options))
    cmd.append(request.url)
    return cmd
