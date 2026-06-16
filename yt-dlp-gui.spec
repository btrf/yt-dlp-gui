# -*- mode: python ; coding: utf-8 -*-

import os
import shutil

# Define files to include conditionally
binaries_list = []
datas_list = []

# Add internal libraries directory if it exists
if os.path.exists('_internal'):
    datas_list.append(('_internal', '_internal'))

# Add icon file if it exists
if os.path.exists('yt-dlp-gui.ico'):
    datas_list.append(('yt-dlp-gui.ico', '.'))

# Include config file if it exists
if os.path.exists('yt_dlp_gui_config.json'):
    datas_list.append(('yt_dlp_gui_config.json', '.'))

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
    icon='yt-dlp-gui.ico',
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

# Post-build: copy exes from bin/ to dist/bin/
dist_bin = os.path.join(coll.name, 'bin')
os.makedirs(dist_bin, exist_ok=True)
for exe_name in ('yt-dlp.exe', 'ffmpeg.exe'):
    src = os.path.join('bin', exe_name)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(dist_bin, exe_name))