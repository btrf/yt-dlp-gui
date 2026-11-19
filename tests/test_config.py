import json
import os

from core.config import CONFIG_FILENAME, is_writable_dir, load_config, save_config


def test_defaults_come_from_resource_dir(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)

    config = load_config(str(root), str(root), str(home))

    assert config.yt_dlp_path == os.path.join(str(root), "bin", "yt-dlp.exe")
    assert config.ffmpeg_path == os.path.join(str(root), "bin", "ffmpeg.exe")
    assert config.ffprobe_path == os.path.join(str(root), "bin", "ffprobe.exe")
    assert config.default_download_path == str(home / "Downloads")
    assert config.config_path == os.path.join(str(root), CONFIG_FILENAME)


def test_portable_config_wins_and_relative_paths_are_resolved(tmp_path):
    launch = tmp_path / "portable"
    launch.mkdir()
    resource = tmp_path / "resources"
    resource.mkdir()
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)

    (launch / CONFIG_FILENAME).write_text(
        json.dumps(
            {
                "yt_dlp_path": "bin/yt-dlp.exe",
                "ffmpeg_path": "tools/ffmpeg.exe",
                "default_download_path": str(home / "Downloads"),
            }
        ),
        encoding="utf-8",
    )

    config = load_config(str(launch), str(resource), str(home))

    assert config.yt_dlp_path == os.path.normpath(os.path.join(str(launch), "bin", "yt-dlp.exe"))
    assert config.ffmpeg_path == os.path.normpath(os.path.join(str(launch), "tools", "ffmpeg.exe"))
    assert config.config_path == os.path.join(str(launch), CONFIG_FILENAME)


def test_broken_config_falls_back_to_defaults(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    (root / CONFIG_FILENAME).write_text("{not json", encoding="utf-8")

    config = load_config(str(root), str(root), str(home))

    assert config.yt_dlp_path == os.path.join(str(root), "bin", "yt-dlp.exe")


def test_missing_download_folder_falls_back_to_launch_dir(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    config = load_config(str(root), str(root), str(home))

    assert config.default_download_path == str(root)


def test_save_config_stores_only_user_settings(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    config = load_config(str(root), str(root), str(home))
    os.makedirs(os.path.join(str(root), "bin"), exist_ok=True)

    assert save_config(config, download_path=str(home / "Downloads"))
    data = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert data["default_download_path"] == str(home / "Downloads")
    # Binary paths must not be frozen into the config: in a one-file build they
    # point into a temporary _MEIPASS folder.
    assert "yt_dlp_path" not in data

    reloaded = load_config(str(root), str(root), str(home))
    assert reloaded.yt_dlp_path == os.path.join(str(root), "bin", "yt-dlp.exe")


def test_is_writable_dir(tmp_path):
    assert is_writable_dir(str(tmp_path))
    assert not is_writable_dir(str(tmp_path / "missing"))


def test_bundled_config_is_never_the_write_target(tmp_path):
    launch = tmp_path / "app"
    launch.mkdir()
    resource = launch / "_internal"
    resource.mkdir()
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    (resource / CONFIG_FILENAME).write_text(
        json.dumps({"yt_dlp_path": "bin/yt-dlp.exe"}), encoding="utf-8"
    )

    config = load_config(str(launch), str(resource), str(home))
    assert config.yt_dlp_path == os.path.join(str(resource), "bin", "yt-dlp.exe")
    assert config.config_path == os.path.join(str(launch), CONFIG_FILENAME)

    assert save_config(config, download_path=str(home / "Downloads"))
    data = json.loads((launch / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert "yt_dlp_path" not in data
    assert data["default_download_path"] == str(home / "Downloads")

    # Reloading must keep resolving binaries from the bundled folder.
    for _ in range(3):
        config = load_config(str(launch), str(resource), str(home))
        assert config.yt_dlp_path == os.path.join(str(resource), "bin", "yt-dlp.exe")
        assert save_config(config, download_path=str(home / "Downloads"))
        data = json.loads((launch / CONFIG_FILENAME).read_text(encoding="utf-8"))
        assert "yt_dlp_path" not in data
