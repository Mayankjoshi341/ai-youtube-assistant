import pytest
from pathlib import Path
from PIL import Image
from utils.image_utils import compose_thumbnail, TARGET_WIDTH, TARGET_HEIGHT


def test_compose_thumbnail_dimensions(tmp_path):
    # Create a 1920x1080 synthetic image frame
    input_frame = tmp_path / "frame_input.png"
    img = Image.new("RGB", (1920, 1080), color=(73, 109, 137))
    img.save(input_frame)

    output_thumb = tmp_path / "thumbnail_output.jpg"
    headline = "How to Code in Python"

    result_path = compose_thumbnail(input_frame, output_thumb, headline)

    assert result_path.exists()
    assert result_path == output_thumb

    with Image.open(result_path) as res_img:
        assert res_img.size == (TARGET_WIDTH, TARGET_HEIGHT)
        assert res_img.format == "JPEG"
