from ui.main_window import _as_bool, _quote, read_url_file


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
