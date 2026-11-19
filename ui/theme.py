"""Shared visual accents for the widgets.

The main action of the window (download) is drawn as a filled primary button so
it is immediately distinguishable from the secondary buttons around it.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

PRIMARY_BUTTON_STYLE = """
QPushButton {
    background-color: #1e7a46;
    color: #ffffff;
    border: 1px solid #155c34;
    border-radius: 6px;
    padding: 8px 26px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #249254;
}
QPushButton:pressed {
    background-color: #155c34;
}
QPushButton:focus {
    border: 2px solid #0f4526;
}
QPushButton:disabled {
    background-color: #9bb7a6;
    border-color: #8aa695;
    color: #f2f2f2;
}
"""


def make_primary_button(button: QPushButton) -> None:
    """Give ``button`` the accent look and a comfortable click target."""
    button.setStyleSheet(PRIMARY_BUTTON_STYLE)
    button.setMinimumHeight(36)
    button.setMinimumWidth(150)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
