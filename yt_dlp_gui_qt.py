"""yt-dlp GUI entry point.

The heavy lifting lives in :mod:`core` (Qt-free where possible) and
:mod:`ui`; this module only wires the application together.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import tempfile

from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.config import CONFIG_FILENAME, default_dirs, load_config
from core.file_log import FileLog
from ui.i18n import I18n, normalize_language
from ui.main_window import MainWindow
from ui.settings import create_settings
from version import APP_VERSION


def find_icon_path() -> str:
    launch_dir, resource_dir = default_dirs()
    for directory in (resource_dir, launch_dir):
        candidate = os.path.join(directory, "yt-dlp-gui.ico")
        if os.path.isfile(candidate):
            return candidate
    return ""


def build_window(interactive: bool = True) -> MainWindow:
    config = load_config()
    # A smoke test must not leave settings or config files next to the
    # executable: release builds run --self-test before packaging.
    launch_dir = config.launch_dir
    if not interactive:
        launch_dir = tempfile.mkdtemp(prefix="yt-dlp-gui-selftest-")
        config.launch_dir = launch_dir
        config.config_path = os.path.join(launch_dir, CONFIG_FILENAME)
    settings = create_settings(launch_dir)
    language = normalize_language(str(settings.value("ui/language", QLocale.system().name())))
    return MainWindow(
        config=config,
        i18n=I18n(language),
        settings=settings,
        file_log=FileLog.default(),
        version=APP_VERSION,
        icon_path=find_icon_path(),
        interactive=interactive,
    )


def self_test() -> int:
    """Start, paint and close the window without user interaction."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv[:1])
    window = build_window(interactive=False)
    launch_dir = window.config.launch_dir
    window.show()
    app.processEvents()
    window.close()
    app.processEvents()
    shutil.rmtree(launch_dir, ignore_errors=True)
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    config = load_config()
    icon_path = find_icon_path()

    file_log = FileLog.default()
    file_log.write(f"=== yt-dlp GUI {APP_VERSION} ===")
    file_log.write(f"yt-dlp: {config.yt_dlp_path}")
    file_log.write(f"ffmpeg: {config.ffmpeg_path}")

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Download Manager")
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("yt-dlp GUI")
    app.setOrganizationName("btrf")
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = build_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
