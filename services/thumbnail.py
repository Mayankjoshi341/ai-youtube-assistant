import os
from pathlib import Path
from typing import List, Tuple, Optional
from models.schemas import VideoAnalysis
from utils.video_utils import get_video_duration, extract_frame
from utils.image_utils import compose_thumbnail
from services.thumbnail_template import generate_branded_thumbnail
from config.settings import get_settings


class ThumbnailService:
    def __init__(self, output_dir: Optional[Path] = None):
        settings = get_settings()
        self.output_dir = output_dir or settings.output_dir

    def get_candidate_timestamps(
        self, video_path: Path, analysis: Optional[VideoAnalysis] = None
    ) -> List[Tuple[int, str]]:
        """
        Determines candidate frame timestamps (timestamp_seconds, label/reason).
        Combines AI-suggested thumbnail moments with evenly spaced sampling.
        """
        duration = get_video_duration(video_path)
        candidates: List[Tuple[int, str]] = []
        seen_secs = set()

        # 1. AI recommended moments
        if analysis and analysis.thumbnail_moments:
            for moment in analysis.thumbnail_moments:
                ts = int(moment.timestamp_seconds)
                if 0 <= ts <= duration and ts not in seen_secs:
                    seen_secs.add(ts)
                    candidates.append((ts, f"AI Suggestion: {moment.reason}"))

        # 2. Regular interval fallback timestamps if duration > 0
        if duration > 0:
            percentages = [0.15, 0.35, 0.50, 0.65, 0.85]
            for pct in percentages:
                ts = int(duration * pct)
                if ts not in seen_secs:
                    seen_secs.add(ts)
                    candidates.append((ts, f"Frame at {ts}s ({int(pct * 100)}%)"))

        if not candidates:
            candidates.append((0, "Start Frame"))

        return candidates

    def create_thumbnail(
        self,
        video_path: Path,
        headline_text: str,
        timestamp_seconds: Optional[int] = None,
        analysis: Optional[VideoAnalysis] = None,
    ) -> Path:
        """
        Extracts selected frame, applies high-contrast headline overlay,
        and saves 1280x720 thumbnail to output directory.
        """
        candidates = self.get_candidate_timestamps(video_path, analysis)

        # Select target timestamp
        if timestamp_seconds is not None:
            target_ts = timestamp_seconds
        else:
            target_ts = candidates[0][0]  # Top candidate

        # Temp raw frame path
        temp_frame_path = self.output_dir / f"temp_frame_{target_ts}s.png"
        final_thumb_path = self.output_dir / "thumbnail.jpg"

        # Extract frame
        success = extract_frame(video_path, float(target_ts), temp_frame_path)
        if not success:
            # Fallback to timestamp 0 if chosen frame fails
            target_ts = 0
            extract_frame(video_path, 0.0, temp_frame_path)

        # Render composite thumbnail with high-contrast text banner
        compose_thumbnail(
            image_path=temp_frame_path,
            output_path=final_thumb_path,
            headline_text=headline_text,
        )

        # Clean up temporary raw frame file
        if temp_frame_path.exists():
            try:
                temp_frame_path.unlink()
            except Exception:
                pass

        return final_thumb_path

    # ─────────────────────────────────────────────────────────────────────────
    # V4.1 — Branded template thumbnail
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Converts a duration in seconds to a human-readable string.
        E.g. 3759 → "01:02:39", 185 → "03:05"
        """
        if seconds <= 0:
            return ""
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def create_branded_thumbnail(
        self,
        video_path: Path,
        analysis: VideoAnalysis,
        tutor_image_path: Optional[Path] = None,
        output_filename: str = "thumbnail_branded.jpg",
    ) -> Path:
        """
        Generates a 1280×720 branded educational thumbnail using the
        deterministic Pillow template renderer.

        Args:
            video_path:       Path to the video file (used for duration extraction).
            analysis:         VideoAnalysis object containing class/subject/topic.
            tutor_image_path: Optional path to the selected tutor photo.
            output_filename:  Filename for the saved thumbnail in the output directory.

        Returns:
            Path to the saved JPEG thumbnail.
        """
        duration_secs = get_video_duration(video_path)
        duration_str = self.format_duration(duration_secs)

        output_path = self.output_dir / output_filename

        return generate_branded_thumbnail(
            class_name=analysis.class_name,
            subject=analysis.subject,
            topic=analysis.topic,
            series_label=analysis.series_label,
            duration=duration_str,
            tutor_image_path=tutor_image_path,
            output_path=output_path,
        )
