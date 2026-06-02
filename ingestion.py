import logging
import os
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import Document, async_session_factory

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self):
        self._embeddings: Optional[HuggingFaceBgeEmbeddings] = None
        self._collections: dict[str, Chroma] = {}

    @property
    def embeddings(self) -> HuggingFaceBgeEmbeddings:
        if self._embeddings is None:
            self._embeddings = HuggingFaceBgeEmbeddings(
                model_name=config.EMBEDDING_MODEL_NAME,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    def get_collection(self, user_id: int) -> Chroma:
        cache_key = f"user_{user_id}"
        if cache_key not in self._collections:
            persist_dir = os.path.join(config.CHROMA_DIR, f"user_{user_id}")
            os.makedirs(persist_dir, exist_ok=True)
            self._collections[cache_key] = Chroma(
                collection_name=f"user_{user_id}",
                embedding_function=self.embeddings,
                persist_directory=persist_dir,
            )
        return self._collections[cache_key]

    def get_org_collection(self, org_id: int) -> Chroma:
        cache_key = f"org_{org_id}"
        if cache_key not in self._collections:
            persist_dir = os.path.join(config.CHROMA_DIR, f"org_{org_id}")
            os.makedirs(persist_dir, exist_ok=True)
            self._collections[cache_key] = Chroma(
                collection_name=f"org_{org_id}",
                embedding_function=self.embeddings,
                persist_directory=persist_dir,
            )
        return self._collections[cache_key]

    def get_retriever(self, user_id: int, k: int = config.RETRIEVAL_K):
        try:
            collection = self.get_collection(user_id)
            return collection.as_retriever(search_kwargs={"k": k})
        except Exception:
            return None

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

        if visibility == "org" and org_id:
            collection = self.get_org_collection(org_id)
        else:
            collection = self.get_collection(user_id)
            
        collection.add_texts(texts=chunks, metadatas=metadatas)

        async with async_session_factory() as session:
            try:
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
        # Check personal or shared documents in org
        from sqlalchemy import or_
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
        
        # Build filter condition
        cond = (Document.user_id == user_id)
        if org_id:
            from sqlalchemy import or_
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

                # Permission check
                is_owner = (doc.user_id == user_id)
                is_shared_org_doc = (doc.visibility == "org" and doc.org_id == org_id)
                
                if not (is_owner or (is_shared_org_doc and is_org_admin)):
                    return False

                filename = doc.filename
                visibility = doc.visibility
                doc_org_id = doc.org_id
                doc_user_id = doc.user_id
                
                await session.delete(doc)
                await session.commit()

                if visibility == "org" and doc_org_id:
                    collection = self.get_org_collection(doc_org_id)
                else:
                    collection = self.get_collection(doc_user_id)
                    
                collection._collection.delete(where={"source": filename})

                logger.info(
                    "Deleted document id=%d filename='%s' (visibility: %s) for user %d",
                    document_id, filename, visibility, user_id,
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

        # Check permissions: owner or shared org member
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

    async def share_document_to_org(self, user_id: int, document_id: int, org_id: int) -> bool:
        async with async_session_factory() as session:
            try:
                # 1. Fetch document
                result = await session.execute(
                    select(Document).where(Document.id == document_id, Document.user_id == user_id)
                )
                doc = result.scalar_one_or_none()
                if not doc or doc.visibility == "org":
                    return False
                
                filename = doc.filename
                
                # 2. Retrieve texts & metadatas from user's Chroma collection
                user_coll = self.get_collection(user_id)
                db_results = user_coll._collection.get(where={"source": filename})
                
                documents = db_results.get("documents", [])
                metadatas = db_results.get("metadatas", [])
                
                if not documents:
                    logger.warning(f"No vector chunks found in user_{user_id} collection for doc: {filename}")
                    return False
                
                # 3. Add to org collection
                org_coll = self.get_org_collection(org_id)
                # Update metadatas with org_id
                for meta in metadatas:
                    meta["org_id"] = str(org_id)
                    
                org_coll.add_texts(texts=documents, metadatas=metadatas)
                
                # 4. Remove from user collection
                user_coll._collection.delete(where={"source": filename})
                
                # 5. Update DB
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


ingestion_service = IngestionService()
