"""
# * Google Sheets API helper shared by all tools.
"""

import os
from pathlib import Path
from typing import Any, Dict

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# * Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "client_secret_138285220800-9425b585vgk9rcglfc8fpejomgr7ar4l.apps.googleusercontent.com.json"
DEFAULT_SPREADSHEET_URL = os.environ.get("SPREADSHEET_URL", "")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsFormulaValidator:
    """Helper class to interact with Google Sheets API."""

    def __init__(self, credentials_path: Path):
        self.credentials_path = Path(credentials_path)
        self.service = self._build_service()

    def _build_service(self):
        """Build Google Sheets API service from credentials."""
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Credentials not found at {self.credentials_path}")

        credentials = None
        token_path = PROJECT_ROOT / "token.json"

        # * Try cached token first (OAuth2)
        if token_path.exists():
            credentials = UserCredentials.from_authorized_user_file(token_path, SCOPES)
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())

        # * Try service account
        if not credentials:
            try:
                credentials = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_path,
                    scopes=SCOPES,
                )
            except (ValueError, KeyError):
                # * Fall back to OAuth2 with server
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path,
                    scopes=SCOPES,
                )
                credentials = flow.run_local_server(port=8080)
                # * Cache the credentials
                if token_path:
                    token_path.write_text(credentials.to_json())

        return build("sheets", "v4", credentials=credentials)

    def fetch_spreadsheet(self, spreadsheet_id: str) -> Dict[str, Any]:
        """Fetch full spreadsheet metadata."""
        response = self.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
        ).execute()
        return response

