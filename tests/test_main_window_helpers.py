from ui.main_window import (
    MAX_RECENT_URLS,
    _as_bool,
    _as_recent_entries,
    _elide_title,
    _elide_url,
    _quote,
    read_url_file,
)


def test_read_url_file_skips_comments_and_bom(tmp_path):
    path = tmp_path / "links.txt"
    path.write_text(
        "\ufeff# comment\nhttps://example.com/1\r\n\n; another comment\n// note\nhttps://example.com/2\n",
        encoding="utf-8",
    )
    assert read_url_file(str(path)) == ["https://example.com/1", "https://example.com/2"]


def test_read_url_file_supports_cp1251(tmp_path):
    path = tmp_path / "links.txt"
    path.write_bytes("https://example.com/Привет\n".encode("cp1251"))
    assert read_url_file(str(path)) == ["https://example.com/Привет"]


def test_as_bool_understands_settings_strings():
    assert _as_bool(True)
    assert _as_bool("true")
    assert _as_bool("1")
    assert not _as_bool("false")
    assert not _as_bool(None)


def test_quote_only_wraps_arguments_with_spaces():
    assert _quote("--limit-rate") == "--limit-rate"
    assert _quote("my file.mkv") == '"my file.mkv"'


def test_as_recent_entries_keeps_order_and_drops_duplicates():
    assert _as_recent_entries("https://example.com/1") == [
        {"url": "https://example.com/1", "title": ""}
    ]
    assert _as_recent_entries(
        ["https://example.com/2", " https://example.com/1 ", "https://example.com/2", ""]
    ) == [
        {"url": "https://example.com/2", "title": ""},
        {"url": "https://example.com/1", "title": ""},
    ]
    assert _as_recent_entries(None) == []


def test_as_recent_entries_reads_new_format_and_keeps_titles():
    value = [
        {"url": "https://example.com/2", "title": "Второе видео"},
        {"url": "https://example.com/1", "title": ""},
        {"url": "https://example.com/2", "title": "Дубликат"},
        {"title": "Без ссылки"},
    ]
    assert _as_recent_entries(value) == [
        {"url": "https://example.com/2", "title": "Второе видео"},
        {"url": "https://example.com/1", "title": ""},
    ]


def test_as_recent_entries_is_limited_to_the_menu_size():
    value = [f"https://example.com/{index}" for index in range(MAX_RECENT_URLS + 3)]
    entries = _as_recent_entries(value)
    assert len(entries) == MAX_RECENT_URLS
    assert entries[0]["url"] == "https://example.com/0"


def test_elide_title_keeps_short_titles_and_trims_long_ones():
    short = "Короткое видео"
    assert _elide_title(short) == short
    long = "Очень длинное название видео " * 10
    elided = _elide_title(long, limit=40)
    assert len(elided) == 40
    assert elided.endswith("…")


def test_elide_url_keeps_short_links_and_trims_long_ones():
    short = "https://example.com/watch?v=1"
    assert _elide_url(short) == short
    long = "https://example.com/watch?v=" + "a" * 120
    elided = _elide_url(long, limit=40)
    assert len(elided) == 40
    assert elided.startswith("https://")
    assert elided.endswith("aaaa")
    assert "…" in elided
