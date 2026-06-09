"""
RAG Chain — Full retrieval-augmented generation pipeline with:
  - Multi-model LLM support
  - Hybrid search (semantic + BM25 + re-ranking)
  - Confidence scoring
  - Risk flagging
"""

import logging
import time
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

import config
from database import Analytics, async_session_factory
from memory_service import memory_service
from llm_provider import llm_provider
from search_engine import search_engine
from language_utils import detect_language, get_language_name

logger = logging.getLogger(__name__)


class RAGChain:
    def __init__(self):
        pass  # LLMs are now created via llm_provider on-demand

    # ── 1. Question rewriter ───────────────────────────────────────────────────
    async def rewriteQuestion(
        self, question: str, recent_messages: list[dict], provider: Optional[str] = None,
    ) -> str:
        if len(recent_messages) < 2:
            return question

        last_four = recent_messages[-4:]
        history = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in last_four
        )
        prompt = (
            "You are a legal search query optimizer.\n"
            "Given the conversation history below and a follow-up question, "
            "rewrite the follow-up question so it is fully self-contained, specific, "
            "and optimized for searching legal documents. "
            "Return ONLY the rewritten question with no preamble or extra text.\n\n"
            f"Conversation History:\n{history}\n\n"
            f"Follow-up Question: {question}\n\n"
            "Rewritten Question:"
        )
        try:
            llm = llm_provider.get_llm(provider, temperature=0.1)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip() or question
        except Exception:
            return question

    # ── 2. Chunk retrieval (hybrid search) ─────────────────────────────────────
    def retrieveChunks(
        self, question: str, user_id: int, org_id: Optional[int] = None,
        document_filter: Optional[list[str]] = None,
    ) -> tuple[list, dict]:
        """Retrieve chunks using hybrid search engine. Returns (docs, search_metadata)."""
        return search_engine.search(
            query=question,
            user_id=user_id,
            org_id=org_id,
            k=config.RETRIEVAL_K,
            document_filter=document_filter,
        )

    # ── 2b. Filtered document search ───────────────────────────────────────────
    def _search_document(self, collection, query: str, document_name: str, k: int) -> list:
        """Search within a specific document (backward-compatible wrapper)."""
        try:
            return collection.similarity_search(query, k=k, filter={"source": document_name})
        except Exception:
            return []

    # ── 3. Confidence scoring ──────────────────────────────────────────────────
    async def _calculate_confidence(
        self, chunks: list, search_metadata: dict, question: str, answer: str,
        provider: Optional[str] = None,
    ) -> dict:
        """
        Calculate confidence score (0-100) based on:
          - Retrieval relevance (cross-encoder scores from re-ranking)
          - Source coverage (number of unique documents)
          - Answer coherence (LLM self-assessment)
        """
        if not chunks:
            return {"score": 0, "label": "Low", "breakdown": {}}

        # 1. Retrieval relevance (from re-ranker scores)
        rerank_scores = search_metadata.get("rerank_scores", [])
        if rerank_scores:
            # Normalize: cross-encoder scores can range roughly -10 to 10
            avg_rerank = sum(rerank_scores) / len(rerank_scores)
            # Map to 0-1 using sigmoid-like scaling
            retrieval_score = max(0.0, min(1.0, (avg_rerank + 5) / 15))
        else:
            # Fallback: assume decent relevance if we got results
            retrieval_score = 0.6 if chunks else 0.0

        # 2. Source coverage
        unique_sources = set()
        for doc in chunks:
            meta = doc.metadata or {}
            unique_sources.add(meta.get("source", ""))
        coverage_score = min(1.0, len(unique_sources) / max(1, config.RETRIEVAL_K))

        # 3. Answer coherence — quick LLM check
        coherence_score = 0.5  # default
        try:
            llm = llm_provider.get_memory_llm(temperature=0)
            coherence_prompt = (
                "Rate how well this answer addresses the question on a scale of 0.0 to 1.0. "
                "Respond with ONLY a decimal number.\n\n"
                f"Question: {question}\n"
                f"Answer (first 500 chars): {answer[:500]}\n\n"
                "Score:"
            )
            resp = await llm.ainvoke([HumanMessage(content=coherence_prompt)])
            parsed = float(resp.content.strip())
            coherence_score = max(0.0, min(1.0, parsed))
        except Exception:
            pass

        # Weighted combination
        raw = (
            0.5 * retrieval_score
            + 0.2 * coverage_score
            + 0.3 * coherence_score
        )
        score = round(raw * 100)

        if raw >= config.CONFIDENCE_HIGH_THRESHOLD:
            label = "High"
        elif raw >= config.CONFIDENCE_MEDIUM_THRESHOLD:
            label = "Medium"
        else:
            label = "Low"

        return {
            "score": score,
            "label": label,
            "breakdown": {
                "retrieval_relevance": round(retrieval_score * 100),
                "source_coverage": round(coverage_score * 100),
                "answer_coherence": round(coherence_score * 100),
            },
        }

    # ── 4. Answer generation ───────────────────────────────────────────────────
    async def generateAnswer(
        self,
        question: str,
        chunks: list,
        summary: str,
        long_term: str,
        provider: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
        firm_name: Optional[str] = None,
    ) -> str:
        if not chunks:
            context = (
                "No documents have been uploaded yet, or no relevant passages were found "
                "for this query. Please upload the relevant legal documents first."
            )
        else:
            parts = []
            for doc in chunks:
                meta = doc.metadata or {}
                source = meta.get("source", "Unknown Document")
                chunk_idx = meta.get("chunk_index", "?")
                parts.append(
                    f"[Document: {source}, Chunk: {chunk_idx}]\n{doc.page_content}"
                )
            context = "\n\n---\n\n".join(parts)

        system_tmpl = custom_system_prompt or config.LEGAL_SYSTEM_PROMPT
        detected_lang = detect_language(question) if config.ENABLE_MULTILINGUAL else "en"
        lang_name = get_language_name(detected_lang)
        if detected_lang == "en":
            lang_instruction = "Respond in English."
        else:
            lang_instruction = f"The user's question appears to be in {lang_name}. Respond in {lang_name} using proper legal terminology for that language. If quoting from documents, provide the quote in its original language followed by a translation."
        fmt_dict = {
            "firm_name": firm_name or config.FIRM_NAME,
            "context": context,
            "summary": summary,
            "long_term_memory": long_term,
            "language_instruction": lang_instruction,
        }

        try:
            system_content = system_tmpl.format(**fmt_dict)
        except Exception as exc:
            logger.warning(f"Failed to format custom system prompt: {exc}. Falling back to default.")
            system_content = config.LEGAL_SYSTEM_PROMPT.format(**fmt_dict)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system}"),
                ("human", "{question}"),
            ]
        )
        llm = llm_provider.get_llm(provider, temperature=0.1)
        chain = prompt | llm
        try:
            response = await chain.ainvoke(
                {"system": system_content, "question": question}
            )
            return response.content
        except Exception as exc:
            return f"An error occurred while generating the answer: {str(exc)}"

    # ── 5. Main query pipeline ─────────────────────────────────────────────────
    async def query(
        self,
        question: str,
        user_id: int,
        session_id: str,
        provider: Optional[str] = None,
        document_filter: Optional[list[str]] = None,
        org_id: Optional[int] = None,
    ) -> dict:
        start_ms = time.time() * 1000

        async with async_session_factory() as db_session:
            try:
                # Load org settings if org_id is provided
                custom_prompt = None
                firm_name = config.FIRM_NAME
                if org_id:
                    from sqlalchemy import select
                    from database import Organization
                    org_stmt = select(Organization).where(Organization.id == org_id)
                    org_res = await db_session.execute(org_stmt)
                    org = org_res.scalar_one_or_none()
                    if org:
                        custom_prompt = org.custom_system_prompt
                        firm_name = org.name

                # Memory loading
                recent_messages = await memory_service.loadRecentMessages(
                    db_session, user_id, session_id
                )
                summary = await memory_service.loadSummary(db_session, user_id, session_id)
                long_term = await memory_service.searchLongTermMemory(
                    db_session, user_id, question
                )

                # Question rewriting
                rewritten = await self.rewriteQuestion(question, recent_messages, provider)

                # Hybrid retrieval
                chunks, search_metadata = self.retrieveChunks(rewritten, user_id, org_id, document_filter)

                # Generation
                answer = await self.generateAnswer(
                    rewritten, chunks, summary, long_term, provider, custom_prompt, firm_name
                )

                # ── Risk flagging ──────────────────────────────────────────
                RISK_TERMS = [
                    "unlimited liability", "perpetual license", "irrevocable",
                    "auto-renewal", "automatic renewal", "unilateral modification",
                    "sole discretion", "non-compete", "non-solicitation",
                    "indemnify and hold harmless", "waiver of jury trial",
                    "class action waiver", "liquidated damages", "penalty clause",
                    "evergreen clause",
                ]
                risk_flags = []
                try:
                    combined_text = " ".join(doc.page_content for doc in chunks).lower()
                    found_terms = [t for t in RISK_TERMS if t in combined_text]
                    if found_terms:
                        risk_flags = found_terms
                        risk_llm = llm_provider.get_memory_llm(temperature=0)
                        risk_prompt = (
                            "You are a legal risk analyst. These potentially risky terms "
                            "were found in the document: " + ", ".join(found_terms) + ". "
                            "Briefly explain in 1-2 sentences why each term could be risky for the client."
                        )
                        risk_response = await risk_llm.ainvoke(
                            [HumanMessage(content=risk_prompt)]
                        )
                        answer += f"\n\n⚠️ Risk Alert\n{risk_response.content.strip()}"
                except Exception:
                    pass

                # ── Confidence scoring ─────────────────────────────────────
                confidence = await self._calculate_confidence(
                    chunks, search_metadata, question, answer, provider
                )

                # Save messages
                await memory_service.saveMessage(
                    db_session, user_id, session_id, "human", question
                )
                await memory_service.saveMessage(
                    db_session, user_id, session_id, "assistant", answer
                )

                elapsed = int(time.time() * 1000 - start_ms)

                analytics_entry = Analytics(
                    user_id=user_id,
                    question=question,
                    response_time_ms=elapsed,
                    sources_used=len(chunks),
                )
                db_session.add(analytics_entry)

                await db_session.commit()
            except Exception:
                await db_session.rollback()
                raise

        # Background memory extraction
        await memory_service.extractMemory(user_id, session_id, question, answer)

        # Build sources list
        sources = []
        for doc in chunks:
            meta = doc.metadata or {}
            sources.append(
                {
                    "document": meta.get("source", "Unknown"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "preview": doc.page_content[:250],
                }
            )

        return {
            "answer": answer,
            "sources": sources,
            "session_id": session_id,
            "response_time_ms": elapsed,
            "rewritten_question": rewritten,
            "risk_flags": risk_flags,
            "confidence": confidence,
            "provider": provider or config.DEFAULT_LLM_PROVIDER,
            "search_metadata": {
                "method": search_metadata.get("search_method", "semantic"),
                "hybrid_used": search_metadata.get("hybrid_used", False),
                "reranker_used": search_metadata.get("reranker_used", False),
            },
        }


    # ── 6. Streaming query pipeline ────────────────────────────────────────────
    async def query_stream(self, question: str, user_id: int, session_id: str):
        """
        Same as query() but yields the answer token by token as Server-Sent Events.
        Memory saving and analytics happen after the full answer is assembled.
        """
        import time
        start_ms = time.time() * 1000

        # Load memory — create own sessions
        async with async_session_factory() as db_session:
            try:
                recent_messages = await memory_service.loadRecentMessages(
                    db_session, user_id, session_id
                )
                summary = await memory_service.loadSummary(db_session, user_id, session_id)
                long_term = await memory_service.searchLongTermMemory(
                    db_session, user_id, question
                )
            except Exception:
                recent_messages = []
                summary = "No summary available."
                long_term = ""

        # Question rewriting
        rewritten = await self.rewriteQuestion(question, recent_messages)

        # Retrieve chunks
        chunks, search_metadata = self.retrieveChunks(rewritten, user_id)

        # Build context exactly like generateAnswer does
        if not chunks:
            context = "No documents found for this query. Please upload relevant legal documents."
        else:
            parts = []
            for doc in chunks:
                meta = doc.metadata or {}
                source = meta.get("source", "Unknown Document")
                chunk_idx = meta.get("chunk_index", "?")
                parts.append(f"[Document: {source}, Chunk: {chunk_idx}]\n{doc.page_content}")
            context = "\n\n---\n\n".join(parts)

        detected_lang = detect_language(question) if config.ENABLE_MULTILINGUAL else "en"
        lang_name = get_language_name(detected_lang)
        if detected_lang == "en":
            lang_instruction = "Respond in English."
        else:
            lang_instruction = f"The user's question appears to be in {lang_name}. Respond in {lang_name} using proper legal terminology for that language. If quoting from documents, provide the quote in its original language followed by a translation."

        system_content = config.LEGAL_SYSTEM_PROMPT.format(
            firm_name=config.FIRM_NAME,
            context=context,
            summary=summary,
            long_term_memory=long_term,
            language_instruction=lang_instruction,
        )

        # Stream from LLM provider
        from langchain_core.messages import SystemMessage, HumanMessage

        streaming_llm = llm_provider.get_llm(temperature=0.1, streaming=True)

        full_answer = ""
        import json

        # Yield metadata first as SSE
        sources = []
        for doc in chunks:
            meta = doc.metadata or {}
            sources.append({
                "document": meta.get("source", "Unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "preview": doc.page_content[:250],
            })

        yield f"data: {json.dumps({'type': 'meta', 'session_id': session_id, 'rewritten_question': rewritten, 'sources': sources})}\n\n"

        # Stream tokens
        try:
            async for chunk in streaming_llm.astream(
                [SystemMessage(content=system_content), HumanMessage(content=rewritten)]
            ):
                token = chunk.content
                if token:
                    full_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
        except Exception as e:
            error_msg = f"Streaming error: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            return

        # Risk flagging on completed answer
        risk_flags = []
        try:
            RISK_TERMS = [
                "unlimited liability", "perpetual license", "irrevocable",
                "auto-renewal", "automatic renewal", "unilateral modification",
                "sole discretion", "non-compete", "non-solicitation",
                "indemnify and hold harmless", "waiver of jury trial",
                "class action waiver", "liquidated damages", "penalty clause",
                "evergreen clause",
            ]
            combined_text = " ".join(doc.page_content for doc in chunks).lower()
            found_terms = [t for t in RISK_TERMS if t in combined_text]
            if found_terms:
                risk_flags = found_terms
                yield f"data: {json.dumps({'type': 'risk_flags', 'risk_flags': found_terms})}\n\n"
        except Exception:
            pass

        # Save memory after stream completes
        elapsed = int(time.time() * 1000 - start_ms)
        async with async_session_factory() as session:
            try:
                await memory_service.saveMessage(
                    session, user_id, session_id, "human", question
                )
                await memory_service.saveMessage(
                    session, user_id, session_id, "assistant", full_answer
                )

                from database import Analytics as AnalyticsModel
                analytics_entry = AnalyticsModel(
                    user_id=user_id,
                    question=question,
                    response_time_ms=elapsed,
                    sources_used=len(chunks),
                )
                session.add(analytics_entry)
                await session.commit()
            except Exception:
                await session.rollback()

        # Background memory extraction
        await memory_service.extractMemory(user_id, session_id, question, full_answer)

        yield f"data: {json.dumps({'type': 'done', 'response_time_ms': elapsed})}\n\n"


# Singleton
rag_chain = RAGChain()
