import os
import asyncio
import datetime
import ffmpeg
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from squad_os.tools.base import BaseTool
from squad_os.core.utils import is_safe_path

class BrowserControlTool(BaseTool):
    name = "browser_control"
    description = (
        "Control a web browser to navigate, click, type, and capture screenshots or videos. "
        "Actions: 'navigate', 'click', 'type', 'screenshot', 'start_recording', 'stop_recording'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["navigate", "click", "type", "screenshot", "start_recording", "stop_recording"]},
            "url": {"type": "string", "description": "URL to navigate to"},
            "selector": {"type": "string", "description": "CSS selector for click or type actions"},
            "text": {"type": "string", "description": "Text to type"},
            "description": {"type": "string", "description": "Description for the screenshot or video file"},
            "wait_for": {"type": "string", "description": "Optional CSS selector to wait for after action"}
        },
        "required": ["action"]
    }

    def __init__(self, branch_id: Optional[str] = None):
        if branch_id:
            self.output_dir = os.path.join("workspace", "projects", branch_id, "visuals")
        else:
            self.output_dir = os.path.join("workspace", "outputs", "visuals")

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def _ensure_browser(self, record_video: bool = False):
        if not self._playwright:
            self._playwright = await async_playwright().start()

        if not self._browser:
            self._browser = await self._playwright.chromium.launch(headless=True)

        if not self._context:
            context_args = {}
            if record_video:
                context_args["record_video_dir"] = self.output_dir
            self._context = await self._browser.new_context(**context_args)
            self._page = await self._context.new_page()

    async def execute(self, action: str, url: str = None, selector: str = None, text: str = None, description: str = None, wait_for: str = None) -> str:
        try:
            if action == "start_recording":
                if self._context:
                    await self._context.close()
                    self._context = None
                    self._page = None
                await self._ensure_browser(record_video=True)
                return "Video recording started. Actions will be recorded until 'stop_recording' is called."

            await self._ensure_browser()

            if action == "navigate":
                if not url: return "Error: URL is required for navigate action."
                # Security check: Prevent SSRF and local file disclosure (e.g., file://)
                if not any(url.startswith(p) for p in ["http://", "https://"]):
                    return f"Error: Access denied. Protocol not allowed for URL: {url}"
                await self._page.goto(url)
                if wait_for:
                    await self._page.wait_for_selector(wait_for)
                return f"Navigated to {url}"

            elif action == "click":
                if not selector: return "Error: Selector is required for click action."
                await self._page.click(selector)
                if wait_for:
                    await self._page.wait_for_selector(wait_for)
                return f"Clicked on {selector}"

            elif action == "type":
                if not selector or text is None: return "Error: Selector and text are required for type action."
                await self._page.fill(selector, text)
                if wait_for:
                    await self._page.wait_for_selector(wait_for)
                return f"Typed '{text}' into {selector}"

            elif action == "screenshot":
                desc = description or "screenshot"
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{desc.replace(' ', '_')}.png"
                filepath = os.path.join(self.output_dir, filename)
                await self._page.screenshot(path=filepath)
                return f"Screenshot saved to {filepath}"

            elif action == "stop_recording":
                if not self._context: return "Error: No active browser session recording."
                video_page = self._page
                # Get the video path BEFORE closing the context if possible
                video_obj = video_page.video
                if not video_obj:
                    await self._context.close()
                    self._context = None
                    self._page = None
                    return "Error: Video recording was not enabled for this session."

                # We need to close context to ensure the video file is flushed and closed by Playwright
                await self._context.close()
                self._context = None
                self._page = None

                video_path = await video_obj.path()
                if video_path and os.path.exists(video_path):
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    desc = description or "demo"
                    mp4_filename = f"{timestamp}_{desc.replace(' ', '_')}.mp4"
                    mp4_filepath = os.path.join(self.output_dir, mp4_filename)

                    try:
                        # Convert .webm to .mp4 using ffmpeg
                        ffmpeg.input(video_path).output(mp4_filepath, vcodec='libx264', crf=23, preset='veryfast').run(overwrite_output=True, quiet=True)
                        # Optionally remove the original .webm file
                        os.remove(video_path)
                        return f"Video recording saved and converted to {mp4_filepath}"
                    except Exception as fe:
                        return f"Video saved to {video_path}, but MP4 conversion failed: {str(fe)}"
                return "Video recording stopped, but no video file was found."

            else:
                return f"Error: Unknown action '{action}'"

        except Exception as e:
            return f"Browser error: {str(e)}"

    async def cleanup(self):
        """Should be called to release browser resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._context = None
        self._browser = None
        self._playwright = None
        self._page = None

class VisionAnalysisTool(BaseTool):
    name = "vision_analysis"
    description = "Analyze an image or screenshot using a vision-capable LLM. Provide the image path and a query."
    parameters = {
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Path to the image file"},
            "query": {"type": "string", "description": "What to look for or analyze in the image"}
        },
        "required": ["image_path", "query"]
    }

    async def execute(self, image_path: str, query: str) -> str:
        # Security Check: Prevent reading images outside the designated areas
        # VisionAnalysisTool can read from workspace/projects/ (active) or workspace/outputs/ (legacy)

        # We need to resolve image_path relative to the current working directory first,
        # then check if it lies within our allowed sandbox.
        abs_image_path = os.path.abspath(image_path)
        is_safe = is_safe_path("workspace/projects", abs_image_path) or \
                  is_safe_path("workspace/outputs", abs_image_path) or \
                  is_safe_path("workspace/archives", abs_image_path)

        if not is_safe:
            return f"Error: Access denied. Image path '{image_path}' is outside the workspace."

        if not os.path.exists(image_path):
            alt_path = os.path.join("workspace", "outputs", "visuals", os.path.basename(image_path))
            if os.path.exists(alt_path):
                image_path = alt_path
            else:
                return f"Error: Image file not found at {image_path}"

        import litellm
        import base64
        import mimetypes

        def encode_image(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')

        try:
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/png" # Default

            base64_image = encode_image(image_path)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            response = await litellm.acompletion(model="gpt-4o-mini", messages=messages)
            return response.choices[0].message.content
        except Exception as e:
            return f"Vision analysis error: {str(e)}"
