import os
from pathlib import Path
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config.settings import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class YouTubeOAuthService:
    def __init__(
        self,
        client_secrets_file: Optional[Path] = None,
        token_file: Optional[Path] = None,
    ):
        settings = get_settings()
        self.client_secrets_file = client_secrets_file or settings.client_secrets_file
        self.token_file = token_file or settings.token_file

    def get_credentials(self) -> Optional[Credentials]:
        """
        Retrieves valid OAuth 2.0 credentials from token.json or runs local browser authorization.
        Returns None if client_secret.json is not configured.
        """
        creds = None

        # Load existing token if available
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file), SCOPES
                )
            except Exception:
                creds = None

        # Refresh expired token
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
                return creds
            except Exception:
                creds = None

        # If valid creds exist, return
        if creds and creds.valid:
            return creds

        # If client_secrets_file is missing, return None (allows dry-run/mock testing)
        if not self.client_secrets_file.exists():
            return None

        # Initiate local web server OAuth flow
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_file), SCOPES
            )
            creds = flow.run_local_server(port=0, open_browser=False)
            self._save_credentials(creds)
            return creds
        except Exception:
            return None


    def _save_credentials(self, creds: Credentials) -> None:
        """Saves authorized user credentials to token_file."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(creds.to_json(), encoding="utf-8")

    def is_authenticated(self) -> bool:
        """Checks if valid credentials exist without launching browser flow."""
        if not self.token_file.exists():
            return False
        try:
            creds = Credentials.from_authorized_user_file(
                str(self.token_file), SCOPES
            )
            if creds.valid:
                return True
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._save_credentials(creds)
                return creds.valid
        except Exception:
            pass
        return False
