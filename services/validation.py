from pathlib import Path
from typing import Tuple, List, Optional
from models.schemas import VideoAnalysis
from utils.video_utils import validate_video_file


class ValidationService:
    def __init__(self, max_video_size_mb: int = 500):
        self.max_video_size_mb = max_video_size_mb

    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """Validates video file format and size."""
        return validate_video_file(file_path, max_size_mb=self.max_video_size_mb)

    def validate_analysis(self, analysis: VideoAnalysis) -> Tuple[bool, List[str]]:
        """
        Validates structure and content of AI analysis output.
        Returns (is_valid, list_of_error_messages).
        """
        errors = []

        if not analysis.topic or not analysis.topic.strip():
            errors.append("Topic is missing or empty.")

        if not analysis.summary or not analysis.summary.strip():
            errors.append("Summary is missing or empty.")

        if not analysis.title_candidates or len(analysis.title_candidates) < 3:
            errors.append(
                f"Expected at least 3 title candidates, got {len(analysis.title_candidates) if analysis.title_candidates else 0}."
            )

        if not analysis.recommended_title or not analysis.recommended_title.strip():
            errors.append("Recommended title is missing or empty.")

        if not analysis.description or not analysis.description.strip():
            errors.append("Description is missing or empty.")

        if not analysis.hashtags:
            errors.append("Hashtags list is missing or empty.")

        return (len(errors) == 0, errors)
