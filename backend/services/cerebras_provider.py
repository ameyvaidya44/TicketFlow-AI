"""
services/cerebras_provider.py — Cerebras cloud LLM provider.

Uses the Cerebras Inference API (OpenAI-compatible endpoint).
Mirrors the OllamaProvider interface so the factory can swap them transparently.

Cerebras runs Llama models on wafer-scale silicon — extremely fast inference.
Default model: llama-3.3-70b (best quality/speed balance on Cerebras hardware).

Requires:
    CEREBRAS_API_KEY — set in environment / .env (never hardcoded)
    CEREBRAS_MODEL   — e.g. "llama-3.3-70b", "llama3.1-8b"
"""

import asyncio
import json
import re
from typing import Optional, Dict, Any, List
from loguru import logger

from core.config import settings


class CerebrasProvider:
    """
    LLM provider backed by Cerebras Inference API.

    The Cerebras API is OpenAI-compatible, so we reuse the openai SDK
    pointed at the Cerebras base URL — same pattern as QwenProvider.

    Mirrors OllamaProvider's public interface:
        generate(), generate_json(), classify_zero_shot(),
        analyze_threat(), is_available()
    """

    CEREBRAS_API_BASE = "https://api.cerebras.ai/v1"

    def __init__(self):
        self._api_key: str = settings.CEREBRAS_API_KEY
        self._model: str = settings.CEREBRAS_MODEL
        self._timeout: float = 30.0
        self._max_retries: int = 2
        self._prompts: Dict[str, str] = {}
        self._client = None  # lazy-initialised openai.AsyncOpenAI

    def _get_client(self):
        """Lazy-init the async OpenAI client pointed at Cerebras."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "openai package is required for Cerebras provider. "
                    "Run: pip install openai"
                ) from exc

            if not self._api_key:
                raise RuntimeError(
                    "CEREBRAS_API_KEY is not set. "
                    "Add it to your .env file before using the Cerebras provider."
                )

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self.CEREBRAS_API_BASE,
                timeout=self._timeout,
            )
        return self._client

    # ── prompt template loading ───────────────────────────────────────
    def load_prompt(self, name: str) -> str:
        if name in self._prompts:
            return self._prompts[name]
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
        if not prompt_path.exists():
            logger.warning(f"Prompt template '{name}' not found at {prompt_path}")
            return ""
        text = prompt_path.read_text(encoding="utf-8")
        self._prompts[name] = text
        return text

    # ── core generation ───────────────────────────────────────────────
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a chat-completion request to Cerebras with retry logic.

        Returns:
            Generated text string. Empty string on total failure.
        """
        target_model = model or self._model
        last_error = None

        for attempt in range(1, self._max_retries + 2):
            try:
                client = self._get_client()
                response = await client.chat.completions.create(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_transient = any(
                    kw in error_str
                    for kw in (
                        "timeout",
                        "connection",
                        "rate_limit",
                        "503",
                        "502",
                        "429",
                    )
                )
                if is_transient and attempt <= self._max_retries:
                    wait = 2**attempt
                    logger.warning(
                        f"Cerebras attempt {attempt}/{self._max_retries + 1} failed "
                        f"({type(e).__name__}). Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Cerebras generation failed: {e}")
                    break

        return ""

    # ── structured JSON generation ────────────────────────────────────
    async def generate_json(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Optional[Dict[str, Any]]:
        """Generate and parse a JSON response. Returns None on failure."""
        raw = await self.generate(
            prompt, temperature=temperature, max_tokens=max_tokens
        )
        if not raw:
            return None

        # Direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Markdown fence extraction
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Brace extraction
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning(f"Could not parse Cerebras response as JSON: {raw[:200]}")
        return None

    # ── zero-shot classification ──────────────────────────────────────
    async def classify_zero_shot(
        self,
        text: str,
        categories: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Zero-shot ticket classification. Returns {category, confidence} or None."""
        template = self.load_prompt("zero_shot_category")
        if not template:
            template = (
                "You are a support ticket classifier. Classify the following ticket "
                "into exactly ONE of these categories: {categories}\n\n"
                "Ticket: {text}\n\n"
                'Respond with ONLY a JSON object: {{"category": "<category>", "confidence": <0.0-1.0>}}'
            )

        prompt = template.format(categories=", ".join(categories), text=text[:1000])
        result = await self.generate_json(prompt, temperature=0.1)

        if result and "category" in result:
            if result["category"] in categories:
                return result
            for cat in categories:
                if cat.lower() == result["category"].lower():
                    result["category"] = cat
                    return result

        return None

    # ── threat analysis ───────────────────────────────────────────────
    async def analyze_threat(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyse a ticket for security threats. Returns structured dict or None."""
        template = self.load_prompt("threat_analysis")
        if not template:
            template = (
                "You are a cybersecurity analyst. Analyse this support ticket for security threats.\n\n"
                "Ticket: {text}\n\n"
                "Respond with ONLY a JSON object:\n"
                "{{\n"
                '  "threat_detected": true/false,\n'
                '  "threat_type": "phishing|malware|data_breach|unauthorized_access|social_engineering|insider_threat|none",\n'
                '  "severity": "critical|high|medium|low|none",\n'
                '  "confidence": 0.0-1.0,\n'
                '  "recommended_action": "brief action description",\n'
                '  "indicators": ["list", "of", "threat", "indicators"]\n'
                "}}"
            )

        prompt = template.format(text=text[:2000])
        return await self.generate_json(prompt, temperature=0.1, max_tokens=512)

    # ── health check ──────────────────────────────────────────────────
    async def is_available(self) -> bool:
        """Check if the Cerebras API is reachable with the configured key."""
        try:
            result = await self.generate(
                "Reply with the single word: ok",
                temperature=0.0,
                max_tokens=5,
            )
            return bool(result)
        except Exception:
            return False


# Module-level singleton
cerebras_provider = CerebrasProvider()
