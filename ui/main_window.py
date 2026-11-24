"""Main window of yt-dlp GUI."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import weakref

from PyQt6.QtCore import QEvent, QObject, QProcess, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QIcon,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.command_builder import (
    AUDIO_FORMATS,
    AUDIO_QUALITY_CHOICES,
    DEFAULT_TEMPLATE,
    DEFAULT_VIDEO_FORMAT,
    DEFAULT_VIDEO_QUALITY,
    VIDEO_FORMATS,
    VIDEO_QUALITY_CHOICES,
    DownloadRequest,
    ExtraOptionsError,
    build_command,
    normalize_format,
)
from core.config import AppConfig, is_writable_dir, save_config
from core.file_log import FileLog
from core.progress import ProgressUpdate, decode_line, split_lines
from core.runner import DownloadRunner, hide_console_window
from ui.dialogs import (
    AboutDialog,
    BatchResult,
    BatchSummaryDialog,
    HistoryDialog,
    SettingsDialog,
    TemplateHelpDialog,
)
from ui.i18n import I18n
from ui.settings import JsonSettings
from ui.theme import THEME_SYSTEM, apply_theme, make_primary_button, resolve_theme

PROJECT_URL = "https://github.com/btrf/yt-dlp-gui"
WEBSITE_URL = "https://btrf.github.io/yt-dlp-gui/"
ISSUES_URL = f"{PROJECT_URL}/issues"
SUPPORT_URL = "https://yoomoney.ru/to/41001937179526"
COOKIE_BROWSERS = ("chrome", "edge", "firefox", "brave", "opera", "vivaldi", "safari")

URL_PREFIXES = ("http://", "https://")
MAX_RECENT_URLS = 10
MAX_HISTORY_ITEMS = 100

STATUS_COLORS = {
    "light": {
        "blue": "#1d4ed8",
        "green": "#1a7f37",
        "orange": "#9a6700",
        "red": "#cf222e",
    },
    "dark": {
        "blue": "#6ea8fe",
        "green": "#56d364",
        "orange": "#e3b341",
        "red": "#ff7b72",
    },
}


def read_url_file(path: str) -> list[str]:
    """Read a URL list, tolerating BOM and cp1251 encoded files."""
    lines: list[str] = []
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(path, "r", encoding=encoding) as file:
                lines = file.readlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise OSError("unsupported file encoding")

    urls: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        urls.append(line)
    return urls


def _inside_dialog(widget: QWidget | None) -> bool:
    while widget is not None:
        if isinstance(widget, QDialog):
            return True
        widget = widget.parentWidget()
    return False


class _AlwaysOnTopShortcut(QObject):
    """Make Alt+Shift+A work even when a text field has focus.

    QLineEdit consumes Alt+Shift+A before a window-level QAction shortcut
    can fire, so the key is intercepted at the application level.
    """

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(QApplication.instance())
        self._window_ref = weakref.ref(window)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt API
        window = self._window_ref()
        if (
            window is not None
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_A
            and event.modifiers()
            == (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier)
            and (obj is window or window.isAncestorOf(obj))
            and not _inside_dialog(obj)
        ):
            window.always_on_top_action.trigger()
            return True
        return super().eventFilter(obj, event)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        i18n: I18n,
        settings: JsonSettings,
        file_log: FileLog,
        version: str,
        icon_path: str = "",
        interactive: bool = True,
    ) -> None:
        super().__init__()
        self.config = config
        self.i18n = i18n
        self.settings = settings
        self.file_log = file_log
        self.version = version
        self._interactive = interactive

        self.url_list: list[str] = []
        self._recent_entries: list[dict[str, str]] = []
        self._batch_queue: list[str] = []
        self._batch_results: list[BatchResult] = []
        self._batch_total = 0
        self._batch_current = 0
        self._batch_active = False
        self._current_url = ""
        self._current_title = ""
        self._item_percent = 0.0
        self._download_active = False
        self._status_color_name = "blue"
        self._loading = False
        self._log_height = 150
        self._ytdlp_ok = True
        self._ytdlp_version = ""
        self._ffmpeg_version = ""
        self._last_output_file = ""
        self._history: list[dict] = []
        self._theme = THEME_SYSTEM
        self._minimize_to_tray = False
        self._always_on_top = False
        self._quitting = False
        self._current_type = "video"
        self._format_state: dict[str, dict[str, str]] = {
            "video": {"quality": DEFAULT_VIDEO_QUALITY, "format": DEFAULT_VIDEO_FORMAT},
            "audio": {"quality": AUDIO_QUALITY_CHOICES[0], "format": AUDIO_FORMATS[0]},
        }

        self.base_title = "Portable Download Manager"
        if icon_path and os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setAcceptDrops(True)
        self.setMinimumSize(QSize(600, 480))
        self.resize(900, 620)

        self.runner = DownloadRunner(file_log, self)
        self.runner.progress.connect(self._on_progress)
        self.runner.log.connect(self._append_log)
        self.runner.title.connect(self._on_video_title)
        self.runner.finished.connect(self._on_finished)

        self._version_process: QProcess | None = None
        self._ffmpeg_process: QProcess | None = None
        self._update_process: QProcess | None = None
        self._update_buffer = b""
        self._tray: QSystemTrayIcon | None = None

        self._build_ui()
        self._restore_settings()
        self._retranslate()
        self._setup_tray()
        self._validate_environment()
        self._fetch_ytdlp_version()
        self._fetch_ffmpeg_version()

        geometry = self.settings.value("window/geometry")
        if not geometry:
            self._center_window()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Everything above the log lives in its own panel so a splitter can
        # give the log a compact, user-resizable share of the window.
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(10)

        self.source_group = QGroupBox()
        self.source_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        source_layout = QGridLayout(self.source_group)

        self.label_url = QLabel()
        source_layout.addWidget(self.label_url, 0, 0)
        self.url_entry = QLineEdit()
        self.url_entry.returnPressed.connect(self.try_start_download)
        source_layout.addWidget(self.url_entry, 0, 1)
        self.paste_url_btn = QPushButton()
        self.paste_url_btn.clicked.connect(self.paste_url_from_clipboard)
        source_layout.addWidget(self.paste_url_btn, 0, 2)

        self.label_path = QLabel()
        source_layout.addWidget(self.label_path, 1, 0)
        self.path_entry = QLineEdit()
        source_layout.addWidget(self.path_entry, 1, 1)
        self.browse_path_btn = QPushButton()
        self.browse_path_btn.clicked.connect(self.browse_path)
        source_layout.addWidget(self.browse_path_btn, 1, 2)
        settings_layout.addWidget(self.source_group)

        self.env_banner = QFrame()
        self.env_banner.setObjectName("envBanner")
        env_layout = QVBoxLayout(self.env_banner)
        env_layout.setContentsMargins(12, 8, 12, 8)
        env_layout.setSpacing(6)
        self.env_title = QLabel()
        self.env_title.setObjectName("envBannerTitle")
        self.env_text = QLabel()
        self.env_text.setObjectName("envBannerText")
        self.env_text.setWordWrap(True)
        self.env_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        env_layout.addWidget(self.env_title)
        env_layout.addWidget(self.env_text)
        env_buttons = QHBoxLayout()
        self.env_download_btn = QPushButton()
        self.env_download_btn.clicked.connect(self.download_ytdlp)
        self.env_retry_btn = QPushButton()
        self.env_retry_btn.clicked.connect(lambda: self._validate_environment(announce=True))
        env_buttons.addWidget(self.env_download_btn)
        env_buttons.addStretch(1)
        env_buttons.addWidget(self.env_retry_btn)
        env_layout.addLayout(env_buttons)
        self.env_banner.setVisible(False)
        settings_layout.addWidget(self.env_banner)

        self.playlist_group = QGroupBox()
        self.playlist_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        playlist_layout = QHBoxLayout(self.playlist_group)
        self.playlist_check = QCheckBox()
        self.playlist_check.toggled.connect(self._update_playlist_controls)
        playlist_layout.addWidget(self.playlist_check)
        self.playlist_scope_combo = QComboBox()
        self.playlist_scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        playlist_layout.addWidget(self.playlist_scope_combo)
        self.playlist_spec_label = QLabel()
        self.playlist_spec_label.setVisible(False)
        playlist_layout.addWidget(self.playlist_spec_label)
        self.playlist_spec_edit = QLineEdit()
        self.playlist_spec_edit.setMinimumWidth(120)
        self.playlist_spec_edit.setMaximumWidth(220)
        self.playlist_spec_edit.setVisible(False)
        playlist_layout.addWidget(self.playlist_spec_edit)
        playlist_layout.addStretch(1)
        settings_layout.addWidget(self.playlist_group)

        self.options_group = QGroupBox()
        self.options_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        options_layout = QVBoxLayout(self.options_group)

        first_row = QHBoxLayout()
        self.label_type = QLabel()
        self.download_type = QComboBox()
        self.download_type.setMinimumWidth(90)
        self.download_type.currentIndexChanged.connect(self._on_type_changed)
        first_row.addWidget(self.label_type)
        first_row.addWidget(self.download_type)
        first_row.addSpacing(12)
        self.label_quality = QLabel()
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumWidth(110)
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        first_row.addWidget(self.label_quality)
        first_row.addWidget(self.quality_combo)
        first_row.addSpacing(12)
        self.label_format = QLabel()
        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(90)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        first_row.addWidget(self.label_format)
        first_row.addWidget(self.format_combo)
        first_row.addSpacing(12)
        self.remove_ads_check = QCheckBox()
        self.remove_ads_check.setChecked(True)
        self.remove_ads_check.toggled.connect(self._persist_settings)
        first_row.addWidget(self.remove_ads_check)
        first_row.addStretch(1)
        self.advanced_btn = QToolButton()
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.advanced_btn.toggled.connect(self._toggle_advanced)
        first_row.addWidget(self.advanced_btn)
        options_layout.addLayout(first_row)

        self.advanced_panel = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_panel)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)

        second_row = QHBoxLayout()
        self.label_filename = QLabel()
        self.filename_template_entry = QLineEdit()
        self.filename_template_entry.setMinimumWidth(220)
        second_row.addWidget(self.label_filename)
        second_row.addWidget(self.filename_template_entry, 2)
        second_row.addSpacing(12)
        self.label_extra = QLabel()
        self.options_entry = QLineEdit()
        self.options_entry.setMinimumWidth(150)
        second_row.addWidget(self.label_extra)
        second_row.addWidget(self.options_entry, 1)
        advanced_layout.addLayout(second_row)

        third_row = QHBoxLayout()
        self.label_cookies = QLabel()
        self.cookies_combo = QComboBox()
        self.cookies_combo.setMinimumWidth(120)
        self.cookies_combo.currentIndexChanged.connect(self._persist_settings)
        third_row.addWidget(self.label_cookies)
        third_row.addWidget(self.cookies_combo)
        third_row.addSpacing(16)
        self.skip_existing_check = QCheckBox()
        self.skip_existing_check.toggled.connect(self._persist_settings)
        third_row.addWidget(self.skip_existing_check)
        self.archive_check = QCheckBox()
        self.archive_check.toggled.connect(self._persist_settings)
        third_row.addWidget(self.archive_check)
        third_row.addStretch(1)
        advanced_layout.addLayout(third_row)
        self.advanced_panel.setVisible(False)
        options_layout.addWidget(self.advanced_panel)
        settings_layout.addWidget(self.options_group)

        self.status_group = QGroupBox()
        self.status_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        status_layout = QVBoxLayout(self.status_group)
        self.status_label = QLabel()
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        status_layout.addWidget(self.progress_bar)
        self.progress_detail_label = QLabel()
        self.progress_detail_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.progress_detail_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.progress_detail_label.setVisible(False)
        status_layout.addWidget(self.progress_detail_label)
        settings_layout.addWidget(self.status_group)

        self.log_group = QWidget()
        log_layout = QVBoxLayout(self.log_group)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(5000)
        self.log_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.log_text.customContextMenuRequested.connect(self._show_log_menu)
        log_layout.addWidget(self.log_text, 1)
        log_buttons = QHBoxLayout()
        self.clear_log_btn = QPushButton()
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        self.open_log_btn = QPushButton()
        self.open_log_btn.clicked.connect(self.open_log_file)
        log_buttons.addWidget(self.clear_log_btn)
        log_buttons.addWidget(self.open_log_btn)
        log_buttons.addStretch(1)
        log_layout.addLayout(log_buttons)

        self.queue_group = QWidget()
        queue_layout = QVBoxLayout(self.queue_group)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.queue_list.setAlternatingRowColors(True)
        self.queue_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self._show_queue_menu)
        queue_layout.addWidget(self.queue_list, 1)
        queue_buttons = QHBoxLayout()
        self.queue_add_btn = QPushButton()
        self.queue_add_btn.clicked.connect(self.add_current_url_to_queue)
        self.queue_remove_btn = QPushButton()
        self.queue_remove_btn.clicked.connect(self.remove_selected_queue_items)
        self.queue_clear_btn = QPushButton()
        self.queue_clear_btn.clicked.connect(self.clear_queue)
        self.queue_save_btn = QPushButton()
        self.queue_save_btn.clicked.connect(self.save_queue_to_file)
        self.queue_start_btn = QPushButton()
        self.queue_start_btn.clicked.connect(self.start_queue)
        queue_buttons.addWidget(self.queue_add_btn)
        queue_buttons.addWidget(self.queue_remove_btn)
        queue_buttons.addWidget(self.queue_clear_btn)
        queue_buttons.addWidget(self.queue_save_btn)
        queue_buttons.addStretch(1)
        queue_buttons.addWidget(self.queue_start_btn)
        queue_layout.addLayout(queue_buttons)

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.log_group, "")
        self.bottom_tabs.addTab(self.queue_group, "")

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(settings_panel)
        self.main_splitter.addWidget(self.bottom_tabs)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([520, 150])
        layout.addWidget(self.main_splitter, 1)

        buttons = QHBoxLayout()
        self.download_btn = QPushButton()
        make_primary_button(self.download_btn)
        self.download_btn.clicked.connect(self.try_start_download)
        self.cancel_btn = QPushButton()
        self.cancel_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.load_links_btn = QPushButton()
        self.load_links_btn.clicked.connect(self.load_links_from_file)
        buttons.addWidget(self.download_btn)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.load_links_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._build_menus()

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        # File: the actions a user needs around a download, most frequent first.
        self.file_menu = menu_bar.addMenu("")
        self.add_queue_action = self.file_menu.addAction("")
        self.add_queue_action.setShortcut(QKeySequence("Ctrl+Shift+Q"))
        self.add_queue_action.triggered.connect(self.add_current_url_to_queue)

        self.recent_menu = self.file_menu.addMenu("")
        self.recent_menu.aboutToShow.connect(self._rebuild_recent_menu)

        self.load_links_action = self.file_menu.addAction("")
        self.load_links_action.setShortcut(QKeySequence("Ctrl+O"))
        self.load_links_action.triggered.connect(self.load_links_from_file)

        self.history_action = self.file_menu.addAction("")
        self.history_action.setShortcut(QKeySequence("Ctrl+H"))
        self.history_action.triggered.connect(self.show_history)

        self.file_menu.addSeparator()
        self.open_folder_action = self.file_menu.addAction("")
        self.open_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.open_folder_action.triggered.connect(self.open_download_folder)

        self.file_menu.addSeparator()
        self.quit_action = self.file_menu.addAction("")
        self.quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.quit_action.triggered.connect(self.close)

        # Edit: clipboard and log helpers.
        self.edit_menu = menu_bar.addMenu("")
        self.paste_action = self.edit_menu.addAction("")
        self.paste_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        self.paste_action.triggered.connect(self.paste_url_from_clipboard)
        self.clear_url_action = self.edit_menu.addAction("")
        self.clear_url_action.triggered.connect(self.url_entry.clear)
        self.copy_log_action = self.edit_menu.addAction("")
        self.copy_log_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.copy_log_action.triggered.connect(self.copy_log_to_clipboard)
        self.edit_menu.addSeparator()
        self.settings_action = self.edit_menu.addAction("")
        self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_action.triggered.connect(self.show_settings)

        # View: window chrome that can be hidden without touching settings.
        self.view_menu = menu_bar.addMenu("")
        self.toggle_log_action = self.view_menu.addAction("")
        self.toggle_log_action.setCheckable(True)
        self.toggle_log_action.setChecked(True)
        self.toggle_log_action.setShortcut(QKeySequence("Ctrl+L"))
        self.toggle_log_action.toggled.connect(self._set_log_visible)

        self.theme_menu = self.view_menu.addMenu("")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        for key, label in (("system", "theme_system"), ("light", "theme_light"), ("dark", "theme_dark")):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setData(key)
            self.theme_group.addAction(action)
            self.theme_menu.addAction(action)
            action.triggered.connect(lambda _checked=False, value=key: self._set_theme(value))
            self.theme_actions[key] = action

        self.language_menu = self.view_menu.addMenu("")
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.language_en_action = QAction("", self)
        self.language_ru_action = QAction("", self)
        for action in (self.language_en_action, self.language_ru_action):
            action.setCheckable(True)
            self.language_group.addAction(action)
            self.language_menu.addAction(action)
        self.language_en_action.triggered.connect(lambda: self.set_language("en"))
        self.language_ru_action.triggered.connect(lambda: self.set_language("ru"))

        self.view_menu.addSeparator()
        self.always_on_top_action = self.view_menu.addAction("")
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setShortcut(QKeySequence("Alt+Shift+A"))
        self.always_on_top_action.toggled.connect(self._set_always_on_top)
        self.minimize_to_tray_action = self.view_menu.addAction("")
        self.minimize_to_tray_action.setCheckable(True)
        self.minimize_to_tray_action.toggled.connect(self._set_minimize_to_tray)

        # Tools: maintenance actions.
        self.tools_menu = menu_bar.addMenu("")
        self.check_env_action = self.tools_menu.addAction("")
        self.check_env_action.setShortcut(QKeySequence("F5"))
        self.check_env_action.triggered.connect(lambda: self._validate_environment(announce=True))
        self.open_config_action = self.tools_menu.addAction("")
        self.open_config_action.triggered.connect(self.open_config_folder)

        self.tools_menu.addSeparator()
        self.update_action = self.tools_menu.addAction("")
        self.update_action.setShortcut(QKeySequence("Ctrl+U"))
        self.update_action.triggered.connect(self.update_ytdlp)
        self.open_log_action = self.tools_menu.addAction("")
        self.open_log_action.setShortcut(QKeySequence("Ctrl+Shift+L"))
        self.open_log_action.triggered.connect(self.open_log_file)
        # Help: website, GitHub project and About.
        self.help_menu = menu_bar.addMenu("")
        self.website_action = self.help_menu.addAction("")
        self.website_action.triggered.connect(lambda: self._open_url(WEBSITE_URL))
        self.github_action = self.help_menu.addAction("")
        self.github_action.triggered.connect(lambda: self._open_url(PROJECT_URL))
        self.issues_action = self.help_menu.addAction("")
        self.issues_action.triggered.connect(lambda: self._open_url(ISSUES_URL))
        self.support_action = self.help_menu.addAction("")
        self.support_action.triggered.connect(lambda: self._open_url(SUPPORT_URL))
        self.help_menu.addSeparator()
        self.templates_action = self.help_menu.addAction("")
        self.templates_action.setShortcut(QKeySequence("F1"))
        self.templates_action.triggered.connect(self.show_template_help)
        self.help_menu.addSeparator()
        self.about_action = self.help_menu.addAction("")
        self.about_action.triggered.connect(self.show_about)

        # Keyboard-only shortcuts for the two most frequent actions.
        self.download_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.download_shortcut.activated.connect(self.try_start_download)
        self.cancel_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.cancel_shortcut.activated.connect(self.cancel_download)

        # Alt+Shift+A must also work while a QLineEdit has focus, where Qt would
        # otherwise deliver it to the widget's built-in "Select All" handler.
        self._hotkey_filter = _AlwaysOnTopShortcut(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self._hotkey_filter)

    def _set_log_visible(self, visible: bool) -> None:
        if self.toggle_log_action.isChecked() != visible:
            self.toggle_log_action.blockSignals(True)
            self.toggle_log_action.setChecked(visible)
            self.toggle_log_action.blockSignals(False)
        if visible:
            self.bottom_tabs.setVisible(True)
            sizes = self.main_splitter.sizes()
            total = max(1, sizes[0] + sizes[1])
            top = max(1, total - self._log_height)
            self.main_splitter.setSizes([top, self._log_height])
        else:
            sizes = self.main_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 0:
                self._log_height = sizes[1]
            self.bottom_tabs.setVisible(False)

    # --------------------------------------------------------------- recent
    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        if not self._recent_entries:
            empty_action = self.recent_menu.addAction(self.i18n.t("menu_recent_empty"))
            empty_action.setEnabled(False)
            return
        for entry in self._recent_entries:
            url = entry["url"]
            title = entry.get("title", "")
            label = _elide_title(title) if title else _elide_url(url)
            action = self.recent_menu.addAction(label)
            action.setToolTip(url)
            action.triggered.connect(lambda _checked=False, value=url: self._use_recent_url(value))
        self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction(self.i18n.t("menu_recent_clear"))
        clear_action.triggered.connect(self.clear_recent_urls)

    def _use_recent_url(self, url: str) -> None:
        self.url_entry.setText(url)
        self.url_entry.setFocus()

    def clear_recent_urls(self) -> None:
        self._recent_entries = []
        self.settings.setValue("recent/urls", [])
        self.settings.sync()

    def _remember_url(self, url: str, title: str = "") -> None:
        url = url.strip()
        if not url:
            return
        previous = next((entry for entry in self._recent_entries if entry["url"] == url), None)
        if not title and previous is not None:
            # Keep the title we already know when a retry starts without one.
            title = previous.get("title", "")
        entries = [entry for entry in self._recent_entries if entry["url"] != url]
        entries.insert(0, {"url": url, "title": title.strip()})
        self._recent_entries = entries[:MAX_RECENT_URLS]
        self.settings.setValue("recent/urls", self._recent_entries)
        self.settings.sync()

    def _on_video_title(self, title: str) -> None:
        title = title.strip()
        if not title or not self._current_url or self._current_title:
            return
        self._current_title = title
        self._update_recent_title(self._current_url, title)

    def _update_recent_title(self, url: str, title: str) -> None:
        for entry in self._recent_entries:
            if entry["url"] == url:
                if entry.get("title") == title:
                    return
                entry["title"] = title
                self.settings.setValue("recent/urls", self._recent_entries)
                self.settings.sync()
                return

    def _retranslate(self) -> None:
        t = self.i18n.t
        self.base_title = t("app_title", version=self.version)
        self._set_window_title()

        self.source_group.setTitle(t("group_source"))
        self.label_url.setText(t("label_url"))
        self.paste_url_btn.setText(t("btn_clipboard"))
        self.paste_url_btn.setToolTip(t("tip_clipboard"))
        self.label_path.setText(t("label_path"))
        self.browse_path_btn.setText(t("btn_browse"))

        self.playlist_group.setTitle(t("group_playlist"))
        self.playlist_check.setText(t("chk_playlist"))
        self._fill_scope_combo()

        self.options_group.setTitle(t("group_options"))
        self._fill_type_combo()
        self._fill_quality_combo()
        self._fill_format_combo()
        self._fill_cookies_combo()
        self.label_type.setText(t("label_type"))
        self.label_quality.setText(t("label_quality"))
        self.label_format.setText(t("label_format"))
        self.label_filename.setText(t("label_filename"))
        self.filename_template_entry.setToolTip(t("tip_filename"))
        self.label_extra.setText(t("label_extra"))
        self.options_entry.setPlaceholderText(t("ph_extra"))
        self.options_entry.setToolTip(t("tip_extra"))
        self.label_cookies.setText(t("label_cookies"))
        self.skip_existing_check.setText(t("chk_skip_existing"))
        self.skip_existing_check.setToolTip(t("tip_skip_existing"))
        self.archive_check.setText(t("chk_archive"))
        self.archive_check.setToolTip(t("tip_archive"))
        self.remove_ads_check.setText(t("chk_remove_ads"))
        self.remove_ads_check.setToolTip(t("tip_remove_ads"))
        self.advanced_btn.setText(t("btn_advanced"))

        self.status_group.setTitle(t("group_status"))
        self.clear_log_btn.setText(t("btn_clear_log"))
        self.open_log_btn.setText(t("btn_open_log"))
        self.download_btn.setText(t("btn_download"))
        self.cancel_btn.setText(t("btn_stop"))
        self.load_links_btn.setText(t("btn_load_links"))
        self.env_title.setText(t("env_title"))
        self.env_download_btn.setText(t("btn_env_download"))
        self.env_retry_btn.setText(t("btn_env_retry"))

        self.bottom_tabs.setTabText(0, t("group_log"))
        self.bottom_tabs.setTabText(1, t("group_queue"))
        self.queue_add_btn.setText(t("btn_queue_add"))
        self.queue_remove_btn.setText(t("btn_queue_remove"))
        self.queue_clear_btn.setText(t("btn_queue_clear"))
        self.queue_save_btn.setText(t("btn_queue_save"))
        self.queue_start_btn.setText(t("btn_queue_start"))
        self._refresh_queue_labels()

        self.file_menu.setTitle(t("menu_file"))
        self.add_queue_action.setText(t("menu_add_queue"))
        self.load_links_action.setText(t("menu_load_links"))
        self.history_action.setText(t("menu_history"))
        self.open_folder_action.setText(t("menu_open_folder"))
        self.recent_menu.setTitle(t("menu_recent"))
        self.quit_action.setText(t("menu_exit"))

        self.edit_menu.setTitle(t("menu_edit"))
        self.paste_action.setText(t("menu_paste_url"))
        self.clear_url_action.setText(t("menu_clear_url"))
        self.copy_log_action.setText(t("menu_copy_log"))
        self.settings_action.setText(t("menu_settings"))

        self.view_menu.setTitle(t("menu_view"))
        self.toggle_log_action.setText(t("menu_show_panel"))
        self.theme_menu.setTitle(t("menu_theme"))
        for key, label_key in (
            ("system", "theme_system"),
            ("light", "theme_light"),
            ("dark", "theme_dark"),
        ):
            self.theme_actions[key].setText(t(label_key))
            self.theme_actions[key].setChecked(self._theme == key)
        self.always_on_top_action.setText(t("menu_always_on_top"))
        self.always_on_top_action.setChecked(self._always_on_top)
        self.minimize_to_tray_action.setText(t("menu_minimize_to_tray"))
        self.minimize_to_tray_action.setChecked(self._minimize_to_tray)

        self.tools_menu.setTitle(t("menu_tools"))
        self.check_env_action.setText(t("menu_check_env"))
        self.open_config_action.setText(t("menu_open_config"))
        self.update_action.setText(t("menu_update"))
        self.open_log_action.setText(t("menu_open_log"))
        self.language_menu.setTitle(t("menu_language"))
        self.help_menu.setTitle(t("menu_help"))
        self.website_action.setText(t("menu_website"))
        self.github_action.setText(t("menu_github"))
        self.issues_action.setText(t("menu_report_issue"))
        self.support_action.setText(t("menu_support"))
        self.templates_action.setText(t("menu_templates"))
        self.about_action.setText(t("menu_about"))
        self.language_en_action.setText(t("lang_en"))
        self.language_ru_action.setText(t("lang_ru"))
        self.language_en_action.setChecked(self.i18n.language == "en")
        self.language_ru_action.setChecked(self.i18n.language == "ru")

        if self._tray is not None:
            self._retranslate_tray()
        if not self._download_active:
            self.status_label.setText(t("label_ready"))
        self._apply_status_color()
        self._update_playlist_controls()


    def _fill_type_combo(self) -> None:
        current = self.download_type.currentData() or self._current_type
        self._fill_combo(
            self.download_type,
            [("video", self.i18n.t("type_video")), ("audio", self.i18n.t("type_audio"))],
            current,
        )

    def _fill_quality_combo(self, preserve: bool = True) -> None:
        media = self.download_type.currentData() or "video"
        if media == "audio":
            choices = [(key, self.i18n.t("quality_audio_best")) for key in AUDIO_QUALITY_CHOICES]
            default = AUDIO_QUALITY_CHOICES[0]
        else:
            choices = [
                (key, self.i18n.t("quality_best") if key == "best" else key) for key in VIDEO_QUALITY_CHOICES
            ]
            default = DEFAULT_VIDEO_QUALITY
        current = self.quality_combo.currentData() if preserve else None
        if current not in [key for key, _ in choices]:
            current = self._format_state.get(media, {}).get("quality", default)
        if current not in [key for key, _ in choices]:
            current = default
        self._fill_combo(self.quality_combo, choices, current)

    def _fill_format_combo(self, preserve: bool = True) -> None:
        media = self.download_type.currentData() or "video"
        formats = AUDIO_FORMATS if media == "audio" else VIDEO_FORMATS
        current = self.format_combo.currentData() if preserve else None
        if current not in formats:
            current = self._format_state.get(media, {}).get("format", formats[0])
        if current not in formats:
            current = normalize_format(media, current or "")
        if current not in formats:
            current = formats[0]
        self._fill_combo(self.format_combo, [(key, key) for key in formats], current)

    def _fill_cookies_combo(self) -> None:
        current = self.cookies_combo.currentData() or ""
        choices = [("", self.i18n.t("cookies_none"))]
        choices.extend((key, key) for key in COOKIE_BROWSERS)
        self._fill_combo(self.cookies_combo, choices, current)

    def _fill_scope_combo(self) -> None:
        current = self.playlist_scope_combo.currentData() or "all"
        choices = [
            ("all", self.i18n.t("scope_all")),
            ("first", self.i18n.t("scope_first")),
            ("last", self.i18n.t("scope_last")),
            ("range", self.i18n.t("scope_range")),
            ("items", self.i18n.t("scope_items")),
        ]
        self._fill_combo(self.playlist_scope_combo, choices, current)
        self._update_playlist_controls()

    @staticmethod
    def _fill_combo(combo: QComboBox, choices: list[tuple[str, str]], current: str) -> None:
        was_loading = combo.blockSignals(True)
        try:
            combo.clear()
            for key, label in choices:
                combo.addItem(label, key)
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
        finally:
            combo.blockSignals(was_loading)

    # ------------------------------------------------------------- settings
    def _restore_settings(self) -> None:
        settings = self.settings
        self._loading = True
        try:
            media = str(settings.value("download/type", "video"))
            self._current_type = media if media in ("video", "audio") else "video"
            self.download_type.setCurrentIndex(max(0, self.download_type.findData(self._current_type)))

            for key, defaults in (
                ("video", {"quality": DEFAULT_VIDEO_QUALITY, "format": DEFAULT_VIDEO_FORMAT}),
                ("audio", {"quality": AUDIO_QUALITY_CHOICES[0], "format": AUDIO_FORMATS[0]}),
            ):
                stored_quality = str(settings.value(f"download/quality/{key}", defaults["quality"]))
                stored_format = str(settings.value(f"download/format/{key}", defaults["format"]))
                self._format_state[key] = {
                    "quality": stored_quality,
                    "format": normalize_format(key, stored_format),
                }

            self._recent_entries = _as_recent_entries(settings.value("recent/urls"))

            self._fill_quality_combo(preserve=False)
            self._fill_format_combo(preserve=False)
            self.filename_template_entry.setText(str(settings.value("download/template", DEFAULT_TEMPLATE)))
            self.options_entry.setText(str(settings.value("download/extra_args", "")))
            self.path_entry.setText(str(settings.value("download/path", self.config.default_download_path)))

            self.playlist_check.setChecked(_as_bool(settings.value("playlist/enabled", False)))
            scope = str(settings.value("playlist/scope", "all"))
            index = self.playlist_scope_combo.findData(scope)
            self.playlist_scope_combo.setCurrentIndex(index if index >= 0 else 0)
            self.playlist_spec_edit.setText(str(settings.value("playlist/items", "")))

            cookies = str(settings.value("download/cookies", ""))
            index = self.cookies_combo.findData(cookies)
            self.cookies_combo.setCurrentIndex(index if index >= 0 else 0)
            self.skip_existing_check.setChecked(_as_bool(settings.value("download/skip_existing", False)))
            self.archive_check.setChecked(_as_bool(settings.value("download/archive", False)))
            self.remove_ads_check.setChecked(_as_bool(settings.value("download/remove_ads", True)))

            self.i18n.set_language(str(settings.value("ui/language", self.i18n.language)))

            self._theme = str(settings.value("ui/theme", THEME_SYSTEM))
            self._minimize_to_tray = _as_bool(settings.value("ui/minimize_to_tray", False))
            self._always_on_top = _as_bool(settings.value("ui/always_on_top", False))
            self._load_history()

            advanced = _as_bool(settings.value("window/advanced", False))
            self.advanced_btn.blockSignals(True)
            self.advanced_btn.setChecked(advanced)
            self.advanced_btn.blockSignals(False)
            self.advanced_panel.setVisible(advanced)
            self.advanced_btn.setArrowType(
                Qt.ArrowType.DownArrow if advanced else Qt.ArrowType.RightArrow
            )

            geometry = settings.value("window/geometry")
            if geometry:
                self.restoreGeometry(geometry)
            splitter_state = settings.value("window/splitter")
            if splitter_state:
                self.main_splitter.restoreState(splitter_state)
            sizes = self.main_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 0:
                self._log_height = sizes[1]
            self._set_log_visible(_as_bool(settings.value("window/log_visible", True)))
            tab_index = settings.value("window/bottom_tab", 0)
            try:
                self.bottom_tabs.setCurrentIndex(int(tab_index))
            except (TypeError, ValueError):
                self.bottom_tabs.setCurrentIndex(0)
        finally:
            self._loading = False
        self._update_playlist_controls()
        if self._always_on_top:
            flags = self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            self.setWindowFlags(flags)
        self._set_theme(self._theme, persist=False)

    def _persist_settings(self) -> None:
        if self._loading:
            return
        settings = self.settings
        media = self.download_type.currentData() or "video"
        self._format_state[media] = {
            "quality": self.quality_combo.currentData() or DEFAULT_VIDEO_QUALITY,
            "format": self.format_combo.currentData() or normalize_format(media, ""),
        }
        settings.setValue("download/type", media)
        for key, state in self._format_state.items():
            settings.setValue(f"download/quality/{key}", state["quality"])
            settings.setValue(f"download/format/{key}", state["format"])
        settings.setValue("download/template", self.filename_template_entry.text())
        settings.setValue("download/extra_args", self.options_entry.text())
        settings.setValue("download/path", self.path_entry.text())
        settings.setValue("download/cookies", self.cookies_combo.currentData() or "")
        settings.setValue("download/skip_existing", self.skip_existing_check.isChecked())
        settings.setValue("download/archive", self.archive_check.isChecked())
        settings.setValue("download/remove_ads", self.remove_ads_check.isChecked())
        settings.setValue("playlist/enabled", self.playlist_check.isChecked())
        settings.setValue("playlist/scope", self.playlist_scope_combo.currentData() or "all")
        settings.setValue("playlist/items", self.playlist_spec_edit.text())
        settings.setValue("ui/language", self.i18n.language)
        settings.setValue("ui/theme", self._theme)
        settings.setValue("ui/minimize_to_tray", self._minimize_to_tray)
        settings.setValue("ui/always_on_top", self._always_on_top)
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/splitter", self.main_splitter.saveState())
        settings.setValue("window/log_visible", self.toggle_log_action.isChecked())
        settings.setValue("window/advanced", self.advanced_btn.isChecked())
        settings.setValue("window/bottom_tab", self.bottom_tabs.currentIndex())
        settings.sync()

    # -------------------------------------------------------------- actions
    def set_language(self, language: str) -> None:
        self.i18n.set_language(language)
        self._retranslate()
        self._persist_settings()

    def _on_type_changed(self) -> None:
        if self._loading:
            return
        media = self.download_type.currentData() or "video"
        if media == self._current_type:
            return
        self._format_state[self._current_type] = {
            "quality": self.quality_combo.currentData() or "",
            "format": self.format_combo.currentData() or "",
        }
        self._current_type = media
        self._fill_quality_combo(preserve=False)
        self._fill_format_combo(preserve=False)
        self._persist_settings()

    def _on_quality_changed(self) -> None:
        if self._loading:
            return
        self._format_state[self._current_type]["quality"] = self.quality_combo.currentData() or ""
        self._persist_settings()

    def _on_format_changed(self) -> None:
        if self._loading:
            return
        self._format_state[self._current_type]["format"] = self.format_combo.currentData() or ""
        self._persist_settings()

    def _on_scope_changed(self) -> None:
        self._update_playlist_controls()
        self._persist_settings()

    def _update_playlist_controls(self) -> None:
        checked = self.playlist_check.isChecked()
        self.playlist_scope_combo.setEnabled(checked)
        scope = self.playlist_scope_combo.currentData() or "all"
        needs_input = checked and scope in ("range", "items")
        self.playlist_spec_label.setVisible(needs_input)
        self.playlist_spec_edit.setVisible(needs_input)
        if needs_input:
            if scope == "range":
                self.playlist_spec_label.setText(self.i18n.t("label_range"))
                self.playlist_spec_edit.setPlaceholderText(self.i18n.t("ph_range"))
            else:
                self.playlist_spec_label.setText(self.i18n.t("label_items"))
                self.playlist_spec_edit.setPlaceholderText(self.i18n.t("ph_items"))

    def _toggle_advanced(self, checked: bool) -> None:
        self.advanced_panel.setVisible(checked)
        self.advanced_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        self.settings.setValue("window/advanced", checked)
        self.settings.sync()

    # ---------------------------------------------------------------- queue
    def _queue_urls(self) -> list[str]:
        return [
            str(self.queue_list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.queue_list.count())
        ]

    def _queue_row_for_url(self, url: str) -> int:
        for row in range(self.queue_list.count()):
            if str(self.queue_list.item(row).data(Qt.ItemDataRole.UserRole)) == url:
                return row
        return -1

    def paste_link_into_queue(self) -> None:
        text = QApplication.clipboard().text().strip()
        if not text:
            QMessageBox.information(
                self, self.i18n.t("btn_clipboard"), self.i18n.t("clipboard_empty")
            )
            return
        url = text.splitlines()[0].strip()
        if not url.lower().startswith(URL_PREFIXES):
            QMessageBox.warning(self, self.i18n.t("dlg_warning"), self.i18n.t("queue_invalid"))
            return
        self.add_url_to_queue(url)

    def add_current_url_to_queue(self) -> None:
        url = self.url_entry.text().strip()
        if not url:
            urls = self.url_list or []
            if len(urls) == 1:
                url = urls[0]
        if not url.lower().startswith(URL_PREFIXES):
            QMessageBox.warning(self, self.i18n.t("dlg_warning"), self.i18n.t("queue_invalid"))
            return
        self.add_url_to_queue(url)

    def add_url_to_queue(self, url: str) -> None:
        if self._queue_row_for_url(url) >= 0:
            return
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, url)
        item.setData(Qt.ItemDataRole.UserRole + 1, "pending")
        self.queue_list.addItem(item)
        self._refresh_queue_labels()
        if self.bottom_tabs.isHidden():
            self._set_log_visible(True)
        self.bottom_tabs.setCurrentWidget(self.queue_group)
        self._append_log(self.i18n.t("queue_added", url=url))

    def remove_selected_queue_items(self) -> None:
        for item in self.queue_list.selectedItems():
            if item.data(Qt.ItemDataRole.UserRole + 1) == "active":
                continue
            self.queue_list.takeItem(self.queue_list.row(item))
        self._refresh_queue_labels()

    def clear_queue(self) -> None:
        for row in range(self.queue_list.count() - 1, -1, -1):
            item = self.queue_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole + 1) != "active":
                self.queue_list.takeItem(row)
        self._refresh_queue_labels()

    def save_queue_to_file(self) -> None:
        urls = self._queue_urls()
        if not urls:
            return
        default_path = os.path.join(self.config.default_download_path, "queue.txt")
        path, _selected = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("btn_queue_save"),
            default_path,
            "Text files (*.txt);;All files (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(urls) + "\n")
        except OSError as exc:
            QMessageBox.warning(self, self.i18n.t("dlg_warning"), str(exc))
            return
        self._append_log(self.i18n.t("queue_saved", path=path))

    def start_queue(self) -> None:
        if self._download_active or self._batch_active:
            QMessageBox.information(self, self.i18n.t("dlg_info"), self.i18n.t("err_already_running"))
            return
        urls = []
        for row in range(self.queue_list.count()):
            item = self.queue_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole + 1) in ("done", "active"):
                continue
            urls.append(str(item.data(Qt.ItemDataRole.UserRole)))
        if not urls:
            QMessageBox.information(self, self.i18n.t("dlg_info"), self.i18n.t("queue_empty_warning"))
            return
        self._start_batch(urls)

    def _queue_mark(self, url: str, status: str) -> None:
        row = self._queue_row_for_url(url)
        if row < 0:
            return
        item = self.queue_list.item(row)
        item.setData(Qt.ItemDataRole.UserRole + 1, status)
        self._refresh_queue_labels()

    def _queue_status_text(self, status: str) -> str:
        key = f"queue_status_{status}"
        text = self.i18n.t(key)
        return self.i18n.t("queue_status_pending") if text.startswith("queue_status_") else text

    def _refresh_queue_labels(self) -> None:
        self.queue_save_btn.setEnabled(self.queue_list.count() > 0)
        for row in range(self.queue_list.count()):
            item = self.queue_list.item(row)
            status = str(item.data(Qt.ItemDataRole.UserRole + 1) or "pending")
            url = str(item.data(Qt.ItemDataRole.UserRole) or "")
            item.setText(f"[{self._queue_status_text(status)}] {_elide_url(url)}")
            item.setToolTip(url)

    def _show_log_menu(self, position) -> None:
        menu = QMenu(self)
        copy_action = menu.addAction(self.i18n.t("menu_copy_log"))
        copy_action.triggered.connect(self.copy_log_to_clipboard)
        menu.addSeparator()
        clear_action = menu.addAction(self.i18n.t("btn_clear_log"))
        clear_action.triggered.connect(self.log_text.clear)
        open_action = menu.addAction(self.i18n.t("btn_open_log"))
        open_action.triggered.connect(self.open_log_file)
        menu.exec(self.log_text.mapToGlobal(position))

    def copy_log_to_clipboard(self) -> None:
        text = self.log_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _build_queue_menu(self, item: QListWidgetItem | None) -> QMenu:
        menu = QMenu(self)
        paste_action = menu.addAction(self.i18n.t("menu_paste_queue"))
        paste_action.triggered.connect(self.paste_link_into_queue)
        url = str(item.data(Qt.ItemDataRole.UserRole) or "") if item is not None else ""
        if url:
            menu.addSeparator()
            copy_action = menu.addAction(self.i18n.t("menu_copy_link"))
            copy_action.triggered.connect(lambda: QApplication.clipboard().setText(url))
        return menu

    def _show_queue_menu(self, position) -> None:
        item = self.queue_list.itemAt(position)
        if item is None:
            selected = self.queue_list.selectedItems()
            item = selected[0] if selected else self.queue_list.currentItem()
        menu = self._build_queue_menu(item)
        menu.exec(self.queue_list.mapToGlobal(position))

    # -------------------------------------------------------------- settings
    def show_settings(self) -> None:
        dialog = SettingsDialog(
            self,
            self.i18n,
            {
                "language": self.i18n.language,
                "theme": self._theme,
                "folder": self.path_entry.text().strip(),
                "minimize_to_tray": self._minimize_to_tray,
                "always_on_top": self._always_on_top,
            },
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.result_values()
        if values["language"] != self.i18n.language:
            self.i18n.set_language(values["language"])
        folder = values["folder"]
        if folder and os.path.isdir(folder):
            self.path_entry.setText(folder)
        self._set_minimize_to_tray(bool(values["minimize_to_tray"]))
        self._set_always_on_top(bool(values["always_on_top"]))
        self._set_theme(str(values["theme"]))
        self._retranslate()
        self._persist_settings()

    def open_config_folder(self) -> None:
        folder = os.path.dirname(self.config.config_path) or self.config.launch_dir
        if not os.path.isdir(folder):
            folder = self.config.launch_dir
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _open_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    # --------------------------------------------------------------- history
    def _load_history(self) -> None:
        raw = self.settings.value("history/items", "")
        entries: list[dict] = []
        if raw:
            try:
                data = json.loads(str(raw))
            except (TypeError, ValueError):
                data = []
            if isinstance(data, list):
                entries = [entry for entry in data if isinstance(entry, dict)]
        self._history = entries[:MAX_HISTORY_ITEMS]

    def _save_history(self) -> None:
        self._history = self._history[:MAX_HISTORY_ITEMS]
        self.settings.setValue("history/items", json.dumps(self._history, ensure_ascii=False))
        self.settings.sync()

    def _append_history(self, status: str) -> None:
        self._history.insert(
            0,
            {
                "time": time.strftime("%Y-%m-%d %H:%M"),
                "url": self._current_url,
                "title": self._current_title,
                "path": self._last_output_file,
                "status": status,
            },
        )
        self._save_history()

    def show_history(self) -> None:
        dialog = HistoryDialog(self, self.i18n, self._history)
        dialog.download_requested.connect(self._download_again)
        dialog.exec()
        if dialog.cleared:
            self._history = []
            self._save_history()

    def _download_again(self, url: str) -> None:
        self.url_entry.setText(url)
        self.raise_()
        self.activateWindow()
        self.try_start_download()

    # ---------------------------------------------------------- theme & tray
    def _set_theme(self, name: str, persist: bool = True) -> None:
        self._theme = name if name in ("system", "light", "dark") else THEME_SYSTEM
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self._theme)
        action = self.theme_actions.get(self._theme)
        if action is not None and not action.isChecked():
            action.setChecked(True)
        self._apply_status_color()
        if persist:
            self.settings.setValue("ui/theme", self._theme)
            self.settings.sync()

    def _set_always_on_top(self, checked: bool) -> None:
        self._always_on_top = bool(checked)
        if self.always_on_top_action.isChecked() != self._always_on_top:
            self.always_on_top_action.blockSignals(True)
            self.always_on_top_action.setChecked(self._always_on_top)
            self.always_on_top_action.blockSignals(False)
        flags = self.windowFlags()
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self.settings.setValue("ui/always_on_top", self._always_on_top)
        self.settings.sync()

    def _set_minimize_to_tray(self, checked: bool) -> None:
        self._minimize_to_tray = bool(checked)
        if self.minimize_to_tray_action.isChecked() != self._minimize_to_tray:
            self.minimize_to_tray_action.blockSignals(True)
            self.minimize_to_tray_action.setChecked(self._minimize_to_tray)
            self.minimize_to_tray_action.blockSignals(False)
        self.settings.setValue("ui/minimize_to_tray", self._minimize_to_tray)
        self.settings.sync()

    def _show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _hide_window(self) -> None:
        self.hide()
        if self._tray is not None and not self._tray.isVisible():
            self._tray.show()

    def _quit_app(self) -> None:
        self._quitting = True
        self.close()

    def _retranslate_tray(self) -> None:
        if self._tray is None:
            return
        self._tray.setToolTip(self.base_title)
        menu = getattr(self, "_tray_menu", None)
        if menu is not None:
            self.tray_show_action.setText(self.i18n.t("tray_show"))
            self.tray_cancel_action.setText(self.i18n.t("tray_cancel"))
            self.tray_folder_action.setText(self.i18n.t("tray_open_folder"))
            self.tray_quit_action.setText(self.i18n.t("tray_quit"))

    def browse_path(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, self.i18n.t("label_path"), self.path_entry.text()
        )
        if directory:
            self.path_entry.setText(directory)
            self._persist_settings()

    def paste_url_from_clipboard(self) -> None:
        text = QApplication.clipboard().text().strip()
        if not text:
            QMessageBox.information(self, self.i18n.t("btn_clipboard"), self.i18n.t("clipboard_empty"))
            return
        self.url_entry.setText(text.splitlines()[0].strip())
        self.url_entry.setFocus()

    def open_download_folder(self) -> None:
        path = self.path_entry.text().strip()
        if not path or not os.path.isdir(path):
            path = self.config.default_download_path
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_log_file(self) -> None:
        if not os.path.isfile(self.file_log.path):
            QMessageBox.information(self, self.i18n.t("group_log"), self.i18n.t("open_log_missing"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_log.path))

    def show_about(self) -> None:
        resource_dir = getattr(sys, "_MEIPASS", self.config.launch_dir)
        AboutDialog(
            self,
            self.i18n,
            self.version,
            PROJECT_URL,
            license_path=os.path.join(resource_dir, "LICENSE"),
            website_url=WEBSITE_URL,
            ytdlp_version=self._ytdlp_version,
            ffmpeg_version=self._ffmpeg_version,
        ).exec()

    def show_template_help(self) -> None:
        dialog = TemplateHelpDialog(
            self, self.i18n, self.filename_template_entry.text().strip() or DEFAULT_TEMPLATE
        )
        dialog.exec()
        if dialog.chosen_template:
            self.filename_template_entry.setText(dialog.chosen_template)
            self._persist_settings()
            self._append_log(self.i18n.t("templates_applied", template=dialog.chosen_template))

    # ------------------------------------------------------------- playlist
    def resolve_playlist_spec(self) -> tuple[str, str | None]:
        if not self.playlist_check.isChecked():
            return "", None
        scope = self.playlist_scope_combo.currentData() or "all"
        if scope in ("all", "first", "last"):
            return scope, None
        raw = self.playlist_spec_edit.text().strip()
        if scope == "range":
            match = re.fullmatch(r"(\d+)\s*[:\-]\s*(\d+)", raw)
            if not match:
                return "", self.i18n.t("err_range")
            start, end = int(match.group(1)), int(match.group(2))
            if start < 1 or end < start:
                return "", self.i18n.t("err_range_order")
            return f"{start}:{end}", None
        parts = [part.strip() for part in raw.split(",")]
        if not raw or not all(re.fullmatch(r"\d+", part) and int(part) >= 1 for part in parts):
            return "", self.i18n.t("err_items")
        return ",".join(str(int(part)) for part in parts), None

    # ------------------------------------------------------------- download
    def try_start_download(self) -> None:
        if self._download_active:
            QMessageBox.information(self, self.i18n.t("dlg_info"), self.i18n.t("err_already_running"))
            return
        url = self.url_entry.text().strip()
        if not url:
            QMessageBox.warning(self, self.i18n.t("dlg_warning"), self.i18n.t("err_no_url"))
            return
        spec, error = self.resolve_playlist_spec()
        if error:
            QMessageBox.warning(self, self.i18n.t("dlg_warning"), error)
            return
        self.start_download(url, spec)

    def _build_request(self, url: str, playlist_items: str) -> DownloadRequest:
        download_type = self.download_type.currentData() or "video"
        return DownloadRequest(
            url=url,
            output_dir=self.path_entry.text().strip() or self.config.default_download_path,
            filename_template=self.filename_template_entry.text().strip() or DEFAULT_TEMPLATE,
            download_type=download_type,
            quality=self.quality_combo.currentData() or "",
            output_format=self.format_combo.currentData() or "",
            playlist_enabled=self.playlist_check.isChecked(),
            playlist_items=playlist_items,
            extra_options=self.options_entry.text(),
            cookies_from_browser=self.cookies_combo.currentData() or "",
            archive_path=self._archive_path() if self.archive_check.isChecked() else "",
            skip_existing=self.skip_existing_check.isChecked(),
            remove_ads=self.remove_ads_check.isChecked(),
        )

    def _archive_path(self) -> str:
        directory = self.path_entry.text().strip() or self.config.default_download_path
        return os.path.join(directory, "yt-dlp-archive.txt")

    def start_download(self, url: str, playlist_items: str = "") -> bool:
        if not self._check_ready(url):
            return False
        try:
            command = build_command(
                self._build_request(url, playlist_items),
                yt_dlp_path=self.config.yt_dlp_path,
                ffmpeg_path=self.config.ffmpeg_path,
            )
        except ExtraOptionsError as exc:
            QMessageBox.warning(
                self, self.i18n.t("dlg_warning"), self.i18n.t("err_extra_args", error=str(exc))
            )
            return False

        self._append_log(" ".join(_quote(part) for part in command))
        self._current_url = url
        self._current_title = ""
        self._last_output_file = ""
        self._set_detail("")
        # The recent list tracks every attempted download, not just the
        # successful ones, so the URL is remembered before yt-dlp starts.
        self._remember_url(url)
        self._item_percent = 0.0
        self._download_active = True
        self._set_running(True)
        self.progress_bar.setValue(0)
        self._set_status(self.i18n.t("status_starting"), "blue")
        self._persist_settings()

        if not self.runner.start(command):
            self._download_active = False
            self._set_running(False)
            QMessageBox.critical(
                self, self.i18n.t("dlg_error"), self.i18n.t("err_start", error=self.config.yt_dlp_path)
            )
            return False
        return True

    def _check_ready(self, url: str) -> bool:
        if not os.path.isfile(self.config.yt_dlp_path):
            self._ytdlp_ok = False
            QMessageBox.critical(
                self,
                self.i18n.t("dlg_error"),
                self.i18n.t("missing_ytdlp", path=self.config.yt_dlp_path),
            )
            return False
        if not is_writable_dir(self.path_entry.text().strip() or self.config.default_download_path):
            QMessageBox.warning(
                self,
                self.i18n.t("dlg_warning"),
                self.i18n.t("path_not_writable", path=self.path_entry.text()),
            )
            return False
        return bool(url)

    def _set_running(self, running: bool) -> None:
        self.download_btn.setEnabled(not running and self._ytdlp_ok)
        self.cancel_btn.setEnabled(running)
        self.load_links_btn.setEnabled(not running)
        self.load_links_action.setEnabled(not running)
        self.update_action.setEnabled(not running and self._ytdlp_ok)
        for group in (self.source_group, self.playlist_group, self.options_group):
            group.setEnabled(not running)

    def cancel_download(self) -> None:
        if not self.runner.is_running:
            return
        self.cancel_btn.setEnabled(False)
        self._set_status(self.i18n.t("status_stopping"), "orange")
        self.runner.cancel()

    def _on_progress(self, update: ProgressUpdate) -> None:
        if update.filename:
            self._last_output_file = update.filename
        if update.percent is not None:
            self._item_percent = update.percent
            if self._batch_active:
                overall = (
                    (self._batch_current - 1) + self._item_percent / 100.0
                ) / max(1, self._batch_total)
                self.progress_bar.setValue(int(overall * 100))
            else:
                self.progress_bar.setValue(int(update.percent))

        parts: list[str] = []
        if update.title:
            parts.append(update.title)
        if update.total:
            parts.append(update.total)
        if update.percent is not None:
            parts.append(f"{update.percent:.1f}%")
        if update.speed:
            parts.append(update.speed)
        if update.eta:
            parts.append(self.i18n.t("eta", value=update.eta))
        if update.stage:
            parts.append(self._stage_text(update.stage))
        detail = " · ".join(parts) if parts else self.i18n.t("status_downloading")
        if self._batch_active:
            detail = (
                f"{self.i18n.t('batch_item', current=self._batch_current, total=self._batch_total)}"
                f" — {detail}"
            )
        self._set_detail(detail, update.filename)

        short_parts: list[str] = []
        if update.percent is not None:
            short_parts.append(f"{update.percent:.1f}%")
        if update.speed:
            short_parts.append(update.speed)
        text = " · ".join(short_parts) if short_parts else self.i18n.t("status_downloading")
        self._set_status(text, "blue")
        self.status_label.setToolTip(update.filename)

    def _stage_text(self, stage: str) -> str:
        text = self.i18n.t(f"stage_{stage}")
        return self.i18n.t("stage_default") if text.startswith("stage_") else text

    def _on_finished(self, exit_code: int, cancelled: bool) -> None:
        if not self._download_active:
            return
        self._download_active = False
        self._set_running(False)

        ok = exit_code == 0 and not cancelled
        if cancelled:
            self._set_status(self.i18n.t("status_cancelled"), "orange")
            history_status = "cancelled"
        elif ok:
            self.progress_bar.setValue(100)
            self._set_status(self.i18n.t("status_done"), "green")
            history_status = "ok"
            self._notify(
                self.i18n.t("notify_done_title"),
                self.i18n.t("notify_done_text", path=self.path_entry.text()),
            )
        else:
            self._set_status(self.i18n.t("status_failed", code=exit_code), "red")
            history_status = "failed"
            self._notify(
                self.i18n.t("notify_failed_title"), self.i18n.t("notify_failed_text", code=exit_code)
            )

        self._append_history(history_status)
        self._queue_mark(
            self._current_url,
            "done" if ok else ("cancelled" if cancelled else "failed"),
        )

        if not self._batch_active:
            return

        detail = ""
        if not ok:
            detail = self.i18n.t("status_cancelled") if cancelled else self.i18n.t(
                "status_failed", code=exit_code
            )
        self._batch_results.append(BatchResult(self._current_url, ok, detail))

        if cancelled:
            self._finish_batch()
        elif self._batch_queue:
            QTimer.singleShot(0, self._start_next_batch_item)
        else:
            self._finish_batch()

    def _apply_status_color(self) -> None:
        palette = STATUS_COLORS[resolve_theme(self._theme)]
        value = palette.get(self._status_color_name, self._status_color_name)
        self.status_label.setStyleSheet(f"color: {value};")

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.setText(text)
        self._status_color_name = color
        self._apply_status_color()

    def _set_detail(self, text: str, tooltip: str = "") -> None:
        self.progress_detail_label.setText(text)
        self.progress_detail_label.setVisible(bool(text))
        self.progress_detail_label.setToolTip(tooltip)

    # ---------------------------------------------------------------- batch
    def _start_batch(self, urls: list[str]) -> None:
        self._batch_queue = [url for url in urls if url.strip()]
        if not self._batch_queue:
            return
        self._batch_results = []
        self._batch_total = len(self._batch_queue)
        self._batch_current = 0
        self._batch_active = True
        self.progress_bar.setValue(0)
        self._set_detail("")
        self._set_window_title()
        self._start_next_batch_item()

    def _start_next_batch_item(self) -> None:
        if not self._batch_queue:
            self._finish_batch()
            return
        url = self._batch_queue.pop(0)
        self._batch_current += 1
        self._queue_mark(url, "active")
        self._append_log(
            self.i18n.t(
                "batch_log_start", current=self._batch_current, total=self._batch_total, url=url
            )
        )
        self._set_window_title()
        if not self.start_download(url, ""):
            self._queue_mark(url, "failed")
            self._batch_results.append(
                BatchResult(url, False, self.i18n.t("err_start", error=self.config.yt_dlp_path))
            )
            if self._batch_queue:
                QTimer.singleShot(0, self._start_next_batch_item)
            else:
                self._finish_batch()

    def _finish_batch(self) -> None:
        results = list(self._batch_results)
        total = self._batch_total
        self._batch_active = False
        self._batch_queue = []
        self._batch_results = []
        self._set_detail("")
        self._set_window_title()
        succeeded = sum(1 for result in results if result.ok)
        self._append_log(self.i18n.t("batch_finished", done=succeeded, total=total))
        dialog = BatchSummaryDialog(self, self.i18n, results)
        dialog.exec()
        if dialog.retry_urls:
            self._start_batch(dialog.retry_urls)

    def _set_window_title(self) -> None:
        title = self.base_title
        if self._batch_active:
            title = self.i18n.t(
                "batch_title", title=title, current=self._batch_current, total=self._batch_total
            )
        self.setWindowTitle(title)

    # ------------------------------------------------------------------- log
    def _append_log(self, text: str) -> None:
        scrollbar = self.log_text.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
        self.log_text.appendPlainText(text)
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _log_event(self, text: str) -> None:
        """Write a UI-generated event to both the log panel and the log file."""
        message = text.replace("\n", " ")
        self._append_log(message)
        self.file_log.write(message)

    # ------------------------------------------------------------ file input
    def load_links_from_file(self) -> None:
        file_path, _selected = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("btn_load_links"),
            "",
            "Text files (*.txt);;All files (*.*)",
        )
        if file_path:
            self._load_links(file_path)

    def _load_links(self, file_path: str) -> None:
        try:
            urls = read_url_file(file_path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self, self.i18n.t("dlg_error"), self.i18n.t("err_read_file", error=str(exc))
            )
            return
        if not urls:
            QMessageBox.warning(self, self.i18n.t("dlg_warning"), self.i18n.t("err_no_urls"))
            return

        self.url_list = urls
        self._append_log(self.i18n.t("loaded_urls", count=len(urls), path=file_path))
        if len(urls) == 1:
            self.url_entry.setText(urls[0])
            return
        answer = QMessageBox.question(
            self,
            self.i18n.t("batch_confirm_title"),
            self.i18n.t("batch_confirm", count=len(urls)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._start_batch(urls)

    # ---------------------------------------------------------- drag & drop
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt API
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt API
        mime = event.mimeData()
        local_files = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
        text_file = next((path for path in local_files if path.lower().endswith(".txt")), None)
        if text_file:
            self._load_links(text_file)
            event.acceptProposedAction()
            return

        urls = [
            url.toString()
            for url in mime.urls()
            if not url.isLocalFile() and url.scheme() in ("http", "https")
        ]
        if not urls and mime.hasText():
            urls = [
                line.strip()
                for line in mime.text().splitlines()
                if line.strip().lower().startswith(URL_PREFIXES)
            ]
        if not urls:
            return
        if len(urls) == 1:
            self.url_entry.setText(urls[0])
        else:
            self.url_list = urls
            answer = QMessageBox.question(
                self,
                self.i18n.t("batch_confirm_title"),
                self.i18n.t("batch_confirm", count=len(urls)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._start_batch(urls)
        event.acceptProposedAction()

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self._maybe_prefill_from_clipboard()

    def _maybe_prefill_from_clipboard(self) -> None:
        if self.url_entry.text().strip() or self._download_active:
            return
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        first_line = text.splitlines()[0].strip()
        if first_line.lower().startswith(URL_PREFIXES):
            self.url_entry.setText(first_line)

    # ------------------------------------------------------------- tray/ver
    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self.windowIcon(), self)
        self._tray.setToolTip(self.base_title)

        self._tray_menu = QMenu(self)
        self.tray_show_action = self._tray_menu.addAction("")
        self.tray_show_action.triggered.connect(self._show_window)
        self.tray_cancel_action = self._tray_menu.addAction("")
        self.tray_cancel_action.triggered.connect(self.cancel_download)
        self.tray_folder_action = self._tray_menu.addAction("")
        self.tray_folder_action.triggered.connect(self.open_download_folder)
        self._tray_menu.addSeparator()
        self.tray_quit_action = self._tray_menu.addAction("")
        self.tray_quit_action.triggered.connect(self._quit_app)
        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._retranslate_tray()
        self._tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self._show_window()

    def _notify(self, title: str, message: str) -> None:
        if self._tray is not None and QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)

    def _fetch_ytdlp_version(self) -> None:
        self._ytdlp_version = ""
        if not os.path.isfile(self.config.yt_dlp_path):
            return
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        hide_console_window(process)
        process.finished.connect(lambda code, _status: self._on_version_finished(process, code))
        self._version_process = process
        process.start(self.config.yt_dlp_path, ["--version"])

    def _on_version_finished(self, process: QProcess, _code: int) -> None:
        output = decode_line(bytes(process.readAllStandardOutput())).strip()
        self._ytdlp_version = output.splitlines()[0].strip() if output else ""
        process.deleteLater()
        self._version_process = None

    def _fetch_ffmpeg_version(self) -> None:
        self._ffmpeg_version = ""
        if not os.path.isfile(self.config.ffmpeg_path):
            return
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        hide_console_window(process)
        process.finished.connect(
            lambda code, _status: self._on_ffmpeg_version_finished(process, code)
        )
        self._ffmpeg_process = process
        process.start(self.config.ffmpeg_path, ["-version"])

    def _on_ffmpeg_version_finished(self, process: QProcess, _code: int) -> None:
        output = decode_line(bytes(process.readAllStandardOutput())).strip()
        first_line = output.splitlines()[0] if output else ""
        match = re.match(r"ffmpeg version\s+(\S+)", first_line)
        self._ffmpeg_version = match.group(1) if match else ""
        process.deleteLater()
        self._ffmpeg_process = None

    def update_ytdlp(self) -> None:
        if not os.path.isfile(self.config.yt_dlp_path):
            QMessageBox.critical(
                self,
                self.i18n.t("dlg_error"),
                self.i18n.t("missing_ytdlp", path=self.config.yt_dlp_path),
            )
            return
        if self._update_process is not None:
            QMessageBox.information(self, self.i18n.t("dlg_info"), self.i18n.t("update_running"))
            return

        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        hide_console_window(process)
        process.readyReadStandardOutput.connect(lambda: self._collect_update_output(process))
        process.finished.connect(
            lambda code, _status: self._on_update_finished(process, code)
        )
        self._update_process = process
        self._update_buffer = b""
        self.update_action.setEnabled(False)
        self._append_log(self.i18n.t("update_started"))
        self._set_status(self.i18n.t("update_started"), "blue")
        process.start(self.config.yt_dlp_path, ["-U"])

    def _collect_update_output(self, process: QProcess) -> None:
        raw = bytes(process.readAllStandardOutput())
        if not raw:
            return
        self._update_buffer += raw
        lines, self._update_buffer = split_lines(self._update_buffer)
        text = "\n".join(decode_line(line) for line in lines).strip()
        if text:
            self._append_log(text)

    def _on_update_finished(self, process: QProcess, code: int) -> None:
        self._collect_update_output(process)
        if self._update_buffer.strip():
            self._append_log(decode_line(self._update_buffer).strip())
            self._update_buffer = b""
        process.deleteLater()
        self._update_process = None
        self.update_action.setEnabled(self._ytdlp_ok)
        if self._download_active:
            return
        self._set_status(self.i18n.t("label_ready"), "blue")
        if code == 0:
            QMessageBox.information(self, self.i18n.t("dlg_info"), self.i18n.t("update_done", code=code))
            self._fetch_ytdlp_version()
        else:
            QMessageBox.warning(
                self, self.i18n.t("dlg_warning"), self.i18n.t("update_failed", code=code)
            )

    # ---------------------------------------------------------- environment
    def _validate_environment(self, announce: bool = False) -> None:
        if announce:
            self._log_event(self.i18n.t("env_check_started"))
        messages: list[str] = []
        ytdlp_missing = not os.path.isfile(self.config.yt_dlp_path)
        if ytdlp_missing:
            messages.append(self.i18n.t("missing_ytdlp", path=self.config.yt_dlp_path))
        if not os.path.isfile(self.config.ffmpeg_path):
            messages.append(self.i18n.t("missing_ffmpeg", path=self.config.ffmpeg_path))
        if not os.path.isfile(self.config.ffprobe_path):
            messages.append(self.i18n.t("missing_ffprobe", path=self.config.ffprobe_path))

        path = self.path_entry.text().strip() or self.config.default_download_path
        path_bad = not is_writable_dir(path)
        if path_bad:
            messages.append(self.i18n.t("path_not_writable", path=path))

        self._ytdlp_ok = not ytdlp_missing
        self.download_btn.setEnabled(self._ytdlp_ok)
        self.update_action.setEnabled(self._ytdlp_ok)
        if not messages:
            self.env_banner.setVisible(False)
            if announce:
                self._log_event(self.i18n.t("env_check_ok"))
            return
        for message in messages:
            self._log_event(message)

        # Keep the problem visible in the window instead of a modal dialog
        # that can be dismissed and forgotten.
        self.env_text.setText("\n".join(messages))
        self.env_download_btn.setVisible(ytdlp_missing)
        self.env_banner.setVisible(True)

    def download_ytdlp(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/yt-dlp/yt-dlp/releases/latest"))

    def _center_window(self) -> None:
        frame = self.frameGeometry()
        screen = self.screen()
        if screen is not None:
            frame.moveCenter(screen.availableGeometry().center())
            self.move(frame.topLeft())

    # ------------------------------------------------------------ lifecycle
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        if (
            self._minimize_to_tray
            and not self._quitting
            and self._tray is not None
            and self._tray.isVisible()
        ):
            event.ignore()
            self._persist_settings()
            self.hide()
            self._notify(
                self.i18n.t("tray_minimized_title"),
                self.i18n.t("tray_minimized_text"),
            )
            return

        self._persist_settings()
        # Portable settings live next to the executable; avoid writing into a
        # source checkout during development.
        if getattr(sys, "frozen", False):
            save_config(self.config, self.path_entry.text().strip() or None)
        if self.runner.is_running:
            answer = QMessageBox.question(
                self,
                self.i18n.t("confirm_close_title"),
                self.i18n.t("confirm_close"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.runner.stop_and_wait()
        if self._tray is not None:
            self._tray.hide()
        self._stop_helper_processes()
        self.file_log.close()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self._hotkey_filter)
        event.accept()

    def _stop_helper_processes(self) -> None:
        for process in (self._version_process, self._ffmpeg_process, self._update_process):
            if process is None:
                continue
            try:
                if process.state() != QProcess.ProcessState.NotRunning:
                    process.kill()
                    process.waitForFinished(1000)
            except RuntimeError:
                pass
        self._version_process = None
        self._ffmpeg_process = None
        self._update_process = None


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_recent_entries(value: object) -> list[dict[str, str]]:
    """Normalize persisted recent downloads, including the old URL-only list."""
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = []

    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in values:
        if isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
        else:
            url = str(item).strip()
            title = ""
        if url and url not in seen:
            seen.add(url)
            entries.append({"url": url, "title": title})
    return entries[:MAX_RECENT_URLS]


def _elide_url(url: str, limit: int = 70) -> str:
    """Shorten a URL for a menu label while keeping both ends readable."""
    if len(url) <= limit:
        return url
    head = (limit - 1) // 2
    tail = limit - 1 - head
    return f"{url[:head]}…{url[-tail:]}"


def _elide_title(title: str, limit: int = 70) -> str:
    """Shorten a title for a menu label, keeping the beginning readable."""
    title = title.strip()
    if len(title) <= limit:
        return title
    return title[: limit - 1].rstrip() + "…"


def _quote(part: str) -> str:
    return f'"{part}"' if " " in part else part
