from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from models.schemas import OrchestratorState, PublishingStatus
from services.validation import ValidationService
from services.video_analysis import VideoAnalysisService
from services.metadata import MetadataService
from services.thumbnail import ThumbnailService
from services.youtube_publisher import YouTubePublisherService
from config.settings import get_settings


@dataclass
class ToolResult:
    success: bool
    state: OrchestratorState
    message: str
    error: Optional[str] = None


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def execute(self, state: OrchestratorState) -> ToolResult:
        pass


class ContentAnalysisTool(BaseTool):
    @property
    def name(self) -> str:
        return "ContentAnalysisTool"

    def execute(self, state: OrchestratorState) -> ToolResult:
        if not state.video_path:
            return ToolResult(
                success=False,
                state=state,
                message="No video file provided for analysis.",
                error="video_path missing",
            )

        video_path = Path(state.video_path)
        state.status = PublishingStatus.ANALYZING
        state.log_step("Started video analysis via Gemini Multimodal model...")

        try:
            service = VideoAnalysisService()
            analysis = service.analyze_video(video_path)
            state.analysis = analysis
            state.log_step("Content analysis successfully completed.")
            return ToolResult(
                success=True,
                state=state,
                message="Video analysis completed successfully.",
            )
        except Exception as e:
            err_str = str(e)
            state.status = PublishingStatus.FAILED
            state.errors.append(err_str)
            state.log_step(f"Content analysis failed: {err_str}")
            return ToolResult(
                success=False,
                state=state,
                message=f"Analysis error: {err_str}",
                error=err_str,
            )


class MetadataGenerationTool(BaseTool):
    @property
    def name(self) -> str:
        return "MetadataGenerationTool"

    def execute(self, state: OrchestratorState) -> ToolResult:
        if not state.analysis or not state.video_path:
            return ToolResult(
                success=False,
                state=state,
                message="Cannot generate metadata without video analysis.",
                error="analysis missing",
            )

        state.log_step("Generating title candidates, description, and hashtags...")

        try:
            assets = MetadataService.process_metadata(state.analysis, state.video_path)
            state.assets = assets
            state.status = PublishingStatus.METADATA_READY
            state.log_step("Metadata generation completed.")
            return ToolResult(
                success=True,
                state=state,
                message="Metadata generated successfully.",
            )
        except Exception as e:
            err_str = str(e)
            state.status = PublishingStatus.FAILED
            state.errors.append(err_str)
            state.log_step(f"Metadata generation failed: {err_str}")
            return ToolResult(
                success=False,
                state=state,
                message=f"Metadata error: {err_str}",
                error=err_str,
            )


class ThumbnailCompositionTool(BaseTool):
    @property
    def name(self) -> str:
        return "ThumbnailCompositionTool"

    def execute(self, state: OrchestratorState) -> ToolResult:
        if not state.video_path or not state.assets:
            return ToolResult(
                success=False,
                state=state,
                message="Video path and assets are required for thumbnail generation.",
                error="prerequisites missing",
            )

        state.log_step("Composing branded 1280×720 thumbnail from template...")

        try:
            service = ThumbnailService()
            video_path = Path(state.video_path)

            # Auto-pick the first available tutor photo from assets/tutors/
            tutor_image_path: Optional[Path] = None
            base_dir = Path(__file__).resolve().parent.parent
            tutors_dir = base_dir / "assets" / "tutors"
            if tutors_dir.exists():
                tutor_files = sorted([
                    f for f in tutors_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg"}
                ])
                if tutor_files:
                    tutor_image_path = tutor_files[0]
                    state.log_step(f"Auto-selected tutor photo: {tutor_image_path.name}")
                else:
                    state.log_step("No tutor photos found in assets/tutors/ — generating without tutor photo.")

            thumb_path = service.create_branded_thumbnail(
                video_path=video_path,
                analysis=state.analysis,
                tutor_image_path=tutor_image_path,
            )

            state.assets.thumbnail_path = str(thumb_path)
            state.status = PublishingStatus.THUMBNAIL_READY
            state.log_step("Branded thumbnail composed successfully.")
            return ToolResult(
                success=True,
                state=state,
                message="Branded thumbnail created successfully.",
            )
        except Exception as e:
            err_str = str(e)
            state.status = PublishingStatus.FAILED
            state.errors.append(err_str)
            state.log_step(f"Thumbnail composition failed: {err_str}")
            return ToolResult(
                success=False,
                state=state,
                message=f"Thumbnail error: {err_str}",
                error=err_str,
            )


class ValidationReviewerTool(BaseTool):
    @property
    def name(self) -> str:
        return "ValidationReviewerTool"

    def execute(self, state: OrchestratorState) -> ToolResult:
        state.log_step("Running automated validation review on generated assets...")

        if not state.analysis or not state.assets:
            return ToolResult(
                success=False,
                state=state,
                message="Analysis and assets must be present for validation.",
                error="missing state assets",
            )

        validator = ValidationService()
        is_valid, errors = validator.validate_analysis(state.analysis)

        if not is_valid:
            for err in errors:
                state.errors.append(f"Validation Warning: {err}")
                state.log_step(f"Validation Warning: {err}")

        # Transition to AWAITING_APPROVAL checkpoint
        state.status = PublishingStatus.AWAITING_APPROVAL
        state.log_step("Validation passed. Workflow paused for Human Approval Checkpoint.")

        return ToolResult(
            success=True,
            state=state,
            message="Assets validated. Ready for human review.",
        )


class YouTubePublishingTool(BaseTool):
    @property
    def name(self) -> str:
        return "YouTubePublishingTool"

    def execute(self, state: OrchestratorState, force_mock: bool = False) -> ToolResult:
        if not state.approved_by_user:
            return ToolResult(
                success=False,
                state=state,
                message="Publishing blocked: Human approval required before uploading to YouTube.",
                error="unapproved",
            )

        if not state.assets:
            return ToolResult(
                success=False,
                state=state,
                message="No assets available for YouTube upload.",
                error="assets missing",
            )

        state.status = PublishingStatus.UPLOADING
        state.log_step("Initiating video upload via YouTube Data API v3...")

        try:
            publisher = YouTubePublisherService()
            result = publisher.upload_video(state.assets, force_mock=force_mock)


            state.upload_result = result
            state.status = PublishingStatus.PUBLISHED
            state.log_step(
                f"Video successfully published to YouTube! (ID: {result.video_id}, Mode: {'Mock' if result.is_mock else 'Real'})"
            )

            return ToolResult(
                success=True,
                state=state,
                message=f"Published successfully to YouTube! Video URL: {result.video_url}",
            )
        except Exception as e:
            err_str = str(e)
            state.status = PublishingStatus.FAILED
            state.errors.append(err_str)
            state.log_step(f"YouTube upload failed: {err_str}")
            return ToolResult(
                success=False,
                state=state,
                message=f"YouTube publishing error: {err_str}",
                error=err_str,
            )
