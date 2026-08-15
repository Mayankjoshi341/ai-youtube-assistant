import time
import uuid
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from models.schemas import YouTubeUploadResult, PublishingAssets
from services.youtube_oauth import YouTubeOAuthService
from config.settings import get_settings


class YouTubePublisherService:
    def __init__(self, oauth_service: Optional[YouTubeOAuthService] = None):
        self.settings = get_settings()
        self.oauth_service = oauth_service or YouTubeOAuthService()

    def _get_youtube_client(self):
        creds = self.oauth_service.get_credentials()
        if not creds:
            return None
        return build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        assets: PublishingAssets,
        category_id: str = "28",  # 28 = Science & Technology
        privacy_status: Optional[str] = None,
        force_mock: bool = False,
    ) -> YouTubeUploadResult:
        """
        Uploads video and custom thumbnail to YouTube Data API v3.
        If OAuth credentials are missing or force_mock is True, runs in safe mock mode.
        """
        privacy = privacy_status or self.settings.default_privacy_status
        video_path = Path(assets.video_path)

        youtube = self._get_youtube_client()

        # Fallback to mock upload if no OAuth credentials configured
        if force_mock or youtube is None:
            mock_id = f"mock_{uuid.uuid4().hex[:11]}"
            return YouTubeUploadResult(
                video_id=mock_id,
                video_url=f"https://www.youtube.com/watch?v={mock_id}",
                privacy_status=privacy,
                thumbnail_uploaded=assets.thumbnail_path is not None,
                processing_status="succeeded",
                is_mock=True,
            )

        # Real YouTube Upload
        body = {
            "snippet": {
                "title": assets.selected_title[:100],  # YouTube title limit
                "description": assets.description[:5000],
                "tags": assets.hashtags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            chunksize=4 * 1024 * 1024,  # 4 MB chunks
            resumable=True,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()

        video_id = response.get("id")
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Upload custom thumbnail if thumbnail_path exists
        thumbnail_uploaded = False
        if assets.thumbnail_path and Path(assets.thumbnail_path).exists():
            thumbnail_uploaded = self.upload_thumbnail(video_id, Path(assets.thumbnail_path))

        return YouTubeUploadResult(
            video_id=video_id,
            video_url=video_url,
            privacy_status=privacy,
            thumbnail_uploaded=thumbnail_uploaded,
            processing_status="processing",
            is_mock=False,
        )

    def upload_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Uploads a custom thumbnail to YouTube for an existing video."""
        youtube = self._get_youtube_client()
        if not youtube or video_id.startswith("mock_"):
            return True  # Simulated success in mock mode

        try:
            media = MediaFileUpload(str(thumbnail_path), mime_type="image/jpeg")
            youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
            return True
        except Exception:
            return False

    def update_privacy_status(self, video_id: str, new_privacy_status: str) -> bool:
        """Updates the privacy status (e.g. from private to public)."""
        youtube = self._get_youtube_client()
        if not youtube or video_id.startswith("mock_"):
            return True

        try:
            body = {
                "id": video_id,
                "status": {
                    "privacyStatus": new_privacy_status,
                },
            }
            youtube.videos().update(part="status", body=body).execute()
            return True
        except Exception:
            return False
