"""Framework-agnostic core of yt-dlp GUI.

Nothing in this package imports PyQt6 except :mod:`core.runner`, which uses
``QProcess`` to drive the downloader without blocking the UI thread.
"""
