"""Main window of yt-dlp GUI."""

from __future__ import annotations

import os
import re
import sys

from PyQt6.QtCore import QEvent, QProcess, QSettings, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
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
from ui.dialogs import AboutDialog, BatchResult, BatchSummaryDialog, TemplateHelpDialog
from ui.i18n import I18n
from ui.theme import make_primary_button

PROJECT_URL = "https://github.com/btrf/yt-dlp-gui"
COOKIE_BROWSERS = ("chrome", "edge", "firefox", "brave", "opera", "vivaldi", "safari")

URL_PREFIXES = ("http://", "https://")


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


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        i18n: I18n,
        settings: QSettings,
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
        self._batch_queue: list[str] = []
        self._batch_results: list[BatchResult] = []
        self._batch_total = 0
        self._batch_current = 0
        self._batch_active = False
        self._current_url = ""
        self._item_percent = 0.0
        self._download_active = False
        self._loading = False
        self._ytdlp_ok = True
        self._current_type = "video"
        self._format_state: dict[str, dict[str, str]] = {
            "video": {"quality": DEFAULT_VIDEO_QUALITY, "format": DEFAULT_VIDEO_FORMAT},
            "audio": {"quality": AUDIO_QUALITY_CHOICES[0], "format": AUDIO_FORMATS[0]},
        }

        self.base_title = "Portable Download Manager"
        if icon_path and os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setAcceptDrops(True)
        self.setMinimumSize(QSize(820, 520))
        self.resize(900, 620)

        self.runner = DownloadRunner(file_log, self)
        self.runner.progress.connect(self._on_progress)
        self.runner.log.connect(self._append_log)
        self.runner.finished.connect(self._on_finished)

        self._version_process: QProcess | None = None
        self._update_process: QProcess | None = None
        self._update_buffer = b""
        self._tray: QSystemTrayIcon | None = None

        self._build_ui()
        self._restore_settings()
        self._retranslate()
        self._setup_tray()
        self._validate_environment()
        self._fetch_ytdlp_version()

        geometry = self.settings.value("window/geometry")
        if not geometry:
            self._center_window()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.source_group = QGroupBox()
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
        path_buttons = QHBoxLayout()
        self.browse_path_btn = QPushButton()
        self.browse_path_btn.clicked.connect(self.browse_path)
        self.open_folder_btn = QPushButton()
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        path_buttons.addWidget(self.browse_path_btn)
        path_buttons.addWidget(self.open_folder_btn)
        path_buttons.addStretch(1)
        source_layout.addLayout(path_buttons, 1, 2)
        layout.addWidget(self.source_group)

        self.playlist_group = QGroupBox()
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
        layout.addWidget(self.playlist_group)

        self.options_group = QGroupBox()
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
        first_row.addStretch(1)
        options_layout.addLayout(first_row)

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
        options_layout.addLayout(second_row)

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
        self.remove_ads_check = QCheckBox()
        self.remove_ads_check.setChecked(True)
        self.remove_ads_check.toggled.connect(self._persist_settings)
        third_row.addWidget(self.remove_ads_check)
        third_row.addStretch(1)
        options_layout.addLayout(third_row)
        layout.addWidget(self.options_group)

        self.status_group = QGroupBox()
        status_layout = QVBoxLayout(self.status_group)
        status_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel()
        self.status_label.setMinimumWidth(220)
        status_row.addWidget(self.progress_bar, 1)
        status_row.addWidget(self.status_label)
        status_layout.addLayout(status_row)
        batch_row = QHBoxLayout()
        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setVisible(False)
        self.ytdlp_version_label = QLabel()
        self.ytdlp_version_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        batch_row.addWidget(self.batch_progress_bar, 1)
        batch_row.addWidget(self.ytdlp_version_label)
        status_layout.addLayout(batch_row)
        layout.addWidget(self.status_group)

        self.log_group = QGroupBox()
        log_layout = QVBoxLayout(self.log_group)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(5000)
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
        layout.addWidget(self.log_group, 1)

        buttons = QHBoxLayout()
        self.download_btn = QPushButton()
        make_primary_button(self.download_btn)
        self.download_btn.clicked.connect(self.try_start_download)
        self.cancel_btn = QPushButton()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.load_links_btn = QPushButton()
        self.load_links_btn.clicked.connect(self.load_links_from_file)
        self.update_btn = QPushButton()
        self.update_btn.clicked.connect(self.update_ytdlp)
        self.quit_btn = QPushButton()
        self.quit_btn.clicked.connect(self.close)
        buttons.addWidget(self.download_btn)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.load_links_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.update_btn)
        buttons.addWidget(self.quit_btn)
        layout.addLayout(buttons)

        self._build_menus()

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()
        self.tools_menu = menu_bar.addMenu("")
        self.update_action = self.tools_menu.addAction("")
        self.update_action.triggered.connect(self.update_ytdlp)
        self.open_folder_action = self.tools_menu.addAction("")
        self.open_folder_action.triggered.connect(self.open_download_folder)
        self.open_log_action = self.tools_menu.addAction("")
        self.open_log_action.triggered.connect(self.open_log_file)

        self.help_menu = menu_bar.addMenu("")
        self.templates_action = self.help_menu.addAction("")
        self.templates_action.triggered.connect(self.show_template_help)
        self.about_action = self.help_menu.addAction("")
        self.about_action.triggered.connect(self.show_about)

        self.language_menu = menu_bar.addMenu("")
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
        self.open_folder_btn.setText(t("btn_open_folder"))
        self.open_folder_btn.setToolTip(t("tip_open_folder"))

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

        self.status_group.setTitle(t("group_status"))
        self.log_group.setTitle(t("group_log"))
        self.clear_log_btn.setText(t("btn_clear_log"))
        self.open_log_btn.setText(t("btn_open_log"))
        self.download_btn.setText(t("btn_download"))
        self.cancel_btn.setText(t("btn_stop"))
        self.load_links_btn.setText(t("btn_load_links"))
        self.update_btn.setText(t("btn_update"))
        self.quit_btn.setText(t("btn_quit"))

        self.tools_menu.setTitle(t("menu_tools"))
        self.update_action.setText(t("menu_update"))
        self.open_folder_action.setText(t("menu_open_folder"))
        self.open_log_action.setText(t("menu_open_log"))
        self.help_menu.setTitle(t("menu_help"))
        self.templates_action.setText(t("menu_templates"))
        self.about_action.setText(t("menu_about"))
        self.language_menu.setTitle(t("menu_language"))
        self.language_en_action.setText(t("lang_en"))
        self.language_ru_action.setText(t("lang_ru"))
        self.language_en_action.setChecked(self.i18n.language == "en")
        self.language_ru_action.setChecked(self.i18n.language == "ru")

        if not self._download_active:
            self.status_label.setText(t("label_ready"))
        if not self._ytdlp_ok:
            self.ytdlp_version_label.setText(t("ytdlp_version_unknown"))
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

            geometry = settings.value("window/geometry")
            if geometry:
                self.restoreGeometry(geometry)
        finally:
            self._loading = False
        self._update_playlist_controls()

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
        settings.setValue("window/geometry", self.saveGeometry())
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
        AboutDialog(self, self.i18n, self.version, PROJECT_URL).exec()

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
        self.update_btn.setEnabled(not running and self._ytdlp_ok)
        for group in (self.source_group, self.playlist_group, self.options_group):
            group.setEnabled(not running)

    def cancel_download(self) -> None:
        if not self.runner.is_running:
            return
        self.cancel_btn.setEnabled(False)
        self._set_status(self.i18n.t("status_stopping"), "orange")
        self.runner.cancel()

    def _on_progress(self, update: ProgressUpdate) -> None:
        if update.percent is not None:
            self._item_percent = update.percent
            self.progress_bar.setValue(int(update.percent))
        if self._batch_active:
            overall = ((self._batch_current - 1) + self._item_percent / 100.0) / max(1, self._batch_total)
            self.batch_progress_bar.setValue(int(overall * 100))

        parts: list[str] = []
        if update.percent is not None:
            parts.append(f"{update.percent:.1f}%")
        if update.speed:
            parts.append(update.speed)
        if update.eta:
            parts.append(self.i18n.t("eta", value=update.eta))
        if update.stage:
            parts.append(self._stage_text(update.stage))
        text = " · ".join(parts) if parts else self.i18n.t("status_downloading")
        if self._batch_active:
            text = f"{self.i18n.t('batch_item', current=self._batch_current, total=self._batch_total)} — {text}"
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
        elif ok:
            self.progress_bar.setValue(100)
            self._set_status(self.i18n.t("status_done"), "green")
            self._notify(
                self.i18n.t("notify_done_title"),
                self.i18n.t("notify_done_text", path=self.path_entry.text()),
            )
        else:
            self._set_status(self.i18n.t("status_failed", code=exit_code), "red")
            self._notify(
                self.i18n.t("notify_failed_title"), self.i18n.t("notify_failed_text", code=exit_code)
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

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    # ---------------------------------------------------------------- batch
    def _start_batch(self, urls: list[str]) -> None:
        self._batch_queue = [url for url in urls if url.strip()]
        if not self._batch_queue:
            return
        self._batch_results = []
        self._batch_total = len(self._batch_queue)
        self._batch_current = 0
        self._batch_active = True
        self.batch_progress_bar.setValue(0)
        self.batch_progress_bar.setVisible(True)
        self._set_window_title()
        self._start_next_batch_item()

    def _start_next_batch_item(self) -> None:
        if not self._batch_queue:
            self._finish_batch()
            return
        url = self._batch_queue.pop(0)
        self._batch_current += 1
        self._append_log(
            self.i18n.t(
                "batch_log_start", current=self._batch_current, total=self._batch_total, url=url
            )
        )
        self._set_window_title()
        if not self.start_download(url, ""):
            self._batch_results.append(
                BatchResult(url, False, self.i18n.t("err_start", error=self.config.yt_dlp_path))
            )
            if self._batch_queue:
                QTimer.singleShot(0, self._start_next_batch_item)
            else:
                self._finish_batch()

    def _finish_batch(self) -> None:
        results = list(self._batch_results)
        self._batch_active = False
        self._batch_queue = []
        self._batch_results = []
        self.batch_progress_bar.setVisible(False)
        self.batch_progress_bar.setValue(0)
        self._set_window_title()
        succeeded = sum(1 for result in results if result.ok)
        self._append_log(
            self.i18n.t("batch_finished", done=succeeded, total=self._batch_total)
        )
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
        self._tray.show()

    def _notify(self, title: str, message: str) -> None:
        if self._tray is not None and QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)

    def _fetch_ytdlp_version(self) -> None:
        if not os.path.isfile(self.config.yt_dlp_path):
            self.ytdlp_version_label.setText(self.i18n.t("ytdlp_version_unknown"))
            return
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        hide_console_window(process)
        process.finished.connect(lambda code, _status: self._on_version_finished(process, code))
        self._version_process = process
        process.start(self.config.yt_dlp_path, ["--version"])

    def _on_version_finished(self, process: QProcess, _code: int) -> None:
        output = decode_line(bytes(process.readAllStandardOutput())).strip()
        version = output.splitlines()[0].strip() if output else ""
        if version:
            self.ytdlp_version_label.setText(self.i18n.t("ytdlp_version", version=version))
        else:
            self.ytdlp_version_label.setText(self.i18n.t("ytdlp_version_unknown"))
        process.deleteLater()
        self._version_process = None

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
        self.update_btn.setEnabled(False)
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
        self.update_btn.setEnabled(self._ytdlp_ok)
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
    def _validate_environment(self) -> None:
        messages: list[str] = []
        ytdlp_missing = not os.path.isfile(self.config.yt_dlp_path)
        if ytdlp_missing:
            messages.append(self.i18n.t("missing_ytdlp", path=self.config.yt_dlp_path))
        if not os.path.isfile(self.config.ffmpeg_path):
            messages.append(self.i18n.t("missing_ffmpeg", path=self.config.ffmpeg_path))
        if not os.path.isfile(self.config.ffprobe_path):
            messages.append(self.i18n.t("missing_ffprobe", path=self.config.ffprobe_path))

        path = self.path_entry.text().strip() or self.config.default_download_path
        if not is_writable_dir(path):
            messages.append(self.i18n.t("path_not_writable", path=path))

        self._ytdlp_ok = not ytdlp_missing
        self.download_btn.setEnabled(self._ytdlp_ok)
        self.update_btn.setEnabled(self._ytdlp_ok)
        if not messages:
            return
        for message in messages:
            self._append_log(message.replace("\n", " "))

        if not self._interactive:
            return
        if ytdlp_missing:
            QMessageBox.critical(self, self.i18n.t("missing_title"), "\n\n".join(messages))
            return
        # Warnings are shown once per unique set of problems to avoid nagging.
        signature = "|".join(messages)
        if str(self.settings.value("env/warning_signature", "")) != signature:
            self.settings.setValue("env/warning_signature", signature)
            self.settings.sync()
            QMessageBox.warning(self, self.i18n.t("missing_title"), "\n\n".join(messages))

    def _center_window(self) -> None:
        frame = self.frameGeometry()
        screen = self.screen()
        if screen is not None:
            frame.moveCenter(screen.availableGeometry().center())
            self.move(frame.topLeft())

    # ------------------------------------------------------------ lifecycle
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
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
        event.accept()

    def _stop_helper_processes(self) -> None:
        for process in (self._version_process, self._update_process):
            if process is None:
                continue
            try:
                if process.state() != QProcess.ProcessState.NotRunning:
                    process.kill()
                    process.waitForFinished(1000)
            except RuntimeError:
                pass
        self._version_process = None
        self._update_process = None


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _quote(part: str) -> str:
    return f'"{part}"' if " " in part else part
