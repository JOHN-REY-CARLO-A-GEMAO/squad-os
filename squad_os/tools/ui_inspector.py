"""
UIInspectorTool — extracts a structured accessibility tree from any window.

Windows:  uses pywinauto + UIA backend
macOS:    uses pyobjc + ApplicationServices (AXUIElement)
Linux:    uses pyatspi2 (ATSPI) via dbus-python or AT-SPI2 direct
"""
import asyncio
import json
import platform
from typing import Optional, List, Dict, Any

from squad_os.tools.base import BaseTool


class UIInspectorTool(BaseTool):
    name = "inspect_element"
    description = (
        "Inspect the accessibility tree of a window — returns a structured JSON tree "
        "of all UI elements (buttons, menus, text fields, etc.) with their roles, names, "
        "IDs, states, and bounding rectangles. Use this to find elements before clicking, "
        "typing, or reading screen content. Pass window_title=None for the currently "
        "focused window."
    )
    parameters = {
        "type": "object",
        "properties": {
            "window_title": {
                "type": "string",
                "description": "Window title to inspect. None = currently focused window. Partial match is fine."
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum tree depth to traverse (default 5). Use smaller values for speed."
            }
        },
        # window_title is optional; omit it to inspect the currently focused window
        "required": []
    }

    def __init__(self):
        self._platform = self._get_platform()

    @staticmethod
    def _get_platform() -> str:
        system = platform.system().lower()
        if system == "darwin":
            return "darwin"
        elif system in ("windows", "nt"):
            return "windows"
        elif system == "linux":
            return "linux"
        return "unsupported"

    async def execute(self, window_title: Optional[str] = None, max_depth: int = 5) -> str:
        try:
            if self._platform == "windows":
                return await self._inspect_windows(window_title, max_depth)
            elif self._platform == "darwin":
                return await self._inspect_darwin(window_title, max_depth)
            elif self._platform == "linux":
                return await self._inspect_linux(window_title, max_depth)
            return f"Error: Unsupported platform '{self._platform}' for inspect_element."
        except Exception as e:
            return f"inspect_element error: {e}"

    # -------------------------------------------------------------------------
    # Windows — pywinauto UIA backend
    # -------------------------------------------------------------------------
    async def _inspect_windows(self, window_title: Optional[str], max_depth: int) -> str:
        try:
            from pywinauto import Desktop
        except ImportError:
            return (
                "Error: pywinauto is required for inspect_element on Windows. "
                "Install it with: pip install pywinauto"
            )

        try:
            wins = Desktop(backend="uia").windows()
        except Exception as e:
            return f"Error enumerating windows: {e}. Is pywinauto correctly installed?"

        target = None
        if window_title:
            for w in wins:
                if window_title.lower() in w.window_text().lower():
                    target = w
                    break
        else:
            # Use foreground window when no title given
            try:
                target = Desktop(backend="uia").active
            except Exception:
                pass

        if not target:
            available = [w.window_text() for w in wins if w.window_text()]
            return f"Window '{window_title}' not found. Available windows: {available[:20]}"

        try:
            tree = self._build_win_uia_tree(target, max_depth)
            return json.dumps({"window": target.window_text(), "tree": tree}, indent=2)
        except Exception as e:
            return f"Error building accessibility tree: {e}"

    def _build_win_uia_tree(self, elem, depth: int, _role: str = "pane") -> Dict[str, Any]:
        if depth == 0:
            return {}
        try:
            node = self._win_uia_node(elem)
            children = []
            for child in elem.children(control_type=None):
                try:
                    child_node = self._build_win_uia_tree(child, depth - 1)
                    if child_node:
                        children.append(child_node)
                except Exception:
                    pass
            node["children"] = children
            return node
        except Exception:
            return {}

    def _win_uia_node(self, elem) -> Dict[str, Any]:
        try:
            rect = elem.rectangle()
            # pywinauto UIA: control_type maps to accessible role
            ctrl_type = (elem.get_attribute("ControlType") or elem.get_attributes().get("ControlType") or "Unknown")
            name = elem.window_text() or ""
            role = str(ctrl_type).split(".")[-1] if ctrl_type else "Unknown"
            try:
                is_enabled = elem.is_enabled()
                is_visible = elem.is_visible()
            except Exception:
                is_enabled = True
                is_visible = True
            return {
                "role": role,
                "name": name,
                "id": elem.get_attributes().get("AutomationId") or "",
                "rect": {"x": rect.left, "y": rect.top, "width": rect.width(), "height": rect.height()},
                "enabled": is_enabled,
                "visible": is_visible,
            }
        except Exception:
            return {"role": "Unknown", "name": "", "id": "", "rect": {}, "enabled": True, "visible": True}

    # -------------------------------------------------------------------------
    # macOS — pyobjc + ApplicationServices AXUIElement
    # -------------------------------------------------------------------------
    async def _inspect_darwin(self, window_title: Optional[str], max_depth: int) -> str:
        try:
            import Cocoa
            import ApplicationServices
            from Cocoa import NSWorkspace
        except ImportError:
            return (
                "Error: pyobjc is required for inspect_element on macOS. "
                "Install it with: pip install pyobjc"
            )

        workspace = NSWorkspace.sharedWorkspace()
        apps = workspace.runningApplications()

        target_app = None
        if window_title:
            for app in apps:
                app_name = app.localizedName() or ""
                if window_title.lower() in app_name.lower():
                    target_app = app
                    break
        else:
            target_app = workspace.frontmostApplication()

        if not target_app:
            return f"Application '{window_title}' not found among running apps."

        pid = target_app.processIdentifier()
        app_elem = ApplicationServices.AXUIElementCreateApplication(pid)

        # Get all windows
        windows_ref = ApplicationServices.AXUIElementCopyAttributeValue(
            app_elem, ApplicationServices.kAXWindowsAttribute, None
        )
        # kAXErrorSuccess = 0
        if windows_ref[0] != 0:
            return f"Could not get windows for app: {target_app.localizedName()}"

        window_list = windows_ref[1]
        if not window_list or len(window_list) == 0:
            return f"No windows found for app: {target_app.localizedName()}"

        # Use the first window
        window_elem = window_list[0]
        tree = self._build_darwin_tree(window_elem, max_depth)
        return json.dumps({
            "window": self._darwin_get_attr(window_elem, ApplicationServices.kAXTitleAttribute) or target_app.localizedName(),
            "tree": tree
        }, indent=2)

    def _build_darwin_tree(self, elem, depth: int) -> Dict[str, Any]:
        if depth == 0:
            return {}
        try:
            node = {
                "role": self._darwin_get_attr(elem, ApplicationServices.kAXRoleAttribute) or "Unknown",
                "name": self._darwin_get_attr(elem, ApplicationServices.kAXTitleAttribute) or "",
                "id": self._darwin_get_attr(elem, ApplicationServices.kAXIdentifierAttribute) or "",
                "enabled": True,
                "visible": True,
                "children": []
            }
            children_ref = ApplicationServices.AXUIElementCopyAttributeValue(
                elem, ApplicationServices.kAXChildrenAttribute, None
            )
            # kAXErrorSuccess = 0
            if children_ref[0] == 0 and children_ref[1]:
                for child in children_ref[1]:
                    child_node = self._build_darwin_tree(child, depth - 1)
                    if child_node:
                        node["children"].append(child_node)
            return node
        except Exception:
            return {}

    def _darwin_get_attr(self, elem, attr) -> Optional[str]:
        val_ref = ApplicationServices.AXUIElementCopyAttributeValue(elem, attr, None)
        # kAXErrorSuccess = 0
        if val_ref[0] == 0 and val_ref[1] is not None:
            v = val_ref[1]
            if isinstance(v, str):
                return v
            return str(v)
        return None

    # -------------------------------------------------------------------------
    # Linux — pyatspi2 via dbus (ATSPI2)
    # -------------------------------------------------------------------------
    async def _inspect_linux(self, window_title: Optional[str], max_depth: int) -> str:
        try:
            import dbus
            import re
        except ImportError:
            return (
                "Error: dbus-python is required for inspect_element on Linux. "
                "Install it with: pip install dbus-python"
            )

        try:
            bus = dbus.SessionBus()
            a11y_bus = bus.get_object('org.a11y.Bus', '/org/a11y/bus')
            a11y_iface = dbus.Interface(a11y_bus, 'org.a11y.Bus')
            a11y_addr = a11y_iface.GetAddress()
        except Exception as e:
            return (
                f"Error connecting to AT-SPI2 bus: {e}. "
                "Ensure at-spi2-core and dbus-python are installed: "
                "sudo apt install at-spi2-core libdbus-1-dev"
            )

        try:
            from dbus.lowlevel import Connection, Message
        except ImportError:
            pass

        # Use atspi2 directly via dbus
        try:
            conn = dbus.connection.Connection(a11y_addr)
            obj = conn.get_object('org.a11y.atspi.Registry', '/org/a11y/atspi/accessible/null')
            iface = dbus.Interface(obj, 'org.a11y.atspi.Accessible')
        except Exception as e:
            return f"Error connecting to AT-SPI2 registry: {e}"

        # Enumerate desktop
        try:
            desktop = conn.get_object('org.a11y.atspi.Registry', '/org/a11y/atspi/accessible')
            desktop_iface = dbus.Interface(desktop, 'org.a11y.atspi.Accessible')
            children = desktop_iface.GetChildren()
        except Exception as e:
            return f"Error getting desktop children: {e}"

        target_app = None
        if window_title:
            for child in children:
                try:
                    name = str(child.get_child().GetName())
                    if window_title.lower() in name.lower():
                        target_app = child
                        break
                except Exception:
                    pass

        if not target_app:
            # Fallback: return top-level apps
            apps = []
            for child in children[:20]:
                try:
                    nm = str(child.get_child().GetName())
                    apps.append(nm)
                except Exception:
                    pass
            return f"Window '{window_title}' not found. Available apps: {apps}"

        tree = self._build_linux_tree(target_app, max_depth)
        try:
            app_name = target_app.get_child().GetName()
        except Exception:
            app_name = window_title or "Unknown"
        return json.dumps({"window": app_name, "tree": tree}, indent=2)

    def _build_linux_tree(self, obj, depth: int) -> Dict[str, Any]:
        if depth == 0:
            return {}
        try:
            name = obj.get_child().GetName() if obj.get_child() else ""
            role = obj.get_child().GetRoleName() if obj.get_child() else "Unknown"
            node = {"role": role, "name": name, "id": "", "enabled": True, "visible": True, "children": []}
            try:
                children = obj.GetChildren()
                for child in children:
                    child_node = self._build_linux_tree(child, depth - 1)
                    if child_node:
                        node["children"].append(child_node)
            except Exception:
                pass
            return node
        except Exception:
            return {}
