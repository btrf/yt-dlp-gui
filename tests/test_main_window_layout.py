import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QByteArray, Qt  # noqa: E402
from PyQt6.QtGui import QKeySequence  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from core.config import AppConfig  # noqa: E402
from core.file_log import FileLog  # noqa: E402
from ui.dialogs import SettingsDialog  # noqa: E402
from ui.i18n import I18n  # noqa: E402
from ui.main_window import PROJECT_URL, WEBSITE_URL, MainWindow  # noqa: E402
from ui.settings import create_settings  # noqa: E402

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
    settings = create_settings(str(tmp_path / "yt-dlp-gui.json"))
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


def test_bottom_panel_scales_with_window(tmp_path):
    window = make_window(tmp_path)
    window.env_banner.setVisible(False)
    window.resize(900, 620)
    window.show()
    QApplication.processEvents()
    before = window.bottom_tabs.height()
    top_before = window.main_splitter.widget(0).height()
    groups = (
        window.source_group,
        window.playlist_group,
        window.options_group,
        window.status_group,
    )
    heights = [group.height() for group in groups]
    window.resize(900, 1000)
    QApplication.processEvents()
    assert window.bottom_tabs.height() > before
    assert window.main_splitter.widget(0).height() == top_before
    assert [group.height() for group in groups] == heights
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


def test_check_environment_logs_the_result(tmp_path):
    window = make_window(tmp_path)
    window.log_text.clear()
    (tmp_path / "bin").mkdir(exist_ok=True)
    for name in ("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe"):
        (tmp_path / "bin" / name).write_bytes(b"")

    window._validate_environment(announce=True)

    log = window.log_text.toPlainText()
    assert "Checking environment" in log
    assert "Environment OK" in log
    file_log = (tmp_path / "log.txt").read_text(encoding="utf-8")
    assert "Checking environment" in file_log
    assert "Environment OK" in file_log
    window.close()


def test_maintenance_actions_moved_to_menus(tmp_path):
    window = make_window(tmp_path)
    assert not hasattr(window, "update_btn")
    assert not hasattr(window, "quit_btn")
    assert window.update_action in window.tools_menu.actions()
    assert window.quit_action in window.file_menu.actions()
    assert window.settings_action in window.edit_menu.actions()
    assert window.history_action in window.file_menu.actions()
    assert window.language_menu.menuAction() in window.view_menu.actions()
    assert window.language_menu.menuAction() not in window.tools_menu.actions()
    assert not hasattr(window, "check_updates_action")
    assert not any(
        "Check for updates" in action.text() for action in window.tools_menu.actions()
    )
    window.close()


def test_recent_menu_speaks_about_links(tmp_path):
    window = make_window(tmp_path)
    assert window.recent_menu.title() == "Recent links"
    window.close()


def test_source_section_is_named_source_destination(tmp_path):
    window = make_window(tmp_path)
    assert window.source_group.title() == "Source/Destination"
    assert I18n("ru").t("group_source") == "Источник/Назначение"
    window.close()


def test_help_menu_starts_with_website(tmp_path, monkeypatch):
    from ui import main_window as main_window_module

    window = make_window(tmp_path)
    actions = window.help_menu.actions()
    assert actions[0] is window.website_action
    assert window.website_action.text() == "Website"
    assert actions[1] is window.github_action
    assert window.github_action.text() == "GitHub project"

    opened = []
    monkeypatch.setattr(
        main_window_module.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()),
    )
    window.website_action.trigger()
    window.github_action.trigger()
    assert opened == [WEBSITE_URL, PROJECT_URL]
    window.close()


def test_ffmpeg_version_is_parsed_from_version_output(tmp_path):
    window = make_window(tmp_path)

    class FakeProcess:
        def readAllStandardOutput(self):
            return QByteArray(
                b"ffmpeg version 9.1-essentials_build-www.gyan.dev Copyright (c) 2000-2026\n"
                b"built with gcc 16.2.0\n"
            )

        def deleteLater(self):
            pass

    process = FakeProcess()
    window._ffmpeg_process = process
    window._on_ffmpeg_version_finished(process, 0)
    assert window._ffmpeg_version == "9.1-essentials_build-www.gyan.dev"
    assert window._ffmpeg_process is None
    window.close()


