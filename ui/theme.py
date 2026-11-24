"""Shared visual accents for the widgets.

The main action of the window (download) is drawn as a filled primary button so
it is immediately distinguishable from the secondary buttons around it.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QPushButton

THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_CHOICES = (THEME_SYSTEM, THEME_LIGHT, THEME_DARK)

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


LIGHT_STYLESHEET = """
QGroupBox {
    border: 1px solid #d0d7de;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #57606a;
}
QTabWidget::pane {
    border: 1px solid #d0d7de;
    border-radius: 6px;
}
QTabBar::tab {
    background: #f6f8fa;
    color: #57606a;
    padding: 6px 14px;
    border: 1px solid #d0d7de;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #24292f;
}
QFrame#envBanner {
    background-color: #fff4e5;
    border: 1px solid #e3a008;
    border-radius: 6px;
}
QLabel#envBannerTitle {
    color: #7a4b00;
    font-weight: 600;
}
QLabel#envBannerText {
    color: #5c3a00;
}
"""

DARK_STYLESHEET = """
QWidget {
    background-color: #161b22;
    color: #e6edf3;
}
QGroupBox {
    border: 1px solid #2a3140;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #9da7b3;
}
QLineEdit, QComboBox, QPlainTextEdit, QListWidget, QTableWidget {
    background-color: #0d1117;
    border: 1px solid #2a3140;
    border-radius: 6px;
    padding: 4px;
    color: #e6edf3;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #2a3140;
    selection-background-color: #1f6feb;
}
QPushButton {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #30363d;
}
QPushButton:pressed {
    background-color: #161b22;
}
QPushButton:disabled {
    color: #6e7681;
    border-color: #21262d;
}
QToolButton {
    color: #9da7b3;
    border: none;
    padding: 4px;
}
QCheckBox {
    color: #e6edf3;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    background-color: #0d1117;
    border: 1px solid #8b949e;
    border-radius: 3px;
}
QCheckBox::indicator:hover {
    border-color: #c9d1d9;
}
QCheckBox::indicator:checked {
    background-color: #1f6feb;
    border: 2px solid #e6edf3;
}
QProgressBar {
    border: 1px solid #2a3140;
    border-radius: 5px;
    background-color: #0d1117;
    text-align: center;
    color: #e6edf3;
}
QProgressBar::chunk {
    background-color: #2ea043;
    border-radius: 4px;
}
QMenuBar {
    background-color: #161b22;
    color: #e6edf3;
}
QMenuBar::item:selected {
    background-color: #21262d;
}
QMenu {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #2a3140;
    padding: 4px 0;
}
QMenu::item {
    padding: 6px 32px 6px 24px;
}
QMenu::item:selected {
    background-color: #1f6feb;
}
QTabWidget::pane {
    border: 1px solid #2a3140;
    border-radius: 6px;
}
QTabBar::tab {
    background: #21262d;
    color: #9da7b3;
    padding: 6px 14px;
    border: 1px solid #2a3140;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #161b22;
    color: #e6edf3;
}
QHeaderView::section {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #2a3140;
    padding: 4px;
}
QFrame#envBanner {
    background-color: #3a2a00;
    border: 1px solid #9e6a00;
    border-radius: 6px;
}
QLabel#envBannerTitle {
    color: #ffd479;
    font-weight: 600;
}
QLabel#envBannerText {
    color: #f0c674;
}
"""


def resolve_theme(name: str) -> str:
    """Return ``light`` or ``dark`` for a stored theme preference."""
    if name == THEME_DARK:
        return THEME_DARK
    if name == THEME_LIGHT:
        return THEME_LIGHT
    app = QApplication.instance()
    if app is not None:
        scheme = getattr(app.styleHints(), "colorScheme", None)
        if callable(scheme):
            try:
                if scheme() == Qt.ColorScheme.Dark:
                    return THEME_DARK
            except AttributeError:
                pass
        if app.palette().color(QPalette.ColorRole.Window).lightness() < 128:
            return THEME_DARK
    return THEME_LIGHT


def _dark_palette() -> QPalette:
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#161b22",
        QPalette.ColorRole.WindowText: "#e6edf3",
        QPalette.ColorRole.Base: "#0d1117",
        QPalette.ColorRole.AlternateBase: "#161b22",
        QPalette.ColorRole.Text: "#e6edf3",
        QPalette.ColorRole.Button: "#21262d",
        QPalette.ColorRole.ButtonText: "#e6edf3",
        QPalette.ColorRole.Highlight: "#1f6feb",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#161b22",
        QPalette.ColorRole.ToolTipText: "#e6edf3",
        QPalette.ColorRole.PlaceholderText: "#6e7681",
        QPalette.ColorRole.Mid: "#2a3140",
        QPalette.ColorRole.Midlight: "#30363d",
        QPalette.ColorRole.Dark: "#0d1117",
    }
    for role, value in colors.items():
        palette.setColor(role, QColor(value))
    return palette


def apply_theme(app: QApplication, name: str) -> str:
    """Apply a light or dark application theme and return the resolved one."""
    theme = resolve_theme(name)
    if theme == THEME_DARK:
        app.setPalette(_dark_palette())
        app.setStyleSheet(DARK_STYLESHEET)
    else:
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet(LIGHT_STYLESHEET)
    return theme
