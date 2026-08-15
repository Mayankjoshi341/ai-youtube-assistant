import os
import json
import time
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from models.schemas import VideoAnalysis
from config.settings import get_settings


class VideoAnalysisService:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self._custom_model_name = model_name

        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "video_analysis.txt"
        if prompt_path.exists():
            self.prompt_text = prompt_path.read_text(encoding="utf-8")
        else:
            self.prompt_text = "Analyze this video and return YouTube title candidates, description, hashtags, and thumbnail moments."

    @property
    def model_name(self) -> str:
        if self._custom_model_name:
            return self._custom_model_name
        return os.getenv("MODEL_NAME") or get_settings().model_name

    def _get_client(self) -> genai.Client:
        key = self.api_key or os.getenv("GEMINI_API_KEY")
        if not key or key.startswith("your_"):
            raise ValueError(
                "Gemini API key is missing or not configured. Please set GEMINI_API_KEY in your .env file."
            )
        return genai.Client(api_key=key)

    def analyze_video(self, video_path: Path, max_retries: int = 3) -> VideoAnalysis:
        """
        Uploads video to Gemini File API, waits for processing, requests structured analysis,
        and cleans up the uploaded file. Includes model fallback and retry logic.
        """
        client = self._get_client()
        uploaded_file = None

        try:
            # 1. Upload file
            uploaded_file = client.files.upload(file=str(video_path))

            # 2. Wait for processing to complete
            max_wait_seconds = 300
            poll_interval = 5
            elapsed = 0

            while elapsed < max_wait_seconds:
                file_info = client.files.get(name=uploaded_file.name)
                state = getattr(file_info, "state", None)

                state_str = str(state).upper()
                if "ACTIVE" in state_str:
                    break
                elif "FAILED" in state_str:
                    raise RuntimeError(
                        f"Gemini video processing failed: {getattr(file_info, 'error', 'Unknown error')}"
                    )

                time.sleep(poll_interval)
                elapsed += poll_interval

            if elapsed >= max_wait_seconds:
                raise TimeoutError("Timed out waiting for video to be processed by Gemini API.")

            # Candidate models sequence (starts with requested model, falls back if 404)
            models_to_try = [self.model_name]
            for fallback in ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]:
                if fallback not in models_to_try:
                    models_to_try.append(fallback)


            last_exception = None
            for current_model in models_to_try:
                for attempt in range(1, max_retries + 1):
                    try:
                        response = client.models.generate_content(
                            model=current_model,
                            contents=[uploaded_file, self.prompt_text],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=VideoAnalysis,
                                temperature=0.3,
                            ),
                        )

                        response_text = response.text
                        if not response_text:
                            raise ValueError("Received empty response text from Gemini model.")

                        # Parse JSON into Pydantic schema
                        analysis = VideoAnalysis.model_validate_json(response_text)
                        return analysis

                    except Exception as e:
                        last_exception = e
                        err_msg = str(e)

                        # If model is 404/NOT_FOUND or 503/UNAVAILABLE, break to try next fallback model immediately
                        if any(code in err_msg for code in ["404", "503", "NOT_FOUND", "UNAVAILABLE"]):
                            break


                        if attempt < max_retries:
                            time.sleep(2 * attempt)

            raise RuntimeError(
                f"Failed to analyze video with models {models_to_try}: {str(last_exception)}"
            ) from last_exception

        finally:
            # Clean up uploaded file from Gemini File API storage
            if uploaded_file and hasattr(uploaded_file, "name"):
                try:
                    client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass
