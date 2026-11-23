import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402
from ui.dialogs import APP_NAME, DONATE_URL, AboutDialog  # noqa: E402
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
    assert dialog.description_label.text() == (
        "Простой менеджер загрузок на базе yt-dlp: видео, аудио, плейлисты."
    )


def test_buttons_are_translated_and_close_is_default():
    dialog = make_dialog()
    assert dialog.project_button.text() == "Страница проекта"
    assert dialog.license_button.text() == "Лицензия"
    assert dialog.close_button.text() == "Закрыть"
    assert dialog.close_button.isDefault()


def test_link_buttons_do_not_steal_enter():
    dialog = make_dialog()
    assert not dialog.project_button.autoDefault()
    assert not dialog.license_button.autoDefault()
    assert not dialog.donate_button.autoDefault()


def test_donate_button_points_to_yoomoney():
    dialog = make_dialog()
    assert dialog.donate_button.text() == "Поддержать на YooMoney"
    assert dialog.donate_url == DONATE_URL
    assert DONATE_URL == "https://yoomoney.ru/to/41001937179526"


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
