"""Small rotating log file so users can attach a log to bug reports."""

from __future__ import annotations

import os
import tempfile
import time


class FileLog:
    """Append-only log with simple size-based rotation."""

    def __init__(self, path: str, max_bytes: int = 1_000_000, backups: int = 2) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self.backups = backups
        self._handle = None
        self._written = 0

    @staticmethod
    def default_path() -> str:
        return os.path.join(tempfile.gettempdir(), "yt-dlp-gui", "yt-dlp-gui.log")

    @classmethod
    def default(cls) -> FileLog:
        return cls(cls.default_path())

    def write(self, message: str) -> None:
        try:
            self._open()
            if self._handle is None:
                return
            line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
            self._handle.write(line)
            self._handle.flush()
            self._written += len(line)
            if self._written >= self.max_bytes:
                self._rotate()
        except OSError:
            self._handle = None

    def _open(self) -> None:
        if self._handle is not None:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        existing = os.path.getsize(self.path) if os.path.isfile(self.path) else 0
        self._handle = open(self.path, "a", encoding="utf-8", errors="replace")
        self._written = existing

    def _rotate(self) -> None:
        self._close()
        try:
            for index in range(self.backups, 0, -1):
                source = self.path if index == 1 else f"{self.path}.{index - 1}"
                target = f"{self.path}.{index}"
                if os.path.isfile(source):
                    os.replace(source, target)
        except OSError:
            pass
        self._written = 0

    def _close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.close()
            finally:
                self._handle = None

    def close(self) -> None:
        self._close()
