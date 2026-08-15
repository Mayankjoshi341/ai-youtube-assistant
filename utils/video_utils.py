import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import cv2


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".wmv", ".webm", ".mkv"}


def validate_video_file(
    file_path: Path, max_size_mb: int = 500, allowed_exts: Optional[set] = None
) -> Tuple[bool, str]:
    """Validates file existence, extension, and file size."""
    if allowed_exts is None:
        allowed_exts = ALLOWED_EXTENSIONS

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return False, f"File not found: {file_path}"

    ext = path.suffix.lower()
    if ext not in allowed_exts:
        return (
            False,
            f"Unsupported video format '{ext}'. Allowed formats: {', '.join(sorted(allowed_exts))}",
        )

    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return (
            False,
            f"File size ({file_size_mb:.1f} MB) exceeds maximum allowed limit ({max_size_mb} MB).",
        )

    return True, ""


def get_video_duration(video_path: Path) -> float:
    """Returns video duration in seconds using OpenCV, falling back to ffprobe."""
    path_str = str(video_path)

    # Primary method: OpenCV
    cap = cv2.VideoCapture(path_str)
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        if fps > 0 and frame_count > 0:
            return float(frame_count / fps)

    # Fallback method: ffprobe
    if shutil.which("ffprobe"):
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path_str,
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            pass

    return 0.0


def extract_frame_cv2(video_path: Path, timestamp_seconds: float, output_path: Path) -> bool:
    """Extracts a single frame at a specific timestamp using OpenCV."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    target_frame = int(timestamp_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    success, frame = cap.read()
    if not success:
        # Retry with millisecond positioning
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000.0)
        success, frame = cap.read()

    cap.release()

    if success and frame is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), frame)
        return True

    return False


def extract_frame(video_path: Path, timestamp_seconds: float, output_path: Path) -> bool:
    """Extracts frame using OpenCV first, falling back to FFmpeg binary if present."""
    if extract_frame_cv2(video_path, timestamp_seconds, output_path):
        return True

    # Fallback to ffmpeg CLI
    if shutil.which("ffmpeg"):
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(timestamp_seconds),
                "-i",
                str(video_path),
                "-vframes",
                "1",
                "-q:v",
                "2",
                str(output_path),
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return output_path.exists()
        except Exception:
            pass

    return False
