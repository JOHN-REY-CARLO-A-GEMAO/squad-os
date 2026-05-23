import os
import ffmpeg
from typing import Optional
from squad_os.tools.base import BaseTool
from squad_os.core.utils import is_safe_path

_FFMPEG_PATH = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-124279-g0f6ba39122-win64-gpl\bin"
if _FFMPEG_PATH not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")

class VideoProcessingTool(BaseTool):
    name = "video_remove_watermark"
    description = (
        "Remove a watermark from a video using ffmpeg's delogo filter. "
        "Use preset positions (e.g. 'bottom-right') or custom coordinates. "
        "Auto-detects video resolution to calculate positions. "
        "The cleaned video is saved to the project workspace for commit."
    )
    parameters = {
        "type": "object",
        "properties": {
            "video_path": {
                "type": "string",
                "description": "Path to the uploaded or project video file"
            },
            "output_filename": {
                "type": "string",
                "description": "Filename for the cleaned video (e.g. 'cleaned_video.mp4')",
                "default": "cleaned_video.mp4"
            },
            "position": {
                "type": "string",
                "enum": ["bottom-right", "bottom-left", "top-right", "top-left"],
                "description": "Preset watermark position on the video frame",
                "default": "bottom-right"
            },
            "width": {
                "type": "integer",
                "description": "Watermark width in pixels",
                "default": 200
            },
            "height": {
                "type": "integer",
                "description": "Watermark height in pixels",
                "default": 50
            },
            "x_offset": {
                "type": "integer",
                "description": "Custom X offset from the edge (pixels). Overrides position preset."
            },
            "y_offset": {
                "type": "integer",
                "description": "Custom Y offset from the edge (pixels). Overrides position preset."
            }
        },
        "required": ["video_path"]
    }

    def __init__(self):
        self.active_branch = None
        self.workspace = None

    async def execute(
        self,
        video_path: str,
        output_filename: str = "cleaned_video.mp4",
        position: str = "bottom-right",
        width: int = 200,
        height: int = 50,
        x_offset: Optional[int] = None,
        y_offset: Optional[int] = None
    ) -> str:
        if not os.path.exists(video_path):
            return f"Error: Video file not found at {video_path}"

        abs_video = os.path.abspath(video_path)
        safe = False
        allowed_bases = ["workspace/uploads", "workspace/projects", "workspace/outputs"]
        for base in allowed_bases:
            if is_safe_path(base, abs_video):
                safe = True
                break
        if not safe:
            return f"Error: Access denied. Video path '{video_path}' is outside the workspace."

        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
            vw = int(video_stream["width"])
            vh = int(video_stream["height"])
        except Exception as e:
            return f"Error: Could not probe video file: {e}"

        if x_offset is None or y_offset is None:
            margin = 10
            if position == "bottom-right":
                x = vw - width - margin
                y = vh - height - margin
            elif position == "bottom-left":
                x = margin
                y = vh - height - margin
            elif position == "top-right":
                x = vw - width - margin
                y = margin
            elif position == "top-left":
                x = margin
                y = margin
            else:
                return f"Error: Unknown position '{position}'"
        else:
            x = x_offset
            y = y_offset

        x = max(0, x)
        y = max(0, y)
        width = min(width, vw - x)
        height = min(height, vh - y)

        output_dir = self.workspace or "workspace"
        if self.active_branch:
            output_dir = self.active_branch.project_path
        output_path = os.path.join(output_dir, output_filename)

        try:
            delogo_filter = f"delogo=x={x}:y={y}:w={width}:h={height}"
            ffmpeg.input(video_path).output(
                output_path,
                vf=delogo_filter,
                vcodec="libx264",
                crf=23,
                preset="veryfast",
                **{"c:a": "copy"}
            ).run(overwrite_output=True, quiet=True)
            return (
                f"Watermark removed successfully. "
                f"Detected resolution: {vw}x{vh}. "
                f"Applied delogo at x={x}, y={y}, w={width}, h={height}. "
                f"Cleaned video saved to: {output_path}"
            )
        except Exception as e:
            return f"Error: Watermark removal failed: {e}"
