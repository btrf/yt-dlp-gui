"""Dialogs: About, filename templates and batch summary."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ui.i18n import I18n

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
    def __init__(self, parent, i18n: I18n, version: str, project_url: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(i18n.t("menu_about"))
        self.setFixedWidth(460)
        layout = QVBoxLayout(self)

        title = QLabel(f"<b>yt-dlp GUI {version}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        description = QLabel(i18n.t("about_description"))
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        link = QLabel(f'<a href="{project_url}">{project_url}</a>')
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(link)

        close_button = QPushButton(i18n.t("btn_close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


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
