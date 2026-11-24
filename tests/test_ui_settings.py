import json

from PyQt6.QtCore import QByteArray, QSettings  # noqa: E402

from core.config import CONFIG_FILENAME  # noqa: E402
from ui.settings import JsonSettings, create_settings  # noqa: E402


def test_settings_live_in_the_single_json_config(tmp_path):
    path = tmp_path / CONFIG_FILENAME
    path.write_text(json.dumps({"yt_dlp_path": "bin/yt-dlp.exe"}), encoding="utf-8")

    settings = JsonSettings(str(path))
    settings.setValue("ui/language", "ru")
    settings.setValue("window/geometry", QByteArray(b"\x01\x02"))
    settings.sync()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["yt_dlp_path"] == "bin/yt-dlp.exe"
    assert data["ui/language"] == "ru"

    reloaded = JsonSettings(str(path))
    assert reloaded.value("ui/language") == "ru"
    assert bytes(reloaded.value("window/geometry")) == b"\x01\x02"


def test_legacy_ini_is_merged_then_removed(tmp_path):
    ini = tmp_path / "yt-dlp-gui.ini"
    legacy = QSettings(str(ini), QSettings.Format.IniFormat)
    legacy.setValue("ui/language", "ru")
    legacy.setValue("history/items", '[{"url": "https://example.com"}]')
    legacy.sync()

    path = tmp_path / CONFIG_FILENAME
    path.write_text(json.dumps({"default_download_path": r"D:\Downloads"}), encoding="utf-8")

    settings = create_settings(str(path))
    assert settings.value("ui/language") == "ru"
    assert not ini.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["default_download_path"] == r"D:\Downloads"
    assert data["ui/language"] == "ru"
    assert "https://example.com" in data["history/items"]
