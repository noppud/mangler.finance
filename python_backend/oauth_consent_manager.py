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
        info = self._load_service_account_info(credentials_path)

        project_id = info.get("project_id") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_PROJECT")
        if not project_id:
            raise ValueError(
                "Unable to determine Google Cloud project id. "
                "Set project_id in the service account JSON or GOOGLE_CLOUD_PROJECT env var."
            )

        self._project_id = project_id
        self._credentials = service_account.Credentials.from_service_account_info(
            info, scopes=self._SCOPES
        )
        self._session = AuthorizedSession(self._credentials)

    def ensure_test_user(self, email: str) -> Dict[str, Any]:
        """
        Ensure the provided email is present in the OAuth consent screen test user list.

        Args:
            email: Google account email address to register

        Returns:
            Dict with information about the resulting list.
        """
        email = (email or "").strip().lower()
        if not email:
            raise ValueError("User email is required to register as a tester.")

        config = self._session.get(self._consent_url)
        if config.status_code == 404:
            logger.error(
                "OAuth consent screen not configured for project %s. "
                "Please configure it at: https://console.cloud.google.com/apis/credentials/consent?project=%s",
                self._project_id,
                self._project_id,
            )
            raise ValueError(
                f"OAuth consent screen not configured for project '{self._project_id}'. "
                f"Please visit https://console.cloud.google.com/apis/credentials/consent?project={self._project_id} "
                "to set it up first."
            )
        if config.status_code >= 400:
            logger.error("Failed to load OAuth consent screen: %s", config.text)
            config.raise_for_status()

        data = config.json()
        current_users = set(data.get("testUsers", []))

        if email in current_users:
            logger.info("OAuth tester already registered: %s", email)
            return {
                "email": email,
                "added": False,
                "testUsers": sorted(current_users),
            }

        current_users.add(email)
        payload = {"testUsers": sorted(current_users)}

        patch = self._session.patch(
            f"{self._consent_url}?updateMask=testUsers",
            json=payload,
        )
        if patch.status_code >= 400:
            logger.error("Failed to update OAuth consent screen: %s", patch.text)
            patch.raise_for_status()

        updated = patch.json()
        logger.info("Added %s to OAuth tester list", email)

        return {
            "email": email,
            "added": True,
            "testUsers": updated.get("testUsers", payload["testUsers"]),
        }

    @property
    def _consent_url(self) -> str:
        return f"https://oauthconfig.googleapis.com/v1/projects/{self._project_id}/oauthConsentScreen"

    def _load_service_account_info(self, credentials_path: Optional[str]) -> Dict[str, Any]:
        if json_blob := os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
            try:
                return json.loads(json_blob)
            except json.JSONDecodeError as exc:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc

        backend_root = Path(__file__).resolve().parent
        env_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

        candidate_paths = []
        if credentials_path:
            candidate_paths.append(Path(credentials_path))
        if env_path:
            candidate_paths.append(Path(env_path))
        candidate_paths.append(backend_root / "service-account.json")

        for path in candidate_paths:
            if path and path.is_file():
                with path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)

        raise FileNotFoundError(
            "Could not locate Google service account JSON. "
            "Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE."
        )
