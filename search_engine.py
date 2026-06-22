import hashlib
import logging
import time
from typing import Optional

from langchain_core.documents import Document as LCDocument

import config
from ingestion import ingestion_service
from database import DocumentChunk, async_session_factory
from sqlalchemy import select, or_

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    def __init__(self):
        self._bm25_indexes: dict[str, tuple] = {}
        self._bm25_timestamps: dict[str, float] = {}
        self._reranker = None
        self._bm25_ttl = 300

    # ── BM25 Index Management ──────────────────────────────────────────────────

    async def _build_bm25_index(self, index_key: str):
        now = time.time()
        if (
            index_key in self._bm25_indexes
            and now - self._bm25_timestamps.get(index_key, 0) < self._bm25_ttl
        ):
            return

        try:
            parts = index_key.split("_")
            user_id = int(parts[1])
            org_id = int(parts[1]) if parts[0] == "org" else None

            async with async_session_factory() as session:
                if index_key.startswith("org_"):
                    chunks = await ingestion_service.get_all_chunks(session, user_id, org_id=org_id)
                else:
                    chunks = await ingestion_service.get_all_chunks(session, user_id)

                if not chunks:
                    self._bm25_indexes[index_key] = (None, [])
                    self._bm25_timestamps[index_key] = now
                    return

                corpus_docs = []
                tokenized_corpus = []
                for c in chunks:
                    if c.content:
                        corpus_docs.append(LCDocument(
                            page_content=c.content,
                            metadata=__import__("json").loads(c.metadata_json) if c.metadata_json else {"source": c.source, "chunk_index": c.chunk_index},
                        ))
                        tokenized_corpus.append(c.content.lower().split())

                if not tokenized_corpus:
                    self._bm25_indexes[index_key] = (None, [])
                    self._bm25_timestamps[index_key] = now
                    return

                from rank_bm25 import BM25Okapi
                bm25 = BM25Okapi(tokenized_corpus)

                self._bm25_indexes[index_key] = (bm25, corpus_docs)
                self._bm25_timestamps[index_key] = now
                logger.info("Built BM25 index for %s: %d documents", index_key, len(corpus_docs))

        except Exception as exc:
            logger.warning("Failed to build BM25 index for %s: %s", index_key, exc)
            self._bm25_indexes[index_key] = (None, [])
            self._bm25_timestamps[index_key] = now

    def invalidate_bm25_cache(self, user_id: int, org_id: Optional[int] = None):
        self._bm25_indexes.pop(f"user_{user_id}", None)
        self._bm25_timestamps.pop(f"user_{user_id}", None)
        if org_id:
            self._bm25_indexes.pop(f"org_{org_id}", None)
            self._bm25_timestamps.pop(f"org_{org_id}", None)

    # ── BM25 Search ────────────────────────────────────────────────────────────

    def _bm25_search(self, query: str, index_key: str, k: int = 10) -> list[tuple[LCDocument, float]]:
        bm25, corpus_docs = self._bm25_indexes.get(index_key, (None, []))

        if bm25 is None or not corpus_docs:
            return []

        try:
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)

            scored = list(zip(corpus_docs, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:k]
        except Exception as exc:
            logger.warning("BM25 search failed: %s", exc)
            return []

    # ── Semantic Search (pgvector) ──────────────────────────────────────────────

    async def _semantic_search(
        self, query: str, user_id: int, org_id: Optional[int] = None, k: int = 10,
        document_filter: Optional[list[str]] = None,
    ) -> list[LCDocument]:
        return await ingestion_service.search_similar(
            query, user_id, k=k, org_id=org_id, document_filter=document_filter,
        )

    # ── Reciprocal Rank Fusion ─────────────────────────────────────────────────

    def _reciprocal_rank_fusion(
        self,
        semantic_results: list[LCDocument],
        bm25_results: list[tuple[LCDocument, float]],
        k_constant: int = 60,
    ) -> list[LCDocument]:
        scores: dict[str, float] = {}
        doc_map: dict[str, LCDocument] = {}

        def doc_key(d: LCDocument) -> str:
            return hashlib.md5(d.page_content.encode()).hexdigest()

        for rank, doc in enumerate(semantic_results):
            key = doc_key(doc)
            rrf = config.SEMANTIC_WEIGHT / (k_constant + rank + 1)
            scores[key] = scores.get(key, 0) + rrf
            doc_map[key] = doc

        for rank, (doc, _bm25_score) in enumerate(bm25_results):
            key = doc_key(doc)
            rrf = config.BM25_WEIGHT / (k_constant + rank + 1)
            scores[key] = scores.get(key, 0) + rrf
            if key not in doc_map:
                doc_map[key] = doc

        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [doc_map[k] for k in sorted_keys]

    # ── Cross-Encoder Re-ranking ───────────────────────────────────────────────

    def _get_reranker(self):
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder(config.RERANKER_MODEL_NAME, max_length=512)
                logger.info("Loaded cross-encoder: %s", config.RERANKER_MODEL_NAME)
            except Exception as exc:
                logger.warning("Failed to load cross-encoder: %s", exc)
                self._reranker = False
        return self._reranker if self._reranker is not False else None

    def _rerank(self, query: str, docs: list[LCDocument], top_k: int) -> list[tuple[LCDocument, float]]:
        if not docs:
            return []

        reranker = self._get_reranker()
        if reranker is None:
            return [(doc, 1.0 - i * 0.05) for i, doc in enumerate(docs[:top_k])]

        try:
            pairs = [(query, doc.page_content) for doc in docs]
            scores = reranker.predict(pairs)

            scored_docs = list(zip(docs, scores.tolist()))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            return scored_docs[:top_k]
        except Exception as exc:
            logger.warning("Re-ranking failed: %s", exc)
            return [(doc, 1.0 - i * 0.05) for i, doc in enumerate(docs[:top_k])]

    # ── Main Search API ────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        user_id: int,
        org_id: Optional[int] = None,
        k: int = config.RETRIEVAL_K,
        document_filter: Optional[list[str]] = None,
    ) -> tuple[list[LCDocument], dict]:
        metadata = {
            "search_method": "semantic",
            "hybrid_used": False,
            "reranker_used": False,
            "semantic_count": 0,
            "bm25_count": 0,
            "rerank_scores": [],
        }

        candidates_k = config.HYBRID_CANDIDATES if config.HYBRID_SEARCH_ENABLED else k

        semantic_results = await self._semantic_search(query, user_id, org_id, k=candidates_k, document_filter=document_filter)
        metadata["semantic_count"] = len(semantic_results)

        if not config.HYBRID_SEARCH_ENABLED or document_filter:
            merged = semantic_results
        else:
            bm25_results_user = self._bm25_search(query, f"user_{user_id}", k=candidates_k)

            bm25_results_org = []
            if org_id:
                bm25_results_org = self._bm25_search(query, f"org_{org_id}", k=candidates_k)

            bm25_results = bm25_results_user + bm25_results_org
            bm25_results.sort(key=lambda x: x[1], reverse=True)
            bm25_results = bm25_results[:candidates_k]

            metadata["bm25_count"] = len(bm25_results)

            if bm25_results:
                merged = self._reciprocal_rank_fusion(
                    semantic_results, bm25_results, config.RRF_CONSTANT,
                )
                metadata["search_method"] = "hybrid"
                metadata["hybrid_used"] = True
            else:
                merged = semantic_results

        if config.RERANKER_ENABLED and merged:
            reranked = self._rerank(query, merged, top_k=k)
            metadata["reranker_used"] = True
            metadata["rerank_scores"] = [round(s, 4) for _, s in reranked]
            final_docs = [doc for doc, _ in reranked]
        else:
            final_docs = merged[:k]

        return final_docs, metadata

    async def search_document(
        self, query: str, user_id: int, document_name: str, k: int = 3, org_id: Optional[int] = None,
    ) -> list[LCDocument]:
        docs, _ = await self.search(query, user_id, org_id=org_id, k=k, document_filter=[document_name])
        return docs


search_engine = HybridSearchEngine()
