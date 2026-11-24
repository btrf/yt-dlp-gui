import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

from ui.theme import DARK_STYLESHEET, PRIMARY_BUTTON_STYLE, make_primary_button  # noqa: E402

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


def test_dark_menu_items_reserve_space_for_shortcuts():
    item_rule = DARK_STYLESHEET.split("QMenu::item {", 1)[1].split("}", 1)[0]
    assert "padding:" in item_rule


def test_dark_checkbox_indicator_is_visible():
    indicator_rule = DARK_STYLESHEET.split("QCheckBox::indicator {", 1)[1].split("}", 1)[0]
    assert "background-color: #0d1117" in indicator_rule
    assert "border: 1px solid #8b949e" in indicator_rule

    checked_rule = DARK_STYLESHEET.split("QCheckBox::indicator:checked {", 1)[1].split("}", 1)[0]
    assert "background-color: #1f6feb" in checked_rule
    assert "border: 2px solid #e6edf3" in checked_rule
