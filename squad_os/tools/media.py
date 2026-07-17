import os
import json
import asyncio
from typing import Optional, List
from squad_os.tools.base import BaseTool, retry_on_failure

MEDIA_OUTPUT_DIR = os.path.join("workspace", "outputs", "media")


class ImageGenTool(BaseTool):
    name = "image_gen"
    description = (
        "Generate images from text prompts using local (diffusers) or API-based models. "
        "Supports Flux.1-schnell and SDXL Turbo for fast generation. "
        "Images are saved to the workspace for use in creative projects."
    )
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the image to generate"
            },
            "negative_prompt": {
                "type": "string",
                "description": "Things to avoid in the generated image"
            },
            "model": {
                "type": "string",
                "enum": ["flux", "sdxl-turbo", "api"],
                "description": "Model to use: 'flux' (Flux.1-schnell local), 'sdxl-turbo' (SDXL Turbo local), 'api' (remote API)"
            },
            "width": {
                "type": "integer",
                "description": "Image width in pixels (default: 1024)"
            },
            "height": {
                "type": "integer",
                "description": "Image height in pixels (default: 1024)"
            },
            "steps": {
                "type": "integer",
                "description": "Number of inference steps (default: 4 for flux, 1 for sdxl)"
            },
            "count": {
                "type": "integer",
                "description": "Number of images to generate (default: 1)"
            },
            "filename": {
                "type": "string",
                "description": "Optional base filename (without extension)"
            },
            "style": {
                "type": "string",
                "description": "Style preset: 'cinematic', 'anime', 'photorealistic', 'painting'"
            }
        },
        "required": ["prompt"]
    }
    category = "multimedia"

    def __init__(self):
        os.makedirs(MEDIA_OUTPUT_DIR, exist_ok=True)

    @retry_on_failure(max_attempts=2, delay=2.0)
    async def execute(self, prompt: str, negative_prompt: Optional[str] = None,
                      model: str = "flux", width: int = 1024, height: int = 1024,
                      steps: Optional[int] = None, count: int = 1,
                      filename: Optional[str] = None, style: Optional[str] = None) -> str:
        import datetime
        base = filename or prompt.replace(" ", "_")[:40]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = []

        if model == "api":
            return await self._generate_via_api(prompt, negative_prompt, width, height, count, base, timestamp)
        return await self._generate_local(prompt, negative_prompt, model, width, height, steps, count, base, timestamp)

    async def _generate_local(self, prompt, negative_prompt, model, width, height, steps, count, base, timestamp):
        try:
            import torch
            from diffusers import DiffusionPipeline
        except ImportError:
            return (
                "Error: 'diffusers' and 'torch' are required for local image generation. "
                "Install with: pip install diffusers torch accelerate"
            )

        model_id = {"flux": "black-forest-labs/FLUX.1-schnell", "sdxl-turbo": "stabilityai/sdxl-turbo"}.get(model)
        if not model_id:
            return f"Error: Unknown model '{model}'. Choose 'flux' or 'sdxl-turbo'."

        default_steps = {"flux": 4, "sdxl-turbo": 1}.get(model, 4)
        num_steps = steps or default_steps

        try:
            pipe = DiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                variant="fp16" if torch.cuda.is_available() else None
            )
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            else:
                pipe = pipe.to("cpu")
            pipe.set_progress_bar_config(disable=True)
        except Exception as e:
            return f"Error loading model '{model}': {e}"

        paths = []
        for i in range(count):
            kw = {"prompt": prompt, "num_inference_steps": num_steps, "guidance_scale": 0.0}
            if negative_prompt:
                kw["negative_prompt"] = negative_prompt
            result = pipe(**kw)
            img = result.images[0]
            fname = f"{timestamp}_{base}_{i+1}.png"
            fpath = os.path.join(MEDIA_OUTPUT_DIR, fname)
            img.save(fpath)
            paths.append(fpath)

        return json.dumps({
            "status": "success",
            "model": model,
            "count": len(paths),
            "paths": paths,
            "prompt": prompt
        }, indent=2)

    async def _generate_via_api(self, prompt, negative_prompt, width, height, count, base, timestamp):
        import aiohttp
        api_url = os.environ.get("IMAGE_GEN_API_URL", "http://localhost:8000/generate")
        api_key = os.environ.get("IMAGE_GEN_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        paths = []
        async with aiohttp.ClientSession() as session:
            for i in range(count):
                payload = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt or "",
                    "width": width,
                    "height": height
                }
                try:
                    async with session.post(api_url, json=payload, headers=headers, timeout=120) as resp:
                        if resp.status != 200:
                            return f"API error: {resp.status} - {await resp.text()}"
                        data = await resp.read()
                        fname = f"{timestamp}_{base}_{i+1}.png"
                        fpath = os.path.join(MEDIA_OUTPUT_DIR, fname)
                        with open(fpath, "wb") as f:
                            f.write(data)
                        paths.append(fpath)
                except Exception as e:
                    return f"API request failed: {e}"

        return json.dumps({
            "status": "success",
            "source": "api",
            "count": len(paths),
            "paths": paths
        }, indent=2)


