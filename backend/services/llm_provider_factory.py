"""
services/llm_provider_factory.py — Environment-based LLM provider selector.

Provider selection (controlled by LLM_PROVIDER env var):
    "auto"      → cerebras if CEREBRAS_API_KEY is set, else ollama  (default)
    "cerebras"  → CerebrasProvider  (fast cloud inference, preferred)
    "ollama"    → OllamaProvider    (local dev)
    "qwen"      → QwenProvider      (production alternative)

Usage:
    from services.llm_provider_factory import llm_provider
    text = await llm_provider.generate(prompt)
"""

from loguru import logger
from core.config import settings


def get_llm_provider():
    """
    Return the active LLM provider instance.

    Resolution order for LLM_PROVIDER="auto":
        1. CEREBRAS_API_KEY present → CerebrasProvider
        2. Fallback                 → OllamaProvider

    Returns:
        CerebrasProvider, OllamaProvider, or QwenProvider —
        all share the same interface.

    Raises:
        ValueError: If LLM_PROVIDER is set to an unknown value.
    """
    provider_name = settings.resolved_llm_provider  # handles "auto" logic

    if provider_name == "cerebras":
        from services.cerebras_provider import cerebras_provider
        logger.info(
            f"LLM provider: Cerebras ({settings.CEREBRAS_MODEL})"
        )
        return cerebras_provider

    if provider_name == "ollama":
        from services.ollama_provider import ollama_provider
        logger.info(
            f"LLM provider: Ollama ({settings.OLLAMA_MODEL}) — local dev"
        )
        return ollama_provider

    if provider_name == "qwen":
        from services.qwen_provider import qwen_provider
        logger.info(
            f"LLM provider: Qwen ({settings.QWEN_MODEL})"
        )
        return qwen_provider

    raise ValueError(
        f"Unknown LLM_PROVIDER='{provider_name}'. "
        f"Valid options: 'auto', 'cerebras', 'ollama', 'qwen'"
    )


# Convenience singleton — resolved once at import time
llm_provider = get_llm_provider()
