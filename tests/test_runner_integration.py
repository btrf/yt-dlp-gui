import json
import sys

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer

from core.command_builder import PROGRESS_MARKER, TITLE_SEPARATOR
from core.runner import DownloadRunner


def test_runner_streams_output_and_finishes():
    _app = QCoreApplication.instance() or QCoreApplication([])

    payload = json.dumps({"downloaded_bytes": 50, "total_bytes": 100})
    progress_line = PROGRESS_MARKER + "Тест видео" + TITLE_SEPARATOR + payload
    script = (
        "print('hello from fake yt-dlp');"
        "print(" + repr(progress_line) + ")"
    )

    runner = DownloadRunner()
    logs: list[str] = []
    updates: list[object] = []
    titles: list[str] = []
    finished: list[tuple[int, bool]] = []
    runner.log.connect(logs.append)
    runner.progress.connect(updates.append)
    runner.title.connect(titles.append)
    runner.finished.connect(lambda code, cancelled: finished.append((code, cancelled)))

    loop = QEventLoop()
    runner.finished.connect(lambda *_: loop.quit())
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)

    assert runner.start([sys.executable, "-c", script])
    timeout.start(20000)
    loop.exec()

    assert finished == [(0, False)]
    assert any("hello from fake yt-dlp" in line for line in logs)
    assert not any(PROGRESS_MARKER in line for line in logs)
    assert titles == ["Тест видео"]
    assert updates
    assert updates[-1].percent == 50.0
    assert updates[-1].title == "Тест видео"
    assert not runner.is_running


def test_runner_reports_missing_binary():
    _app = QCoreApplication.instance() or QCoreApplication([])

    runner = DownloadRunner()
    finished: list[tuple[int, bool]] = []
    logs: list[str] = []
    runner.finished.connect(lambda code, cancelled: finished.append((code, cancelled)))
    runner.log.connect(logs.append)

    assert not runner.start(["definitely-not-a-real-binary-xyz"])

    deadline = QEventLoop()
    QTimer.singleShot(3000, deadline.quit)
    deadline.exec()

    assert finished and finished[0][0] == -1
    assert logs
