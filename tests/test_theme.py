import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

from ui.theme import PRIMARY_BUTTON_STYLE, make_primary_button  # noqa: E402

_app = QApplication.instance() or QApplication([])


def test_primary_button_gets_the_accent_style():
    button = QPushButton("Download")
    make_primary_button(button)
    assert button.styleSheet() == PRIMARY_BUTTON_STYLE
    assert button.minimumHeight() >= 32
    assert button.minimumWidth() >= 120
    assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor


def test_primary_style_covers_all_button_states():
    for state in (":hover", ":pressed", ":focus", ":disabled"):
        assert state in PRIMARY_BUTTON_STYLE
    # A filled button needs an explicit background and readable text colour.
    assert "background-color" in PRIMARY_BUTTON_STYLE
    assert "color: #ffffff" in PRIMARY_BUTTON_STYLE
    assert "font-weight" in PRIMARY_BUTTON_STYLE
