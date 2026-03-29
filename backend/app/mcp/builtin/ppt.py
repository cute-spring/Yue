import os
import sys
import json
import asyncio
import datetime
import logging
import re
from pathlib import Path
from typing import Any, Dict
from pydantic_ai import RunContext
from ..base import BaseTool
from .registry import builtin_tool_registry

logger = logging.getLogger(__name__)


def _resolve_exports_dir(backend_dir: str) -> str:
    data_dir = Path(os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")))
    exports_dir = data_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return str(exports_dir.resolve())

class GeneratePptxTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="generate_pptx",
            description="Generate a .pptx file from a structured JSON object. Use this ONLY after the user has confirmed the slide content and outline. Supports rich themes and slide types: title, section, content, two_column, image_left, image_right, quote, stats, timeline, table, chart. Legacy schema with 'title', 'subtitle', and 'slides' list (each with 'title' and 'content' array) is supported.",
            parameters={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "The presentation data including slides, titles, and layout information."
                    }
                },
                "required": ["data"],
            }
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        data = args.get("data")
        if not data:
            return "Error: No data provided for PPT generation."

        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        script_path = os.path.join(backend_dir, "data/skills/ppt-expert/scripts/generate_pptx.py")
        exports_dir = _resolve_exports_dir(backend_dir)
        
        if not os.path.exists(script_path):
            return f"Error: PPT generation script not found at {script_path}"

        def _slugify(value: str) -> str:
            safe = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip())
            return safe.strip("_").lower()

        # Generate a consistent filename if not provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        title = data.get("title")
        title_slug = _slugify(title) if isinstance(title, str) else ""
        default_name = f"{title_slug}.pptx" if title_slug else f"presentation_{timestamp}.pptx"
        filename = data.get("output_file") or default_name
        if not filename.endswith(".pptx"):
            filename += ".pptx"
        
        # Ensure it's just the filename, not a path
        filename = os.path.basename(filename)
        output_path = os.path.join(exports_dir, filename)
        
        # Update data with the absolute path for the script to write to
        data["output_file"] = output_path

        try:
            # Run the script with JSON input
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=json.dumps(data).encode())
            
            if process.returncode != 0:
                return f"Error generating PPT: {stderr.decode()}"
            
            # Return both the local path and the download URL
            download_url = f"/exports/{filename}"
            return json.dumps(
                {
                    "file_path": output_path,
                    "download_url": download_url,
                    "download_markdown": f"[{filename}]({download_url})",
                    "filename": filename,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            logger.exception("Failed to run PPT generation script")
            return f"Error: {str(e)}"

# Register the tool
builtin_tool_registry.register(GeneratePptxTool())
