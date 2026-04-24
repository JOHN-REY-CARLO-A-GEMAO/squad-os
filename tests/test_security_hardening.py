import pytest
import os
from squad_os.tools.registry import _validate_terminal_command
from squad_os.tools.visual import BrowserControlTool
from squad_os.tools.desktop import DesktopControlTool
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_terminal_validation_hardening():
    # Test safe chains
    valid, msg = _validate_terminal_command("ls && echo hello")
    assert valid, f"Safe chain should be valid: {msg}"

    valid, msg = _validate_terminal_command("ls; pwd")
    assert valid, f"Safe chain with semicolon should be valid: {msg}"

    # Test malicious chains
    valid, msg = _validate_terminal_command("ls && malicious_cmd")
    assert not valid, "Chain with malicious command should be blocked"
    assert "not in allowed command list" in msg

    valid, msg = _validate_terminal_command("echo hello | evil_cmd")
    assert not valid, "Chain with malicious command in pipe should be blocked"
    assert "not in allowed command list" in msg

    valid, msg = _validate_terminal_command("ls ; rm -rf /")
    assert not valid, "Chain with dangerous pattern should be blocked"
    assert "contains dangerous patterns" in msg

@pytest.mark.asyncio
async def test_visual_tool_path_traversal_mitigation():
    tool = BrowserControlTool(branch_id="test_branch")

    # Mock playwright/browser/page
    tool._playwright = MagicMock()
    tool._browser = MagicMock()
    tool._page = AsyncMock()
    tool._context = MagicMock()

    # screenshot
    await tool.execute(action="screenshot", description="../../../traversal")
    # The path passed to screenshot should NOT contain ../../../
    called_path = tool._page.screenshot.call_args[1]['path']
    assert "../../../" not in called_path
    assert os.path.basename(called_path).endswith("_traversal.png")

@pytest.mark.asyncio
async def test_desktop_tool_path_traversal_mitigation():
    # Avoid importing pyautogui by mocking it before it's even imported if possible,
    # but DesktopControlTool imports it inside its methods.

    # We will mock the 'pyautogui' module in sys.modules
    import sys
    mock_pyautogui = MagicMock()
    sys.modules["pyautogui"] = mock_pyautogui

    tool = DesktopControlTool(output_dir="workspace/outputs/visuals")

    mock_img = MagicMock()
    mock_pyautogui.screenshot.return_value = mock_img

    await tool.execute(action="screenshot", description="../../../evil")

    called_path = mock_img.save.call_args[0][0]
    assert "../../../" not in called_path
    assert os.path.basename(called_path).endswith("_evil.png")
