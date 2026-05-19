"""
services/llm_service.py — Agent 4: LLM response generation.

Implements RAG (Retrieval-Augmented Generation) using retrieved solutions
as context. Includes hallucination detection via cosine similarity check.

Provider is selected at startup via LLM_PROVIDER env var:
    "ollama" → Ollama/Mistral  (local dev)
    "qwen"   → Qwen cloud API  (production)
"""

import time
from typing import Optional
from loguru import logger

from core.config import settings
from services.embedding_service import embedding_service
from services.llm_provider_factory import llm_provider

# ─── Prompt templates ─────────────────────────────────────────────────
RAG_PROMPT_TEMPLATE = """\
You are an IT support specialist.

Ticket: {ticket_text}
Category: {category}
Previous solution: {retrieved_solution}

Provide a clear, actionable response in 3-4 sentences with numbered steps.
Be specific and technical. No disclaimers or greetings.
"""

KNOWLEDGE_ARTICLE_PROMPT = """\
Convert this resolved support ticket into a knowledge base article.

Original issue: {ticket_text}
Category: {category}
Resolution applied: {solution}
Resolution time: {resolution_hours} hours

Output ONLY valid JSON in this exact format:
{{
  "title": "concise issue title",
  "problem_description": "one sentence",
  "likely_cause": "one sentence",
  "solution_steps": ["step 1", "step 2", "step 3"],
  "prevention": "one sentence",
  "tags": ["tag1", "tag2", "tag3"],
  "difficulty": "Easy",
  "estimated_resolution_time": "X minutes"
}}
"""

ROOT_CAUSE_PROMPT = """\
Multiple support tickets report issues with: {keywords}
Category: {category}
Ticket count in last {window} minutes: {count}

What is the most likely root cause? Answer in one concise sentence.
"""


class LLMService:
    """
    Agent 4 of the TicketFlow pipeline.

    Delegates all LLM calls to the active provider (Ollama or Qwen),
    selected via the LLM_PROVIDER environment variable.

    Responsibilities:
    - Build RAG prompt from retrieved solution context
    - Call the active LLM provider for response generation
    - Detect hallucination via cosine similarity check
    - Fall back to retrieved solution if hallucination detected
    - Generate knowledge base articles from resolved tickets
    - Generate root cause hypotheses for spike incidents
    """

    @property
    def _provider(self):
        """Active LLM provider (resolved from factory at import time)."""
        return llm_provider

    @property
    def model(self) -> str:
        """Human-readable model name for logging/storage."""
        provider = settings.resolved_llm_provider
        if provider == "cerebras":
            return settings.CEREBRAS_MODEL
        if provider == "qwen":
            return settings.QWEN_MODEL
        return settings.OLLAMA_MODEL

    async def generate_response(
        self,
        ticket_text: str,
        category: str,
        retrieved_solution: str,
        routing_decision: str,
    ) -> dict:
        """
        Agent 4 main method: Generate a support response via RAG.

        Only called when routing != ESCALATE_TO_HUMAN.
        """
        if routing_decision == "ESCALATE_TO_HUMAN":
            return {
                "generated_response": None,
                "generation_time_ms": 0,
                "hallucination_detected": False,
                "fallback_used": False,
                "model_used": None,
            }

        start_time = time.time()

        prompt = RAG_PROMPT_TEMPLATE.format(
            ticket_text=ticket_text[:500],  # Reduced from 800
            category=category,
            retrieved_solution=retrieved_solution[:400],  # Reduced from 600
        )

        generated_text = await self._provider.generate(
            prompt, temperature=0.3, max_tokens=150  # Reduced from 250
        )
        generation_time_ms = int((time.time() - start_time) * 1000)

        hallucination_detected = False
        fallback_used = False

        if not generated_text:
            # Provider unavailable — fall back to retrieved solution
            generated_text = retrieved_solution
            fallback_used = True
        else:
            similarity = await self._check_hallucination(
                generated_text, retrieved_solution
            )
            if similarity < settings.HALLUCINATION_SIM_THRESHOLD:
                hallucination_detected = True
                fallback_used = True
                generated_text = retrieved_solution
                logger.warning(
                    f"Hallucination detected (similarity={similarity:.3f} < "
                    f"{settings.HALLUCINATION_SIM_THRESHOLD}). "
                    f"Falling back to retrieved solution."
                )

        return {
            "generated_response": generated_text,
            "generation_time_ms": generation_time_ms,
            "hallucination_detected": hallucination_detected,
            "fallback_used": fallback_used,
            "model_used": self.model if not fallback_used else "fallback",
        }

    async def _check_hallucination(
        self, generated_text: str, reference_text: str
    ) -> float:
        """Cosine similarity guard against hallucinated responses."""
        try:
            return await embedding_service.cosine_similarity_async(
                generated_text, reference_text
            )
        except Exception as e:
            logger.warning(f"Hallucination check error: {e}. Assuming ok.")
            return 1.0

    async def generate_knowledge_article(
        self,
        ticket_text: str,
        category: str,
        solution: str,
        resolution_hours: float,
    ) -> Optional[dict]:
        """Generate a structured KB article from a resolved ticket."""
        prompt = KNOWLEDGE_ARTICLE_PROMPT.format(
            ticket_text=ticket_text[:500],
            category=category,
            solution=solution[:500],
            resolution_hours=round(resolution_hours, 1),
        )
        return await self._provider.generate_json(
            prompt, temperature=0.2, max_tokens=400
        )

    async def generate_root_cause_hypothesis(
        self,
        keywords: list,
        category: str,
        ticket_count: int,
        window_minutes: int,
    ) -> str:
        """Generate a one-sentence root cause hypothesis for an incident spike."""
        prompt = ROOT_CAUSE_PROMPT.format(
            keywords=", ".join(keywords[:5]),
            category=category,
            count=ticket_count,
            window=window_minutes,
        )

        response = await self._provider.generate(
            prompt, temperature=0.1, max_tokens=100
        )

        if response:
            return response.split(".")[0].strip() + "."

        return (
            f"Possible {category.lower()} system issue affecting multiple users, "
            f"related to: {', '.join(keywords[:3])}."
        )


# Module-level singleton
llm_service = LLMService()
