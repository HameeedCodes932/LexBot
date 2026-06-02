from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import Analytics, Document, FeatureUsage, User


async def get_admin_stats(session: AsyncSession) -> dict:
    total_users = await session.scalar(select(func.count(User.id)))
    total_documents = await session.scalar(select(func.count(Document.id)))
    total_queries = await session.scalar(select(func.count(Analytics.id)))

    avg_row = await session.scalar(select(func.avg(Analytics.response_time_ms)))
    avg_response_ms = round(avg_row) if avg_row is not None else 0

    queries_today = await session.scalar(
        select(func.count(Analytics.id)).where(
            func.date(Analytics.created_at) == func.current_date()
        )
    )

    top_questions_result = await session.execute(
        select(Analytics.question, func.count(Analytics.id).label("frequency"))
        .group_by(Analytics.question)
        .order_by(text("frequency DESC"))
        .limit(5)
    )
    top_questions = [
        {"question": row[0], "frequency": row[1]}
        for row in top_questions_result
    ]

    user_doc_counts_result = await session.execute(
        select(
            User.username,
            func.count(Document.id).label("document_count"),
        )
        .outerjoin(Document, Document.user_id == User.id)
        .group_by(User.id)
        .order_by(text("document_count DESC"))
    )
    user_doc_counts = [
        {"username": row[0], "document_count": row[1]}
        for row in user_doc_counts_result
    ]

    total_clause_extractions = await session.scalar(
        select(func.count(FeatureUsage.id)).where(
            FeatureUsage.feature_name == "extract-clauses"
        )
    )

    total_comparisons = await session.scalar(
        select(func.count(FeatureUsage.id)).where(
            FeatureUsage.feature_name == "compare-clauses"
        )
    )

    most_searched_result = await session.execute(
        select(FeatureUsage.clause_type, func.count(FeatureUsage.id).label("frequency"))
        .where(FeatureUsage.clause_type.isnot(None))
        .group_by(FeatureUsage.clause_type)
        .order_by(text("frequency DESC"))
        .limit(3)
    )
    most_searched_clause_types = [
        {"clause_type": row[0], "frequency": row[1]}
        for row in most_searched_result
    ]

    return {
        "total_users": total_users or 0,
        "total_documents": total_documents or 0,
        "total_queries": total_queries or 0,
        "avg_response_time_ms": avg_response_ms,
        "queries_today": queries_today or 0,
        "top_questions": top_questions,
        "user_document_counts": user_doc_counts,
        "total_clause_extractions": total_clause_extractions or 0,
        "total_comparisons": total_comparisons or 0,
        "most_searched_clause_types": most_searched_clause_types,
    }
