from core.progress import KNOWN_STAGES
from ui.i18n import TRANSLATIONS, I18n, normalize_language


def test_both_languages_have_the_same_keys():
    assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["ru"])


def test_every_postprocessor_stage_is_translated():
    missing = [stage for stage in KNOWN_STAGES if f"stage_{stage}" not in TRANSLATIONS["ru"]]
    assert not missing


def test_missing_key_is_returned_as_is():
    assert I18n("en").t("definitely_missing") == "definitely_missing"


def test_placeholders_are_formatted():
    assert I18n("ru").t("batch_item", current=1, total=3) == "элемент 1/3"
    assert I18n("en").t("batch_item", current=1, total=3) == "item 1/3"


def test_language_normalization():
    assert normalize_language("ru_RU") == "ru"
    assert normalize_language("en_US") == "en"
    assert normalize_language("de_DE") == "en"
    assert normalize_language(None) == "en"


def test_language_switch():
    i18n = I18n("en")
    i18n.set_language("ru")
    assert i18n.t("menu_help") == "Справка"
