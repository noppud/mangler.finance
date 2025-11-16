"""
User Identity Resolver: Links Google users to Kinde users
Enables Google Sheets users to access their Kinde-scoped MCPs
"""

from typing import Optional
from .models import UserIdentityLink, IdentityResolveResponse
from .supabase_client import get_supabase_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IdentityResolver:
    """Resolves Google email to Kinde user ID"""

    async def resolve_google_to_kinde(
        self,
        google_email: str
    ) -> IdentityResolveResponse:
        """
        Resolve Google email to Kinde user ID.
        Returns None if no link exists.
        """
        supabase = get_supabase_client()
        if not supabase:
            logger.warning("Supabase not configured, identity resolution unavailable")
            return IdentityResolveResponse(
                kinde_user_id=None,
                linked=False,
                google_email=google_email
            )

        try:
            result = supabase.table("user_identity_links")\
                .select("*")\
                .eq("google_email", google_email.lower())\
                .execute()

            if result.data and len(result.data) > 0:
                link = UserIdentityLink(**result.data[0])

                # Update last_verified_at
                supabase.table("user_identity_links")\
                    .update({"last_verified_at": datetime.utcnow().isoformat()})\
                    .eq("id", link.id)\
                    .execute()

                logger.info(f"Resolved {google_email} -> {link.kinde_user_id}")

                return IdentityResolveResponse(
                    kinde_user_id=link.kinde_user_id,
                    linked=True,
                    google_email=google_email
                )
            else:
                logger.info(f"No identity link found for {google_email}")
                return IdentityResolveResponse(
                    kinde_user_id=None,
                    linked=False,
                    google_email=google_email
                )

        except Exception as e:
            logger.error(f"Failed to resolve identity for {google_email}: {e}")
            return IdentityResolveResponse(
                kinde_user_id=None,
                linked=False,
                google_email=google_email
            )

    async def create_link(
        self,
        kinde_user_id: str,
        google_email: str,
        google_sub: Optional[str] = None
    ) -> UserIdentityLink:
        """Create a new identity link"""
        supabase = get_supabase_client()
        if not supabase:
            raise RuntimeError("Supabase not configured")

        try:
            result = supabase.table("user_identity_links").insert({
                "kinde_user_id": kinde_user_id,
                "google_email": google_email.lower(),
                "google_sub": google_sub
            }).execute()

            link = UserIdentityLink(**result.data[0])
            logger.info(f"Created identity link: {google_email} -> {kinde_user_id}")
            return link

        except Exception as e:
            logger.error(f"Failed to create identity link: {e}")
            raise

    async def delete_link(self, kinde_user_id: str) -> bool:
        """Delete an identity link"""
        supabase = get_supabase_client()
        if not supabase:
            raise RuntimeError("Supabase not configured")

        try:
            result = supabase.table("user_identity_links")\
                .delete()\
                .eq("kinde_user_id", kinde_user_id)\
                .execute()

            success = result.data and len(result.data) > 0
            if success:
                logger.info(f"Deleted identity link for user {kinde_user_id}")
            return success

        except Exception as e:
            logger.error(f"Failed to delete identity link: {e}")
            return False


# Global instance
_resolver: Optional[IdentityResolver] = None


def get_identity_resolver() -> IdentityResolver:
    """Get or create the global identity resolver"""
    global _resolver
    if _resolver is None:
        _resolver = IdentityResolver()
    return _resolver
