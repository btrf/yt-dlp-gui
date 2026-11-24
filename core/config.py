"""Configuration loading/saving (portable-first, Qt-free)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass

CONFIG_FILENAME = "yt-dlp-gui.json"
BIN_FILES = ("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe")


@dataclass
class AppConfig:
    yt_dlp_path: str
    ffmpeg_path: str
    ffprobe_path: str
    default_download_path: str
    config_path: str
    launch_dir: str


def default_dirs() -> tuple[str, str]:
    """Return ``(launch_dir, resource_dir)`` for onefile and source runs."""
    if getattr(sys, "frozen", False):
        executable = os.path.abspath(sys.executable)
        launch_dir = os.path.dirname(executable)
        resource_dir = getattr(sys, "_MEIPASS", launch_dir)
        return launch_dir, resource_dir
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return package_dir, package_dir


def home_downloads(home: str | os.PathLike[str] | None = None) -> str:
    base = os.fspath(home) if home else os.path.expanduser("~")
    return os.path.join(base, "Downloads")


def is_writable_dir(path: str) -> bool:
    if not path or not os.path.isdir(path):
        return False
    try:
        handle, probe = tempfile.mkstemp(prefix=".ytdlp-gui-", dir=path)
    except OSError:
        return False
    os.close(handle)
    try:
        os.remove(probe)
    except OSError:
        pass
    return True


def load_config(
    launch_dir: str | None = None,
    resource_dir: str | None = None,
    home: str | None = None,
) -> AppConfig:
    if launch_dir is None or resource_dir is None:
        detected_launch, detected_resource = default_dirs()
        launch_dir = launch_dir or detected_launch
        resource_dir = resource_dir or detected_resource

    config = {
        "yt_dlp_path": os.path.join(resource_dir, "bin", BIN_FILES[0]),
        "ffmpeg_path": os.path.join(resource_dir, "bin", BIN_FILES[1]),
        "ffprobe_path": os.path.join(resource_dir, "bin", BIN_FILES[2]),
        "default_download_path": home_downloads(home),
    }

    # Settings are always written next to the executable, never into a bundled
    # (_MEIPASS) directory. Read the bundled file first, then let the portable
    # one override it.
    config_path = os.path.join(launch_dir, CONFIG_FILENAME)
    for config_dir in _unique((resource_dir, launch_dir)):
        candidate = os.path.join(config_dir, CONFIG_FILENAME)
        if not os.path.isfile(candidate):
            continue
        data = read_json(candidate)
        if not data:
            continue
        config.update({key: value for key, value in data.items() if value not in (None, "")})
        for key in ("yt_dlp_path", "ffmpeg_path", "ffprobe_path"):
            value = str(config.get(key) or "")
            if value and not os.path.isabs(value):
                config[key] = os.path.normpath(os.path.join(config_dir, value))

    download_path = os.path.expanduser(str(config.get("default_download_path") or ""))
    if not os.path.isdir(download_path):
        fallback = home_downloads(home)
        download_path = fallback if os.path.isdir(fallback) else launch_dir
    config["default_download_path"] = download_path

    return AppConfig(
        yt_dlp_path=str(config["yt_dlp_path"]),
        ffmpeg_path=str(config["ffmpeg_path"]),
        ffprobe_path=str(config["ffprobe_path"]),
        default_download_path=download_path,
        config_path=config_path,
        launch_dir=launch_dir,
    )


def save_config(config: AppConfig, download_path: str | None = None) -> bool:
    """Persist user settings next to the executable.

    Only user choices are stored. Derived binary paths are intentionally not
    written: in a one-file build they point into a temporary ``_MEIPASS``
    folder that does not exist on the next launch.
    """
    data = read_json(config.config_path)
    if download_path:
        data["default_download_path"] = download_path
    return write_json(config.config_path, data)


def write_json(path: str, data: dict) -> bool:
    """Atomically write a JSON config shared by the app and UI settings."""
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
        handle, temp_path = tempfile.mkstemp(prefix=".ytdlp-gui-config-", dir=directory, text=True)
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")
        os.replace(temp_path, path)
        return True
    except OSError:
        return False


def read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return tuple(seen)
