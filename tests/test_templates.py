import re

from ui.dialogs import TEMPLATE_PRESETS
from ui.i18n import TRANSLATIONS


def test_presets_are_unique_and_produce_files():
    templates = [template for template, _description in TEMPLATE_PRESETS]
    assert len(templates) == len(set(templates))
    assert all("%(ext)s" in template for template in templates)


def test_default_template_is_offered():
    templates = [template for template, _description in TEMPLATE_PRESETS]
    assert "%(upload_date)s - %(title)s.%(ext)s" in templates


def test_every_preset_has_a_description_in_both_languages():
    for _template, key in TEMPLATE_PRESETS:
        assert key in TRANSLATIONS["en"], key
        assert key in TRANSLATIONS["ru"], key
        assert key != TRANSLATIONS["en"][key]


def test_presets_avoid_illegal_windows_characters():
    # yt-dlp sanitises names itself, but the literal text of a template should
    # not contain characters Windows forbids in file names.
    for template, _description in TEMPLATE_PRESETS:
        literal = re.sub(r"%\([^)]*\)[a-zA-Z]?", "", template)
        assert not any(char in literal for char in '<>:"|?*'), literal
