import pytest
from pathlib import Path
from models.schemas import VideoAnalysis, PublishingAssets, YouTubeUploadResult
from services.youtube_publisher import YouTubePublisherService


def test_youtube_publisher_mock_upload():
    service = YouTubePublisherService()

    dummy_analysis = VideoAnalysis(
        topic="Python Tutorial",
        summary="A summary of Python basics",
        key_points=["Variables", "Loops"],
        audience="Beginners",
        tone="Educational",
        title_candidates=["Title 1", "Title 2", "Title 3"],
        recommended_title="Title 1",
        description="Learn Python basics step by step.",
        hashtags=["#python", "#coding"],
        thumbnail_moments=[],
    )

    assets = PublishingAssets(
        selected_title="Learn Python Basics in 10 Minutes",
        description="A great tutorial on Python.",
        hashtags=["#python", "#programming"],
        thumbnail_path=None,
        video_path="data/uploads/sample.mp4",
        analysis=dummy_analysis,
    )

    result = service.upload_video(assets, force_mock=True, privacy_status="private")

    assert isinstance(result, YouTubeUploadResult)
    assert result.is_mock is True
    assert result.video_id.startswith("mock_")
    assert "youtube.com/watch?v=mock_" in result.video_url
    assert result.privacy_status == "private"


def test_youtube_publisher_update_privacy_mock():
    service = YouTubePublisherService()
    success = service.update_privacy_status("mock_12345", "public")
    assert success is True
