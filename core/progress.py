"""Parse yt-dlp output into structured progress updates.

Primary source is the machine-readable ``--progress-template`` JSON line;
plain-text progress, destination changes and post-processing markers are used
as a fallback and for status text.
"""

from __future__ import annotations

import json
import locale
import re
from dataclasses import dataclass

from .command_builder import PROGRESS_MARKER

# Encoding Python uses for redirected stdio on this machine (cp1251 on Russian
# Windows). Used only as a fallback when a line is not valid UTF-8.
_ANSI_ENCODING = locale.getpreferredencoding(False) or "utf-8"

_DESTINATION_RE = re.compile(r"^\[download\] Destination: (?P<path>.+)$")
_ALREADY_RE = re.compile(r"^\[download\] (?P<path>.+) has already been downloaded")
_PERCENT_RE = re.compile(r"\[download\]\s+(?P<percent>\d{1,3}(?:[.,]\d+)?)%")
_STAGE_RE = re.compile(r"^\[(?P<stage>[A-Za-z0-9_]+)\](?:\s+(?P<detail>.*))?$")

KNOWN_STAGES = frozenset(
    {
        "Merger",
        "ExtractAudio",
        "VideoConvertor",
        "VideoRemuxer",
        "Metadata",
        "EmbedThumbnail",
        "EmbedSubtitle",
        "ThumbnailsConvertor",
        "SplitChapters",
        "ModifyChapters",
        "MoveFiles",
        "FixupM3u8",
        "FixupM4a",
        "FixupStretched",
        "FixupDuplicateMoov",
        "FixupTimestamp",
        "FixupDuration",
        "SponsorBlock",
    }
)


@dataclass
class ProgressUpdate:
    """One progress sample. All fields are optional in practice."""

    percent: float | None = None
    speed: str = ""
    eta: str = ""
    total: str = ""
    filename: str = ""
    stage: str = ""


def format_bytes(value: object) -> str:
    """Format a byte count as ``1.2 MiB``; empty string for unknown values."""
    try:
        amount = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if amount <= 0:
        return ""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return ""


def format_eta(value: object) -> str:
    """Format seconds as ``MM:SS`` / ``H:MM:SS``."""
    try:
        seconds = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if seconds < 0:
        return ""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def split_lines(buffer: str) -> tuple[list[str], str]:
    """Split raw output on ``\\n``, ``\\r\\n`` and bare ``\\r``.

    yt-dlp separates progress updates with ``\\r``; treating it as a line
    separator keeps rendering responsive even without ``--newline``. Splitting
    bytes (not text) means a multi-byte character can never be cut in half by a
    chunk boundary, because only complete lines are handed to the decoder.
    """
    parts = re.split(rb"\r\n|\r|\n", buffer)
    remainder = parts.pop()
    return parts, remainder


def decode_line(raw: bytes, fallback_encoding: str | None = None) -> str:
    """Decode one line of child-process output.

    yt-dlp is asked for UTF-8 via ``--encoding utf-8``, but output from other
    tools (or an older yt-dlp) may still be in the Windows ANSI codepage, which
    is cp1251 on Russian systems.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    encoding = fallback_encoding or _ANSI_ENCODING
    if encoding.replace("-", "").lower() not in ("utf8", "ascii"):
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            pass
    return raw.decode("utf-8", "replace")


def parse_progress_line(line: str) -> ProgressUpdate | None:
    """Return a progress update for ``line`` or ``None`` if it is plain log."""
    line = line.strip("\r\n")
    if not line:
        return None

    if line.startswith(PROGRESS_MARKER):
        return _parse_progress_json(line[len(PROGRESS_MARKER) :])

    match = _DESTINATION_RE.match(line)
    if match:
        return ProgressUpdate(filename=match.group("path"), stage="Downloading", percent=0.0)

    match = _ALREADY_RE.match(line)
    if match:
        return ProgressUpdate(filename=match.group("path"), stage="Skipping")

    match = _PERCENT_RE.search(line)
    if match:
        try:
            percent = float(match.group("percent").replace(",", "."))
        except ValueError:
            percent = None
        speed_match = re.search(r"at\s+(?P<speed>[\d.]+\s*[KMGTP]?i?B/s)", line)
        eta_match = re.search(r"ETA\s+(?P<eta>\d+:\d{2}(?::\d{2})?)", line)
        total_match = re.search(r"of\s+~?\s*(?P<total>[\d.]+\s*[KMGTP]?i?B)", line)
        return ProgressUpdate(
            percent=percent,
            speed=speed_match.group("speed") if speed_match else "",
            eta=eta_match.group("eta") if eta_match else "",
            total=total_match.group("total") if total_match else "",
            stage="Downloading",
        )

    match = _STAGE_RE.match(line)
    if match and match.group("stage") in KNOWN_STAGES:
        return ProgressUpdate(stage=match.group("stage"), percent=100.0)

    return None


def _parse_progress_json(payload: str) -> ProgressUpdate | None:
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None

    progress = data.get("progress") if isinstance(data.get("progress"), dict) else data
    status = str(progress.get("status") or data.get("status") or "")

    total_bytes = progress.get("total_bytes") or progress.get("total_bytes_estimate")
    downloaded = progress.get("downloaded_bytes") or 0
    percent: float | None = None
    if total_bytes:
        try:
            percent = max(0.0, min(100.0, float(downloaded) / float(total_bytes) * 100.0))
        except (TypeError, ValueError, ZeroDivisionError):
            percent = None
    if percent is None:
        raw_percent = progress.get("_percent_str")
        if isinstance(raw_percent, str):
            match = re.search(r"(\d+(?:[.,]\d+)?)", raw_percent)
            if match:
                percent = float(match.group(1).replace(",", "."))

    stage = ""
    if status == "finished":
        stage = "Finished"
        percent = 100.0
    elif status == "downloading":
        stage = "Downloading"

    speed_text = format_bytes(progress.get("speed"))
    return ProgressUpdate(
        percent=percent,
        speed=f"{speed_text}/s" if speed_text else "",
        eta=format_eta(progress.get("eta")),
        total=format_bytes(total_bytes),
        filename=str(progress.get("filename") or progress.get("tmpfilename") or ""),
        stage=stage,
    )
