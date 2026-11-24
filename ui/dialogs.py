"""Dialogs: About, filename templates and batch summary."""

from __future__ import annotations

import os
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ui.i18n import I18n

APP_NAME = "Portable Download Manager"
LICENSE_FALLBACK_PATH = "blob/main/LICENSE"
DONATE_URL = "https://yoomoney.ru/to/41001937179526"
WEBSITE_URL = "https://btrf.github.io/yt-dlp-gui/"

# Most common and useful yt-dlp output templates. The second element is a
# translation key describing when the template is handy.
TEMPLATE_PRESETS: tuple[tuple[str, str], ...] = (
    ("%(title)s.%(ext)s", "tpl_title"),
    ("%(upload_date)s - %(title)s.%(ext)s", "tpl_date_title"),
    ("%(uploader)s - %(title)s.%(ext)s", "tpl_uploader_title"),
    ("%(upload_date)s - %(uploader)s - %(title)s.%(ext)s", "tpl_full"),
    ("%(title)s [%(id)s].%(ext)s", "tpl_title_id"),
    ("%(uploader)s/%(title)s.%(ext)s", "tpl_per_uploader"),
    ("%(channel)s/%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s", "tpl_channel_date"),
    ("%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s", "tpl_playlist"),
    ("%(title).100s.%(ext)s", "tpl_truncated"),
)


