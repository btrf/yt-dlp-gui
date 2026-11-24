"""UI settings stored in the single portable ``yt-dlp-gui.json`` config."""

from __future__ import annotations

import os

from PyQt6.QtCore import QByteArray, QSettings

from core.config import read_json, write_json

LEGACY_FILENAME = "yt-dlp-gui.ini"


class JsonSettings:
    """Small QSettings-like facade over the app's JSON config."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._data = read_json(path)

    def value(self, key: str, default=None):
        stored = self._data.get(key, default)
        if isinstance(stored, dict) and "__bytes__" in stored:
            return QByteArray.fromHex(stored["__bytes__"].encode("ascii"))
        return stored

    def setValue(self, key: str, value) -> None:  # noqa: N802 - Qt-style API
        self._data[key] = _to_stored(value)

    def sync(self) -> None:
        write_json(self._path, self._data)


def create_settings(config_path: str) -> JsonSettings:
    """Open the shared config, migrating an old INI file if one is present."""
    settings = JsonSettings(config_path)
    legacy_path = os.path.join(os.path.dirname(config_path), LEGACY_FILENAME)
    if not os.path.isfile(legacy_path):
        return settings

    legacy = QSettings(legacy_path, QSettings.Format.IniFormat)
    for key in legacy.allKeys():
        if key not in settings._data:
            settings._data[key] = _to_stored(legacy.value(key))
    legacy.clear()
    legacy.sync()
    settings.sync()
    try:
        os.remove(legacy_path)
    except OSError:
        pass
    return settings


def _to_stored(value):
    if isinstance(value, QByteArray):
        return {"__bytes__": bytes(value).hex()}
    if isinstance(value, (list, tuple)):
        return [_to_stored(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_stored(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
