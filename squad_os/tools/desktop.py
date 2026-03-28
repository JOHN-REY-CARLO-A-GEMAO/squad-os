import os
import asyncio
import datetime
from typing import Optional
from squad_os.tools.base import BaseTool

class DesktopControlTool(BaseTool):
    name = "desktop_control"
    description = (
        "Control the desktop: take screenshots, open apps, click, type text, "
        "read screen content via OCR, and find/focus windows. "
        "Actions: 'screenshot', 'open_app', 'click', 'type_text', 'read_screen', 'find_window'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "open_app", "click", "type_text", "read_screen", "find_window"]
            },
            "app": {"type": "string", "description": "App name or full path for open_app"},
            "x": {"type": "integer", "description": "X coordinate for click"},
            "y": {"type": "integer", "description": "Y coordinate for click"},
            "text": {"type": "string", "description": "Text to type"},
            "window_title": {"type": "string", "description": "Window title for find_window"},
            "description": {"type": "string", "description": "Description for screenshot filename"},
            "region": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional region [x, y, width, height] for read_screen"
            }
        },
        "required": ["action"]
    }

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join("workspace", "outputs", "visuals")
        os.makedirs(self.output_dir, exist_ok=True)

    async def execute(self, action: str, app: str = None, x: int = None, y: int = None,
                      text: str = None, window_title: str = None,
                      description: str = None, region: list = None) -> str:
        try:
            if action == "screenshot":
                return await self._screenshot(description)
            elif action == "open_app":
                return await self._open_app(app)
            elif action == "click":
                return await self._click(x, y)
            elif action == "type_text":
                return await self._type_text(text)
            elif action == "read_screen":
                return await self._read_screen(region)
            elif action == "find_window":
                return await self._find_window(window_title)
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"DesktopControlTool error: {str(e)}"

    async def _screenshot(self, description: str = None) -> str:
        import pyautogui
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        desc = description or "screenshot"
        filename = f"{timestamp}_{desc.replace(' ', '_')}.png"
        filepath = os.path.join(self.output_dir, filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        return f"Screenshot saved to {filepath}"

    async def _open_app(self, app: str) -> str:
        if not app:
            return "Error: app name or path is required."
        try:
            from pywinauto import Application
            app_obj = Application().start(app)
            await asyncio.sleep(1)
            return f"Opened app: {app}"
        except Exception:
            # Fallback to os.startfile for simple app names
            import subprocess
            subprocess.Popen(app, shell=True)
            await asyncio.sleep(1)
            return f"Opened app: {app}"

    async def _click(self, x: int, y: int) -> str:
        if x is None or y is None:
            return "Error: x and y coordinates are required for click."
        import pyautogui
        pyautogui.click(x, y)
        return f"Clicked at ({x}, {y})"

    async def _type_text(self, text: str) -> str:
        if not text:
            return "Error: text is required for type_text."
        import pyautogui
        pyautogui.typewrite(text, interval=0.05)
        return f"Typed: {text}"

    async def _read_screen(self, region: list = None) -> str:
        import pytesseract
        from PIL import ImageGrab
        if region:
            x, y, w, h = region
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        else:
            img = ImageGrab.grab()
        text = pytesseract.image_to_string(img)
        return f"Screen text:\n{text}"

    async def _find_window(self, window_title: str) -> str:
        if not window_title:
            return "Error: window_title is required for find_window."
        from pywinauto import Desktop
        wins = Desktop(backend="uia").windows()
        for w in wins:
            if window_title.lower() in w.window_text().lower():
                w.set_focus()
                return f"Found and focused window: {w.window_text()}"
        return f"Window with title '{window_title}' not found."