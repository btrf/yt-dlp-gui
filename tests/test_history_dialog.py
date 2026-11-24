import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui import dialogs  # noqa: E402
from ui.dialogs import HistoryDialog  # noqa: E402
from ui.i18n import I18n  # noqa: E402

_app = QApplication.instance() or QApplication([])

ENTRIES = [
    {
        "time": "2026-11-24 10:00",
        "title": "First video",
        "url": "https://example.com/watch?v=1",
        "status": "ok",
        "path": "",
    },
    {
        "time": "2026-11-23 09:00",
        "title": "Second video",
        "url": "https://example.com/watch?v=2",
        "status": "failed",
        "path": "",
    },
]


def make_dialog() -> HistoryDialog:
    return HistoryDialog(None, I18n("en"), ENTRIES)


def test_history_table_uses_a_context_menu():
    dialog = make_dialog()
    assert dialog.table.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
    dialog.close()


def test_context_menu_copies_link_and_requests_download(monkeypatch):
    dialog = make_dialog()
    menu = dialog._build_context_menu(0)
    assert menu is not None
    assert [action.text() for action in menu.actions()] == [
        "Copy link",
        "Download again",
    ]

    class Clipboard:
        def __init__(self):
            self.text = ""

        def setText(self, text):
            self.text = text

    clipboard = Clipboard()
    monkeypatch.setattr(dialogs.QApplication, "clipboard", lambda: clipboard)
    menu.actions()[0].trigger()
    assert clipboard.text == ENTRIES[0]["url"]

    requested = []
    dialog.download_requested.connect(requested.append)
    menu.actions()[1].trigger()
    assert requested == [ENTRIES[0]["url"]]
    dialog.close()


def test_context_menu_uses_the_row_url():
    dialog = make_dialog()
    menu = dialog._build_context_menu(1)
    assert menu is not None
    requested = []
    dialog.download_requested.connect(requested.append)
    menu.actions()[1].trigger()
    assert requested == [ENTRIES[1]["url"]]
    dialog.close()


def test_context_menu_is_not_built_for_missing_or_linkless_rows():
    dialog = make_dialog()
    assert dialog._build_context_menu(-1) is None
    assert dialog._build_context_menu(len(ENTRIES)) is None
    dialog.entries[0]["url"] = ""
    assert dialog._build_context_menu(0) is None
    dialog.close()
