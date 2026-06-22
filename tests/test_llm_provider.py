from unittest.mock import patch

from llm_provider import LLMProvider


class TestAvailableProviders:
    def test_returns_empty_when_no_keys(self):
        provider = LLMProvider()
        with patch("config.GROQ_API_KEY", ""), \
             patch("config.OPENAI_API_KEY", ""), \
             patch("config.ANTHROPIC_API_KEY", ""), \
             patch("config.GOOGLE_API_KEY", ""):
            result = provider.get_available_providers()
            assert result == []

    def test_returns_groq_when_key_set(self):
        provider = LLMProvider()
        with patch("config.GROQ_API_KEY", "sk-test"), \
             patch("config.DEFAULT_LLM_PROVIDER", "groq"):
            result = provider.get_available_providers()
            names = [p["name"] for p in result]
            assert "groq" in names
            groq = next(p for p in result if p["name"] == "groq")
            assert groq["is_default"] is True

    def test_marks_default_provider(self):
        provider = LLMProvider()
        with patch("config.GROQ_API_KEY", "sk-test"), \
             patch("config.OPENAI_API_KEY", "sk-test"), \
             patch("config.DEFAULT_LLM_PROVIDER", "openai"):
            result = provider.get_available_providers()
            openai = next(p for p in result if p["name"] == "openai")
            assert openai["is_default"] is True
            groq = next(p for p in result if p["name"] == "groq")
            assert groq["is_default"] is False


class TestGetLLM:
    def test_raises_when_no_keys_for_default(self):
        provider = LLMProvider()
        with patch("config.GROQ_API_KEY", ""), \
             patch("config.DEFAULT_LLM_PROVIDER", "groq"):
            try:
                provider.get_llm()
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "No API key" in str(e)

    def test_falls_back_to_default_when_provider_unavailable(self):
        provider = LLMProvider()
        with patch("config.GROQ_API_KEY", "sk-groq"), \
             patch("config.OPENAI_API_KEY", ""), \
             patch("config.DEFAULT_LLM_PROVIDER", "groq"):
            llm = provider.get_llm("openai")
            assert llm is not None

    def test_unknown_provider_falls_back(self):
        provider = LLMProvider()
        with patch("config.GROQ_API_KEY", "sk-groq"), \
             patch("config.DEFAULT_LLM_PROVIDER", "groq"):
            llm = provider.get_llm("nonexistent")
            assert llm is not None

    def test_get_memory_llm_uses_groq_when_available(self):
        provider = LLMProvider()
        with patch("config.GROQ_API_KEY", "sk-groq"):
            llm = provider.get_memory_llm()
            assert llm is not None
