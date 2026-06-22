from unittest.mock import AsyncMock, MagicMock, PropertyMock

from retention import RetentionService


class TestApplyRetention:
    async def test_skipped_when_no_policy(self, mock_session):
        org = MagicMock(data_retention_days=0)
        mock_session.get = AsyncMock(return_value=org)

        service = RetentionService()
        result = await service.apply_retention(mock_session, 1)

        assert result["status"] == "skipped"

    async def test_applies_retention_policy(self, mock_session):
        org = MagicMock()
        type(org).data_retention_days = PropertyMock(return_value=30)
        type(org).name = PropertyMock(return_value="TestOrg")
        mock_session.get = AsyncMock(return_value=org)

        mock_user_result = MagicMock()
        mock_user_result.scalars.return_value.all.return_value = [1, 2, 3]
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 5

        mock_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_delete_result, mock_delete_result,
                         mock_delete_result, mock_delete_result, mock_delete_result]
        )

        service = RetentionService()
        result = await service.apply_retention(mock_session, 1)

        assert result["status"] == "success"
        assert result["retention_days"] == 30
        assert result["org_name"] == "TestOrg"

    async def test_handles_no_members(self, mock_session):
        org = MagicMock()
        type(org).data_retention_days = PropertyMock(return_value=30)
        type(org).name = PropertyMock(return_value="EmptyOrg")
        mock_session.get = AsyncMock(return_value=org)

        mock_user_result = MagicMock()
        mock_user_result.scalars.return_value.all.return_value = []

        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 0

        mock_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_delete_result]
        )

        service = RetentionService()
        result = await service.apply_retention(mock_session, 1)

        assert result["status"] == "success"
        assert result["org_name"] == "EmptyOrg"


class TestApplyAllRetentionPolicies:
    async def test_no_orgs_with_policies(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RetentionService()
        results = await service.apply_all_retention_policies(mock_session)
        assert results == []

    async def test_returns_results_for_each_org(self, mock_session):
        mock_org_result = MagicMock()
        mock_org_result.scalars.return_value.all.return_value = [1, 2]
        mock_session.execute = AsyncMock(return_value=mock_org_result)

        org = MagicMock()
        type(org).data_retention_days = PropertyMock(return_value=30)
        type(org).name = PropertyMock(return_value="Org")
        mock_session.get = AsyncMock(return_value=org)

        mock_user_result = MagicMock()
        mock_user_result.scalars.return_value.all.return_value = [1]
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 0

        call_index = [0]
        results_cycle = [
            mock_user_result,        # 0: member query for org 1
            mock_delete_result,      # 1: delete Message
            mock_delete_result,      # 2: delete Summary
            mock_delete_result,      # 3: delete LTM
            mock_delete_result,      # 4: delete Analytics
            mock_delete_result,      # 5: delete AuditLog
            mock_user_result,        # 6: member query for org 2
            mock_delete_result,      # 7: delete Message
            mock_delete_result,      # 8: delete Summary
            mock_delete_result,      # 9: delete LTM
            mock_delete_result,      # 10: delete Analytics
            mock_delete_result,      # 11: delete AuditLog
        ]

        async def execute_side_effect(*args, **kwargs):
            idx = call_index[0]
            call_index[0] += 1
            # First call (select org ids) returns mock_org_result
            if idx == 0:
                return mock_org_result
            return results_cycle[idx - 1]

        mock_session.execute = AsyncMock(side_effect=execute_side_effect)

        service = RetentionService()
        results = await service.apply_all_retention_policies(mock_session)
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
