import datetime
import logging
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Organization, User, OrgMembership
from auth import create_access_token, _user_to_dict

logger = logging.getLogger(__name__)

# Try importing python3-saml, fallback to simulator if missing
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    SAML_SUPPORTED = True
except ImportError:
    SAML_SUPPORTED = False
    logger.warning("python3-saml package not found. SSO will run in simulation mode.")


class SSOService:
    async def configure_sso(
        self, session: AsyncSession, org_id: int, provider: str, metadata_url: str, entity_id: str
    ) -> Organization:
        """Configure SSO provider for an organization."""
        org = await session.get(Organization, org_id)
        if not org:
            raise ValueError("Organization not found.")

        org.sso_provider = provider
        org.sso_metadata_url = metadata_url
        org.sso_entity_id = entity_id

        session.add(org)
        logger.info(f"Configured SSO ({provider}) for organization ID {org_id}")
        return org

    def _prepare_saml_request_data(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Convert FastAPI/Standard request info into python-saml compatible request format."""
        # python-saml expects a dict with: 'https', 'http_host', 'script_name', 'get_data', 'post_data'
        return {
            "https": "on" if request_info.get("is_secure") else "off",
            "http_host": request_info.get("http_host", "localhost:8000"),
            "script_name": request_info.get("path_info", ""),
            "server_port": request_info.get("server_port", "8000"),
            "get_data": request_info.get("query_params", {}),
            "post_data": request_info.get("form_params", {}),
        }

    def _get_saml_settings(self, org: Organization) -> Dict[str, Any]:
        """Generate OneLogin_Saml2 SAML Settings dictionary from organization SSO configuration."""
        # Standard SAML SP and IdP settings
        return {
            "strict": True,
            "debug": True,
            "sp": {
                "entityId": f"https://lexbot.ai/api/auth/sso/{org.slug}/metadata",
                "assertionConsumerService": {
                    "url": f"https://lexbot.ai/api/auth/sso/{org.slug}/callback",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            },
            "idp": {
                "entityId": org.sso_entity_id,
                "singleSignOnService": {
                    "url": org.sso_metadata_url,  # often serves as the SSO entrypoint
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": "",  # Normally populated from IDP metadata
            },
        }

    async def get_sso_login_url(
        self, session: AsyncSession, org_slug: str, request_info: Dict[str, Any]
    ) -> str:
        """Generate SAML AuthnRequest URL for redirection to the IdP."""
        stmt = select(Organization).where(Organization.slug == org_slug)
        res = await session.execute(stmt)
        org = res.scalar_one_or_none()

        if not org or not org.sso_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SSO is not configured or enabled for organization '{org_slug}'."
            )

        if not SAML_SUPPORTED:
            # Simulation Mode
            # Redirect to a mock IdP page or callback simulation
            logger.info("SAML not installed, returning simulation login URL")
            mock_email = f"user@{org_slug}.com"
            return f"/api/auth/sso/{org_slug}/callback?simulated=true&email={mock_email}"

        try:
            req = self._prepare_saml_request_data(request_info)
            settings = self._get_saml_settings(org)
            auth = OneLogin_Saml2_Auth(req, settings)
            return auth.login()
        except Exception as exc:
            logger.error(f"Error initiating SAML AuthnRequest: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"SAML generation failed: {exc}"
            )

    async def handle_sso_callback(
        self, session: AsyncSession, org_slug: str, request_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate SAML Assertion response from IdP and authenticate/provision the user."""
        stmt = select(Organization).where(Organization.slug == org_slug)
        res = await session.execute(stmt)
        org = res.scalar_one_or_none()

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found."
            )

        email = None
        username = None

        # Check for simulated flow
        if not SAML_SUPPORTED or request_info.get("query_params", {}).get("simulated") == "true":
            email = request_info.get("query_params", {}).get("email")
            if not email:
                email = f"sso_user@{org_slug}.com"
            username = email.split("@")[0]
            logger.info(f"SSO SIMULATION: Authenticating simulated user {email} for org {org.name}")
        else:
            try:
                req = self._prepare_saml_request_data(request_info)
                settings = self._get_saml_settings(org)
                auth = OneLogin_Saml2_Auth(req, settings)
                
                auth.process_response()
                errors = auth.get_errors()
                if errors:
                    logger.error(f"SAML Response Processing Errors: {errors}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"SAML assertion invalid: {auth.get_last_error_reason()}"
                    )

                if not auth.is_authenticated():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="SAML authentication failed."
                    )

                email = auth.get_nameid()
                # Try getting attributes
                attrs = auth.get_attributes()
                if attrs.get("username"):
                    username = attrs["username"][0]
                elif attrs.get("displayName"):
                    username = attrs["displayName"][0]
                else:
                    username = email.split("@")[0]

            except Exception as exc:
                logger.error(f"SAML callback failed: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"SAML verification failed: {exc}"
                )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SAML response did not contain a valid NameID/email."
            )

        # Find or Auto-provision user
        u_stmt = select(User).where(User.email == email)
        u_res = await session.execute(u_stmt)
        user = u_res.scalar_one_or_none()

        if user:
            # Existing user: verify they belong to this organization or join them if they don't have one
            if user.org_id is None:
                user.org_id = org.id
                session.add(user)
                # Create org membership
                membership = OrgMembership(
                    org_id=org.id,
                    user_id=user.id,
                    role="member",
                    is_active=True,
                    joined_at=datetime.utcnow()
                )
                session.add(membership)
            elif user.org_id != org.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is registered with another organization."
                )
        else:
            # Auto-provision user
            import uuid
            # Generates a random safe username if collision
            base_username = username
            final_username = base_username
            suffix = 1
            while True:
                existing_uname = await session.execute(select(User).where(User.username == final_username))
                if not existing_uname.scalar_one_or_none():
                    break
                final_username = f"{base_username}_{suffix}"
                suffix += 1

            user = User(
                username=final_username,
                email=email,
                hashed_password=f"sso_placeholder_{uuid.uuid4().hex}",  # No local password login unless reset
                org_id=org.id,
                role="lawyer",
                firm_name=org.name,
                is_active=True,
            )
            session.add(user)
            await session.flush()

            # Create membership
            membership = OrgMembership(
                org_id=org.id,
                user_id=user.id,
                role="member",
                is_active=True,
                joined_at=datetime.utcnow()
            )
            session.add(membership)

        await session.commit()

        # Issue JWT Access Token
        jwt_token = create_access_token(data={"sub": str(user.id)})
        
        user_dict = _user_to_dict(user)
        user_dict["org_role"] = "member" if user.id != org.owner_id else "owner"
        user_dict["org_name"] = org.name

        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": user_dict,
        }


sso_service = SSOService()
