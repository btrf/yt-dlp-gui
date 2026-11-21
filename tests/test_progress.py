import json

from core.command_builder import PROGRESS_MARKER, TITLE_SEPARATOR
from core.progress import (
    decode_line,
    format_bytes,
    format_eta,
    parse_progress_line,
    split_lines,
)


def progress_line(payload: dict) -> str:
    return PROGRESS_MARKER + json.dumps(payload)


def test_json_progress_is_parsed():
    update = parse_progress_line(
        progress_line(
            {
                "status": "downloading",
                "downloaded_bytes": 512,
                "total_bytes": 1024,
                "speed": 2 * 1024 * 1024,
                "eta": 65,
                "filename": "video.f137.mp4",
            }
        )
    )
    assert update is not None
    assert update.percent == 50.0
    assert update.speed == "2.0 MiB/s"
    assert update.eta == "01:05"
    assert update.total == "1.0 KiB"
    assert update.filename == "video.f137.mp4"


def test_json_progress_uses_estimate_and_percent_string():
    update = parse_progress_line(
        progress_line(
            {
                "status": "downloading",
                "downloaded_bytes": 25,
                "total_bytes_estimate": 100,
                "_percent_str": " 25.0%",
            }
        )
    )
    assert update is not None
    assert update.percent == 25.0


def test_broken_json_is_ignored():
    assert parse_progress_line(PROGRESS_MARKER + "{not json") is None


def test_json_progress_carries_video_title():
    payload = json.dumps(
        {"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2}
    )
    update = parse_progress_line(
        f"{PROGRESS_MARKER}Тест видео{TITLE_SEPARATOR}{payload}"
    )
    assert update is not None
    assert update.title == "Тест видео"
    assert update.percent == 50.0


def test_missing_title_placeholder_is_ignored():
    payload = json.dumps({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2})
    update = parse_progress_line(f"{PROGRESS_MARKER}NA{TITLE_SEPARATOR}{payload}")
    assert update is not None
    assert update.title == ""


def test_plain_progress_line_is_parsed():
    line = "[download]  45.2% of ~ 10.00MiB at 3.40MiB/s ETA 00:12"
    update = parse_progress_line(line)
    assert update is not None
    assert update.percent == 45.2
    assert update.speed == "3.40MiB/s"
    assert update.eta == "00:12"


def test_destination_line_sets_filename():
    update = parse_progress_line(r'[download] Destination: C:\Downloads\video.f251.webm')
    assert update is not None
    assert update.filename.endswith("video.f251.webm")


def test_postprocessor_stage_is_detected():
    update = parse_progress_line('[Merger] Merging formats into "C:\\Downloads\\video.mkv"')
    assert update is not None
    assert update.stage == "Merger"


def test_plain_log_line_is_not_progress():
    assert parse_progress_line("[youtube] Extracting URL: https://youtu.be/x") is None


def test_split_lines_handles_carriage_returns():
    lines, remainder = split_lines(b"one\rtwo\rthree\nfour")
    assert lines == [b"one", b"two", b"three"]
    assert remainder == b"four"


def test_split_lines_keeps_incomplete_character_for_next_chunk():
    raw = "Привет".encode("utf-8")
    lines, remainder = split_lines(b"ok\n" + raw[:4])
    assert lines == [b"ok"]
    assert remainder == raw[:4]
    assert decode_line(remainder + raw[4:]) == "Привет"


def test_utf8_output_is_decoded():
    assert decode_line("Привет мир — тест".encode("utf-8")) == "Привет мир — тест"


def test_ansi_output_is_decoded():
    # Windows yt-dlp builds write titles in the ANSI codepage (cp1251 on RU).
    assert decode_line("Привет".encode("cp1251"), fallback_encoding="cp1251") == "Привет"


def test_unknown_bytes_never_raise():
    assert decode_line(b"\xff\xfe\x00broken", fallback_encoding="cp1251")


def test_format_helpers():
    assert format_bytes(0) == ""
    assert format_bytes(1536) == "1.5 KiB"
    assert format_eta(0) == "00:00"
    assert format_eta(3725) == "1:02:05"
    assert format_eta(None) == ""
