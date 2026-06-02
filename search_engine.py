"""
Hybrid Search Engine — combines semantic (ChromaDB) + keyword (BM25) retrieval
with Reciprocal Rank Fusion and optional cross-encoder re-ranking.
"""

import hashlib
import logging
import time
from typing import Optional

from langchain_core.documents import Document as LCDocument

import config
from ingestion import ingestion_service

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Two-stage retrieval engine:
      1. Parallel semantic (ChromaDB) + BM25 keyword search
      2. Reciprocal Rank Fusion to merge result lists
      3. Optional cross-encoder re-ranking for precision
    """

    def __init__(self):
        self._bm25_indexes: dict[str, tuple] = {}  # index_key -> (bm25, corpus_docs)
        self._bm25_timestamps: dict[str, float] = {}
        self._reranker = None
        self._bm25_ttl = 300  # 5 minutes cache

    # ── BM25 Index Management ──────────────────────────────────────────────────

    def _build_bm25_index(self, index_key: str):
        """Build or refresh BM25 index from ChromaDB for a given key (e.g. 'user_1' or 'org_2')."""
        now = time.time()
        if (
            index_key in self._bm25_indexes
            and now - self._bm25_timestamps.get(index_key, 0) < self._bm25_ttl
        ):
            return

        try:
            if index_key.startswith("org_"):
                org_id = int(index_key.split("_")[1])
                collection = ingestion_service.get_org_collection(org_id)
            else:
                user_id = int(index_key.split("_")[1])
                collection = ingestion_service.get_collection(user_id)
                
            result = collection.get(include=["documents", "metadatas"])

            if not result or not result.get("documents"):
                self._bm25_indexes[index_key] = (None, [])
                self._bm25_timestamps[index_key] = now
                return

            documents = result["documents"]
            metadatas = result["metadatas"] or [{}] * len(documents)

            # Build LangChain Document objects for consistent return type
            corpus_docs = []
            tokenized_corpus = []
            for text, meta in zip(documents, metadatas):
                if text:
                    corpus_docs.append(LCDocument(page_content=text, metadata=meta or {}))
                    tokenized_corpus.append(text.lower().split())

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
        """Invalidate cached BM25 index."""
        self._bm25_indexes.pop(f"user_{user_id}", None)
        self._bm25_timestamps.pop(f"user_{user_id}", None)
        if org_id:
            self._bm25_indexes.pop(f"org_{org_id}", None)
            self._bm25_timestamps.pop(f"org_{org_id}", None)

    # ── BM25 Search ────────────────────────────────────────────────────────────

    def _bm25_search(self, query: str, index_key: str, k: int = 10) -> list[tuple[LCDocument, float]]:
        """Search using BM25 keyword matching. Returns (doc, score) pairs."""
        self._build_bm25_index(index_key)
        bm25, corpus_docs = self._bm25_indexes.get(index_key, (None, []))

        if bm25 is None or not corpus_docs:
            return []

        try:
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)

            # Get top-k by score
            scored = list(zip(corpus_docs, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:k]
        except Exception as exc:
            logger.warning("BM25 search failed: %s", exc)
            return []

    # ── Semantic Search ────────────────────────────────────────────────────────

    def _semantic_search(
        self, query: str, user_id: int, org_id: Optional[int] = None, k: int = 10,
        document_filter: Optional[list[str]] = None,
    ) -> list[LCDocument]:
        """Search using ChromaDB semantic similarity across user and org collections."""
        search_kwargs = {"k": k}
        if document_filter:
            if len(document_filter) == 1:
                search_kwargs["filter"] = {"source": document_filter[0]}
            else:
                search_kwargs["filter"] = {"source": {"$in": document_filter}}

        user_docs = []
        try:
            collection = ingestion_service.get_collection(user_id)
            user_docs = collection.similarity_search(query, **search_kwargs)
        except Exception as exc:
            logger.warning("User semantic search failed: %s", exc)

        org_docs = []
        if org_id:
            try:
                collection = ingestion_service.get_org_collection(org_id)
                org_docs = collection.similarity_search(query, **search_kwargs)
            except Exception as exc:
                logger.warning("Org semantic search failed: %s", exc)

        combined = user_docs + org_docs
        return combined[:k]

    # ── Reciprocal Rank Fusion ─────────────────────────────────────────────────

    def _reciprocal_rank_fusion(
        self,
        semantic_results: list[LCDocument],
        bm25_results: list[tuple[LCDocument, float]],
        k_constant: int = 60,
    ) -> list[LCDocument]:
        """
        Merge two ranked lists using Reciprocal Rank Fusion.
        RRF score = sum( 1 / (k + rank) ) across all lists.
        """
        scores: dict[str, float] = {}
        doc_map: dict[str, LCDocument] = {}

        def doc_key(doc: LCDocument) -> str:
            return hashlib.md5(doc.page_content.encode()).hexdigest()

        # Score semantic results
        for rank, doc in enumerate(semantic_results):
            key = doc_key(doc)
            rrf = config.SEMANTIC_WEIGHT / (k_constant + rank + 1)
            scores[key] = scores.get(key, 0) + rrf
            doc_map[key] = doc

        # Score BM25 results
        for rank, (doc, _bm25_score) in enumerate(bm25_results):
            key = doc_key(doc)
            rrf = config.BM25_WEIGHT / (k_constant + rank + 1)
            scores[key] = scores.get(key, 0) + rrf
            if key not in doc_map:
                doc_map[key] = doc

        # Sort by combined RRF score
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [doc_map[k] for k in sorted_keys]

    # ── Cross-Encoder Re-ranking ───────────────────────────────────────────────

    def _get_reranker(self):
        """Lazy-load the cross-encoder re-ranker."""
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder(config.RERANKER_MODEL_NAME, max_length=512)
                logger.info("Loaded cross-encoder: %s", config.RERANKER_MODEL_NAME)
            except Exception as exc:
                logger.warning("Failed to load cross-encoder: %s", exc)
                self._reranker = False  # Mark as unavailable
        return self._reranker if self._reranker is not False else None

    def _rerank(self, query: str, docs: list[LCDocument], top_k: int) -> list[tuple[LCDocument, float]]:
        """Re-rank documents using cross-encoder. Returns (doc, score) pairs."""
        if not docs:
            return []

        reranker = self._get_reranker()
        if reranker is None:
            # No re-ranker available, return docs with dummy scores
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

    def search(
        self,
        query: str,
        user_id: int,
        org_id: Optional[int] = None,
        k: int = config.RETRIEVAL_K,
        document_filter: Optional[list[str]] = None,
    ) -> tuple[list[LCDocument], dict]:
        """
        Full hybrid search pipeline:
          1. Semantic + BM25 retrieval
          2. Reciprocal Rank Fusion
          3. Cross-encoder re-ranking

        Returns: (ranked_documents, search_metadata)
        """
        metadata = {
            "search_method": "semantic",
            "hybrid_used": False,
            "reranker_used": False,
            "semantic_count": 0,
            "bm25_count": 0,
            "rerank_scores": [],
        }

        candidates_k = config.HYBRID_CANDIDATES if config.HYBRID_SEARCH_ENABLED else k

        # 1. Semantic search
        semantic_results = self._semantic_search(query, user_id, org_id, k=candidates_k, document_filter=document_filter)
        metadata["semantic_count"] = len(semantic_results)

        if not config.HYBRID_SEARCH_ENABLED or document_filter:
            # Skip BM25 when filtering by specific documents (semantic is better for that)
            merged = semantic_results
        else:
            # 2. BM25 search
            bm25_results_user = self._bm25_search(query, f"user_{user_id}", k=candidates_k)
            bm25_results_org = []
            if org_id:
                bm25_results_org = self._bm25_search(query, f"org_{org_id}", k=candidates_k)
                
            bm25_results = bm25_results_user + bm25_results_org
            bm25_results.sort(key=lambda x: x[1], reverse=True)
            bm25_results = bm25_results[:candidates_k]
            
            metadata["bm25_count"] = len(bm25_results)

            if bm25_results:
                # 3. Reciprocal Rank Fusion
                merged = self._reciprocal_rank_fusion(
                    semantic_results, bm25_results, config.RRF_CONSTANT,
                )
                metadata["search_method"] = "hybrid"
                metadata["hybrid_used"] = True
            else:
                merged = semantic_results

        # 4. Re-ranking
        if config.RERANKER_ENABLED and merged:
            reranked = self._rerank(query, merged, top_k=k)
            metadata["reranker_used"] = True
            metadata["rerank_scores"] = [round(s, 4) for _, s in reranked]
            final_docs = [doc for doc, _ in reranked]
        else:
            final_docs = merged[:k]

        return final_docs, metadata

    def search_document(
        self, query: str, user_id: int, document_name: str, k: int = 3, org_id: Optional[int] = None,
    ) -> list[LCDocument]:
        """Search within a specific document (for clause extraction/comparison)."""
        docs, _ = self.search(query, user_id, org_id=org_id, k=k, document_filter=[document_name])
        return docs


# Singleton
search_engine = HybridSearchEngine()
