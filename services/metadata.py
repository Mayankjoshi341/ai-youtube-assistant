import re
from typing import List
from models.schemas import VideoAnalysis, PublishingAssets


class MetadataService:
    @staticmethod
    def normalize_hashtags(raw_hashtags: List[str]) -> List[str]:
        """
        Normalizes hashtags:
        - Ensures leading '#'
        - Removes invalid characters/spaces
        - Deduplicates while preserving order and case
        """
        normalized = []
        seen = set()

        for tag in raw_hashtags:
            if not tag:
                continue

            # Strip leading # if present, remove spaces & non-alphanumeric except underscores
            clean_tag = tag.strip().lstrip("#")
            clean_tag = re.sub(r"[^\w]", "", clean_tag)

            if not clean_tag:
                continue

            formatted = f"#{clean_tag}"
            lower_tag = formatted.lower()

            if lower_tag not in seen:
                seen.add(lower_tag)
                normalized.append(formatted)

        return normalized

    @staticmethod
    def process_metadata(analysis: VideoAnalysis, video_path: str) -> PublishingAssets:
        """Transforms VideoAnalysis into PublishingAssets bundle."""
        clean_hashtags = MetadataService.normalize_hashtags(analysis.hashtags)

        # Ensure description fits YouTube 5000 character limit
        description = analysis.description.strip()
        if len(description) > 5000:
            description = description[:4997] + "..."

        selected_title = analysis.recommended_title
        if not selected_title and analysis.title_candidates:
            selected_title = analysis.title_candidates[0]

        return PublishingAssets(
            selected_title=selected_title,
            description=description,
            hashtags=clean_hashtags,
            thumbnail_path=None,
            video_path=str(video_path),
            analysis=analysis,
        )
