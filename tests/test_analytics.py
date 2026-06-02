from unittest.mock import AsyncMock

from analytics import get_admin_stats


class TestAdminStats:
    async def test_returns_all_keys(self, mock_session):
        mock_session.scalar = AsyncMock(side_effect=lambda *a, **kw: 5)
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        stats = await get_admin_stats(mock_session)

        assert "total_users" in stats
        assert "total_documents" in stats
        assert "total_queries" in stats
        assert "avg_response_time_ms" in stats
        assert "queries_today" in stats
        assert "top_questions" in stats
        assert "user_document_counts" in stats
        assert "total_clause_extractions" in stats
        assert "total_comparisons" in stats
        assert "most_searched_clause_types" in stats

    async def test_counts_are_aggregated(self, mock_session):
        mock_session.scalar = AsyncMock(side_effect=lambda *a, **kw: 10)
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        stats = await get_admin_stats(mock_session)

        assert stats["total_users"] == 10
        assert stats["total_documents"] == 10
        assert stats["total_queries"] == 10
