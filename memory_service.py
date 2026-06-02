import logging

from langchain_core.messages import HumanMessage
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import LongTermMemory, Message, Summary, async_session_factory
from llm_provider import llm_provider

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self):
        pass  # LLM created on-demand via llm_provider

    @property
    def _llm(self):
        return llm_provider.get_memory_llm(temperature=0)

    async def loadRecentMessages(
        self, session: AsyncSession, user_id: int, session_id: str
    ) -> list[dict]:
        result = await session.execute(
            select(Message.role, Message.content, Message.created_at)
            .where(Message.user_id == user_id, Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(config.MAX_RECENT_MESSAGES)
        )
        rows = result.all()
        return [
            {"role": r.role, "content": r.content, "created_at": str(r.created_at) if r.created_at else None}
            for r in reversed(rows)
        ]

    async def loadSummary(
        self, session: AsyncSession, user_id: int, session_id: str
    ) -> str:
        result = await session.execute(
            select(Summary.summary)
            .where(Summary.user_id == user_id, Summary.session_id == session_id)
            .order_by(Summary.updated_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row else "No summary available for this session yet."

    async def searchLongTermMemory(
        self, session: AsyncSession, user_id: int, query: str
    ) -> str:
        result = await session.execute(
            select(LongTermMemory.memory_text)
            .where(LongTermMemory.user_id == user_id)
            .order_by(LongTermMemory.created_at.desc())
            .limit(config.MAX_LONG_TERM_RESULTS)
        )
        rows = result.scalars().all()
        if not rows:
            return "No long-term memory found for this user."
        return "\n".join(rows)

    async def saveMessage(
        self, session: AsyncSession, user_id: int, session_id: str, role: str, content: str
    ) -> None:
        assert role in ("human", "assistant"), "role must be 'human' or 'assistant'"
        msg = Message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
        )
        session.add(msg)

    async def clearSessionMemory(
        self, session: AsyncSession, user_id: int, session_id: str
    ) -> None:
        await session.execute(
            delete(Message).where(
                Message.user_id == user_id, Message.session_id == session_id
            )
        )
        await session.execute(
            delete(Summary).where(
                Summary.user_id == user_id, Summary.session_id == session_id
            )
        )

    async def extractMemory(
        self,
        user_id: int,
        session_id: str,
        question: str,
        answer: str,
    ) -> None:
        # ── a) Long-term fact extraction ──────────────────────────────────────
        try:
            fact_prompt = (
                "You are a legal memory extractor.\n"
                "Given the following legal Q&A, extract ONE important legal fact "
                "worth remembering long-term (e.g. a key obligation, deadline, party name, "
                "or clause detail). If there is nothing worth remembering, respond with exactly: NONE\n\n"
                f"Question: {question}\nAnswer: {answer}\n\n"
                "Respond with the fact only, or NONE."
            )
            fact_response = await self._llm.ainvoke(
                [HumanMessage(content=fact_prompt)]
            )
            fact_text = fact_response.content.strip()
            if fact_text and fact_text.upper() != "NONE":
                async with async_session_factory() as session:
                    try:
                        m = LongTermMemory(user_id=user_id, memory_text=fact_text)
                        session.add(m)
                        await session.commit()
                    except Exception:
                        await session.rollback()
        except Exception:
            pass

        # ── b) Session summary update ─────────────────────────────────────────
        try:
            async with async_session_factory() as session:
                recent = await self.loadRecentMessages(session, user_id, session_id)
                if len(recent) >= config.SUMMARIZE_AFTER_MESSAGES:
                    last_six = recent[-6:]
                    conversation = "\n".join(
                        f"{m['role'].upper()}: {m['content']}" for m in last_six
                    )
                    summary_prompt = (
                        "You are a legal session summarizer.\n"
                        "Write a 2-3 sentence summary of the conversation below, "
                        "focusing on: which documents were reviewed and what key findings "
                        "or issues were identified.\n\n"
                        f"Conversation:\n{conversation}\n\nSummary:"
                    )
                    summary_response = await self._llm.ainvoke(
                        [HumanMessage(content=summary_prompt)]
                    )
                    summary_text = summary_response.content.strip()

                    existing = await session.execute(
                        select(Summary.id).where(
                            Summary.user_id == user_id,
                            Summary.session_id == session_id,
                        )
                    )
                    existing_row = existing.scalar_one_or_none()
                    if existing_row:
                        await session.execute(
                            update(Summary)
                            .where(
                                Summary.user_id == user_id,
                                Summary.session_id == session_id,
                            )
                            .values(summary=summary_text)
                        )
                    else:
                        s = Summary(
                            user_id=user_id,
                            session_id=session_id,
                            summary=summary_text,
                        )
                        session.add(s)
                    await session.commit()
        except Exception:
            pass


memory_service = MemoryService()
