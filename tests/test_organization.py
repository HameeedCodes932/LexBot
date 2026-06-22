from unittest.mock import AsyncMock, MagicMock, patch

from organization import OrganizationService, slugify


class TestSlugify:
    def test_basic_slug(self):
        assert slugify("Hello World") == "hello-world"

    def test_slug_with_special_chars(self):
        assert slugify("My Firm, LLC!") == "my-firm-llc"

    def test_slug_whitespace_collapse(self):
        assert slugify("  too   many   spaces  ") == "too-many-spaces"

    def test_slug_lowercase(self):
        assert slugify("ALLCAPS") == "allcaps"


class TestCreateOrg:
    async def test_creates_org_and_membership(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        org_service = OrganizationService()
        org, membership = await org_service.create_org(mock_session, "Test Org", 1)

        assert org.name == "Test Org"
        assert org.owner_id == 1
        assert org.subscription_status == "free"
        assert membership.role == "owner"
        assert membership.user_id == 1
        assert membership.is_active is True

    async def test_generates_unique_slug_on_collision(self, mock_session):
        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = MagicMock()
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = mock_execute
        mock_session.flush = AsyncMock()

        org_service = OrganizationService()
        org, _ = await org_service.create_org(mock_session, "Test Org", 1)
        assert org.slug == "test-org-1"

    async def test_handles_empty_name(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        org_service = OrganizationService()
        org, _ = await org_service.create_org(mock_session, "", 1)
        assert org.slug.startswith("org")


class TestInviteMember:
    async def test_invite_existing_user(self, mock_session):
        user = MagicMock(id=42, email="test@test.com", org_id=None)
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.side_effect = [user, None]
        mock_session.execute.return_value = mock_user_result
        mock_session.flush = AsyncMock()

        org_service = OrganizationService()
        membership = await org_service.invite_member(
            mock_session, 1, "test@test.com", "member", 2
        )
        assert membership.user_id == 42
        assert membership.role == "member"
        assert membership.invited_by == 2

    async def test_invite_creates_placeholder_for_nonexistent_user(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Simulate flush generating an ID for the placeholder user
        async def flush_side_effect():
            # Find any User objects added to the session and assign an id
            for call_args in mock_session.add.call_args_list:
                user = call_args[0][0]
                if hasattr(user, 'id') and user.id is None:
                    user.id = 99

        mock_session.flush = AsyncMock(side_effect=flush_side_effect)

        org_service = OrganizationService()
        membership = await org_service.invite_member(
            mock_session, 1, "nobody@test.com", "member", 2
        )
        assert membership.user_id == 99
        assert membership.is_active is False

    async def test_invite_raises_if_user_already_in_org(self, mock_session):
        user = MagicMock(id=42, email="test@test.com", org_id=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        org_service = OrganizationService()
        try:
            await org_service.invite_member(mock_session, 1, "test@test.com", "member", 2)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already" in str(e).lower()
