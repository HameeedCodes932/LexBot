import logging
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import User, get_session, APIKey, OrgMembership, Organization

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Pydantic models ───────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    firm_name: str = ""

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


# ── Core helpers ──────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)


# ── Database helpers ──────────────────────────────────────────────────────────
async def create_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
    firm_name: str = "",
) -> dict:
    hashed = hash_password(password)
    try:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed,
            role="lawyer",
            firm_name=firm_name,
        )
        session.add(user)
        await session.flush()
        logger.info("User created: username=%s email=%s", username, email)
        return {"success": True, "message": "User created successfully."}
    except Exception as exc:
        logger.warning("User creation failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def promote_user_to_admin(session: AsyncSession, user_id: int) -> dict:
    result = await session.execute(select(User.role).where(User.id == user_id))
    row = result.scalar_one_or_none()
    if row is None:
        return {"success": False, "error": "User not found."}
    if row == "admin":
        return {"success": False, "error": "User is already an admin."}
    await session.execute(
        update(User).where(User.id == user_id).values(role="admin")
    )
    logger.info("User promoted to admin: user_id=%d", user_id)
    return {"success": True, "message": f"User {user_id} promoted to admin."}


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[dict]:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    return _user_to_dict(user)


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[dict]:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    return _user_to_dict(user)


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "hashed_password": user.hashed_password,
        "role": user.role,
        "firm_name": user.firm_name,
        "org_id": user.org_id,
        "is_active": user.is_active,
        "created_at": str(user.created_at) if user.created_at else None,
        "stripe_customer_id": user.stripe_customer_id,
        "subscription_status": user.subscription_status,
    }


# ── FastAPI dependencies ──────────────────────────────────────────────────────
async def get_api_key_user(token: str, session: AsyncSession) -> Optional[dict]:
    if not token.startswith(config.API_KEY_PREFIX):
        return None
    # Hash the token
    key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    # Query API Key
    stmt = select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active)
    res = await session.execute(stmt)
    api_key = res.scalar_one_or_none()
    if not api_key:
        return None

    # Check expiry
    if api_key.expires_at and api_key.expires_at.replace(tzinfo=None) < datetime.utcnow():
        return None

    # Update last used
    api_key.last_used_at = datetime.utcnow()
    session.add(api_key)

    # Get user
    user_stmt = select(User).where(User.id == api_key.user_id)
    u_res = await session.execute(user_stmt)
    user = u_res.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    user_dict = _user_to_dict(user)

    # Attach Org Context
    if user.org_id:
        m_stmt = select(OrgMembership.role).where(
            OrgMembership.org_id == user.org_id,
            OrgMembership.user_id == user.id
        )
        m_res = await session.execute(m_stmt)
        org_role = m_res.scalar_one_or_none()

        o_stmt = select(Organization.name).where(Organization.id == user.org_id)
        o_res = await session.execute(o_stmt)
        org_name = o_res.scalar_one_or_none()

        user_dict["org_role"] = org_role
        user_dict["org_name"] = org_name
    else:
        user_dict["org_role"] = None
        user_dict["org_name"] = None

    return user_dict


# ── FastAPI dependencies ──────────────────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token.startswith(config.API_KEY_PREFIX):
        user = await get_api_key_user(token, session)
        if user is None:
            raise credentials_exception
        return user

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(session, int(user_id))
    if user is None or not user.get("is_active"):
        raise credentials_exception

    # Attach Org Context
    if user.get("org_id"):
        # Get role in this org
        m_stmt = select(OrgMembership.role).where(
            OrgMembership.org_id == user["org_id"],
            OrgMembership.user_id == user["id"]
        )
        m_res = await session.execute(m_stmt)
        org_role = m_res.scalar_one_or_none()

        # Get org name
        o_stmt = select(Organization.name).where(Organization.id == user["org_id"])
        o_res = await session.execute(o_stmt)
        org_name = o_res.scalar_one_or_none()

        user["org_role"] = org_role
        user["org_name"] = org_name
    else:
        user["org_role"] = None
        user["org_name"] = None

    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


async def require_org_member(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("org_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership required.",
        )
    return current_user


async def require_org_admin(current_user: dict = Depends(get_current_user)) -> dict:
    current_user = await require_org_member(current_user)
    if current_user.get("org_role") not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrator access required.",
        )
    return current_user
