import json
import logging
import os
from typing import Optional

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import func, select, delete as sa_delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import Document, DocumentChunk, async_session_factory

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self):
        self._embeddings = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=config.EMBEDDING_MODEL_NAME,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    # ── Document chunk storage ──────────────────────────────────────────────────

    async def _store_chunks(
        self, session: AsyncSession, user_id: int, filename: str, chunks: list[str],
        metadatas: list[dict], org_id: Optional[int] = None,
    ) -> None:
        embeddings_list = self.embeddings.embed_documents(chunks)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings_list)):
            doc_chunk = DocumentChunk(
                user_id=user_id,
                org_id=org_id,
                chunk_index=i,
                content=chunk,
                embedding=emb,
                source=filename,
                metadata_json=json.dumps(metadatas[i]) if metadatas and i < len(metadatas) else None,
            )
            session.add(doc_chunk)

    async def _delete_chunks_by_source(self, session: AsyncSession, filename: str, user_id: int, org_id: Optional[int] = None) -> None:
        stmt = sa_delete(DocumentChunk).where(
            DocumentChunk.source == filename,
            DocumentChunk.user_id == user_id,
        )
        if org_id:
            stmt = stmt.where(DocumentChunk.org_id == org_id)
        await session.execute(stmt)

    async def search_similar(
        self, query: str, user_id: int, k: int = config.RETRIEVAL_K,
        org_id: Optional[int] = None, document_filter: Optional[list[str]] = None,
    ) -> list[LCDocument]:
        query_embedding = self.embeddings.embed_query(query)
        async with async_session_factory() as session:
            try:
                stmt = (
                    select(DocumentChunk)
                    .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                    .limit(k)
                )
                cond = (DocumentChunk.user_id == user_id)
                if org_id:
                    cond = or_(cond, DocumentChunk.org_id == org_id)
                if document_filter:
                    if len(document_filter) == 1:
                        cond = cond & (DocumentChunk.source == document_filter[0])
                    else:
                        cond = cond & (DocumentChunk.source.in_(document_filter))
                stmt = stmt.where(cond)
                result = await session.execute(stmt)
                rows = result.scalars().all()
                return [
                    LCDocument(
                        page_content=row.content,
                        metadata=json.loads(row.metadata_json) if row.metadata_json else {"source": row.source, "chunk_index": row.chunk_index},
                    )
                    for row in rows
                ]
            except Exception as exc:
                logger.warning("pgvector similarity search failed: %s", exc)
                return []

    async def get_chunks_by_source(
        self, session: AsyncSession, user_id: int, source: str, org_id: Optional[int] = None,
    ) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.source == source, DocumentChunk.user_id == user_id)
            .order_by(DocumentChunk.chunk_index)
        )
        if org_id:
            stmt = stmt.where(or_(DocumentChunk.org_id == org_id, DocumentChunk.user_id == user_id))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_chunks(
        self, session: AsyncSession, user_id: int, org_id: Optional[int] = None,
    ) -> list[DocumentChunk]:
        stmt = select(DocumentChunk).where(DocumentChunk.user_id == user_id).order_by(DocumentChunk.chunk_index)
        if org_id:
            stmt = select(DocumentChunk).where(
                or_(DocumentChunk.user_id == user_id, DocumentChunk.org_id == org_id)
            ).order_by(DocumentChunk.chunk_index)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ── Ingestion ───────────────────────────────────────────────────────────────

    async def ingest_text(
        self, text: str, filename: str, user_id: int, org_id: Optional[int] = None, visibility: str = "personal"
    ) -> dict:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(text)

        if not chunks:
            return {
                "status": "error",
                "message": "No text chunks produced.",
                "filename": filename,
                "chunks": 0,
                "characters": 0,
            }

        metadatas = [
            {"source": filename, "chunk_index": i, "user_id": str(user_id), "org_id": str(org_id) if org_id else ""}
            for i in range(len(chunks))
        ]

        async with async_session_factory() as session:
            try:
                await self._store_chunks(session, user_id, filename, chunks, metadatas, org_id=org_id if visibility == "org" else None)

                doc = Document(
                    user_id=user_id,
                    org_id=org_id if visibility == "org" else None,
                    visibility=visibility,
                    shared_by=user_id if visibility == "org" else None,
                    filename=filename,
                    chunks=len(chunks),
                    characters=len(text),
                )
                session.add(doc)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

        logger.info(
            "Ingested %d chunks from '%s' for user %d (org: %s, visibility: %s)",
            len(chunks), filename, user_id, org_id, visibility,
        )
        return {
            "status": "success",
            "message": f"Ingested {len(chunks)} chunks from '{filename}'.",
            "filename": filename,
            "chunks": len(chunks),
            "characters": len(text),
        }

    async def check_document_exists(
        self, session: AsyncSession, user_id: int, filename: str, org_id: Optional[int] = None
    ) -> bool:
        cond = (Document.user_id == user_id) & (Document.filename == filename)
        if org_id:
            cond = or_(
                cond,
                (Document.org_id == org_id) & (Document.visibility == "org") & (Document.filename == filename)
            )
        result = await session.execute(
            select(Document).where(cond)
        )
        return result.scalar_one_or_none() is not None

    async def get_user_documents(
        self, session: AsyncSession, user_id: int, org_id: Optional[int] = None,
        page: int = 1, page_size: int = config.DEFAULT_PAGE_SIZE,
    ) -> dict:
        offset = (page - 1) * page_size

        cond = (Document.user_id == user_id)
        if org_id:
            cond = or_(Document.user_id == user_id, (Document.org_id == org_id) & (Document.visibility == "org"))

        total = await session.scalar(
            select(func.count(Document.id)).where(cond)
        ) or 0

        result = await session.execute(
            select(Document)
            .where(cond)
            .order_by(Document.uploaded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = result.scalars().all()
        items = [
            {
                "id": r.id,
                "user_id": r.user_id,
                "org_id": r.org_id,
                "visibility": r.visibility,
                "shared_by": r.shared_by,
                "filename": r.filename,
                "doc_type": r.doc_type,
                "chunks": r.chunks,
                "characters": r.characters,
                "is_privileged": r.is_privileged,
                "privilege_notes": r.privilege_notes,
                "uploaded_at": str(r.uploaded_at) if r.uploaded_at else None,
            }
            for r in rows
        ]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": -(-total // page_size) if total else 0,
        }

    async def delete_document(self, user_id: int, document_id: int, org_id: Optional[int] = None, is_org_admin: bool = False) -> bool:
        async with async_session_factory() as session:
            try:
                result = await session.execute(
                    select(Document).where(Document.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if doc is None:
                    return False

                is_owner = (doc.user_id == user_id)
                is_shared_org_doc = (doc.visibility == "org" and doc.org_id == org_id)

                if not (is_owner or (is_shared_org_doc and is_org_admin)):
                    return False

                filename = doc.filename

                await self._delete_chunks_by_source(session, filename, doc.user_id, doc.org_id)
                await session.delete(doc)
                await session.commit()

                logger.info(
                    "Deleted document id=%d filename='%s' for user %d",
                    document_id, filename, user_id,
                )
                return True
            except Exception:
                await session.rollback()
                raise

    async def get_user_document(
        self, session: AsyncSession, user_id: int, document_id: int, org_id: Optional[int] = None
    ) -> Optional[dict]:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return None

        is_owner = (doc.user_id == user_id)
        is_shared = (doc.visibility == "org" and doc.org_id == org_id)

        if not (is_owner or is_shared):
            return None

        return {
            "id": doc.id,
            "filename": doc.filename,
            "user_id": doc.user_id,
            "org_id": doc.org_id,
            "visibility": doc.visibility,
            "shared_by": doc.shared_by,
        }

    async def get_document_text(self, document_id: int, user_id: int) -> Optional[str]:
        async with async_session_factory() as session:
            doc = await session.execute(select(Document).where(Document.id == document_id))
            doc = doc.scalar_one_or_none()
            if not doc:
                return None
            org_id = doc.org_id if doc.visibility == "org" else None
            chunks = await self.get_chunks_by_source(session, user_id, doc.filename, org_id)
            if not chunks:
                return None
            return "\n\n".join(c.content for c in chunks)

    async def share_document_to_org(self, user_id: int, document_id: int, org_id: int) -> bool:
        async with async_session_factory() as session:
            try:
                result = await session.execute(
                    select(Document).where(Document.id == document_id, Document.user_id == user_id)
                )
                doc = result.scalar_one_or_none()
                if not doc or doc.visibility == "org":
                    return False

                filename = doc.filename

                chunks = await self.get_chunks_by_source(session, user_id, filename)
                if not chunks:
                    logger.warning(f"No chunks found for doc: {filename}")
                    return False

                for chunk in chunks:
                    chunk.org_id = org_id
                    session.add(chunk)

                doc.org_id = org_id
                doc.visibility = "org"
                doc.shared_by = user_id
                session.add(doc)
                await session.commit()

                logger.info(f"Shared document {document_id} ({filename}) to org {org_id}")
                return True
            except Exception as exc:
                await session.rollback()
                logger.error(f"Error sharing document to org: {exc}")
                raise

    # ── Startup rebuild ─────────────────────────────────────────────────────────

    async def rebuild_on_startup(self) -> None:
        """Rebuild chunk embeddings from stored chunk content if missing."""
        async with async_session_factory() as session:
            try:
                result = await session.execute(
                    select(DocumentChunk).where(DocumentChunk.embedding == None).limit(1)
                )
                missing = result.scalar_one_or_none()
                if not missing:
                    return

                result = await session.execute(
                    select(DocumentChunk).where(DocumentChunk.embedding == None)
                )
                chunks = result.scalars().all()
                texts = [c.content for c in chunks]
                embeddings_list = self.embeddings.embed_documents(texts)
                for chunk, emb in zip(chunks, embeddings_list):
                    chunk.embedding = emb
                await session.commit()
                logger.info("Rebuilt embeddings for %d chunks on startup", len(chunks))
            except Exception as exc:
                await session.rollback()
                logger.warning("Startup rebuild skipped: %s", exc)


ingestion_service = IngestionService()
