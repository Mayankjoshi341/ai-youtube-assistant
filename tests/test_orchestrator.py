import pytest
from pathlib import Path
from models.schemas import (
    OrchestratorState,
    PublishingStatus,
    VideoAnalysis,
    PublishingAssets,
    ThumbnailMoment,
)
from orchestrator.agent import OrchestratorAgent
from orchestrator.tools import YouTubePublishingTool


def test_orchestrator_initialization():
    agent = OrchestratorAgent()
    state = agent.start_pipeline("data/uploads/test.mp4")
    assert state.status == PublishingStatus.IDLE
    assert state.video_path == "data/uploads/test.mp4"
    assert len(state.step_logs) == 1


def test_youtube_tool_blocks_unapproved_publishing():
    tool = YouTubePublishingTool()
    state = OrchestratorState(
        status=PublishingStatus.AWAITING_APPROVAL,
        approved_by_user=False,
    )
    result = tool.execute(state)
    assert result.success is False
    assert "Human approval required" in result.message
    assert result.error == "unapproved"


def test_orchestrator_approval_and_publish_flow():
    agent = OrchestratorAgent()
    agent.start_pipeline("data/uploads/sample.mp4")

    # Manually populate state to simulate state at checkpoint
    dummy_analysis = VideoAnalysis(
        topic="OpenCV Image Processing",
        summary="Tutorial on OpenCV and Pillow",
        key_points=["OpenCV crop", "Pillow text overlay"],
        audience="Developers",
        tone="Technical",
        title_candidates=["OpenCV Guide", "Pillow Guide", "Python Image Processing"],
        recommended_title="Python Image Processing",
        description="Comprehensive guide to image processing in Python.",
        hashtags=["#opencv", "#python"],
        thumbnail_moments=[ThumbnailMoment(timestamp_seconds=5, reason="Nice frame")],
    )

    agent.state.analysis = dummy_analysis
    agent.state.assets = PublishingAssets(
        selected_title="Python Image Processing Tutorial",
        description="Learn OpenCV and Pillow.",
        hashtags=["#opencv", "#python"],
        thumbnail_path=None,
        video_path="data/uploads/sample.mp4",
        analysis=dummy_analysis,
    )
    agent.state.status = PublishingStatus.AWAITING_APPROVAL

    # Trigger human approval
    final_state = agent.approve_and_publish(force_mock=True)

    assert final_state.approved_by_user is True
    assert final_state.status == PublishingStatus.PUBLISHED
    assert final_state.upload_result is not None
    assert final_state.upload_result.is_mock is True
    assert "published to YouTube" in final_state.step_logs[-1]
