"""Non-blocking yt-dlp process runner built on ``QProcess``.

Compared to the previous ``QThread`` + ``Popen`` + queue design this removes two
helper threads, makes cancellation immediate and never blocks the UI thread.
"""

from __future__ import annotations

import os
import subprocess
import sys

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from .file_log import FileLog
from .progress import ProgressUpdate, decode_line, parse_progress_line, split_lines


def hide_console_window(process: QProcess) -> None:
    """Keep console windows of child processes hidden on Windows."""
    if sys.platform != "win32":
        return
    modifier = getattr(process, "setCreateProcessArgumentsModifier", None)
    if modifier is None:
        return

    def apply(arguments) -> None:  # noqa: ANN001 - Qt struct
        try:
            arguments.flags |= subprocess.CREATE_NO_WINDOW
        except Exception:  # pragma: no cover - Qt binding differences
            pass

    try:
        modifier(apply)
    except Exception:  # pragma: no cover - Qt binding differences
        pass


class DownloadRunner(QObject):
    """Runs one yt-dlp command and reports progress/log/finish."""

    progress = pyqtSignal(object)  # ProgressUpdate
    log = pyqtSignal(str)  # one or more lines, already decoded
    finished = pyqtSignal(int, bool)  # exit code, cancelled

    FLUSH_INTERVAL_MS = 100
    KILL_AFTER_MS = 2000

    def __init__(self, file_log: FileLog | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._file_log = file_log
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        hide_console_window(self._process)

        self._buffer = b""
        self._pending_log: list[str] = []
        self._pending_progress: ProgressUpdate | None = None
        self._last_filename = ""
        self._cancelled = False
        self._finished = True

        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(self.FLUSH_INTERVAL_MS)
        self._flush_timer.timeout.connect(self._flush)

        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.setInterval(self.KILL_AFTER_MS)
        self._kill_timer.timeout.connect(self._force_kill)

        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

    # --- public API -----------------------------------------------------
    @property
    def is_running(self) -> bool:
        return not self._finished

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def start(self, command: list[str]) -> bool:
        if not command:
            return False
        if self.is_running:
            return False
        self._reset()
        self._process.setProgram(command[0])
        self._process.setArguments(command[1:])
        self._process.start()
        if not self._process.waitForStarted(5000):
            self._emit_log(f"Could not start {command[0]}: {self._process.errorString()}")
            self._finish(-1)
            return False
        return True

    def cancel(self) -> None:
        if not self.is_running or self._cancelled:
            return
        self._cancelled = True
        self._emit_log("Stopping download...")
        self._process.terminate()
        self._kill_timer.start()

    def stop_and_wait(self, timeout_ms: int = 3000) -> None:
        """Best-effort synchronous stop used when the window is closing."""
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._cancelled = True
            self._kill_tree()
            self._process.waitForFinished(timeout_ms)

    # --- internals ------------------------------------------------------
    def _reset(self) -> None:
        self._buffer = b""
        self._pending_log = []
        self._pending_progress = None
        self._last_filename = ""
        self._cancelled = False
        self._finished = False
        self._kill_timer.stop()

    def _read_output(self) -> None:
        raw = bytes(self._process.readAllStandardOutput())
        if not raw:
            return
        self._buffer += raw
        lines, self._buffer = split_lines(self._buffer)
        for line in lines:
            self._handle_line(decode_line(line))
        if self._pending_log or self._pending_progress is not None:
            if not self._flush_timer.isActive():
                self._flush_timer.start()

    def _handle_line(self, line: str) -> None:
        line = line.rstrip()
        if not line:
            return
        self._pending_log.append(line)
        if self._file_log is not None:
            self._file_log.write(line)

        update = parse_progress_line(line)
        if update is None:
            return
        if update.filename:
            self._last_filename = update.filename
        elif self._last_filename:
            update.filename = self._last_filename
        self._pending_progress = update

    def _flush(self) -> None:
        if self._pending_log:
            text = "\n".join(self._pending_log)
            self._pending_log = []
            self.log.emit(text)
        if self._pending_progress is not None:
            update = self._pending_progress
            self._pending_progress = None
            self.progress.emit(update)

    def _emit_log(self, message: str) -> None:
        self._pending_log.append(message)
        if self._file_log is not None:
            self._file_log.write(message)
        self._flush()

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._kill_timer.stop()
        self._read_output()
        if self._buffer.strip():
            self._handle_line(decode_line(self._buffer))
            self._buffer = b""
        self._finish(exit_code if exit_code >= 0 else -1)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._emit_log(f"yt-dlp failed to start: {self._process.errorString()}")
            self._finish(-1)

    def _finish(self, exit_code: int) -> None:
        if self._finished:
            return
        self._finished = True
        self._flush_timer.stop()
        self._kill_timer.stop()
        self._flush()
        self.finished.emit(exit_code, self._cancelled)

    def _force_kill(self) -> None:
        if self._process.state() == QProcess.ProcessState.NotRunning:
            return
        self._kill_tree()

    def _kill_tree(self) -> None:
        pid = int(self._process.processId())
        if sys.platform == "win32" and pid and os.name == "nt":
            try:
                subprocess.Popen(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError:
                pass
        self._process.kill()
