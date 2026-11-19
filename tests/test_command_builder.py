import os

import pytest

from core.command_builder import (
    DEFAULT_TEMPLATE,
    ExtraOptionsError,
    DownloadRequest,
    build_command,
    normalize_format,
    split_extra_options,
)

YTDLP = "yt-dlp"


def make_request(**kwargs) -> DownloadRequest:
    defaults = {
        "url": "https://example.com/video",
        "output_dir": r"C:\Downloads",
    }
    defaults.update(kwargs)
    return DownloadRequest(**defaults)


def build(**kwargs):
    request = make_request(**kwargs)
    return build_command(request, yt_dlp_path=YTDLP, ffmpeg_path="ffmpeg")


def value_after(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def test_default_container_is_mkv():
    command = build()
    assert value_after(command, "--merge-output-format") == "mkv"
    assert value_after(command, "-o") == os.path.join(r"C:\Downloads", DEFAULT_TEMPLATE)


def test_video_uses_quality_sorting_instead_of_format_strings():
    command = build(quality="1080p")
    assert value_after(command, "-S") == "res:1080"
    assert "-f" not in command


def test_best_quality_leaves_selection_to_ytdlp():
    command = build(quality="best")
    assert "-S" not in command
    assert "-f" not in command


def test_raw_format_expression_is_passed_through():
    command = build(quality="bv*[height<=480]+ba")
    assert value_after(command, "-f") == "bv*[height<=480]+ba"


def test_audio_extraction_uses_audio_quality():
    command = build(download_type="audio", output_format="mp3")
    assert "-x" in command
    assert value_after(command, "--audio-format") == "mp3"
    assert value_after(command, "-f") == "bestaudio/best"
    assert "--merge-output-format" not in command


def test_unknown_audio_format_falls_back_to_mp3():
    command = build(download_type="audio", output_format="mkv")
    assert value_after(command, "--audio-format") == "mp3"


def test_unknown_video_format_falls_back_to_mkv():
    command = build(download_type="video", output_format="mp3")
    assert value_after(command, "--merge-output-format") == "mkv"


def test_single_video_disables_playlist():
    command = build()
    assert "--no-playlist" in command
    assert "--yes-playlist" not in command


def test_playlist_all_enables_playlist():
    command = build(playlist_enabled=True, playlist_items="all")
    assert "--yes-playlist" in command
    assert "--no-playlist" not in command


@pytest.mark.parametrize(
    ("spec", "expected"),
    [("first", "1"), ("last", "-1"), ("2:5", "2:5"), ("1,3,5", "1,3,5")],
)
def test_playlist_scopes(spec, expected):
    command = build(playlist_enabled=True, playlist_items=spec)
    assert value_after(command, "--playlist-items") == expected
    assert "--yes-playlist" not in command


def test_extra_options_keep_quoted_values_together():
    command = build(extra_options='--username "user name" --limit-rate 1M --cookies "C:\\my dir\\c.txt"')
    assert "user name" in command
    assert "1M" in command
    assert r"C:\my dir\c.txt" in command


def test_empty_extra_options_are_ignored():
    command = build(extra_options="   ")
    assert command[-1] == "https://example.com/video"


def test_unbalanced_quotes_raise():
    with pytest.raises(ExtraOptionsError):
        split_extra_options('--username "user')


def test_archive_and_skip_existing_and_cookies():
    command = build(
        archive_path=r"C:\Downloads\archive.txt",
        skip_existing=True,
        cookies_from_browser="edge",
    )
    assert value_after(command, "--download-archive") == r"C:\Downloads\archive.txt"
    assert "--no-overwrites" in command
    assert value_after(command, "--cookies-from-browser") == "edge"


def test_ffmpeg_location_points_to_bundle_directory():
    request = make_request()
    command = build_command(
        request, yt_dlp_path=YTDLP, ffmpeg_path=r"C:\app\bin\ffmpeg.exe"
    )
    assert value_after(command, "--ffmpeg-location") == r"C:\app\bin"


def test_machine_readable_progress_is_requested():
    command = build()
    assert "--newline" in command
    assert "--no-color" in command
    assert "--progress-template" in command


def test_output_encoding_is_forced_to_utf8():
    # Otherwise yt-dlp prints Russian titles in the ANSI codepage (cp1251)
    # and the log window shows mojibake.
    command = build()
    assert value_after(command, "--encoding") == "utf-8"


def test_ads_are_removed_by_default():
    command = build()
    assert value_after(command, "--sponsorblock-remove") == "sponsor"


def test_ads_can_be_kept():
    command = build(remove_ads=False)
    assert "--sponsorblock-remove" not in command


def test_output_directory_may_be_empty():
    command = build(output_dir="")
    assert value_after(command, "-o") == DEFAULT_TEMPLATE


def test_normalize_format_per_media_type():
    assert normalize_format("video", "webm") == "webm"
    assert normalize_format("video", "mp3") == "mkv"
    assert normalize_format("audio", "m4a") == "m4a"
    assert normalize_format("audio", "mp4") == "mp3"
