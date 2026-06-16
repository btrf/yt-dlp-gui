@echo off
setlocal enabledelayedexpansion

python yt_dlp_gui.py

if errorlevel 1 (
    echo Error: Failed to start the application.
    echo.
    echo Please ensure:
    echo - Python is installed and in your PATH
    echo - tkinter is available (usually included with Python)
    echo - yt-dlp is installed (pip install yt-dlp)
    echo.
    echo Press any key to exit...
    pause >nul
)