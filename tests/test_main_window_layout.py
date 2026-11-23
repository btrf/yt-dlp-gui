import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from core.config import AppConfig  # noqa: E402
from core.file_log import FileLog  # noqa: E402
from ui.dialogs import SettingsDialog  # noqa: E402
from ui.i18n import I18n  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

_app = QApplication.instance() or QApplication([])


def make_window(tmp_path) -> MainWindow:
    config = AppConfig(
        yt_dlp_path=str(tmp_path / "bin" / "yt-dlp.exe"),
        ffmpeg_path=str(tmp_path / "bin" / "ffmpeg.exe"),
        ffprobe_path=str(tmp_path / "bin" / "ffprobe.exe"),
        default_download_path=str(tmp_path),
        config_path=str(tmp_path / "yt-dlp-gui.json"),
        launch_dir=str(tmp_path),
    )
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    return MainWindow(
        config,
        I18n("en"),
        settings,
        FileLog(str(tmp_path / "log.txt")),
        "3.1.0",
        interactive=False,
    )


def test_bottom_panel_lives_in_a_splitter_and_can_be_toggled(tmp_path):
    window = make_window(tmp_path)
    assert window.main_splitter.count() == 2
    assert window.main_splitter.widget(1) is window.bottom_tabs
    assert window.bottom_tabs.widget(0) is window.log_group
    assert window.bottom_tabs.widget(1) is window.queue_group
    assert window.toggle_log_action.isChecked()
    assert not window.bottom_tabs.isHidden()

    window.toggle_log_action.setChecked(False)
    assert window.bottom_tabs.isHidden()

    window.toggle_log_action.setChecked(True)
    assert not window.bottom_tabs.isHidden()
    window.close()


def test_panel_visibility_is_remembered(tmp_path):
    window = make_window(tmp_path)
    window.toggle_log_action.setChecked(False)
    window._persist_settings()
    window.close()

    reopened = make_window(tmp_path)
    assert not reopened.toggle_log_action.isChecked()
    assert reopened.bottom_tabs.isHidden()
    reopened.close()


def test_environment_problems_are_shown_inline(tmp_path):
    window = make_window(tmp_path)
    assert not window.env_banner.isHidden()
    assert "yt-dlp" in window.env_text.text()
    assert not window.download_btn.isEnabled()
    assert not window.env_download_btn.isHidden()

    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "yt-dlp.exe").write_bytes(b"")
    window._validate_environment()
    assert window.env_download_btn.isHidden()
    assert window.download_btn.isEnabled()
    window.close()


def test_maintenance_actions_moved_to_menus(tmp_path):
    window = make_window(tmp_path)
    assert not hasattr(window, "update_btn")
    assert not hasattr(window, "quit_btn")
    assert window.update_action in window.tools_menu.actions()
    assert window.quit_action in window.file_menu.actions()
    assert window.settings_action in window.edit_menu.actions()
    assert window.history_action in window.file_menu.actions()
    window.close()


def test_recent_menu_speaks_about_links(tmp_path):
    window = make_window(tmp_path)
    assert window.recent_menu.title() == "Recent links"
    window.close()


def test_advanced_panel_is_collapsed_and_remembered(tmp_path):
    window = make_window(tmp_path)
    assert window.advanced_panel.isHidden()

    window.advanced_btn.setChecked(True)
    assert not window.advanced_panel.isHidden()
    window._persist_settings()
    window.close()

    reopened = make_window(tmp_path)
    assert reopened.advanced_btn.isChecked()
    assert not reopened.advanced_panel.isHidden()
    reopened.close()


def test_presets_apply_type_quality_and_format(tmp_path):
    window = make_window(tmp_path)
    index = window.preset_combo.findData("video_720")
    assert index >= 0
    window.preset_combo.setCurrentIndex(index)

    assert window.download_type.currentData() == "video"
    assert window.quality_combo.currentData() == "720p"
    assert window.format_combo.currentData() == "mp4"

    index = window.preset_combo.findData("audio_mp3")
    window.preset_combo.setCurrentIndex(index)
    assert window.download_type.currentData() == "audio"
    assert window.format_combo.currentData() == "mp3"
    window.close()


def test_queue_adds_removes_and_persists_items(tmp_path):
    window = make_window(tmp_path)
    window.url_entry.setText("https://example.com/video")
    window.add_current_url_to_queue()
    assert window.queue_list.count() == 1
    assert not window.bottom_tabs.isHidden()
    assert window.bottom_tabs.currentWidget() is window.queue_group

    window.queue_list.item(0).setSelected(True)
    window.remove_selected_queue_items()
    assert window.queue_list.count() == 0
    window.close()


def test_history_is_recorded_and_reloaded(tmp_path):
    window = make_window(tmp_path)
    window._current_url = "https://example.com/video"
    window._current_title = "Example"
    window._last_output_file = str(tmp_path / "Example.mkv")
    window._append_history("ok")
    assert window._history[0]["status"] == "ok"
    window.close()

    reopened = make_window(tmp_path)
    assert len(reopened._history) == 1
    assert reopened._history[0]["title"] == "Example"
    reopened.close()


def test_theme_can_be_switched(tmp_path):
    window = make_window(tmp_path)
    assert "dark" in window.theme_actions
    window._set_theme("dark")
    assert window._theme == "dark"
    assert window.theme_actions["dark"].isChecked()
    window.close()


def test_settings_dialog_returns_selected_values(tmp_path):
    window = make_window(tmp_path)
    dialog = SettingsDialog(
        window,
        window.i18n,
        {
            "language": "ru",
            "theme": "dark",
            "folder": str(tmp_path),
            "minimize_to_tray": True,
            "always_on_top": True,
        },
    )
    values = dialog.result_values()
    assert values == {
        "language": "ru",
        "theme": "dark",
        "folder": str(tmp_path),
        "minimize_to_tray": True,
        "always_on_top": True,
    }
    dialog.close()
    window.close()


def test_progress_uses_one_bar_and_shows_rich_detail(tmp_path):
    from core.progress import ProgressUpdate

    window = make_window(tmp_path)
    assert not hasattr(window, "batch_progress_bar")
    window._batch_active = True
    window._batch_current = 2
    window._batch_total = 4
    window._on_progress(
        ProgressUpdate(
            percent=50.0,
            speed="1.5MiB/s",
            eta="00:10",
            total="10MiB",
            filename=str(tmp_path / "clip.mkv"),
            title="Clip",
            stage="Downloading",
        )
    )
    assert window.progress_bar.value() == 37
    detail = window.progress_detail_label.text()
    assert "2/4" in detail
    assert "Clip" in detail
    assert "1.5MiB/s" in detail
    assert window._last_output_file.endswith("clip.mkv")
    window._batch_active = False
    window.close()
