from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PublishingStatus(str, Enum):
    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    METADATA_READY = "METADATA_READY"
    THUMBNAIL_READY = "THUMBNAIL_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class ThumbnailMoment(BaseModel):
    timestamp_seconds: int = Field(
        ..., description="Timestamp in seconds for a visually compelling frame"
    )
    reason: str = Field(
        ..., description="Why this moment is strong for a thumbnail frame"
    )


class VideoAnalysis(BaseModel):
    topic: str = Field(..., description="Main subject or topic of the video")
    # --- Structured educational metadata (for thumbnail template) ---
    class_name: Optional[str] = Field(
        None,
        description="Class/grade level if applicable, e.g. 'CLASS IX', 'CLASS X', 'CLASS XII'",
    )
    subject: Optional[str] = Field(
        None,
        description="Academic subject if applicable, e.g. 'MATHS', 'BIOLOGY', 'PHYSICS', 'CHEMISTRY'",
    )
    series_label: Optional[str] = Field(
        None,
        description="Exercise / chapter / series label, e.g. 'NCERT EXERCISE', 'CHAPTER 2', 'PART 3'",
    )
    # ----------------------------------------------------------------
    summary: str = Field(
        ..., description="Factual summary of what actually happens in the video"
    )
    key_points: List[str] = Field(
        default_factory=list, description="Important events, facts, or demonstrations"
    )
    audience: str = Field(..., description="Intended viewer demographic or interest group")
    tone: str = Field(..., description="Overall style and tone of the video content")
    title_candidates: List[str] = Field(
        ..., description="List of 3 to 5 candidate titles"
    )
    recommended_title: str = Field(
        ..., description="The top recommended title selected from candidates"
    )
    description: str = Field(
        ..., description="Accurate YouTube-ready video description (150-300 words, structured)"
    )
    hashtags: List[str] = Field(
        ..., description="Relevant YouTube hashtags starting with #"
    )
    thumbnail_moments: List[ThumbnailMoment] = Field(
        default_factory=list,
        description="List of timestamps with strong visual thumbnail potential",
    )


class PublishingAssets(BaseModel):
    selected_title: str
    description: str
    hashtags: List[str]
    thumbnail_path: Optional[str] = None
    video_path: str
    analysis: VideoAnalysis


class YouTubeUploadResult(BaseModel):
    video_id: str
    video_url: str
    privacy_status: str = "private"
    thumbnail_uploaded: bool = False
    processing_status: str = "uploaded"
    is_mock: bool = False


class OrchestratorState(BaseModel):
    status: PublishingStatus = PublishingStatus.IDLE
    video_path: Optional[str] = None
    analysis: Optional[VideoAnalysis] = None
    assets: Optional[PublishingAssets] = None
    upload_result: Optional[YouTubeUploadResult] = None
    approved_by_user: bool = False
    errors: List[str] = Field(default_factory=list)
    step_logs: List[str] = Field(default_factory=list)

    def log_step(self, message: str) -> None:
        self.step_logs.append(message)