class AboutDialog(QDialog):
    """Compact product card: name, version, project links and license."""

    def __init__(
        self,
        parent,
        i18n: I18n,
        version: str,
        project_url: str,
        license_path: str = "",
        donate_url: str = DONATE_URL,
        website_url: str = WEBSITE_URL,
        ytdlp_version: str = "",
        ffmpeg_version: str = "",
    ) -> None:
        super().__init__(parent)
        self.project_url = project_url
        self.license_path = license_path
        self.donate_url = donate_url
        self.website_url = website_url
        self.setWindowTitle(i18n.t("about_title"))
        self.setMinimumWidth(460)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(14)

        self.name_label = QLabel(APP_NAME)
        self.name_label.setStyleSheet("font-size: 15pt; font-weight: 600;")
        layout.addWidget(self.name_label)
        self.version_label = QLabel(i18n.t("about_version", version=version))
        layout.addWidget(self.version_label)
        self.ytdlp_version_label = QLabel(
            i18n.t("ytdlp_version", version=ytdlp_version)
            if ytdlp_version
            else i18n.t("ytdlp_version_unknown")
        )
        layout.addWidget(self.ytdlp_version_label)
        self.ffmpeg_version_label = QLabel(
            i18n.t("ffmpeg_version", version=ffmpeg_version)
            if ffmpeg_version
            else i18n.t("ffmpeg_version_unknown")
        )
        layout.addWidget(self.ffmpeg_version_label)

        donate_row = QHBoxLayout()
        self.donate_button = QPushButton(i18n.t("about_support"))
        self.donate_button.setAutoDefault(False)
        self.donate_button.clicked.connect(self.open_donate)
        donate_row.addWidget(self.donate_button)
        donate_row.addStretch(1)
        layout.addLayout(donate_row)

        buttons = QHBoxLayout()
        self.website_button = QPushButton(i18n.t("about_website"))
        self.website_button.setAutoDefault(False)
        self.website_button.clicked.connect(self.open_website)
        self.project_button = QPushButton(i18n.t("about_project"))
        self.project_button.setAutoDefault(False)
        self.project_button.clicked.connect(self.open_project)
        self.license_button = QPushButton(i18n.t("about_license"))
        self.license_button.setAutoDefault(False)
        self.license_button.clicked.connect(self.open_license)
        self.close_button = QPushButton(i18n.t("btn_close"))
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        buttons.addWidget(self.website_button)
        buttons.addWidget(self.project_button)
        buttons.addWidget(self.license_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def license_target(self) -> str:
        """Local license file when bundled, otherwise the project's copy online."""
        if self.license_path and os.path.isfile(self.license_path):
            return QUrl.fromLocalFile(self.license_path).toString()
        return f"{self.project_url.rstrip('/')}/{LICENSE_FALLBACK_PATH}"

    def open_website(self) -> None:
        QDesktopServices.openUrl(QUrl(self.website_url))

    def open_project(self) -> None:
        QDesktopServices.openUrl(QUrl(self.project_url))

    def open_license(self) -> None:
        QDesktopServices.openUrl(QUrl(self.license_target()))

    def open_donate(self) -> None:
        QDesktopServices.openUrl(QUrl(self.donate_url))


class TemplateHelpDialog(QDialog):
    """Curated filename templates with descriptions, copy and apply actions."""

    def __init__(self, parent, i18n: I18n, current_template: str = "") -> None:
        super().__init__(parent)
        self.chosen_template = ""
        self.setWindowTitle(i18n.t("templates_title"))
        self.resize(820, 560)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(i18n.t("templates_hint")))

        self.template_list = QListWidget(self)
        selected_row = -1
        for index, (template, description_key) in enumerate(TEMPLATE_PRESETS):
            item = QListWidgetItem(template)
            item.setToolTip(i18n.t(description_key))
            self.template_list.addItem(item)
            if template == current_template:
                selected_row = index
        if selected_row < 0:
            selected_row = 0
        self.template_list.setCurrentRow(selected_row)
        layout.addWidget(self.template_list, 1)

        reference = QPlainTextEdit(self)
        reference.setReadOnly(True)
        reference.setPlainText(i18n.t("templates_reference"))
        reference.setMaximumHeight(160)
        layout.addWidget(reference)

        self.feedback = QLabel("")
        buttons = QHBoxLayout()
        copy_selected_button = QPushButton(i18n.t("btn_copy_selected"))
        copy_all_button = QPushButton(i18n.t("btn_copy_all"))
        apply_button = QPushButton(i18n.t("btn_apply_template"))
        apply_button.setDefault(True)
        close_button = QPushButton(i18n.t("btn_close"))
        buttons.addWidget(copy_selected_button)
        buttons.addWidget(copy_all_button)
        buttons.addWidget(apply_button)
        buttons.addWidget(self.feedback, 1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def selected_template() -> str:
            item = self.template_list.currentItem()
            return item.text() if item else ""

        def copy_selected() -> None:
            template = selected_template()
            if template:
                QApplication.clipboard().setText(template)
                self.feedback.setText(i18n.t("templates_copied"))

        def copy_all() -> None:
            QApplication.clipboard().setText(
                "\n".join(template for template, _key in TEMPLATE_PRESETS)
            )
            self.feedback.setText(i18n.t("templates_copied_all"))

        def apply_selected() -> None:
            template = selected_template()
            if template:
                self.chosen_template = template
                self.accept()

        copy_selected_button.clicked.connect(copy_selected)
        copy_all_button.clicked.connect(copy_all)
        apply_button.clicked.connect(apply_selected)
        close_button.clicked.connect(self.accept)
        self.template_list.itemDoubleClicked.connect(lambda _item: apply_selected())
        self.template_list.currentItemChanged.connect(lambda *_: self.feedback.clear())


@dataclass
class BatchResult:
    url: str
    ok: bool
    detail: str = ""


class BatchSummaryDialog(QDialog):
    """Shows per-URL batch results and lets the user retry failures."""

    def __init__(self, parent, i18n: I18n, results: list[BatchResult]) -> None:
        super().__init__(parent)
        self.retry_urls: list[str] = []
        self.setWindowTitle(i18n.t("batch_summary_title"))
        self.resize(680, 380)
        layout = QVBoxLayout(self)

        succeeded = [result for result in results if result.ok]
        failed = [result for result in results if not result.ok]
        layout.addWidget(QLabel(i18n.t("batch_summary_counts", ok=len(succeeded), failed=len(failed))))

        details = QPlainTextEdit(self)
        details.setReadOnly(True)
        lines: list[str] = []
        for result in results:
            if result.ok:
                lines.append(i18n.t("batch_summary_line_ok", url=result.url))
            else:
                lines.append(
                    i18n.t("batch_summary_line_failed", url=result.url, detail=result.detail or "?")
                )
        details.setPlainText("\n".join(lines))
        layout.addWidget(details, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        retry_button = QPushButton(i18n.t("btn_retry_failed"))
        retry_button.setEnabled(bool(failed))
        close_button = QPushButton(i18n.t("btn_close"))
        buttons.addWidget(retry_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def retry() -> None:
            self.retry_urls = [result.url for result in failed]
            self.accept()

        retry_button.clicked.connect(retry)
        close_button.clicked.connect(self.reject)


class SettingsDialog(QDialog):
    """Small preferences dialog for values that are not download-specific."""

    def __init__(self, parent, i18n: I18n, values: dict) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.setWindowTitle(i18n.t("settings_title"))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.language_combo = QComboBox()
        for code, key in (("en", "lang_en"), ("ru", "lang_ru")):
            self.language_combo.addItem(i18n.t(key), code)
        _select_data(self.language_combo, str(values.get("language", "en")))
        form.addRow(i18n.t("settings_language"), self.language_combo)

        self.theme_combo = QComboBox()
        for code, key in (
            ("system", "theme_system"),
            ("light", "theme_light"),
            ("dark", "theme_dark"),
        ):
            self.theme_combo.addItem(i18n.t(key), code)
        _select_data(self.theme_combo, str(values.get("theme", "system")))
        form.addRow(i18n.t("settings_theme"), self.theme_combo)

        self.folder_entry = QLineEdit(str(values.get("folder", "")))
        browse_button = QPushButton(i18n.t("btn_browse"))
        browse_button.clicked.connect(self._browse_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_entry, 1)
        folder_row.addWidget(browse_button)
        form.addRow(i18n.t("settings_default_folder"), folder_row)

        self.minimize_check = QCheckBox(i18n.t("settings_minimize_to_tray"))
        self.minimize_check.setChecked(bool(values.get("minimize_to_tray", False)))
        form.addRow("", self.minimize_check)
        self.on_top_check = QCheckBox(i18n.t("settings_always_on_top"))
        self.on_top_check.setChecked(bool(values.get("always_on_top", False)))
        form.addRow("", self.on_top_check)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.save_button = QPushButton(i18n.t("btn_save"))
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.accept)
        cancel_button = QPushButton(i18n.t("btn_cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def _browse_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, self.i18n.t("settings_default_folder"), self.folder_entry.text()
        )
        if directory:
            self.folder_entry.setText(directory)

    def result_values(self) -> dict:
        return {
            "language": self.language_combo.currentData() or "en",
            "theme": self.theme_combo.currentData() or "system",
            "folder": self.folder_entry.text().strip(),
            "minimize_to_tray": self.minimize_check.isChecked(),
            "always_on_top": self.on_top_check.isChecked(),
        }


class HistoryDialog(QDialog):
    """Completed and failed downloads with quick access to their files."""

    download_requested = pyqtSignal(str)

    STATUS_KEYS = {
        "ok": "history_status_ok",
        "failed": "history_status_failed",
        "cancelled": "history_status_cancelled",
    }

    def __init__(self, parent, i18n: I18n, entries: list[dict]) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.entries = list(entries)
        self.cleared = False
        self.setWindowTitle(i18n.t("history_title"))
        self.resize(760, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(i18n.t("history_open_hint")))

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(
            [
                i18n.t("history_col_date"),
                i18n.t("history_col_title"),
                i18n.t("history_col_status"),
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)
        self._populate()
        self.table.itemDoubleClicked.connect(self._open_entry)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_menu)

        buttons = QHBoxLayout()
        self.clear_button = QPushButton(i18n.t("btn_clear_history"))
        self.clear_button.setEnabled(bool(self.entries))
        self.clear_button.clicked.connect(self._clear)
        close_button = QPushButton(i18n.t("btn_close"))
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)
        buttons.addWidget(self.clear_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _populate(self) -> None:
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            status = self.STATUS_KEYS.get(str(entry.get("status", "")), "history_status_failed")
            values = (
                str(entry.get("time", "")),
                str(entry.get("title") or entry.get("url", "")),
                self.i18n.t(status),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 1:
                    item.setToolTip(str(entry.get("url", "")))
                self.table.setItem(row, column, item)

    def _show_menu(self, position) -> None:
        item = self.table.itemAt(position)
        if item is None:
            selected = self.table.selectedItems()
            item = selected[0] if selected else self.table.currentItem()
        if item is None:
            return
        menu = self._build_context_menu(item.row())
        if menu is not None:
            menu.exec(self.table.viewport().mapToGlobal(position))

    def _build_context_menu(self, row: int) -> QMenu | None:
        if not 0 <= row < len(self.entries):
            return None
        url = str(self.entries[row].get("url", ""))
        if not url:
            return None
        menu = QMenu(self)
        copy_action = menu.addAction(self.i18n.t("menu_copy_link"))
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(url))
        again_action = menu.addAction(self.i18n.t("history_download_again"))
        again_action.triggered.connect(lambda: self._request_download(url))
        return menu

    def _request_download(self, url: str) -> None:
        self.accept()
        self.download_requested.emit(url)

    def _open_entry(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if row < 0 or row >= len(self.entries):
            return
        path = str(self.entries[row].get("path", ""))
        if path and os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            return
        folder = os.path.dirname(path) if path else ""
        if folder and os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            return
        QMessageBox.information(self, self.windowTitle(), self.i18n.t("history_missing_file"))

    def _clear(self) -> None:
        self.entries = []
        self.cleared = True
        self.table.setRowCount(0)
        self.clear_button.setEnabled(False)


def _select_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    combo.setCurrentIndex(index if index >= 0 else 0)
