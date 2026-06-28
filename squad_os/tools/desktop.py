import os
import asyncio
import datetime
import subprocess
import platform
import re
import shlex
from typing import Optional
from squad_os.tools.base import BaseTool


class DesktopControlTool(BaseTool):
    name = "desktop_control"
    description = (
        "Control the desktop: take screenshots, open apps, click, type text, "
        "press keyboard shortcuts, read screen content via OCR, find/focus windows, "
        "inspect UI elements, and perform coordinate-free interaction. "
        "Actions: 'screenshot', 'open_app', 'click', 'type_text', 'press_key', "
        "'read_screen', 'find_window', 'wait', 'inspect_element', 'click_element', "
        "'wait_for_element', 'drag_element'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "open_app", "click", "type_text", "press_key",
                         "read_screen", "find_window", "wait", "inspect_element",
                         "click_element", "wait_for_element", "drag_element"]
            },
            "app": {"type": "string", "description": "App name or full path for open_app"},
            "x": {"type": "integer", "description": "X coordinate for click"},
            "y": {"type": "integer", "description": "Y coordinate for click"},
            "text": {"type": "string", "description": "Text to type or key to press (e.g. 'ctrl+shift+enter', 'enter', 'tab')"},
            "window_title": {"type": "string", "description": "Window title for find_window and element actions"},
            "description": {"type": "string", "description": "Description for screenshot filename"},
            "seconds": {"type": "number", "description": "Seconds to wait for wait action"},
            "region": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional region [x, y, width, height] for read_screen"
            },
            "element_query": {
                "type": "string",
                "description": "Element description e.g. 'Submit button', 'File menu', 'Username field', or 'role:name' pair like 'button:OK'"
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds for wait_for_element (default 10)"
            },
            "state": {
                "type": "string",
                "enum": ["exists", "visible", "enabled", "focused"],
                "description": "Desired state to wait for with wait_for_element"
            },
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "description": "Mouse button for click_element (default left)"
            },
            "start_query": {
                "type": "string",
                "description": "Start element for drag_element (element description or 'x,y')"
            },
            "end_query": {
                "type": "string",
                "description": "End element/position for drag_element (element description or 'x,y')"
            }
        },
        "required": ["action"]
    }

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join("workspace", "outputs", "visuals")
        os.makedirs(self.output_dir, exist_ok=True)
        self._platform_backend = None

    def _get_platform(self) -> str:
        system = platform.system().lower()
        if system == "darwin":
            return "darwin"
        elif system in ("windows", "nt"):
            return "windows"
        elif system == "linux":
            return "linux"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

    def _get_backend(self):
        if self._platform_backend is None:
            self._platform_backend = self._PlatformBackend(self, self._get_platform())
        return self._platform_backend

    async def execute(self, action: str, app: str = None, x: int = None, y: int = None,
                      text: str = None, window_title: str = None, description: str = None,
                      region: list = None, seconds: float = None,
                      element_query: str = None, timeout: float = None,
                      state: str = None, button: str = None,
                      start_query: str = None, end_query: str = None) -> str:
        try:
            if action == "screenshot":
                return await self._screenshot(description)
            elif action == "open_app":
                return await self._open_app(app)
            elif action == "click":
                return await self._click(x, y)
            elif action == "type_text":
                return await self._type_text(text)
            elif action == "press_key":
                return await self._press_key(text)
            elif action == "read_screen":
                return await self._read_screen(region)
            elif action == "find_window":
                return await self._find_window(window_title)
            elif action == "wait":
                return await self._wait(seconds or 2)
            elif action == "inspect_element":
                return await self._inspect_element(window_title)
            elif action == "click_element":
                return await self._click_element(element_query, window_title, button)
            elif action == "wait_for_element":
                return await self._wait_for_element(element_query, window_title, timeout, state)
            elif action == "drag_element":
                return await self._drag_element(start_query, end_query, window_title)
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"DesktopControlTool error: {str(e)}"

    async def _screenshot(self, description: str = None) -> str:
        import pyautogui
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Security: Prevent path traversal via description
        desc = os.path.basename(description or "screenshot")
        filename = f"{timestamp}_{desc.replace(' ', '_')}.png"
        filepath = os.path.join(self.output_dir, filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        return f"Screenshot saved to {filepath}"

    async def _open_app(self, app: str) -> str:
        if not app:
            return "Error: app name or path is required."
        backend = self._get_backend()
        return backend.open_app(app)

    async def _click(self, x: int, y: int) -> str:
        if x is None or y is None:
            return "Error: x and y coordinates are required for click."
        import pyautogui
        pyautogui.click(x, y)
        await asyncio.sleep(0.3)
        return f"Clicked at ({x}, {y})"

    async def _type_text(self, text: str) -> str:
        if not text:
            return "Error: text is required for type_text."
        import pyautogui
        modifier_key = 'command' if platform.system().lower() == 'darwin' else 'ctrl'
        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey(modifier_key, 'v')
        except ImportError:
            pyautogui.typewrite(text, interval=0.05)
        await asyncio.sleep(0.3)
        return f"Typed: {text}"

    async def _press_key(self, text: str) -> str:
        if not text:
            return "Error: text is required for press_key."
        import pyautogui
        if '+' in text:
            keys = [k.strip() for k in text.split('+')]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(text)
        await asyncio.sleep(0.3)
        return f"Pressed key: {text}"

    async def _read_screen(self, region: list = None) -> str:
        backend = self._get_backend()
        return backend.read_screen(region)

    async def _find_window(self, window_title: str) -> str:
        if not window_title:
            return "Error: window_title is required for find_window."
        backend = self._get_backend()
        return backend.find_window(window_title)

    async def _wait(self, seconds: float) -> str:
        await asyncio.sleep(seconds)
        return f"Waited {seconds} seconds"

    # -------------------------------------------------------------------------
    # Coordinate-free UI interaction — delegates to platform backend
    # -------------------------------------------------------------------------

    async def _inspect_element(self, window_title: str = None) -> str:
        backend = self._get_backend()
        return backend.inspect_element(window_title)

    async def _click_element(self, element_query: str = None, window_title: str = None,
                              button: str = "left") -> str:
        backend = self._get_backend()
        return backend.click_element(element_query, window_title, button)

    async def _wait_for_element(self, element_query: str = None, window_title: str = None,
                                  timeout: float = 10.0, state: str = "exists") -> str:
        backend = self._get_backend()
        return await backend.wait_for_element(element_query, window_title, timeout, state)

    async def _drag_element(self, start_query: str = None, end_query: str = None,
                             window_title: str = None) -> str:
        backend = self._get_backend()
        return backend.drag_element(start_query, end_query, window_title)

    # -------------------------------------------------------------------------
    # Platform backend — lazily initialized, encapsulates OS-specific logic
    # -------------------------------------------------------------------------
    class _PlatformBackend:
        def __init__(self, tool, platform_name: str):
            self.tool = tool
            self._platform = platform_name

        # -- open_app ------------------------------------------------------------

        def open_app(self, app: str) -> str:
            p = self._platform
            try:
                if p == "windows":
                    # Security: Use shell=False and shlex.split to prevent command injection.
                    # We use posix=False to properly handle Windows paths with spaces.
                    parts = shlex.split(app, posix=False)
                    # Manually strip quotes to avoid double-quoting regressions on paths with spaces
                    # when passing to subprocess.Popen with shell=False.
                    parts = [part.strip('"') for part in parts]
                    subprocess.Popen(parts, shell=False)
                elif p == "darwin":
                    # Use -- to prevent argument injection
                    subprocess.Popen(["open", "--", app])
                elif p == "linux":
                    # Note: xdg-open often doesn't support --, but list-based Popen is already safe from command injection.
                    subprocess.Popen(["xdg-open", app])
                else:
                    return f"Error: Unsupported platform '{p}' for open_app."
            except FileNotFoundError as e:
                if p == "linux" and "xdg-open" in str(e):
                    return (
                        "Error: 'xdg-open' is not installed on this Linux system. "
                        "Install it with: sudo apt install xdg-utils (Debian/Ubuntu) or "
                        "sudo dnf install xdg-utils (Fedora)."
                    )
                return f"Error opening app '{app}': {e}"
            except Exception as e:
                return f"Error opening app '{app}': {e}"

            return f"Opened app: {app}"

        # -- read_screen --------------------------------------------------------

        def read_screen(self, region: list = None) -> str:
            try:
                import pytesseract
            except ImportError:
                return (
                    "Error: 'pytesseract' is required for OCR. "
                    "Install it with: pip install pytesseract"
                )

            try:
                from PIL import Image
            except ImportError:
                return "Error: Pillow is required. Install with: pip install Pillow"

            p = self._platform
            img = None

            try:
                if p == "darwin":
                    img = self._read_screen_darwin(region)
                elif p in ("windows", "linux"):
                    img = self._read_screen_mss(region)
                else:
                    return f"Error: Unsupported platform '{p}' for read_screen."
            except Exception as e:
                return f"Error capturing screen: {e}"

            try:
                text = pytesseract.image_to_string(img)
            except Exception as e:
                return (
                    f"OCR failed: {e}. "
                    "Ensure Tesseract is installed: "
                    "Windows: https://github.com/UB-Mannheim/tesseract/wiki | "
                    "macOS: brew install tesseract | "
                    "Linux: sudo apt install tesseract-ocr"
                )

            return f"Screen text:\n{text}"

        def _read_screen_darwin(self, region: list = None) -> "Image.Image":
            import subprocess
            tmp = "/tmp/squad_os_screenshot.png"
            cmd = ["screencapture", "-x", tmp]
            subprocess.run(cmd, capture_output=True, timeout=10)
            from PIL import Image
            img = Image.open(tmp)
            if region:
                x, y, w, h = region
                img = img.crop((x, y, x + w, y + h))
            return img

        def _read_screen_mss(self, region: list = None) -> "Image.Image":
            import mss
            with mss.mss() as sct:
                if region:
                    x, y, w, h = region
                    monitor = {"left": x, "top": y, "width": w, "height": h}
                else:
                    monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                from PIL import Image
                return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # -- find_window --------------------------------------------------------

        def find_window(self, window_title: str) -> str:
            p = self._platform
            if p == "windows":
                return self._find_window_windows(window_title)
            elif p == "darwin":
                return self._find_window_darwin(window_title)
            elif p == "linux":
                return self._find_window_linux(window_title)
            else:
                return f"Error: Unsupported platform '{p}' for find_window."

        def _find_window_windows(self, window_title: str) -> str:
            try:
                from pywinauto import Desktop
            except ImportError:
                return (
                    "Error: pywinauto is required for find_window on Windows. "
                    "Install it with: pip install pywinauto"
                )
            try:
                wins = Desktop(backend="uia").windows()
            except Exception as e:
                return f"Error enumerating windows: {e}. Is pywinauto correctly installed?"
            for w in wins:
                if window_title.lower() in w.window_text().lower():
                    try:
                        w.set_focus()
                    except Exception:
                        pass
                    return f"Found and focused window: {w.window_text()}"
            return f"Window with title '{window_title}' not found."

        def _find_window_darwin(self, window_title: str) -> str:
            try:
                import pyobjc
            except ImportError:
                return (
                    "Error: pyobjc is required for find_window on macOS. "
                    "Install it with: pip install pyobjc"
                )

            try:
                import Cocoa
                import Foundation

                workspace = Cocoa.NSWorkspace.sharedWorkspace()
                apps = workspace.runningApplications()

                for app in apps:
                    app_name = app.localizedName() or ""
                    if window_title.lower() in app_name.lower():
                        app.activateWithOptions_(Cocoa.NSApplicationActivateIgnoringOtherApps)
                        return f"Found and focused app: {app_name}"

                # Fall back to osascript to enumerate windows
                script = (
                    'tell application "System Events"\n'
                    'set winList to windows of (every process whose name contains "%s")\n'
                    'repeat with w in winList\n'
                    'set winName to name of w\n'
                    'end repeat\n'
                    'end tell'
                ) % window_title

                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return f"Found and focused window with title containing '{window_title}'"
                return f"Window with title '{window_title}' not found."

            except subprocess.TimeoutExpired:
                return f"Error: AppleScript timed out searching for '{window_title}'."
            except Exception as e:
                return f"Error accessing windows on macOS: {e}"

        def _find_window_linux(self, window_title: str) -> str:
            try:
                result = subprocess.run(
                    ["xdotool", "search", "--name", window_title],
                    capture_output=True, text=True, timeout=10
                )
                window_ids = [wid for wid in result.stdout.strip().split("\n") if wid]
                if not window_ids:
                    return f"Window with title '{window_title}' not found."
                window_id = window_ids[0]
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", window_id],
                    capture_output=True, timeout=10
                )
                return f"Found and focused window with title '{window_title}' (ID: {window_id})"
            except FileNotFoundError:
                return (
                    "Error: 'xdotool' is not installed on this Linux system. "
                    "Install it with: sudo apt install xdotool (Debian/Ubuntu) or "
                    "sudo dnf install xdotool (Fedora)."
                )
            except subprocess.TimeoutExpired:
                return f"Error: xdotool timed out while searching for '{window_title}'."
            except Exception as e:
                return f"Error finding window on Linux: {e}"

        # -------------------------------------------------------------------------
        # Coordinate-free UI interaction
        # -------------------------------------------------------------------------

        def inspect_element(self, window_title: str = None) -> str:
            """Return a JSON accessibility tree for the given window."""
            p = self._platform
            if p == "windows":
                return self._inspect_element_windows(window_title)
            elif p == "darwin":
                return self._inspect_element_darwin(window_title)
            elif p == "linux":
                return self._inspect_element_linux(window_title)
            return f"Error: Unsupported platform '{p}' for inspect_element."

        def _inspect_element_windows(self, window_title: str = None) -> str:
            import json
            try:
                from pywinauto import Desktop
            except ImportError:
                return "Error: pywinauto is required. Install: pip install pywinauto"
            try:
                wins = Desktop(backend="uia").windows()
            except Exception as e:
                return f"Error enumerating windows: {e}"
            target = None
            if window_title:
                for w in wins:
                    if window_title.lower() in w.window_text().lower():
                        target = w
                        break
            else:
                try:
                    target = Desktop(backend="uia").active
                except Exception:
                    pass
            if not target:
                available = [w.window_text() for w in wins if w.window_text()]
                return f"Window '{window_title}' not found. Available: {available[:20]}"
            try:
                tree = self._build_win_uia_tree(target, max_depth=5)
                return json.dumps({"window": target.window_text(), "tree": tree}, indent=2)
            except Exception as e:
                return f"Error building tree: {e}"

        def _build_win_uia_tree(self, elem, depth: int = 5):
            if depth == 0:
                return {}
            try:
                attrs = elem.get_attributes()
                ctrl_type = attrs.get("ControlType", "Unknown")
                role = str(ctrl_type).split(".")[-1] if ctrl_type else "Unknown"
                rect = elem.rectangle()
                node = {
                    "role": role,
                    "name": elem.window_text() or "",
                    "id": attrs.get("AutomationId") or "",
                    "rect": {"x": rect.left, "y": rect.top, "width": rect.width(), "height": rect.height()},
                    "enabled": elem.is_enabled(),
                    "visible": elem.is_visible(),
                    "children": []
                }
                for child in elem.children(control_type=None):
                    try:
                        child_node = self._build_win_uia_tree(child, depth - 1)
                        if child_node:
                            node["children"].append(child_node)
                    except Exception:
                        pass
                return node
            except Exception:
                return {}

        def _inspect_element_darwin(self, window_title: str = None) -> str:
            import json
            try:
                import Cocoa
                import ApplicationServices
            except ImportError:
                return "Error: pyobjc is required. Install: pip install pyobjc"
            workspace = Cocoa.NSWorkspace.sharedWorkspace()
            apps = workspace.runningApplications()
            target_app = None
            if window_title:
                for app in apps:
                    if window_title.lower() in (app.localizedName() or "").lower():
                        target_app = app
                        break
            else:
                target_app = workspace.frontmostApplication()
            if not target_app:
                return f"App '{window_title}' not found among running apps."
            pid = target_app.processIdentifier()
            app_elem = ApplicationServices.AXUIElementCreateApplication(pid)
            windows_ref = ApplicationServices.AXUIElementCopyAttributeValue(
                app_elem, ApplicationServices.kAXWindowsAttribute, None
            )
            if windows_ref[0] != 0 or not windows_ref[1]:
                return f"Could not get windows for: {target_app.localizedName()}"
            window_elem = windows_ref[1][0]
            tree = self._build_darwin_tree(window_elem, max_depth=5)
            title = self._darwin_attr(window_elem, ApplicationServices.kAXTitleAttribute)
            return json.dumps({
                "window": title or target_app.localizedName(),
                "tree": tree
            }, indent=2)

        def _build_darwin_tree(self, elem, depth: int = 5):
            if depth == 0:
                return {}
            try:
                node = {
                    "role": self._darwin_attr(elem, ApplicationServices.kAXRoleAttribute) or "Unknown",
                    "name": self._darwin_attr(elem, ApplicationServices.kAXTitleAttribute) or "",
                    "id": self._darwin_attr(elem, ApplicationServices.kAXIdentifierAttribute) or "",
                    "enabled": True,
                    "visible": True,
                    "children": []
                }
                children_ref = ApplicationServices.AXUIElementCopyAttributeValue(
                    elem, ApplicationServices.kAXChildrenAttribute, None
                )
                if children_ref[0] == 0 and children_ref[1]:
                    for child in children_ref[1]:
                        child_node = self._build_darwin_tree(child, depth - 1)
                        if child_node:
                            node["children"].append(child_node)
                return node
            except Exception:
                return {}

        def _darwin_attr(self, elem, attr):
            ref = ApplicationServices.AXUIElementCopyAttributeValue(elem, attr, None)
            if ref[0] == 0 and ref[1] is not None:
                v = ref[1]
                return str(v) if not isinstance(v, str) else v
            return None

        def _inspect_element_linux(self, window_title: str = None) -> str:
            import json
            try:
                import dbus
            except ImportError:
                return "Error: dbus-python is required. Install: pip install dbus-python"
            try:
                bus = dbus.SessionBus()
                a11y_bus = bus.get_object('org.a11y.Bus', '/org/a11y/bus')
                a11y_addr = a11y_iface = dbus.Interface(a11y_bus, 'org.a11y.Bus').GetAddress()
            except Exception as e:
                return f"Error connecting to AT-SPI2 bus: {e}. Install: sudo apt install at-spi2-core libdbus-1-dev"
            try:
                conn = dbus.connection.Connection(a11y_addr)
                obj = conn.get_object('org.a11y.atspi.Registry', '/org/a11y/atspi/accessible')
                desktop_iface = dbus.Interface(obj, 'org.a11y.atspi.Accessible')
                children = desktop_iface.GetChildren()
            except Exception as e:
                return f"Error accessing AT-SPI2: {e}"
            target = None
            for child in children:
                try:
                    nm = child.get_child().GetName()
                    if window_title and window_title.lower() in str(nm).lower():
                        target = child
                        break
                    elif not window_title:
                        target = child
                        break
                except Exception:
                    pass
            if not target:
                apps = [str(c.get_child().GetName()) for c in children[:20] if c]
                return f"Window '{window_title}' not found. Available: {apps}"
            tree = self._build_linux_tree(target, max_depth=5)
            try:
                name = target.get_child().GetName()
            except Exception:
                name = window_title or "Unknown"
            return json.dumps({"window": str(name), "tree": tree}, indent=2)

        def _build_linux_tree(self, obj, depth: int = 5):
            if depth == 0:
                return {}
            try:
                child = obj.get_child()
                node = {
                    "role": str(child.GetRoleName()) if child else "Unknown",
                    "name": str(child.GetName()) if child else "",
                    "id": "",
                    "enabled": True,
                    "visible": True,
                    "children": []
                }
                try:
                    for c in obj.GetChildren():
                        cn = self._build_linux_tree(c, depth - 1)
                        if cn:
                            node["children"].append(cn)
                except Exception:
                    pass
                return node
            except Exception:
                return {}

        # -------------------------------------------------------------------------
        # Element search + click
        # -------------------------------------------------------------------------

        def _find_element_in_window(self, element_query: str, window_title: str = None):
            """Find a UI element by query string. Returns (x, y, element_info) or None."""
            import json
            import re

            # Get the accessibility tree
            tree_json = self.inspect_element(window_title)
            if tree_json.startswith("Error") or tree_json.startswith("Window"):
                return None

            try:
                data = json.loads(tree_json)
            except Exception:
                return None

            # Parse "role:name" syntax
            query_role = None
            query_name = element_query
            if ":" in element_query:
                parts = element_query.split(":", 1)
                query_role = parts[0].strip().lower()
                query_name = parts[1].strip()

            # Fuzzy search through the tree
            candidates = []

            def search_tree(node, path=""):
                role = (node.get("role") or "").lower()
                name = (node.get("name") or "").lower()
                query_name_lower = query_name.lower()

                # Score this node
                score = 0
                if query_role and query_role in role:
                    score += 10
                if query_name_lower in name or name in query_name_lower:
                    score += 20
                if query_name_lower in role:  # match role partially
                    score += 5
                # Check if query words appear in name
                query_words = query_name_lower.split()
                for word in query_words:
                    if word and word in name:
                        score += 3

                if score > 0 and node.get("rect"):
                    candidates.append((score, node))

                for child in node.get("children", []):
                    search_tree(child)

            search_tree(data.get("tree", {}))
            if not candidates:
                return None

            # Return highest scoring element
            candidates.sort(key=lambda x: x[0], reverse=True)
            best = candidates[0][1]
            rect = best["rect"]
            x = rect["x"] + rect["width"] // 2
            y = rect["y"] + rect["height"] // 2
            return (x, y, best)

        def click_element(self, element_query: str, window_title: str = None,
                          button: str = "left") -> str:
            import pyautogui
            result = self._find_element_in_window(element_query, window_title)
            if not result:
                return f"Element '{element_query}' not found in window '{window_title}'."
            x, y, elem_info = result
            btn = button or "left"
            try:
                if btn == "right":
                    pyautogui.click(x, y, button="right")
                elif btn == "middle":
                    pyautogui.click(x, y, button="middle")
                else:
                    pyautogui.click(x, y)
                return f"Clicked '{elem_info.get('name')}' ({elem_info.get('role')}) at ({x}, {y})"
            except Exception as e:
                return f"Error clicking element: {e}"

        async def wait_for_element(self, element_query: str, window_title: str = None,
                              timeout: float = 10.0, state: str = "exists") -> str:
            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < timeout:
                result = self._find_element_in_window(element_query, window_title)
                if result:
                    elem_info = result[2]
                    if state == "exists":
                        return f"Element '{element_query}' found at ({result[0]}, {result[1]})"
                    elif state == "visible" and elem_info.get("visible", True):
                        return f"Element '{element_query}' is visible."
                    elif state == "enabled" and elem_info.get("enabled", True):
                        return f"Element '{element_query}' is enabled."
                await asyncio.sleep(0.5)
            return f"Timeout: Element '{element_query}' not found within {timeout}s (state={state})."

        def drag_element(self, start_query: str, end_query: str,
                         window_title: str = None) -> str:
            import pyautogui

            def parse_xy(q: str):
                """Parse 'x,y' string or find element and return center."""
                m = re.match(r"^\s*(-?\d+)\s*,\s*(-?\d+)\s*$", q)
                if m:
                    return int(m.group(1)), int(m.group(2))
                result = self._find_element_in_window(q, window_title)
                if not result:
                    raise ValueError(f"Could not resolve query: {q}")
                return result[0], result[1]

            try:
                sx, sy = parse_xy(start_query)
                ex, ey = parse_xy(end_query)
            except ValueError as e:
                return f"Error resolving drag positions: {e}"

            try:
                pyautogui.moveTo(sx, sy)
                pyautogui.drag(ex - sx, ey - sy, duration=0.5)
                return f"Dragged from ({sx}, {sy}) to ({ex}, {ey})"
            except Exception as e:
                return f"Error during drag: {e}"

