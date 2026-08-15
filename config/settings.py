import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


@dataclass
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "gemini-3.5-flash")
    max_video_size_mb: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))


    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "data/outputs"))
    client_secrets_file: Path = Path(os.getenv("CLIENT_SECRETS_FILE", "client_secret.json"))
    token_file: Path = Path(os.getenv("TOKEN_FILE", "token.json"))
    default_privacy_status: str = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")

    def __post_init__(self):
        # Base directory relative to project root
        base_dir = Path(__file__).resolve().parent.parent
        if not self.upload_dir.is_absolute():
            self.upload_dir = base_dir / self.upload_dir
        if not self.output_dir.is_absolute():
            self.output_dir = base_dir / self.output_dir
        if not self.client_secrets_file.is_absolute():
            self.client_secrets_file = base_dir / self.client_secrets_file
        if not self.token_file.is_absolute():
            self.token_file = base_dir / self.token_file

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)



def get_settings() -> Settings:
    return Settings()
