# 🎬 AI YouTube Publishing Assistant

An AI-assisted YouTube publishing system that accepts an existing video file and automatically analyzes it to produce four key publishing assets:
1. **YouTube Title** (with AI candidate recommendations and custom editing)
2. **YouTube Description** (factual, readable summary based on video content)
3. **Hashtags** (normalized, deduplicated set of relevant tags)
4. **Thumbnail** (frame extracted locally and styled in 1280×720 HD format with high-contrast headline overlay)

Built with **Python**, **Streamlit**, **Google Gemini API** (`google-genai`), **OpenCV**, and **Pillow**.

---

## 🚀 Features

- **Multimodal Video Understanding:** Sends uploaded video directly to Gemini Multimodal models for accurate factual analysis without hallucination.
- **Structured AI Output:** Uses Pydantic schemas to strictly enforce machine-readable JSON responses from Gemini.
- **Local Thumbnail Composition:** Samples video frames with OpenCV, resizes to 16:9 (1280×720), and overlays high-contrast bold headlines with dark translucent contrast badges.
- **Interactive Streamlit Web UI:** Upload video, preview AI understanding, edit titles/description/hashtags, customize thumbnail candidate frames and headlines, and download ready-to-publish assets.
- **Near-Zero Cost & High Reliability:** Performs heavy media operations locally without paid image generation APIs.

---

## 🛠️ Setup & Installation

### Prerequisites
- **Python 3.11+** installed
- **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/)

### 1. Clone & Navigate to Project
```bash
cd ai-youtube-assistant
```

### 2. Create and Activate Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and set your `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=AIzaSy...
MODEL_NAME=gemini-2.5-flash
MAX_VIDEO_SIZE_MB=500
```

---

## 🖥️ Running the Application

Launch the Streamlit web interface:
```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

---

## 🧪 Running Tests

To run the automated validation and thumbnail unit tests:
```bash
pytest tests/ -v
```

---

## 📁 Project Structure

```
ai-youtube-assistant/
├── app.py                     # Streamlit user interface
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── config/
│   └── settings.py            # Typed settings & env loader
├── models/
│   └── schemas.py             # Pydantic JSON schemas
├── services/
│   ├── video_analysis.py      # Gemini API integration & polling
│   ├── metadata.py            # Title/desc/hashtag processing
│   ├── thumbnail.py           # Frame selection & thumbnail composition
│   └── validation.py         # File & asset validation rules
├── prompts/
│   └── video_analysis.txt     # Gemini multimodal prompt
├── utils/
│   ├── video_utils.py         # OpenCV / FFmpeg frame extraction & duration
│   └── image_utils.py         # Pillow 16:9 cropping & text overlay
├── tests/
│   ├── test_validation.py     # Unit tests for validation
│   └── test_thumbnail.py      # Unit tests for thumbnail generation
└── data/
    ├── uploads/               # Temporary uploaded video storage
    └── outputs/               # Generated thumbnails and metadata outputs
```

---

## 🔒 Security & Privacy

- `GEMINI_API_KEY` is loaded securely via environment variables and never logged or exposed in UI outputs.
- Uploaded video files on Gemini File API are automatically deleted immediately after analysis completes.
