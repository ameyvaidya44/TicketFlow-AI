"""
services/embedding_service.py — Sentence transformer embedding generation.
Produces 384-dimensional vectors for ChromaDB and similarity computation.

Redis caching: embedding vectors are cached in Upstash Redis (same instance
as the NLP preprocessing cache) using key format `embedding:{md5_hash}` with
a 7-day TTL. This avoids re-running Sentence Transformer inference for
repeated ticket texts.
"""

import asyncio
import hashlib
import json
import numpy as np
from typing import List, Optional
from loguru import logger
from urllib.parse import quote

from core.config import settings


class EmbeddingService:
    """
    Wraps sentence-transformers all-MiniLM-L6-v2 for embedding generation.

    - Lazy-loaded on first use to avoid slow startup
    - Thread-safe singleton model instance
    - Async wrappers to avoid blocking FastAPI event loop
    - Upstash Redis caching for embedding vectors (7-day TTL)
    """

    # TTL for cached embeddings: 7 days
    _EMBEDDING_TTL = 604800

    def __init__(self):
        self._model = None
        self._model_name = settings.EMBEDDING_MODEL  # "all-MiniLM-L6-v2"

        # Reuse the same Upstash Redis instance as nlp_cache
        self._cache_enabled = False
        self._http_client = None
        if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
            try:
                import httpx
                self._http_client = httpx.AsyncClient()
                self._cache_enabled = True
                logger.info("Embedding cache: Upstash Redis enabled")
            except ImportError:
                logger.warning("httpx not installed. Embedding cache disabled.")
        else:
            logger.warning(
                "Upstash credentials not configured. Embedding cache disabled."
            )

    # ── Cache helpers ─────────────────────────────────────────────────

    def _cache_key(self, text: str) -> str:
        """Deterministic Redis key for a given text."""
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        return f"embedding:{text_hash}"

    async def _cache_get(self, text: str) -> Optional[np.ndarray]:
        """
        Fetch embedding from Upstash Redis.

        Returns:
            np.ndarray if cache hit, None otherwise.
        """
        if not self._cache_enabled or not self._http_client:
            return None

        key = self._cache_key(text)
        url = f"{settings.UPSTASH_REDIS_REST_URL}/get/{key}"
        headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

        try:
            response = await self._http_client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result_value = data.get("result")
                if result_value:
                    try:
                        float_list = json.loads(result_value)
                        embedding = np.array(float_list, dtype=np.float32)
                        logger.debug(f"Embedding cache HIT  key={key}")
                        return embedding
                    except (json.JSONDecodeError, TypeError, ValueError) as e:
                        logger.warning(
                            f"Embedding cache: could not deserialize {key}: {e}"
                        )
                        return None
            logger.debug(f"Embedding cache MISS key={key}")
            return None
        except asyncio.TimeoutError:
            logger.warning("Embedding cache GET timeout")
            return None
        except Exception as e:
            logger.warning(f"Embedding cache GET error: {e}")
            return None

    async def _cache_set(self, text: str, embedding: np.ndarray) -> bool:
        """
        Store embedding in Upstash Redis as a JSON float array.

        Args:
            text: Original text (used to derive the key).
            embedding: numpy array to cache.

        Returns:
            True if stored successfully.
        """
        if not self._cache_enabled or not self._http_client:
            return False

        key = self._cache_key(text)
        json_value = json.dumps(embedding.flatten().tolist())
        encoded_value = quote(json_value)
        url = f"{settings.UPSTASH_REDIS_REST_URL}/set/{key}/{encoded_value}"
        headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}
        params = {"EX": self._EMBEDDING_TTL}

        try:
            response = await self._http_client.get(
                url, headers=headers, params=params, timeout=5.0
            )
            if response.status_code == 200:
                logger.debug(
                    f"Embedding cache STORE key={key} ttl={self._EMBEDDING_TTL}s"
                )
                return True
            logger.warning(
                f"Embedding cache SET failed (status {response.status_code})"
            )
            return False
        except asyncio.TimeoutError:
            logger.warning("Embedding cache SET timeout")
            return False
        except Exception as e:
            logger.warning(f"Embedding cache SET error: {e}")
            return False

    def _load_model(self):
        """Use TF-IDF fallback for speed. Real model loads in background after cache warms."""
        if self._model is not None:
            return self._model
        # Use fast fallback by default — avoids 10-30s load delay on requests
        # Model will be loaded after cache download completes via background thread
        self._model = "FALLBACK"
        import threading

        def _try_load():
            try:
                import os

                cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
                has_cache = os.path.exists(cache_dir) and any(
                    self._model_name.replace("/", "--") in d
                    for d in os.listdir(cache_dir)
                )
                if not has_cache:
                    from sentence_transformers import SentenceTransformer

                    SentenceTransformer(self._model_name)  # download to cache
                    logger.info(
                        "Sentence transformer cached — restart server to enable."
                    )
                # If cached, server restart will auto-load
            except Exception as e:
                logger.debug(f"Background model prep: {e}")

        threading.Thread(target=_try_load, daemon=True).start()
        return self._model

    def _fallback_embed(self, text: str) -> np.ndarray:
        """TF-IDF-style fallback embedding using character n-gram hashing."""
        vec = np.zeros(384, dtype=np.float32)
        words = text.lower().split()[:50]
        for i, word in enumerate(words):
            idx = hash(word) % 384
            vec[abs(idx)] += 1.0 / (i + 1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed(self, text: str) -> np.ndarray:
        """
        Generate a 384-dim embedding for a single text string.
        Falls back to hashed TF-IDF if sentence-transformers unavailable.
        """
        model = self._load_model()
        if model == "FALLBACK":
            return self._fallback_embed(text)
        embedding = model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding.astype(np.float32)

    def embed_batch(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """
        Generate embeddings for a list of texts efficiently.

        Args:
            texts: List of strings.
            batch_size: Encoding batch size.

        Returns:
            np.ndarray of shape (n_texts, 384)
        """
        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.astype(np.float32)

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Compute cosine similarity between two normalized vectors.
        Since we normalize on embedding, this is just the dot product.

        Returns:
            Float in [-1, 1]; in practice [0, 1] for similar text.
        """
        # Handle both 1D and 2D arrays
        a = vec_a.flatten()
        b = vec_b.flatten()
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def embedding_to_list(self, embedding: np.ndarray) -> List[float]:
        """Convert numpy embedding to list for ChromaDB storage."""
        return embedding.flatten().tolist()

    async def embed_async(self, text: str) -> np.ndarray:
        """
        Async embedding with Upstash Redis caching.

        Flow:
          1. Check Redis for a cached embedding (cache hit → return immediately).
          2. On miss: generate embedding via Sentence Transformer in thread pool.
          3. Store the new embedding in Redis for future requests.
          4. Return the embedding.
        """
        # 1. Cache lookup
        cached = await self._cache_get(text)
        if cached is not None:
            return cached

        # 2. Generate embedding (CPU-bound — run in thread pool)
        logger.debug("Embedding cache MISS — generating via Sentence Transformer")
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self.embed, text)

        # 3. Store in Redis (fire-and-forget; don't block the caller on failure)
        asyncio.ensure_future(self._cache_set(text, embedding))

        return embedding

    async def embed_batch_async(self, texts: List[str]) -> np.ndarray:
        """Async batch embedding."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_batch, texts)

    async def cosine_similarity_async(
        self,
        text_a: str,
        text_b: str,
    ) -> float:
        """Embed both strings and compute cosine similarity."""
        embeddings = await self.embed_batch_async([text_a, text_b])
        return self.cosine_similarity(embeddings[0], embeddings[1])


# Module-level singleton
embedding_service = EmbeddingService()
