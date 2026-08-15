import time
from typing import Dict, List, Optional, Callable
from models.schemas import OrchestratorState, PublishingStatus
from orchestrator.tools import (
    BaseTool,
    ContentAnalysisTool,
    MetadataGenerationTool,
    ThumbnailCompositionTool,
    ValidationReviewerTool,
    YouTubePublishingTool,
    ToolResult,
)


class OrchestratorAgent:
    def __init__(self, state: Optional[OrchestratorState] = None):
        self.state = state or OrchestratorState()
        self.tools: Dict[str, BaseTool] = {
            "analysis": ContentAnalysisTool(),
            "metadata": MetadataGenerationTool(),
            "thumbnail": ThumbnailCompositionTool(),
            "validation": ValidationReviewerTool(),
            "publisher": YouTubePublishingTool(),
        }

    def start_pipeline(self, video_path: str) -> OrchestratorState:
        """Initializes orchestrator state with target video path."""
        self.state = OrchestratorState(
            status=PublishingStatus.IDLE,
            video_path=video_path,
        )
        self.state.log_step(f"Pipeline initialized for video: {video_path}")
        return self.state

    def execute_tool_with_retry(
        self, tool_name: str, max_retries: int = 2, delay_seconds: int = 2, **kwargs
    ) -> ToolResult:
        """Executes a registered tool by name with retry recovery logic."""
        tool = self.tools.get(tool_name)
        if not tool:
            err = f"Tool '{tool_name}' not found in registry."
            self.state.errors.append(err)
            self.state.status = PublishingStatus.FAILED
            return ToolResult(success=False, state=self.state, message=err, error=err)

        last_result = None
        for attempt in range(1, max_retries + 1):
            if kwargs:
                result = tool.execute(self.state, **kwargs)
            else:
                result = tool.execute(self.state)
            self.state = result.state
            if result.success:
                return result

            last_result = result
            if attempt < max_retries:
                self.state.log_step(
                    f"Retrying tool '{tool_name}' (Attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(delay_seconds)

        return last_result or ToolResult(
            success=False,
            state=self.state,
            message=f"Tool '{tool_name}' failed after {max_retries} attempts.",
            error="max retries reached",
        )

    def run_to_checkpoint(
        self,
        video_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> OrchestratorState:
        """
        Runs the full analysis, metadata generation, thumbnail creation, and validation pipeline.
        Pauses execution at the AWAITING_APPROVAL checkpoint for human review.
        """
        if video_path:
            self.start_pipeline(video_path)

        def notify(msg: str):
            if progress_callback:
                progress_callback(msg)

        # 1. Content Analysis
        notify("1️⃣ Analyzing video content via Gemini API (Uploading & Processing)...")
        res1 = self.execute_tool_with_retry("analysis")
        if not res1.success:
            return self.state

        # 2. Metadata Generation
        notify("2️⃣ Generating titles, description, and hashtags...")
        res2 = self.execute_tool_with_retry("metadata")
        if not res2.success:
            return self.state

        # 3. Thumbnail Composition
        notify("3️⃣ Extracting frame & composing 1280x720 thumbnail...")
        res3 = self.execute_tool_with_retry("thumbnail")
        if not res3.success:
            return self.state

        # 4. Automated Validation Review
        notify("4️⃣ Running automated quality checks & pausing for Human Review...")
        res4 = self.execute_tool_with_retry("validation")
        return self.state

    def approve_and_publish(self, force_mock: bool = False) -> OrchestratorState:
        """
        Human approval callback: sets approved_by_user = True and triggers YouTube publishing tool.
        """
        if self.state.status != PublishingStatus.AWAITING_APPROVAL and not self.state.assets:
            err = "Cannot publish: Workflow is not in AWAITING_APPROVAL state or assets are missing."
            self.state.errors.append(err)
            return self.state

        self.state.approved_by_user = True
        self.state.log_step("Human Approval granted! Proceeding to YouTube publishing...")

        res = self.execute_tool_with_retry("publisher", force_mock=force_mock)
        return self.state

