import pytest
import os
from squad_os.tools.visual import BrowserControlTool

@pytest.mark.asyncio
async def test_browser_navigation_restriction():
    tool = BrowserControlTool()

    # Test file scheme (blocked)
    result = await tool.execute(action="navigate", url="file:///etc/passwd")
    assert "Error: Forbidden URL scheme 'file'" in result

    # Test data scheme (blocked)
    result = await tool.execute(action="navigate", url="data:text/html,<html>hacked</html>")
    assert "Error: Forbidden URL scheme 'data'" in result

    # Test empty scheme (blocked)
    result = await tool.execute(action="navigate", url="/etc/passwd")
    assert "Error: Forbidden URL scheme ''" in result

    await tool.cleanup()

@pytest.mark.asyncio
async def test_screenshot_restriction():
    tool = BrowserControlTool()

    # Test screenshot before navigation (blocked)
    result = await tool.execute(action="screenshot", description="test")
    assert "Error: Cannot take screenshot of an empty or uninitialized page" in result

    await tool.cleanup()

@pytest.mark.asyncio
async def test_valid_navigation():
    tool = BrowserControlTool()

    # Test valid http scheme (should attempt to navigate, might fail if no internet but shouldn't be blocked by scheme check)
    result = await tool.execute(action="navigate", url="http://example.com")
    # If it's a timeout or DNS error, it won't be our scheme error
    assert "Error: Forbidden URL scheme" not in result

    # Test uppercase scheme (should be allowed)
    result = await tool.execute(action="navigate", url="HTTP://example.com")
    assert "Error: Forbidden URL scheme" not in result

    await tool.cleanup()