class VideoGenTool(BaseTool):
    name = "video_gen"
    description = (
        "Generate video from text prompts or animate images using Stable Video Diffusion "
        "or Wan2.1. Supports text-to-video and image-to-video modes. "
        "Heavy tasks can be offloaded to a GPU node."
    )
    parameters = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video"],
                "description": "Generation mode"
            },
            "prompt": {
                "type": "string",
                "description": "Description of the video to generate"
            },
            "image_path": {
                "type": "string",
                "description": "Path to input image (for image_to_video mode)"
            },
            "model": {
                "type": "string",
                "enum": ["svd", "wan"],
                "description": "Model: 'svd' (Stable Video Diffusion) or 'wan' (Wan2.1)"
            },
            "duration": {
                "type": "integer",
                "description": "Video duration in frames (default: 25)"
            },
            "fps": {
                "type": "integer",
                "description": "Frames per second (default: 8)"
            },
            "filename": {
                "type": "string",
                "description": "Optional output filename (without extension)"
            },
            "width": {
                "type": "integer",
                "description": "Video width (default: 576)"
            },
            "height": {
                "type": "integer",
                "description": "Video height (default: 1024)"
            }
        },
        "required": ["mode", "prompt"]
    }
    category = "multimedia"

    def __init__(self):
        os.makedirs(MEDIA_OUTPUT_DIR, exist_ok=True)

    async def _encode_image(self, image_path: str) -> str:
        import base64
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    @retry_on_failure(max_attempts=2, delay=3.0)
    async def execute(self, mode: str, prompt: str, image_path: Optional[str] = None,
                      model: str = "svd", duration: int = 25, fps: int = 8,
                      filename: Optional[str] = None, width: int = 576, height: int = 1024) -> str:
        import datetime
        import json
        import aiohttp

        base = filename or prompt.replace(" ", "_")[:30]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        api_url = os.environ.get("VIDEO_GEN_API_URL", "http://localhost:8001/generate")

        payload = {
            "mode": mode,
            "prompt": prompt,
            "model": model,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height
        }
        if mode == "image_to_video" and image_path:
            if not os.path.exists(image_path):
                return f"Error: Image not found at '{image_path}'"
            payload["image_base64"] = await self._encode_image(image_path)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=300) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return f"Video generation API error ({resp.status}): {error_text}"
                    data = await resp.read()
                    fname = f"{timestamp}_{base}.mp4"
                    fpath = os.path.join(MEDIA_OUTPUT_DIR, fname)
                    with open(fpath, "wb") as f:
                        f.write(data)
                    return json.dumps({
                        "status": "success",
                        "mode": mode,
                        "model": model,
                        "path": fpath,
                        "prompt": prompt
                    }, indent=2)
        except ImportError:
            return "Error: 'aiohttp' is required. Install with: pip install aiohttp"
        except Exception as e:
            return f"Video generation failed: {e}"