def test_window_can_snap_to_half_of_a_narrow_screen(tmp_path):
    window = make_window(tmp_path)
    assert window.minimumWidth() <= 640
    assert window.always_on_top_action.shortcut() == QKeySequence("Alt+Shift+A")
    window.close()


def test_status_and_progress_span_the_status_group(tmp_path):
    window = make_window(tmp_path)
    window.env_banner.setVisible(False)
    window.resize(900, 620)
    window.show()
    QApplication.processEvents()

    margins = window.status_group.layout().contentsMargins()
    inner_width = window.status_group.contentsRect().width() - margins.left() - margins.right()
    assert abs(window.status_label.width() - inner_width) <= 2
    assert abs(window.progress_bar.width() - inner_width) <= 2
    assert window.progress_detail_label.isHidden()
    window.close()


def test_status_color_is_readable_in_both_themes(tmp_path):
    window = make_window(tmp_path)
    window._set_status("Downloading", "blue")
    assert "#1d4ed8" in window.status_label.styleSheet()

    window._set_theme("dark", persist=False)
    assert "#6ea8fe" in window.status_label.styleSheet()
    assert "color: blue;" not in window.status_label.styleSheet()

    window._set_theme("light", persist=False)
    window.close()


def test_ctrl_a_toggles_always_on_top_from_text_fields(tmp_path):
    window = make_window(tmp_path)
    window.show()
    QApplication.processEvents()

    for widget in (window.url_entry, window.options_entry, window):
        widget.setFocus()
        QTest.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier)
        QApplication.processEvents()
        assert window.always_on_top_action.isChecked()
        assert bool(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)

        QTest.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier)
        QApplication.processEvents()
        assert not window.always_on_top_action.isChecked()
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


def test_download_controls_have_no_preset_selector_or_arrow(tmp_path):
    window = make_window(tmp_path)
    assert not hasattr(window, "preset_combo")
    assert not hasattr(window, "label_preset")
    assert window.download_btn.icon().isNull()
    assert not hasattr(window, "ytdlp_version_label")
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


def test_queue_has_context_menu_for_copying_links(tmp_path):
    window = make_window(tmp_path)
    assert window.queue_list.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
    window.add_url_to_queue("https://example.com/video")
    item = window.queue_list.item(0)
    assert item.data(Qt.ItemDataRole.UserRole) == "https://example.com/video"

    menu = window._build_queue_menu(item)
    labels = [action.text() for action in menu.actions()]
    assert labels[0] == "Paste link from clipboard"
    assert labels[-1] == "Copy link"

    QApplication.clipboard().setText("")
    menu.actions()[-1].trigger()
    assert QApplication.clipboard().text() == "https://example.com/video"
    window.close()


def test_queue_context_menu_pastes_link_from_clipboard(tmp_path):
    window = make_window(tmp_path)
    QApplication.clipboard().setText("https://example.com/from-clipboard")

    menu = window._build_queue_menu(None)
    assert [action.text() for action in menu.actions()] == ["Paste link from clipboard"]
    menu.actions()[0].trigger()

    assert window._queue_urls() == ["https://example.com/from-clipboard"]
    assert "https://example.com/from-clipboard" in window.log_text.toPlainText()
    window.close()


def test_queue_save_button_writes_links_to_file(tmp_path, monkeypatch):
    from ui import main_window as main_window_module

    window = make_window(tmp_path)
    assert not window.queue_save_btn.isEnabled()

    window.add_url_to_queue("https://example.com/one")
    window.add_url_to_queue("https://example.com/two")
    assert window.queue_save_btn.isEnabled()

    target = tmp_path / "queue.txt"
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), "Text files (*.txt)"),
    )
    window.queue_save_btn.click()

    assert target.read_text(encoding="utf-8").splitlines() == [
        "https://example.com/one",
        "https://example.com/two",
    ]
    assert str(target) in window.log_text.toPlainText()

    window.clear_queue()
    assert not window.queue_save_btn.isEnabled()
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
