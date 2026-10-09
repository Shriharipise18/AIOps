"""Construct the configured LLM provider without exposing API credentials."""
from app.core.config import settings
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.provider import LLMProvider


def get_llm_provider() -> LLMProvider | None:
    """Return the selected provider when its key is configured."""
    if settings.LLM_PROVIDER == "groq":
        if not settings.GROQ_API_KEY or not settings.GROQ_API_KEY.get_secret_value().strip():
            return None
        return GroqProvider()

    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.get_secret_value().strip():
        return None
    return OpenAIProvider()


def llm_health() -> dict[str, str]:
    """Report configuration only; this does not make a paid API request."""
    if settings.LLM_PROVIDER == "groq":
        configured = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.get_secret_value().strip())
        return {
            "status": "configured" if configured else "not_configured",
            "provider": "Groq",
            "model": settings.GROQ_MODEL,
        }

    configured = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.get_secret_value().strip())
    return {
        "status": "configured" if configured else "not_configured",
        "provider": "OpenAI",
        "model": "gpt-4o",
    }