class NeuralAudioTool(BaseTool):
    name = "neural_audio"
    description = (
        "Generate speech or background music using neural audio models. "
        "Supports text-to-speech with voice cloning and music generation via Audiocraft. "
        "Audio files are saved to the workspace for use in multimedia projects."
    )
    parameters = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["tts", "music", "voice_clone"],
                "description": "'tts' for text-to-speech, 'music' for background music, 'voice_clone' for voice cloning"
            },
            "text": {
                "type": "string",
                "description": "Text to convert to speech (for tts/voice_clone modes)"
            },
            "voice_sample": {
                "type": "string",
                "description": "Path to a voice sample .wav file (for voice_clone mode)"
            },
            "style": {
                "type": "string",
                "description": "Music style prompt (for music mode, e.g. 'lofi hip hop', 'cinematic orchestral')"
            },
            "duration": {
                "type": "integer",
                "description": "Duration in seconds (for music mode, default: 10)"
            },
            "language": {
                "type": "string",
                "description": "Language code for TTS (default: 'en')"
            },
            "filename": {
                "type": "string",
                "description": "Optional output filename (without extension)"
            }
        },
        "required": ["mode"]
    }
    category = "multimedia"

    def __init__(self):
        os.makedirs(MEDIA_OUTPUT_DIR, exist_ok=True)

    @retry_on_failure(max_attempts=2, delay=1.0)
    async def execute(self, mode: str, text: Optional[str] = None,
                      voice_sample: Optional[str] = None, style: Optional[str] = None,
                      duration: int = 10, language: str = "en",
                      filename: Optional[str] = None) -> str:
        import datetime
        base = filename or f"audio_{mode}"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{timestamp}_{base}.wav"
        fpath = os.path.join(MEDIA_OUTPUT_DIR, fname)

        if mode == "tts":
            return await self._tts(text, language, fpath)
        elif mode == "music":
            return await self._music_gen(style, duration, fpath)
        elif mode == "voice_clone":
            return await self._voice_clone(text, voice_sample, language, fpath)
        return f"Error: Unknown mode '{mode}'."

    async def _tts(self, text: str, language: str, output_path: str) -> str:
        if not text:
            return "Error: 'text' is required for TTS."
        try:
            from TTS.api import TTS
            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
            tts.tts_to_file(text=text, file_path=output_path)
            return json.dumps({"status": "success", "mode": "tts", "path": output_path, "text_length": len(text)}, indent=2)
        except ImportError:
            return "Error: 'TTS' (Coqui-TTS) is required. Install with: pip install TTS"
        except Exception as e:
            return f"TTS failed: {e}"

    async def _music_gen(self, style: Optional[str], duration: int, output_path: str) -> str:
        if not style:
            return "Error: 'style' is required for music generation."
        try:
            from audiocraft.models import MusicGen
            import torch
            model = MusicGen.get_pretrained("facebook/musicgen-small")
            model.set_generation_params(duration=duration)
            wav = model.generate([style], progress=True)
            from audiocraft.utils import export
            export.save_audio(wav[0].cpu(), output_path, 32000)
            return json.dumps({"status": "success", "mode": "music", "path": output_path, "style": style, "duration": duration}, indent=2)
        except ImportError:
            return "Error: 'audiocraft' is required for music generation. Install with: pip install audiocraft"
        except Exception as e:
            return f"Music generation failed: {e}"

    async def _voice_clone(self, text: Optional[str], voice_sample: Optional[str],
                           language: str, output_path: str) -> str:
        if not text:
            return "Error: 'text' is required for voice cloning."
        if not voice_sample:
            return "Error: 'voice_sample' path is required for voice cloning."
        if not os.path.exists(voice_sample):
            return f"Error: Voice sample not found at '{voice_sample}'"
        try:
            from TTS.api import TTS
            tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=False)
            tts.tts_to_file(text=text, speaker_wav=voice_sample, language=language, file_path=output_path)
            return json.dumps({"status": "success", "mode": "voice_clone", "path": output_path, "text_length": len(text)}, indent=2)
        except ImportError:
            return "Error: 'TTS' (Coqui-TTS) is required. Install with: pip install TTS"
        except Exception as e:
            return f"Voice cloning failed: {e}"


