# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

project_dir = Path(SPECPATH)
sys.path.insert(0, str(project_dir))
from version import APP_VERSION
site_packages = project_dir / ".venv" / "Lib" / "site-packages"

a = Analysis(
    [str(project_dir / "yt_dlp_gui_qt.py")],
    pathex=[str(project_dir), str(site_packages)],
    binaries=[
        (str(project_dir / "bin" / "yt-dlp.exe"), "bin"),
        (str(project_dir / "bin" / "ffmpeg.exe"), "bin"),
    ],
    datas=[
        (str(project_dir / "yt-dlp-gui.ico"), "."),
        (str(project_dir / "yt-dlp-gui.json"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"yt-dlp-gui-portable-v{APP_VERSION}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_dir / "yt-dlp-gui.ico"),
)
