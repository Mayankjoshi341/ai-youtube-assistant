import json
import os
from pathlib import Path
import streamlit as st

from config.settings import get_settings
from services.validation import ValidationService
from services.youtube_oauth import YouTubeOAuthService
from services.thumbnail import ThumbnailService
from orchestrator.agent import OrchestratorAgent
from models.schemas import PublishingStatus, OrchestratorState

# Page configuration
st.set_page_config(
    page_title="AI YouTube Publishing Assistant (V3)",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished aesthetics
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF0000 0%, #FF4B4B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6C757D;
        margin-bottom: 1.5rem;
    }
    .checkpoint-card {
        background-color: #FFF8E1;
        border-left: 5px solid #FFA000;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .published-card {
        background-color: #E8F5E9;
        border-left: 5px solid #2E7D32;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        font-weight: 600;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = get_settings()

# Initialize Session State
if "usage_counter" not in st.session_state:
    st.session_state.usage_counter = 0
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = OrchestratorAgent()

agent: OrchestratorAgent = st.session_state.orchestrator
oauth_service = YouTubeOAuthService()

# Sidebar Setup
with st.sidebar:
    st.image("https://img.icons8.com/color/96/youtube-play.png", width=64)
    st.title("Settings & Accounts")

    # Gemini API Key configuration
    api_key_input = st.text_input(
        "Gemini API Key",
        value=settings.gemini_api_key if not settings.gemini_api_key.startswith("your_") else "",
        type="password",
        help="API Key for Google Gemini.",
    )
    active_api_key = api_key_input or settings.gemini_api_key
    if active_api_key and not active_api_key.startswith("your_"):
        st.success("✅ Gemini API Key Configured")
    else:
        st.warning("⚠️ Gemini API Key Missing")

    # YouTube OAuth Status
    st.markdown("---")
    st.subheader("YouTube Data API Account")
    if oauth_service.is_authenticated():
        st.success("✅ Connected to YouTube Account")
    elif settings.client_secrets_file.exists():
        st.info("ℹ️ OAuth Client Secrets Found")
        if st.button("🔑 Authorize YouTube Account"):
            creds = oauth_service.get_credentials()
            if creds:
                st.success("Successfully authenticated!")
                st.rerun()
            else:
                st.error("OAuth authorization failed.")
    else:
        st.caption("ℹ️ Running in Mock/Dry-Run Publishing Mode (`client_secret.json` not found).")

    model_name = st.selectbox(
        "Gemini Model",
        options=["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"],
        index=0,
    )


    max_size_mb = st.number_input(
        "Max Video Size (MB)",
        value=settings.max_video_size_mb,
        min_value=10,
        max_value=2000,
        step=50,
    )

    st.markdown("---")
    st.metric("Session Videos Processed", st.session_state.usage_counter)
    st.caption("AI YouTube Publishing Assistant V3.0 (Agentic Architecture)")

# Main Header
st.markdown('<div class="main-header">🎬 AI YouTube Publishing Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Agentic workflow that analyzes videos, generates assets, enforces human review, and publishes directly to YouTube.</div>',
    unsafe_allow_html=True,
)

# Step 1: File Upload
uploaded_file = st.file_uploader(
    "Choose a video file (MP4, MOV, AVI, WMV, WebM, MKV)",
    type=["mp4", "mov", "avi", "wmv", "webm", "mkv"],
)

validator = ValidationService(max_video_size_mb=max_size_mb)

if uploaded_file is not None:
    file_path = settings.upload_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    is_valid, err_msg = validator.validate_file(file_path)
    if not is_valid:
        st.error(f"❌ File Validation Error: {err_msg}")
    else:
        st.success(f"✅ Video ready: `{uploaded_file.name}` ({file_path.stat().st_size / (1024*1024):.1f} MB)")

        if st.button("🚀 Run Agentic Orchestrator (Analysis & Assets)", type="primary", use_container_width=True):
            if not active_api_key or active_api_key.startswith("your_"):
                st.error("Please configure your Gemini API Key in the sidebar before running.")
            else:
                os.environ["GEMINI_API_KEY"] = active_api_key
                os.environ["MODEL_NAME"] = model_name

                with st.status("Agentic Orchestrator in progress...", expanded=True) as status:
                    agent.start_pipeline(str(file_path))
                    agent.run_to_checkpoint(progress_callback=st.write)

                    if agent.state.status == PublishingStatus.FAILED:
                        status.update(label="❌ Orchestrator Pipeline Failed", state="error", expanded=True)
                    else:
                        status.update(label="✅ Asset Generation Complete! Awaiting Human Approval.", state="complete", expanded=False)
                        st.session_state.usage_counter += 1
                        st.rerun()

# Display Execution Log Expander if state exists
if agent.state.step_logs:
    with st.expander("📜 Agentic Execution Log", expanded=False):
        for log in agent.state.step_logs:
            st.text(f"• {log}")

# Display Errors if failed
if agent.state.status == PublishingStatus.FAILED and agent.state.errors:
    st.error(f"❌ Orchestrator Error: {agent.state.errors[-1]}")

# Display Assets & Human Approval Checkpoint
if agent.state.assets and agent.state.analysis:
    assets = agent.state.assets
    analysis = agent.state.analysis

    st.markdown("---")

    # Display Published Result Banner if video is published
    if agent.state.status == PublishingStatus.PUBLISHED and agent.state.upload_result:
        res = agent.state.upload_result
        st.markdown(
            f"""
            <div class="published-card">
                <h3>🎉 Video Successfully Published to YouTube!</h3>
                <p><strong>Video ID:</strong> <code>{res.video_id}</code> | <strong>Privacy:</strong> <code>{res.privacy_status.upper()}</code> | <strong>Mode:</strong> {'Mock (Dry-Run)' if res.is_mock else 'Real Upload'}</p>
                <p><a href="{res.video_url}" target="_blank" style="font-weight: bold; color: #1B5E20; text-decoration: underline;">👉 Click here to watch on YouTube</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Human Approval Checkpoint Card
    if agent.state.status == PublishingStatus.AWAITING_APPROVAL:
        st.markdown(
            """
            <div class="checkpoint-card">
                <h3>✋ Human Approval Checkpoint</h3>
                <p>Review the generated metadata and thumbnail below. When you are satisfied, select your privacy setting and click <strong>Approve & Upload to YouTube</strong>.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.header("📋 Publishing Asset Review")

    # Factual understanding accordion
    with st.expander("🔍 AI Video Content Understanding (Factual Summary)", expanded=False):
        st.markdown(f"**Topic:** {analysis.topic}")
        st.markdown(f"**Audience:** {analysis.audience}")
        st.markdown(f"**Tone:** {analysis.tone}")
        st.markdown(f"**Factual Summary:** {analysis.summary}")
        if analysis.key_points:
            st.markdown("**Key Points:**")
            for pt in analysis.key_points:
                st.markdown(f"- {pt}")

    col_meta, col_thumb = st.columns([3, 2])

    with col_meta:
        st.subheader("1. Title Selection")
        selected_title_radio = st.radio(
            "AI Candidate Titles:",
            options=analysis.title_candidates,
            index=analysis.title_candidates.index(assets.selected_title)
            if assets.selected_title in analysis.title_candidates
            else 0,
        )

        final_title = st.text_input("Final Selected Title (Editable):", value=selected_title_radio)
        assets.selected_title = final_title

        st.subheader("2. Description")
        final_description = st.text_area("YouTube Description (Editable):", value=assets.description, height=220)
        assets.description = final_description

        st.subheader("3. Hashtags")
        hashtags_str = " ".join(assets.hashtags)
        final_hashtags_input = st.text_input("Hashtags (Space separated):", value=hashtags_str)
        assets.hashtags = final_hashtags_input.split()

    with col_thumb:
        st.subheader("4. Thumbnail Preview")
        if assets.thumbnail_path and Path(assets.thumbnail_path).exists():
            st.image(assets.thumbnail_path, caption="YouTube Thumbnail (1280x720 - 16:9)", use_container_width=True)

            with open(assets.thumbnail_path, "rb") as file:
                st.download_button(
                    label="📥 Download Thumbnail (JPG)",
                    data=file,
                    file_name="youtube_thumbnail.jpg",
                    mime="image/jpeg",
                    use_container_width=True,
                )

        st.markdown("---")
        st.subheader("🖼️ Thumbnail Customization")

        thumbnail_service = ThumbnailService(output_dir=settings.output_dir)

        # ── Tutor Photo Selector ──────────────────────────────────────────
        base_dir = Path(__file__).resolve().parent
        tutors_dir = base_dir / "assets" / "tutors"
        tutors_dir.mkdir(parents=True, exist_ok=True)

        tutor_files = sorted([
            f for f in tutors_dir.iterdir()
            if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg"}
        ])

        selected_tutor_path = None
        if tutor_files:
            st.markdown("**👤 Tutor Photo**")
            tutor_names = [f.name for f in tutor_files]
            selected_tutor_name = st.selectbox(
                "Select Tutor:",
                options=tutor_names,
                help="Photos from assets/tutors/ — add more PNGs/JPGs there to expand the list.",
            )
            selected_tutor_path = tutors_dir / selected_tutor_name
            st.caption(f"📁 `assets/tutors/{selected_tutor_name}`")
        else:
            st.info(
                "ℹ️ No tutor photos found.\n\n"
                "Add `.png` or `.jpg` photos to `assets/tutors/` and they will appear here."
            )

        # ── Regenerate Branded Thumbnail ──────────────────────────────────
        if st.button("🔄 Regenerate Branded Thumbnail", use_container_width=True):
            with st.spinner("Re-rendering branded thumbnail..."):
                new_thumb = thumbnail_service.create_branded_thumbnail(
                    video_path=Path(assets.video_path),
                    analysis=analysis,
                    tutor_image_path=selected_tutor_path,
                )
                assets.thumbnail_path = str(new_thumb)
                st.success("✅ Thumbnail updated!")
                st.rerun()

        # ── Advanced: Video Frame Selector (collapsed) ────────────────────
        with st.expander("⚙️ Advanced: Video Frame Overlay (Legacy)", expanded=False):
            st.caption("Select a specific video frame and apply a text headline overlay instead of the branded template.")
            candidate_moments = thumbnail_service.get_candidate_timestamps(Path(assets.video_path), analysis)
            moment_options = [f"{ts}s - {label}" for ts, label in candidate_moments]
            selected_moment_str = st.selectbox("Select Candidate Frame:", options=moment_options, key="frame_select_adv")
            selected_ts = int(selected_moment_str.split("s")[0])

            custom_headline = st.text_input(
                "Headline Text:",
                value=analysis.topic[:35] if analysis.topic else "WATCH THIS",
                key="headline_adv",
            )

            if st.button("🔄 Use Frame Overlay Instead", key="regen_frame"):
                with st.spinner("Composing frame overlay thumbnail..."):
                    new_thumb = thumbnail_service.create_thumbnail(
                        video_path=Path(assets.video_path),
                        headline_text=custom_headline,
                        timestamp_seconds=selected_ts,
                        analysis=analysis,
                    )
                    assets.thumbnail_path = str(new_thumb)
                    st.success("Thumbnail updated (frame overlay)!")
                    st.rerun()

    # YouTube Upload Trigger Section (Human Approval Action)
    st.markdown("---")
    st.subheader("🚀 Direct YouTube Upload (V2 / V3 Agentic Action)")

    col_pub1, col_pub2 = st.columns([2, 3])
    with col_pub1:
        privacy_choice = st.selectbox(
            "Target YouTube Privacy Setting:",
            options=["private", "unlisted", "public"],
            index=0,
            help="Videos are uploaded in Private mode by default for safety.",
        )

    with col_pub2:
        st.write("") # vertical alignment spacer
        st.write("")
        if st.button("✅ Approve & Publish to YouTube", type="primary", use_container_width=True):
            settings.default_privacy_status = privacy_choice
            with st.spinner("Executing YouTubePublishingTool..."):
                agent.approve_and_publish()
                st.rerun()

    # Export Metadata Section
    st.markdown("---")
    st.subheader("📦 Export Local Publishing Assets")
    col_exp1, col_exp2 = st.columns(2)

    export_json = json.dumps(
        {
            "title": assets.selected_title,
            "description": assets.description,
            "hashtags": assets.hashtags,
            "topic": analysis.topic,
            "summary": analysis.summary,
        },
        indent=2,
    )

    with col_exp1:
        st.download_button(
            label="📄 Download Metadata JSON",
            data=export_json,
            file_name="youtube_publishing_metadata.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_exp2:
        copy_text = f"TITLE:\n{assets.selected_title}\n\nDESCRIPTION:\n{assets.description}\n\nHASHTAGS:\n{' '.join(assets.hashtags)}"
        st.download_button(
            label="📋 Download Text File (YouTube Copy-Paste)",
            data=copy_text,
            file_name="youtube_publishing_text.txt",
            mime="text/plain",
            use_container_width=True,
        )