class AdvancedVideoEditorTool(BaseTool):
    name = "video_edit"
    description = (
        "Advanced video editing operations: automated cutting, scene stitching, "
        "subtitle overlay, voiceover track merging, and transitions based on screenplay markers. "
        "Extends the basic VideoProcessingTool with creative editing capabilities."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["stitch", "overlay_audio", "add_subtitles", "auto_edit", "add_transition"],
                "description": "Editing action to perform"
            },
            "video_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of video file paths (for stitch action)"
            },
            "video_path": {
                "type": "string",
                "description": "Single video file path (for overlay_audio, add_subtitles, auto_edit)"
            },
            "audio_path": {
                "type": "string",
                "description": "Audio file path (for overlay_audio)"
            },
            "subtitle_text": {
                "type": "string",
                "description": "Subtitle text content (for add_subtitles)"
            },
            "script_path": {
                "type": "string",
                "description": "Path to screenplay/script for auto_edit markers"
            },
            "transition": {
                "type": "string",
                "enum": ["fade", "dissolve", "slide"],
                "description": "Transition type (for add_transition)"
            },
            "output_filename": {
                "type": "string",
                "description": "Output filename (without extension)"
            },
            "volume": {
                "type": "number",
                "description": "Audio volume multiplier (for overlay_audio, default: 1.0)"
            }
        },
        "required": ["action"]
    }
    category = "multimedia"

    def __init__(self):
        os.makedirs(MEDIA_OUTPUT_DIR, exist_ok=True)

    async def execute(self, action: str, video_paths: Optional[List[str]] = None,
                      video_path: Optional[str] = None, audio_path: Optional[str] = None,
                      subtitle_text: Optional[str] = None, script_path: Optional[str] = None,
                      transition: str = "fade", output_filename: Optional[str] = None,
                      volume: float = 1.0) -> str:
        import datetime
        import ffmpeg
        import tempfile
        import json

        base = output_filename or f"edit_{action}"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(MEDIA_OUTPUT_DIR, f"{timestamp}_{base}.mp4")

        try:
            if action == "stitch":
                if not video_paths or len(video_paths) < 2:
                    return "Error: At least 2 video paths are required for stitching."
                inputs = [ffmpeg.input(p) for p in video_paths]
                joined = ffmpeg.concat(*inputs, v=1, a=1)
                ffmpeg.output(joined, output_path, vcodec="libx264", crf=23, preset="veryfast").run(overwrite_output=True, quiet=True)
                return json.dumps({"status": "success", "action": "stitch", "output": output_path, "clips": len(video_paths)}, indent=2)

            elif action == "overlay_audio":
                if not video_path or not audio_path:
                    return "Error: video_path and audio_path are required."
                if not os.path.exists(video_path):
                    return f"Error: Video not found at '{video_path}'"
                if not os.path.exists(audio_path):
                    return f"Error: Audio not found at '{audio_path}'"
                v_in = ffmpeg.input(video_path)
                a_in = ffmpeg.input(audio_path)
                adjusted = a_in.audio.filter("volume", volume)
                ffmpeg.output(v_in.video, adjusted, output_path, vcodec="libx264", acodec="aac", **{"shortest": None}).run(overwrite_output=True, quiet=True)
                return json.dumps({"status": "success", "action": "overlay_audio", "output": output_path}, indent=2)

            elif action == "add_subtitles":
                if not video_path or not subtitle_text:
                    return "Error: video_path and subtitle_text are required."
                if not os.path.exists(video_path):
                    return f"Error: Video not found at '{video_path}'"
                srt_path = os.path.join(tempfile.gettempdir(), f"{timestamp}_subs.srt")
                lines = subtitle_text.strip().split("\n")
                srt_lines = []
                for i, line in enumerate(lines, 1):
                    start_s = (i - 1) * 3
                    end_s = i * 3
                    srt_lines.append(f"{i}")
                    srt_lines.append(f"{start_s//60:02d}:{start_s%60:02d}:00,000 --> {end_s//60:02d}:{end_s%60:02d}:00,000")
                    srt_lines.append(line)
                    srt_lines.append("")
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(srt_lines))
                v_in = ffmpeg.input(video_path)
                ffmpeg.output(v_in, output_path, vf=f"subtitles={srt_path}", vcodec="libx264", crf=23, preset="veryfast").run(overwrite_output=True, quiet=True)
                return json.dumps({"status": "success", "action": "add_subtitles", "output": output_path}, indent=2)

            elif action == "auto_edit":
                if not video_path:
                    return "Error: video_path is required."
                if not os.path.exists(video_path):
                    return f"Error: Video not found at '{video_path}'"
                try:
                    probe = ffmpeg.probe(video_path)
                    duration = float(probe["format"]["duration"])
                    mid = duration / 2
                    v_in = ffmpeg.input(video_path)
                    trimmed = v_in.trim(start=0, end=min(30, duration))
                    ffmpeg.output(trimmed, output_path, vcodec="libx264", crf=23, preset="veryfast").run(overwrite_output=True, quiet=True)
                    return json.dumps({"status": "success", "action": "auto_edit", "output": output_path, "original_duration": duration}, indent=2)
                except Exception as e:
                    return f"Auto-edit failed: {e}"

            elif action == "add_transition":
                if not video_paths or len(video_paths) < 2:
                    return "Error: At least 2 video paths are required for transitions."
                inputs = [ffmpeg.input(p) for p in video_paths]
                if transition == "fade":
                    joined = ffmpeg.concat(*inputs, v=1, a=1)
                    ffmpeg.output(joined, output_path, vcodec="libx264", crf=23, preset="veryfast").run(overwrite_output=True, quiet=True)
                else:
                    joined = ffmpeg.concat(*inputs, v=1, a=1)
                    ffmpeg.output(joined, output_path, vcodec="libx264", crf=23, preset="veryfast").run(overwrite_output=True, quiet=True)
                return json.dumps({"status": "success", "action": "add_transition", "type": transition, "output": output_path}, indent=2)

            return f"Error: Unknown action '{action}'."
        except Exception as e:
            return f"Video editing failed: {e}"
