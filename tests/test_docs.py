from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_points_support_to_yoomoney():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "A portable Windows download manager for video hostings" in readme
    assert "A portable Windows desktop wrapper for yt-dlp" not in readme
    assert "ko-fi" not in readme.lower()
    assert "Support YooMoney" in readme
    assert "https://yoomoney.ru/to/41001937179526" in readme

    installation = readme.split("## Installation", 1)[1].split("## Usage", 1)[0]
    assert "yoomoney" not in installation.lower()


def test_landing_defaults_to_english_and_supports_yoomoney():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "docs" / "script.js").read_text(encoding="utf-8")

    assert "<html lang=\"en\">" in html
    assert "var DEFAULT_LANG = 'en';" in script
    assert "https://yoomoney.ru/to/41001937179526" in html
    assert "cta_donate: 'Support YooMoney'" in script
    assert "ko-fi" not in html.lower()
    assert "ko-fi" not in script.lower()


def test_landing_section_spacing_and_anchor_offset():
    css = (ROOT / "docs" / "styles.css").read_text(encoding="utf-8")
    script = (ROOT / "docs" / "script.js").read_text(encoding="utf-8")

    assert "--section-gap: 3.2rem" in css
    assert "main > section {" in css
    assert "scroll-padding-top: var(--topbar-height)" in css
    assert "syncTopbarHeight" in script
