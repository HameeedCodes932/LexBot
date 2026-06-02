import logging
import re
import uuid
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import Organization, OrgMembership, User
import config

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Generate a URL-safe slug from a string."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


class OrganizationService:
    async def create_org(
        self, session: AsyncSession, name: str, owner_user_id: int
    ) -> Tuple[Organization, OrgMembership]:
        """Create a new organization, assign user as owner, and update user record."""
        # 1. Generate unique slug
        base_slug = slugify(name) or "org"
        slug = base_slug
        suffix = 1
        while True:
            # Check if slug exists
            q = await session.execute(select(Organization).where(Organization.slug == slug))
            if q.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        # 2. Create organization
        org = Organization(
            name=name,
            slug=slug,
            owner_id=owner_user_id,
            subscription_status="free",
            data_retention_days=config.DEFAULT_DATA_RETENTION_DAYS,
        )
        session.add(org)
        await session.flush()  # to get org.id

        # 3. Create membership as owner
        membership = OrgMembership(
            org_id=org.id,
            user_id=owner_user_id,
            role="owner",
            is_active=True,
            joined_at=org.created_at,  # or func.now(), but flush may not set created_at until commit. Using None or setting manually
        )
        session.add(membership)

        # 4. Update the User's org_id
        await session.execute(
            update(User).where(User.id == owner_user_id).values(org_id=org.id)
        )

        logger.info(f"Created organization '{name}' (slug: {slug}) with owner {owner_user_id}")
        return org, membership

    async def get_user_org(self, session: AsyncSession, user_id: int) -> Optional[Organization]:
        """Get the organization a user belongs to."""
        stmt = (
            select(Organization)
            .join(OrgMembership, OrgMembership.org_id == Organization.id)
            .where(OrgMembership.user_id == user_id, OrgMembership.is_active == True)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_org_by_slug(self, session: AsyncSession, slug: str) -> Optional[Organization]:
        """Get an organization by its slug."""
        stmt = select(Organization).where(Organization.slug == slug)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_org_members(
        self, session: AsyncSession, org_id: int
    ) -> List[Dict[str, Any]]:
        """List all members of an organization with their user profiles and roles."""
        stmt = (
            select(OrgMembership, User)
            .join(User, OrgMembership.user_id == User.id)
            .where(OrgMembership.org_id == org_id)
        )
        res = await session.execute(stmt)
        members = []
        for membership, user in res:
            members.append(
                {
                    "membership_id": membership.id,
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": membership.role,
                    "is_active": membership.is_active,
                    "invited_at": membership.invited_at,
                    "joined_at": membership.joined_at,
                }
            )
        return members

    async def get_org_settings(self, session: AsyncSession, org_id: int) -> Optional[Dict[str, Any]]:
        """Get custom system prompt, data retention policy, and branding for an organization."""
        org = await session.get(Organization, org_id)
        if not org:
            return None
        return {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "custom_system_prompt": org.custom_system_prompt,
            "logo_url": org.logo_url,
            "primary_color": org.primary_color,
            "secondary_color": org.secondary_color,
            "custom_domain": org.custom_domain,
            "data_retention_days": org.data_retention_days,
            "sso_provider": org.sso_provider,
            "sso_metadata_url": org.sso_metadata_url,
            "sso_entity_id": org.sso_entity_id,
            "subscription_status": org.subscription_status,
        }

    async def update_org_settings(
        self, session: AsyncSession, org_id: int, settings: Dict[str, Any]
    ) -> Optional[Organization]:
        """Update organization-level settings."""
        org = await session.get(Organization, org_id)
        if not org:
            return None

        for key, val in settings.items():
            if hasattr(org, key):
                setattr(org, key, val)

        session.add(org)
        logger.info(f"Updated settings for organization ID {org_id}")
        return org

    async def invite_member(
        self, session: AsyncSession, org_id: int, email: str, role: str, invited_by_user_id: int
    ) -> OrgMembership:
        """Invite a member by email. If the user doesn't exist, they'll register later."""
        # Find if user already exists
        user_stmt = select(User).where(User.email == email)
        res = await session.execute(user_stmt)
        user = res.scalar_one_or_none()

        # Check if already invited / member
        if user:
            member_stmt = select(OrgMembership).where(
                OrgMembership.org_id == org_id, OrgMembership.user_id == user.id
            )
            m_res = await session.execute(member_stmt)
            existing_membership = m_res.scalar_one_or_none()
            if existing_membership:
                raise ValueError("User is already a member or has a pending invitation.")

        # Create user placeholder or get existing user ID
        target_user_id = None
        if user:
            target_user_id = user.id
        else:
            # Create a placeholder user
            placeholder_username = f"invited_{uuid.uuid4().hex[:8]}"
            placeholder_pwd = uuid.uuid4().hex
            placeholder = User(
                username=placeholder_username,
                email=email,
                hashed_password=placeholder_pwd,  # Must be updated during accept/onboarding
                is_active=False,
            )
            session.add(placeholder)
            await session.flush()
            target_user_id = placeholder.id

        # Create membership
        membership = OrgMembership(
            org_id=org_id,
            user_id=target_user_id,
            role=role,
            invited_by=invited_by_user_id,
            is_active=False,
        )
        session.add(membership)
        await session.flush()

        logger.info(f"Invited {email} to organization {org_id} as {role}")
        return membership

    async def accept_invitation(self, session: AsyncSession, membership_id: int, user_id: int) -> OrgMembership:
        """Accept an invitation to an organization."""
        membership = await session.get(OrgMembership, membership_id)
        if not membership:
            raise ValueError("Invitation not found.")

        if membership.user_id != user_id:
            raise ValueError("Invitation does not belong to this user.")

        membership.is_active = True
        import datetime
        membership.joined_at = datetime.datetime.now(datetime.timezone.utc)
        session.add(membership)

        # Update User org_id
        await session.execute(
            update(User).where(User.id == user_id).values(org_id=membership.org_id, is_active=True)
        )

        logger.info(f"User {user_id} accepted invitation to organization {membership.org_id}")
        return membership

    async def update_member_role(
        self, session: AsyncSession, org_id: int, target_user_id: int, new_role: str
    ) -> OrgMembership:
        """Update role of an organization member."""
        stmt = select(OrgMembership).where(
            OrgMembership.org_id == org_id, OrgMembership.user_id == target_user_id
        )
        res = await session.execute(stmt)
        membership = res.scalar_one_or_none()
        if not membership:
            raise ValueError("Membership not found.")

        if membership.role == "owner" and new_role != "owner":
            # Demoting owner requires another owner to be set first or specialized logic
            # Let's verify if there is at least another owner
            owner_stmt = select(OrgMembership).where(
                OrgMembership.org_id == org_id,
                OrgMembership.role == "owner",
                OrgMembership.user_id != target_user_id,
            )
            owner_res = await session.execute(owner_stmt)
            if not owner_res.first():
                raise ValueError("Cannot demote the only owner of the organization.")

        membership.role = new_role
        session.add(membership)
        logger.info(f"Updated role of member {target_user_id} in org {org_id} to {new_role}")
        return membership

    async def remove_member(self, session: AsyncSession, org_id: int, target_user_id: int) -> None:
        """Remove a member from the organization."""
        # Check if owner
        stmt = select(OrgMembership).where(
            OrgMembership.org_id == org_id, OrgMembership.user_id == target_user_id
        )
        res = await session.execute(stmt)
        membership = res.scalar_one_or_none()
        if not membership:
            raise ValueError("Membership not found.")

        if membership.role == "owner":
            owner_stmt = select(OrgMembership).where(
                OrgMembership.org_id == org_id,
                OrgMembership.role == "owner",
                OrgMembership.user_id != target_user_id,
            )
            owner_res = await session.execute(owner_stmt)
            if not owner_res.first():
                raise ValueError("Cannot remove the only owner of the organization.")

        # Delete membership
        await session.execute(
            delete(OrgMembership).where(
                OrgMembership.org_id == org_id, OrgMembership.user_id == target_user_id
            )
        )

        # Clear User org_id
        await session.execute(
            update(User).where(User.id == target_user_id).values(org_id=None)
        )
        logger.info(f"Removed user {target_user_id} from organization {org_id}")


org_service = OrganizationService()
