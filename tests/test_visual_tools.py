import asyncio
import os
import pytest
from squad_os.tools.visual import BrowserControlTool, VisionAnalysisTool
from squad_os.agents.base import BaseAgent

@pytest.mark.asyncio
async def test_visual_tools():
    # Test BrowserControlTool directly
    browser_tool = BrowserControlTool()

    print("Testing navigate and screenshot...")
    result = await browser_tool.execute(action="navigate", url="https://www.example.com")
    print(f"Navigate: {result}")

    result = await browser_tool.execute(action="screenshot", description="example_com")
    print(f"Screenshot: {result}")

    screenshot_path = result.split("saved to ")[-1]
    if os.path.exists(screenshot_path):
        print(f"Screenshot verified at {screenshot_path}")
    else:
        print(f"Screenshot NOT found at {screenshot_path}")

    # Test VisionAnalysisTool
    print("\nTesting VisionAnalysisTool...")
    vision_tool = VisionAnalysisTool()
    analysis = await vision_tool.execute(image_path=screenshot_path, query="What website is this?")
    print(f"Vision analysis result: {analysis}")

    # Test recording
    print("\nTesting recording...")
    await browser_tool.execute(action="start_recording")
    await browser_tool.execute(action="navigate", url="https://www.wikipedia.org")
    result = await browser_tool.execute(action="stop_recording", description="wikipedia_demo")
    print(f"Recording: {result}")

    # Updated verification logic
    video_path = result.split("converted to ")[-1]
    if os.path.exists(video_path):
        print(f"Video verified at {video_path}")
    else:
        print(f"Video NOT found at {video_path}")

    await browser_tool.cleanup()

if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is set for VisionAnalysisTool
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY is not set. VisionAnalysisTool will likely fail.")

    asyncio.run(test_visual_tools())
