# -*- mode: python ; coding: utf-8 -*-
#
# Builds the single-file portable exe:
#   python -m PyInstaller yt_dlp_gui.spec
#
import sys
from pathlib import Path

project_dir = Path(SPECPATH)
sys.path.insert(0, str(project_dir))
from version import APP_VERSION  # noqa: E402

site_packages = project_dir / ".venv" / "Lib" / "site-packages"

binaries = []
for name in ("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe"):
    candidate = project_dir / "bin" / name
    if candidate.is_file():
        binaries.append((str(candidate), "bin"))

datas = [
    (str(project_dir / "yt-dlp-gui.ico"), "."),
    (str(project_dir / "yt-dlp-gui.json"), "."),
    # The About dialog opens this file, so it must survive the one-file build.
    (str(project_dir / "LICENSE"), "."),
]

# FFmpeg is bundled under the GPL, so ship its license text next to the binaries.
ffmpeg_license = project_dir / "bin" / "FFMPEG-LICENSE.txt"
if ffmpeg_license.is_file():
    datas.append((str(ffmpeg_license), "bin"))

# Qt modules the GUI never touches. Dropping them keeps the build smaller.
excludes = [
    "tkinter",
    "_tkinter",
    "PyQt6.QtNetwork",
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtQuickWidgets",
    "PyQt6.QtSql",
    "PyQt6.QtTest",
    "PyQt6.QtDBus",
    "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebChannel",
    "PyQt6.QtWebSockets",
    "PyQt6.QtPositioning",
    "PyQt6.QtSerialPort",
    "PyQt6.QtBluetooth",
    "PyQt6.QtNfc",
    "PyQt6.QtPdf",
    "PyQt6.QtPdfWidgets",
    "PyQt6.QtCharts",
    "PyQt6.QtDataVisualization",
]

a = Analysis(
    [str(project_dir / "yt_dlp_gui_qt.py")],
    pathex=[str(project_dir), str(site_packages)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

name = f"yt-dlp-gui-portable-v{APP_VERSION}"
common = dict(
    console=False,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_dir / "yt-dlp-gui.ico"),
    version=str(project_dir / "version_info.txt"),
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=name,
    **common,
)
