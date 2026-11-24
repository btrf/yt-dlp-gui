import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402
from ui import dialogs  # noqa: E402
from ui.dialogs import APP_NAME, DONATE_URL, WEBSITE_URL, AboutDialog  # noqa: E402
from ui.i18n import I18n  # noqa: E402

_app = QApplication.instance() or QApplication([])

PROJECT_URL = "https://github.com/btrf/yt-dlp-gui"


def make_dialog(**kwargs) -> AboutDialog:
    return AboutDialog(None, I18n("ru"), "3.1.0", PROJECT_URL, **kwargs)


def test_dialog_shows_product_name_and_version():
    dialog = make_dialog()
    assert dialog.windowTitle() == "О программе"
    assert dialog.name_label.text() == APP_NAME
    assert dialog.version_label.text() == "Версия 3.1.0"
    assert not hasattr(dialog, "description_label")
    assert "palette(mid)" not in dialog.version_label.styleSheet()
    assert "palette(mid)" not in dialog.ytdlp_version_label.styleSheet()
    assert "palette(mid)" not in dialog.ffmpeg_version_label.styleSheet()


def test_dialog_shows_ytdlp_version():
    dialog = make_dialog(ytdlp_version="2026.11.23")
    assert dialog.ytdlp_version_label.text() == "yt-dlp 2026.11.23"
    dialog.close()

    unknown = make_dialog()
    assert unknown.ytdlp_version_label.text() == "yt-dlp: версия неизвестна"
    unknown.close()


def test_dialog_shows_ffmpeg_version():
    dialog = make_dialog(ffmpeg_version="9.1-essentials_build-www.gyan.dev")
    assert dialog.ffmpeg_version_label.text() == "FFmpeg 9.1-essentials_build-www.gyan.dev"
    dialog.close()

    unknown = make_dialog()
    assert unknown.ffmpeg_version_label.text() == "FFmpeg: версия неизвестна"
    unknown.close()


def test_buttons_are_translated_and_close_is_default():
    dialog = make_dialog()
    assert dialog.website_button.text() == "Сайт"
    assert dialog.project_button.text() == "Страница проекта"
    assert dialog.license_button.text() == "Лицензия"
    assert dialog.close_button.text() == "Закрыть"
    assert dialog.close_button.isDefault()


def test_link_buttons_do_not_steal_enter():
    dialog = make_dialog()
    assert not dialog.website_button.autoDefault()
    assert not dialog.project_button.autoDefault()
    assert not dialog.license_button.autoDefault()
    assert not dialog.donate_button.autoDefault()


def test_donate_button_is_a_regular_button():
    dialog = make_dialog()
    assert dialog.donate_button.styleSheet() == ""


def test_donate_button_points_to_yoomoney():
    dialog = make_dialog()
    assert dialog.donate_button.text() == "Поддержать на YooMoney"
    assert dialog.donate_url == DONATE_URL
    assert DONATE_URL == "https://yoomoney.ru/to/41001937179526"


def test_website_button_opens_the_project_site(monkeypatch):
    dialog = make_dialog()
    opened = []
    monkeypatch.setattr(
        dialogs.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()),
    )
    dialog.website_button.click()
    assert opened == [WEBSITE_URL]
    assert WEBSITE_URL == "https://btrf.github.io/yt-dlp-gui/"
    dialog.close()


def test_license_falls_back_to_the_project_page(tmp_path):
    missing = str(tmp_path / "LICENSE")
    dialog = make_dialog(license_path=missing)
    assert dialog.license_target() == f"{PROJECT_URL}/blob/main/LICENSE"


def test_license_uses_the_bundled_file(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_text("MIT License", encoding="utf-8")
    dialog = make_dialog(license_path=str(license_file))
    target = dialog.license_target()
    assert target.startswith("file:")
    assert "LICENSE" in target
