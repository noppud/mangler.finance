"""
Helpers for managing the OAuth consent screen test user list.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class OAuthConsentManager:
    """
    Provides utilities for adding Google accounts to the OAuth consent screen test user list.
    """

    _SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

    def __init__(self, credentials_path: Optional[str] = None) -> None:
        logger.info("[OAuthConsentManager] Initializing OAuth consent manager")
        info = self._load_service_account_info(credentials_path)

        project_id = info.get("project_id") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_PROJECT")
        if not project_id:
            logger.error("[OAuthConsentManager] No project_id found in service account or environment")
            raise ValueError(
                "Unable to determine Google Cloud project id. "
                "Set project_id in the service account JSON or GOOGLE_CLOUD_PROJECT env var."
            )

        self._project_id = project_id
        logger.info(
            "[OAuthConsentManager] Initialized for project: %s",
            project_id,
            extra={"project_id": project_id}
        )

        self._credentials = service_account.Credentials.from_service_account_info(
            info, scopes=self._SCOPES
        )
        self._session = AuthorizedSession(self._credentials)
        logger.debug("[OAuthConsentManager] Service account credentials loaded and session created")

    def ensure_test_user(self, email: str) -> Dict[str, Any]:
        """
        Ensure the provided email is present in the OAuth consent screen test user list.

        Args:
            email: Google account email address to register

        Returns:
            Dict with information about the resulting list.
        """
        logger.info(
            "[OAuthConsentManager] ensure_test_user called",
            extra={"email": email, "project_id": self._project_id}
        )

        email = (email or "").strip().lower()
        if not email:
            logger.error("[OAuthConsentManager] Empty email provided")
            raise ValueError("User email is required to register as a tester.")

        logger.info(
            "[OAuthConsentManager] Fetching OAuth consent screen config from: %s",
            self._consent_url,
            extra={"url": self._consent_url, "email": email}
        )

        config = self._session.get(self._consent_url)

        logger.info(
            "[OAuthConsentManager] OAuth config GET response: status=%s",
            config.status_code,
            extra={
                "status_code": config.status_code,
                "url": self._consent_url,
                "email": email,
                "response_headers": dict(config.headers),
            }
        )

        if config.status_code == 404:
            logger.error(
                "[OAuthConsentManager] OAuth consent screen not configured (404). "
                "Project: %s. "
                "Configure at: https://console.cloud.google.com/apis/credentials/consent?project=%s",
                self._project_id,
                self._project_id,
                extra={
                    "project_id": self._project_id,
                    "email": email,
                    "response_body": config.text[:500] if config.text else "(empty)",
                }
            )
            raise ValueError(
                f"OAuth consent screen not configured for project '{self._project_id}'. "
                f"Please visit https://console.cloud.google.com/apis/credentials/consent?project={self._project_id} "
                "to set it up first."
            )
        if config.status_code >= 400:
            logger.error(
                "[OAuthConsentManager] Failed to load OAuth consent screen: status=%s, body=%s",
                config.status_code,
                config.text[:500] if config.text else "(empty)",
                extra={
                    "status_code": config.status_code,
                    "response_body": config.text[:1000] if config.text else "(empty)",
                    "email": email,
                }
            )
            config.raise_for_status()

        data = config.json()
        current_users = set(data.get("testUsers", []))

        logger.info(
            "[OAuthConsentManager] Current test users count: %s",
            len(current_users),
            extra={"current_users_count": len(current_users), "email": email}
        )

        if email in current_users:
            logger.info(
                "[OAuthConsentManager] Email already in test user list: %s",
                email,
                extra={"email": email, "already_registered": True}
            )
            return {
                "email": email,
                "added": False,
                "testUsers": sorted(current_users),
            }

        current_users.add(email)
        payload = {"testUsers": sorted(current_users)}

        logger.info(
            "[OAuthConsentManager] Adding email to test users. Total count after add: %s",
            len(current_users),
            extra={
                "email": email,
                "total_users_after": len(current_users),
                "url": f"{self._consent_url}?updateMask=testUsers"
            }
        )

        patch = self._session.patch(
            f"{self._consent_url}?updateMask=testUsers",
            json=payload,
        )

        logger.info(
            "[OAuthConsentManager] OAuth config PATCH response: status=%s",
            patch.status_code,
            extra={
                "status_code": patch.status_code,
                "email": email,
                "response_headers": dict(patch.headers),
            }
        )

        if patch.status_code >= 400:
            logger.error(
                "[OAuthConsentManager] Failed to update OAuth consent screen: status=%s, body=%s",
                patch.status_code,
                patch.text[:500] if patch.text else "(empty)",
                extra={
                    "status_code": patch.status_code,
                    "response_body": patch.text[:1000] if patch.text else "(empty)",
                    "email": email,
                }
            )
            patch.raise_for_status()

        updated = patch.json()
        logger.info(
            "[OAuthConsentManager] Successfully added %s to OAuth tester list",
            email,
            extra={
                "email": email,
                "added": True,
                "final_users_count": len(updated.get("testUsers", [])),
            }
        )

        return {
            "email": email,
            "added": True,
            "testUsers": updated.get("testUsers", payload["testUsers"]),
        }

    @property
    def _consent_url(self) -> str:
        return f"https://oauthconfig.googleapis.com/v1/projects/{self._project_id}/oauthConsentScreen"

    def _load_service_account_info(self, credentials_path: Optional[str]) -> Dict[str, Any]:
        logger.debug("[OAuthConsentManager] Loading service account credentials")

        if json_blob := os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
            logger.info("[OAuthConsentManager] Using service account from GOOGLE_SERVICE_ACCOUNT_JSON env var")
            try:
                info = json.loads(json_blob)
                logger.debug(
                    "[OAuthConsentManager] Service account loaded: project_id=%s, client_email=%s",
                    info.get("project_id", "(missing)"),
                    info.get("client_email", "(missing)")
                )
                return info
            except json.JSONDecodeError as exc:
                logger.error("[OAuthConsentManager] GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON")
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc

        backend_root = Path(__file__).resolve().parent
        env_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

        candidate_paths = []
        if credentials_path:
            candidate_paths.append(Path(credentials_path))
        if env_path:
            candidate_paths.append(Path(env_path))
        candidate_paths.append(backend_root / "service-account.json")

        logger.debug(
            "[OAuthConsentManager] Searching for service account file in: %s",
            [str(p) for p in candidate_paths]
        )

        for path in candidate_paths:
            if path and path.is_file():
                logger.info(
                    "[OAuthConsentManager] Using service account from file: %s",
                    str(path)
                )
                with path.open("r", encoding="utf-8") as handle:
                    info = json.load(handle)
                    logger.debug(
                        "[OAuthConsentManager] Service account loaded: project_id=%s, client_email=%s",
                        info.get("project_id", "(missing)"),
                        info.get("client_email", "(missing)")
                    )
                    return info

        logger.error(
            "[OAuthConsentManager] No service account file found. Searched: %s",
            [str(p) for p in candidate_paths]
        )
        raise FileNotFoundError(
            "Could not locate Google service account JSON. "
            "Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE."
        )
