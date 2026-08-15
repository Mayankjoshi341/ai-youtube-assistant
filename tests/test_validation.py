import pytest
from pathlib import Path
from services.validation import ValidationService
from models.schemas import VideoAnalysis, ThumbnailMoment


def test_validate_video_file_extension(tmp_path):
    validator = ValidationService(max_video_size_mb=100)

    # Valid extension
    valid_file = tmp_path / "test.mp4"
    valid_file.write_bytes(b"dummy video data")
    is_valid, msg = validator.validate_file(valid_file)
    assert is_valid is True
    assert msg == ""

    # Invalid extension
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("not a video")
    is_valid, msg = validator.validate_file(invalid_file)
    assert is_valid is False
    assert "Unsupported video format" in msg


def test_validate_video_file_size(tmp_path):
    validator = ValidationService(max_video_size_mb=1)  # 1 MB max

    large_file = tmp_path / "large.mp4"
    # Write 2 MB of dummy data
    large_file.write_bytes(b"0" * (2 * 1024 * 1024))

    is_valid, msg = validator.validate_file(large_file)
    assert is_valid is False
    assert "exceeds maximum allowed limit" in msg


def test_validate_analysis_success():
    validator = ValidationService()
    analysis = VideoAnalysis(
        topic="Python Tutorial",
        summary="A guide to Python functions",
        key_points=["Defines functions", "Explains return statements"],
        audience="Beginner Developers",
        tone="Educational",
        title_candidates=[
            "Python Functions 101",
            "Learn Python Functions",
            "Python Basics",
        ],
        recommended_title="Python Functions 101",
        description="Learn Python functions step by step.",
        hashtags=["#python", "#coding", "#tutorial"],
        thumbnail_moments=[
            ThumbnailMoment(timestamp_seconds=10, reason="Clear code title slide")
        ],
    )

    is_valid, errors = validator.validate_analysis(analysis)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_analysis_missing_fields():
    validator = ValidationService()
    analysis = VideoAnalysis(
        topic="",
        summary="",
        key_points=[],
        audience="Developers",
        tone="Informative",
        title_candidates=["Single Title"],
        recommended_title="",
        description="",
        hashtags=[],
        thumbnail_moments=[],
    )

    is_valid, errors = validator.validate_analysis(analysis)
    assert is_valid is False
    assert len(errors) >= 4
