from unittest.mock import patch

from language_utils import detect_language, get_language_name, is_multilingual_embedding_needed


class TestDetectLanguage:
    def test_returns_english_for_empty_text(self):
        assert detect_language("") == "en"

    def test_returns_english_for_english_text(self):
        with patch("config.DETECT_LANGUAGE", True):
            lang = detect_language("This is a legal contract between parties.")
            assert lang == "en"

    def test_returns_english_when_detection_disabled(self):
        with patch("config.DETECT_LANGUAGE", False):
            lang = detect_language("Cualquier texto")
            assert lang == "en"

    def test_falls_back_to_english_when_langdetect_missing(self):
        with patch("config.DETECT_LANGUAGE", True):
            lang = detect_language("Some text when langdetect unavailable")
            assert lang == "en"


class TestGetLanguageName:
    def test_returns_name_for_known_code(self):
        assert get_language_name("en") == "English"
        assert get_language_name("es") == "Spanish"
        assert get_language_name("fr") == "French"

    def test_returns_code_for_unknown(self):
        assert get_language_name("xx") == "xx"


class TestIsMultilingualEmbeddingNeeded:
    def test_false_when_multilingual_disabled(self):
        with patch("language_utils.detect_language", return_value="es"):
            with patch("config.ENABLE_MULTILINGUAL", False):
                assert is_multilingual_embedding_needed("Cualquier texto") is False

    def test_true_for_non_english_when_enabled(self):
        with patch("language_utils.detect_language", return_value="es"):
            with patch("config.ENABLE_MULTILINGUAL", True):
                assert is_multilingual_embedding_needed("Cualquier texto") is True

    def test_false_for_english_text(self):
        with patch("language_utils.detect_language", return_value="en"):
            with patch("config.ENABLE_MULTILINGUAL", True):
                assert is_multilingual_embedding_needed("Hello world") is False
