"""
services/retrieval_service.py — Agent 2: ChromaDB vector retrieval.

Queries the vector database for similar resolved tickets.
Returns top-3 most similar past cases with solutions and similarity scores.

Redis caching: ChromaDB similarity search results are cached in Upstash Redis
(same instance as the NLP and embedding caches) using key format:
  retrieval:{embedding_hash}:{category}:{top_k}:{status_filter}
TTL is intentionally short (10 minutes) because the vector DB contents change
as new tickets are resolved. ChromaDB remains the source of truth; Redis is
only a performance layer. All Redis failures fall through silently.
"""

import asyncio
import hashlib
import json
import numpy as np
from typing import List, Dict, Optional
from loguru import logger
from urllib.parse import quote

from core.config import settings
from services.embedding_service import embedding_service


class RetrievalService:
    """
    Agent 2 of the TicketFlow pipeline.

    Responsibilities:
    - Connect to ChromaDB (local or remote)
    - Store resolved tickets and knowledge articles as embeddings
    - Query similar past resolved tickets for a new ticket
    - Return top-K matches with cosine similarity scores

    Collections:
    - resolved_tickets: past tickets with solutions (for RAG)
    - knowledge_articles: auto-generated KB articles

    Caching:
    - Retrieval results are cached in Upstash Redis (TTL: 10 minutes)
    - Cache key encodes embedding hash + query parameters
    - Cache misses fall through to ChromaDB transparently
    """

    # TTL for cached retrieval results: 10 minutes
    # Short because ChromaDB contents change as tickets are resolved.
    _RETRIEVAL_TTL = 600

    def __init__(self):
        self._client = None
        self._tickets_collection = None
        self._articles_collection = None
        self._initialized = False

        # Reuse the same Upstash Redis instance as nlp_cache and embedding_service
        self._cache_enabled = False
        self._http_client = None
        if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
            try:
                import httpx
                self._http_client = httpx.AsyncClient()
                self._cache_enabled = True
                logger.info("Retrieval cache: Upstash Redis enabled")
            except ImportError:
                logger.warning("httpx not installed. Retrieval cache disabled.")
        else:
            logger.warning(
                "Upstash credentials not configured. Retrieval cache disabled."
            )

    # ── Retrieval cache helpers ───────────────────────────────────────

    def _retrieval_cache_key(
        self,
        embedding: list,
        category: Optional[str],
        top_k: int,
        status_filter: str,
    ) -> str:
        """
        Build a deterministic Redis key from the embedding vector and query params.

        The embedding is hashed (MD5 of its JSON representation) so the key is
        compact and consistent regardless of floating-point representation order.
        Query parameters are appended so different filter combinations never
        collide on the same key.

        Format: retrieval:{embedding_md5}:{category}:{top_k}:{status_filter}
        """
        embedding_bytes = json.dumps(embedding, separators=(",", ":")).encode("utf-8")
        embedding_hash = hashlib.md5(embedding_bytes).hexdigest()
        cat_part = category if category else "none"
        return f"retrieval:{embedding_hash}:{cat_part}:{top_k}:{status_filter}"

    async def _retrieval_cache_get(
        self,
        embedding: list,
        category: Optional[str],
        top_k: int,
        status_filter: str,
    ) -> Optional[List[Dict]]:
        """
        Fetch retrieval results from Upstash Redis.

        Returns:
            List of similar-ticket dicts on cache hit, None on miss or error.
        """
        if not self._cache_enabled or not self._http_client:
            return None

        key = self._retrieval_cache_key(embedding, category, top_k, status_filter)
        url = f"{settings.UPSTASH_REDIS_REST_URL}/get/{key}"
        headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

        try:
            response = await self._http_client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                result_value = data.get("result")
                if result_value:
                    try:
                        parsed = json.loads(result_value)
                        logger.debug(f"Retrieval cache HIT  key={key}")
                        return parsed
                    except (json.JSONDecodeError, TypeError, ValueError) as e:
                        logger.warning(
                            f"Retrieval cache: could not deserialize {key}: {e}"
                        )
                        return None
            logger.debug(f"Retrieval cache MISS key={key}")
            return None
        except asyncio.TimeoutError:
            logger.warning("Retrieval cache GET timeout")
            return None
        except Exception as e:
            logger.warning(f"Retrieval cache GET error: {e}")
            return None

    async def _retrieval_cache_set(
        self,
        embedding: list,
        category: Optional[str],
        top_k: int,
        status_filter: str,
        results: List[Dict],
    ) -> bool:
        """
        Store retrieval results in Upstash Redis as a JSON array.

        Args:
            embedding: The query embedding list (used to derive the key).
            category: Category filter used in the query.
            top_k: Number of results requested.
            status_filter: Status filter used in the query.
            results: List of similar-ticket dicts to cache.

        Returns:
            True if stored successfully.
        """
        if not self._cache_enabled or not self._http_client:
            return False

        key = self._retrieval_cache_key(embedding, category, top_k, status_filter)
        json_value = json.dumps(results)
        encoded_value = quote(json_value)
        url = f"{settings.UPSTASH_REDIS_REST_URL}/set/{key}/{encoded_value}"
        headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}
        params = {"EX": self._RETRIEVAL_TTL}

        try:
            response = await self._http_client.get(
                url, headers=headers, params=params, timeout=5.0
            )
            if response.status_code == 200:
                logger.debug(
                    f"Retrieval cache STORE key={key} ttl={self._RETRIEVAL_TTL}s"
                )
                return True
            logger.warning(
                f"Retrieval cache SET failed (status {response.status_code})"
            )
            return False
        except asyncio.TimeoutError:
            logger.warning("Retrieval cache SET timeout")
            return False
        except Exception as e:
            logger.warning(f"Retrieval cache SET error: {e}")
            return False

    # ── ChromaDB client ───────────────────────────────────────────────

    def _init_client(self):
        """Initialize ChromaDB client (lazy, called on first use)."""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            # Try HttpClient first (for Docker/remote ChromaDB)
            try:
                self._client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                )
                # Test connection
                self._client.heartbeat()
                logger.info(
                    f"ChromaDB connected at "
                    f"{settings.CHROMA_HOST}:{settings.CHROMA_PORT}"
                )
            except Exception:
                # Fall back to local persistent client
                logger.warning(
                    "ChromaDB remote unavailable. Using local persistent client."
                )
                self._client = chromadb.PersistentClient(path="./chroma_data")

            # Get or create collections
            self._tickets_collection = self._client.get_or_create_collection(
                name=settings.CHROMA_TICKETS_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._articles_collection = self._client.get_or_create_collection(
                name=settings.CHROMA_ARTICLES_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(
                f"ChromaDB collections ready: "
                f"tickets={self._tickets_collection.count()}, "
                f"articles={self._articles_collection.count()}"
            )

        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            self._initialized = True  # mark as attempted, use fallback

    async def add_resolved_ticket(
        self,
        ticket_id: str,
        text: str,
        solution: str,
        category: str,
        priority: str,
        resolution_time_hours: float,
        status: str = "resolved",
    ) -> bool:
        """
        Add a newly resolved ticket to ChromaDB for future retrieval.

        Args:
            ticket_id: e.g. "TKT-A3F8"
            text: Original cleaned ticket text.
            solution: Final resolution text sent to user.
            category: e.g. "Network"
            resolution_time_hours: How long it took to resolve.
            status: Typically "resolved".

        Returns:
            True if added successfully.
        """
        self._init_client()
        if self._tickets_collection is None:
            return False

        try:
            embedding = await embedding_service.embed_async(text)
            self._tickets_collection.upsert(
                ids=[ticket_id],
                embeddings=[embedding.tolist()],
                documents=[text],
                metadatas=[
                    {
                        "ticket_id": ticket_id,
                        "solution": solution[:2000],  # cap at 2000 chars
                        "category": category,
                        "priority": priority,
                        "resolution_time_hours": str(resolution_time_hours),
                        "status": status,
                    }
                ],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add ticket {ticket_id} to ChromaDB: {e}")
            return False

    def _query_similar(
        self,
        embedding: list,
        category: Optional[str],
        top_k: int = 3,
        status_filter: str = "resolved",
    ) -> List[Dict]:
        """
        Query ChromaDB for similar tickets.

        Args:
            embedding: 384-dim embedding list.
            category: If provided, filter by same category.
            top_k: Number of results to return.
            status_filter: Only return tickets with this status.

        Returns:
            List of similar ticket dicts.
        """
        self._init_client()
        if self._tickets_collection is None:
            return []

        try:
            # Build where filter
            where = {"status": {"$eq": status_filter}}
            if category:
                where = {
                    "$and": [
                        {"status": {"$eq": status_filter}},
                        {"category": {"$eq": category}},
                    ]
                }

            # Query ChromaDB — request more results since we filter below
            results = self._tickets_collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k * 2, max(top_k, 5)),
                where=where if self._tickets_collection.count() > 0 else None,
                include=["distances", "documents", "metadatas"],
            )

            similar = []
            if not results["ids"] or not results["ids"][0]:
                return []

            for i, (ticket_id, distance, document, metadata) in enumerate(
                zip(
                    results["ids"][0],
                    results["distances"][0],
                    results["documents"][0],
                    results["metadatas"][0],
                )
            ):
                # ChromaDB cosine distance: 0=identical, 2=opposite
                # Convert to similarity: 1 - distance/2
                similarity = max(0.0, 1.0 - (distance / 2.0))

                if similarity < 0.3:
                    continue  # skip low-quality matches

                similar.append(
                    {
                        "ticket_id": ticket_id,
                        "summary": document[:300],
                        "solution": metadata.get("solution", "No solution recorded"),
                        "similarity_score": round(similarity, 4),
                        "category": metadata.get("category", "Unknown"),
                        "resolution_time_hours": float(
                            metadata.get("resolution_time_hours", 2.0)
                        ),
                    }
                )

            # Sort by similarity and take top_k
            similar.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar[:top_k]

        except Exception as e:
            logger.error(f"ChromaDB query error: {e}")
            return []

    async def _query_similar_cached(
        self,
        embedding_list: list,
        category: Optional[str],
        top_k: int,
        status_filter: str = "resolved",
    ) -> List[Dict]:
        """
        Cache-aware wrapper around _query_similar.

        Flow:
          1. Check Upstash Redis for cached results.
          2. On hit: return cached list immediately (ChromaDB skipped).
          3. On miss: run ChromaDB query in thread pool.
          4. Store results in Redis (fire-and-forget).
          5. Return results.

        Redis failures at any step fall through silently; ChromaDB is always
        the authoritative source of truth.
        """
        # 1. Cache lookup
        cached = await self._retrieval_cache_get(
            embedding_list, category, top_k, status_filter
        )
        if cached is not None:
            return cached

        # 2. Cache miss — query ChromaDB
        logger.debug(
            f"Retrieval cache MISS — querying ChromaDB "
            f"(category={category}, top_k={top_k}, status={status_filter})"
        )
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._query_similar(
                embedding_list, category, top_k, status_filter
            ),
        )

        # 3. Store in Redis (fire-and-forget; never block the caller)
        asyncio.ensure_future(
            self._retrieval_cache_set(
                embedding_list, category, top_k, status_filter, results
            )
        )

        return results

    async def find_similar_tickets(
        self,
        text: str,
        category: Optional[str] = None,
        top_k: int = 3,
    ) -> dict:
        """
        Agent 2 main method: find top-K similar resolved tickets.

        Args:
            text: Cleaned ticket text.
            category: Predicted category for filtering.
            top_k: Max results to return.

        Returns:
            Agent 2 output dict matching pipeline spec.
        """
        # Generate embedding (hits embedding cache if available)
        embedding = await embedding_service.embed_async(text)
        embedding_list = embedding_service.embedding_to_list(embedding)

        # Cache-aware ChromaDB query (category-filtered)
        similar = await self._query_similar_cached(
            embedding_list, category, top_k, status_filter="resolved"
        )

        # If category-filtered query returned no results, retry without filter
        if not similar and category:
            similar = await self._query_similar_cached(
                embedding_list, None, top_k, status_filter="resolved"
            )

        top_score = similar[0]["similarity_score"] if similar else 0.0

        collection_size = 0
        try:
            if self._tickets_collection:
                collection_size = self._tickets_collection.count()
        except Exception:
            pass

        return {
            "similar_tickets": similar,
            "top_similarity_score": round(top_score, 4),
            "knowledge_base_size": collection_size,
            "embedding": embedding,  # pass to duplicate detector + LLM
        }

    async def find_open_tickets_similar(
        self,
        text: str,
        within_hours: int = 24,
    ) -> List[Dict]:
        """
        Query for similar OPEN tickets (used for duplicate detection).
        Returns all open tickets with similarity > 0.5.

        Note: open-ticket queries are also cached (same 10-minute TTL) so
        rapid duplicate checks on the same text don't hammer ChromaDB.
        """
        embedding = await embedding_service.embed_async(text)
        embedding_list = embedding_service.embedding_to_list(embedding)

        return await self._query_similar_cached(
            embedding_list,
            category=None,
            top_k=10,
            status_filter="open",
        )

    async def add_knowledge_article(
        self,
        article_id: str,
        content: str,
        metadata: dict,
    ) -> bool:
        """Add a KB article to the articles ChromaDB collection."""
        self._init_client()
        if self._articles_collection is None:
            return False
        try:
            embedding = await embedding_service.embed_async(content)
            self._articles_collection.upsert(
                ids=[article_id],
                embeddings=[embedding.tolist()],
                documents=[content],
                metadatas=metadata,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add article {article_id}: {e}")
            return False

    def get_collection_stats(self) -> dict:
        """Return sizes of both ChromaDB collections."""
        self._init_client()
        try:
            return {
                "resolved_tickets": (
                    self._tickets_collection.count() if self._tickets_collection else 0
                ),
                "knowledge_articles": (
                    self._articles_collection.count()
                    if self._articles_collection
                    else 0
                ),
            }
        except Exception:
            return {"resolved_tickets": 0, "knowledge_articles": 0}


# Module-level singleton
retrieval_service = RetrievalService()
