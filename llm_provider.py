"""
LLM Provider Factory — supports Groq, OpenAI, Anthropic, and Google Gemini.

Usage:
    from llm_provider import llm_provider
    llm = llm_provider.get_llm("openai")
    llm = llm_provider.get_llm("groq", temperature=0)
"""

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel

import config

logger = logging.getLogger(__name__)

# Provider → (module_path, class_name, api_key_attr, model_attr)
_PROVIDER_REGISTRY: dict[str, tuple[str, str, str, str]] = {
    "groq": ("langchain_groq", "ChatGroq", "GROQ_API_KEY", "GROQ_MODEL"),
    "openai": ("langchain_openai", "ChatOpenAI", "OPENAI_API_KEY", "OPENAI_MODEL"),
    "anthropic": ("langchain_anthropic", "ChatAnthropic", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "google": ("langchain_google_genai", "ChatGoogleGenerativeAI", "GOOGLE_API_KEY", "GOOGLE_MODEL"),
}


class LLMProvider:
    """Factory that creates LangChain chat LLM instances by provider name."""

    def __init__(self):
        self._cache: dict[str, BaseChatModel] = {}

    def get_available_providers(self) -> list[dict]:
        """Return list of providers that have API keys configured."""
        providers = []
        for name, (_, _, key_attr, model_attr) in _PROVIDER_REGISTRY.items():
            api_key = getattr(config, key_attr, "")
            if api_key:
                providers.append({
                    "name": name,
                    "model": getattr(config, model_attr, ""),
                    "is_default": name == config.DEFAULT_LLM_PROVIDER,
                })
        return providers

    def get_llm(
        self,
        provider: Optional[str] = None,
        temperature: float = 0.1,
        model_override: Optional[str] = None,
    ) -> BaseChatModel:
        """
        Get a LangChain chat LLM for the given provider.

        Falls back to DEFAULT_LLM_PROVIDER if provider is None or unavailable.
        """
        provider = provider or config.DEFAULT_LLM_PROVIDER

        if provider not in _PROVIDER_REGISTRY:
            logger.warning("Unknown provider '%s', falling back to '%s'", provider, config.DEFAULT_LLM_PROVIDER)
            provider = config.DEFAULT_LLM_PROVIDER

        module_path, class_name, key_attr, model_attr = _PROVIDER_REGISTRY[provider]
        api_key = getattr(config, key_attr, "")

        if not api_key:
            # Fall back to default provider
            if provider != config.DEFAULT_LLM_PROVIDER:
                logger.warning(
                    "No API key for '%s', falling back to '%s'",
                    provider, config.DEFAULT_LLM_PROVIDER,
                )
                return self.get_llm(config.DEFAULT_LLM_PROVIDER, temperature, model_override)
            raise ValueError(f"No API key configured for default provider '{provider}'")

        model_name = model_override or getattr(config, model_attr, "")

        cache_key = f"{provider}:{model_name}:{temperature}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            import importlib
            module = importlib.import_module(module_path)
            llm_class = getattr(module, class_name)
        except ImportError:
            logger.error("Package '%s' not installed for provider '%s'", module_path, provider)
            if provider != config.DEFAULT_LLM_PROVIDER:
                return self.get_llm(config.DEFAULT_LLM_PROVIDER, temperature, model_override)
            raise

        # Build constructor kwargs — each provider has slightly different parameter names
        kwargs: dict = {"temperature": temperature}

        if provider == "groq":
            kwargs["api_key"] = api_key
            kwargs["model"] = model_name
        elif provider == "openai":
            kwargs["api_key"] = api_key
            kwargs["model"] = model_name
        elif provider == "anthropic":
            kwargs["api_key"] = api_key
            kwargs["model"] = model_name
        elif provider == "google":
            kwargs["google_api_key"] = api_key
            kwargs["model"] = model_name

        llm = llm_class(**kwargs)
        self._cache[cache_key] = llm
        logger.info("Created LLM: provider=%s model=%s temp=%.1f", provider, model_name, temperature)
        return llm

    def get_memory_llm(self, temperature: float = 0) -> BaseChatModel:
        """Get a fast/cheap LLM for memory tasks (summarization, fact extraction)."""
        # Always use Groq's fast model for memory tasks to keep costs low
        if config.GROQ_API_KEY:
            return self.get_llm("groq", temperature=temperature, model_override=config.GROQ_MEMORY_MODEL)
        # Fall back to default provider
        return self.get_llm(temperature=temperature)


# Singleton
llm_provider = LLMProvider()
