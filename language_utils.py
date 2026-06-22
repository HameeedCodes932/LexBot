import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

_LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "cs": "Czech",
    "ro": "Romanian",
    "hu": "Hungarian",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
}


def detect_language(text: str) -> str:
    if not config.DETECT_LANGUAGE or not text.strip():
        return "en"
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42
        lang = detect(text[:500])
        return lang if lang else "en"
    except Exception:
        return "en"


def get_language_name(lang_code: str) -> str:
    return _LANGUAGE_NAMES.get(lang_code, lang_code)


def is_multilingual_embedding_needed(text: str) -> bool:
    lang = detect_language(text)
    return lang != "en" if config.ENABLE_MULTILINGUAL else False


def get_multilingual_embeddings():
    if not config.ENABLE_MULTILINGUAL:
        return None
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        logger.info("Loading multilingual embedding model: %s", config.MULTILINGUAL_EMBEDDING_MODEL)
        return HuggingFaceEmbeddings(
            model_name=config.MULTILINGUAL_EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as exc:
        logger.warning("Failed to load multilingual embedding model: %s", exc)
        return None
