import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_user,
    promote_user_to_admin,
    get_user_by_email,
    get_user_by_id,
    UserRegister,
    Token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "TestPass1"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)

    def test_verify_wrong_password(self):
        hashed = hash_password("TestPass1")
        assert not verify_password("WrongPass1", hashed)


class TestUserRegisterValidation:
    def test_valid_password(self):
        model = UserRegister(username="u", email="u@u.com", password="Strong12")
        assert model.password == "Strong12"

    def test_password_too_short(self):
        with pytest.raises(ValueError, match="at least 8 characters"):
            UserRegister(username="u", email="u@u.com", password="Sh0rt")

    def test_password_no_uppercase(self):
        with pytest.raises(ValueError, match="uppercase"):
            UserRegister(username="u", email="u@u.com", password="lowercase1")

    def test_password_no_lowercase(self):
        with pytest.raises(ValueError, match="lowercase"):
            UserRegister(username="u", email="u@u.com", password="UPPERCASE1")

    def test_password_no_digit(self):
        with pytest.raises(ValueError, match="digit"):
            UserRegister(username="u", email="u@u.com", password="NoDigits!")


class TestTokenModel:
    def test_token_creation(self):
        token = Token(access_token="abc", token_type="bearer", user={"id": 1})
        assert token.access_token == "abc"
        assert token.token_type == "bearer"
        assert token.user["id"] == 1


class TestJWT:
    def test_create_access_token(self):
        token = create_access_token({"sub": "1"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_decodes(self):
        from jose import jwt
        import config
        token = create_access_token({"sub": "42"})
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        assert payload["sub"] == "42"


class TestCreateUser:
    @patch("auth.User")
    @patch("auth.hash_password", return_value="hashed_pw")
    async def test_create_user_success(self, mock_hash, mock_user_class, mock_session):
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        result = await create_user(
            mock_session, "testuser", "test@example.com", "TestPass1", "Firm"
        )

        assert result["success"] is True
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    async def test_create_user_handles_db_error(self, mock_session):
        mock_session.flush = AsyncMock(side_effect=Exception("DB error"))

        result = await create_user(
            mock_session, "testuser", "test@example.com", "TestPass1", "Firm"
        )

        assert result["success"] is False
        assert "DB error" in result["error"]


class TestPromoteToAdmin:
    async def test_promote_success(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "lawyer"
        mock_session.execute.return_value = mock_result

        result = await promote_user_to_admin(mock_session, 1)

        assert result["success"] is True
        assert "promoted" in result["message"].lower()

    async def test_promote_already_admin(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "admin"
        mock_session.execute.return_value = mock_result

        result = await promote_user_to_admin(mock_session, 1)

        assert result["success"] is False
        assert "already" in result["error"].lower()

    async def test_promote_nonexistent(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await promote_user_to_admin(mock_session, 999)

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestGetUserByEmail:
    async def test_user_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id=1, username="test", email="test@test.com",
            hashed_password="hash", role="lawyer", firm_name="F",
            is_active=True, created_at=None,
            stripe_customer_id=None, subscription_status="free",
        )
        mock_session.execute.return_value = mock_result

        result = await get_user_by_email(mock_session, "test@test.com")
        assert result is not None
        assert result["email"] == "test@test.com"

    async def test_user_not_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await get_user_by_email(mock_session, "nope@nope.com")
        assert result is None


class TestGetUserById:
    async def test_user_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id=42, username="found", email="f@f.com",
            hashed_password="h", role="lawyer", firm_name="F",
            is_active=True, created_at=None,
            stripe_customer_id=None, subscription_status="free",
        )
        mock_session.execute.return_value = mock_result

        result = await get_user_by_id(mock_session, 42)
        assert result["id"] == 42
        assert result["username"] == "found"

    async def test_user_not_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await get_user_by_id(mock_session, 999)
        assert result is None
