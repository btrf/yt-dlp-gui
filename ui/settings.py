"""Portable-first UI settings (QSettings in INI format)."""

from __future__ import annotations

import os

from PyQt6.QtCore import QSettings, QStandardPaths

SETTINGS_FILENAME = "yt-dlp-gui.ini"


def create_settings(launch_dir: str) -> QSettings:
    """Prefer an INI file next to the executable, fall back to AppData."""
    portable = os.path.join(launch_dir, SETTINGS_FILENAME)
    if _can_write(launch_dir):
        return QSettings(portable, QSettings.Format.IniFormat)

    app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    directory = app_data or os.path.join(os.path.expanduser("~"), ".yt-dlp-gui")
    os.makedirs(directory, exist_ok=True)
    return QSettings(os.path.join(directory, SETTINGS_FILENAME), QSettings.Format.IniFormat)


def _can_write(directory: str) -> bool:
    probe = os.path.join(directory, ".ytdlp-gui-write-test")
    try:
        with open(probe, "w", encoding="utf-8") as file:
            file.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False
