import os
import sys
import json
import asyncio
import datetime
import logging
from typing import Any, Dict
from pydantic_ai import RunContext
from ..base import BaseTool
from .registry import builtin_tool_registry

logger = logging.getLogger(__name__)

class GeneratePptxTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="generate_pptx",
            description="Generate a .pptx file from a structured JSON object. Use this ONLY after the user has confirmed the slide content and outline. The JSON must contain 'title', 'subtitle', and a 'slides' list (each with 'title' and 'content' array).",
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
        project_root = os.path.abspath(os.path.join(backend_dir, "../"))
        script_path = os.path.join(project_root, ".trae/skills/ppt-expert/scripts/generate_pptx.py")
        exports_dir = os.path.join(backend_dir, "data/exports")
        
        if not os.path.exists(script_path):
            return f"Error: PPT generation script not found at {script_path}"

        # Ensure exports directory exists
        os.makedirs(exports_dir, exist_ok=True)

        # Generate a unique filename if not provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = data.get("output_file") or f"presentation_{timestamp}.pptx"
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
            return (
                f"Successfully generated PPT!\n"
                f"- **Local Path**: `{output_path}`\n"
                f"- **Download Link**: [{filename}]({download_url})\n\n"
                f"You can click the link above to download the file, or find it in the `backend/data/exports` directory."
            )
        except Exception as e:
            logger.exception("Failed to run PPT generation script")
            return f"Error: {str(e)}"

# Register the tool
builtin_tool_registry.register(GeneratePptxTool())
