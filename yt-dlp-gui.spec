# -*- mode: python ; coding: utf-8 -*-

import os

# Define files to include conditionally
binaries_list = []
datas_list = []

# Add internal libraries directory if it exists
if os.path.exists('_internal'):
    datas_list.append(('_internal', '_internal'))

# Add icon files if they exist
if os.path.exists('yt_dlp_gui.ico'):
    datas_list.append(('yt_dlp_gui.ico', '.'))
if os.path.exists('yt_dlp_gui_1.ico'):
    datas_list.append(('yt_dlp_gui_1.ico', '.'))
if os.path.exists('yt_dlp_gui_2.ico'):
    datas_list.append(('yt_dlp_gui_2.ico', '.'))

# Include config file if it exists
if os.path.exists('yt_dlp_gui_config.json'):
    datas_list.append(('yt_dlp_gui_config.json', '.'))

# Include yt-dlp executable if it exists in the current directory (in the same directory as main executable)
if os.path.exists('yt-dlp.exe'):
    binaries_list.append(('yt-dlp.exe', '.'))

# Include ffmpeg executable if it exists in the current directory (in the same directory as main executable)
if os.path.exists('ffmpeg.exe'):
    binaries_list.append(('ffmpeg.exe', '.'))

a = Analysis(
    ['yt_dlp_gui.py'],
    pathex=[],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='yt-dlp-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='yt_dlp_gui.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='yt-dlp-gui',
)