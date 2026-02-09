import base64
import uuid
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
URL_PREFIX = "/files"

def save_base64_image(base64_str: str) -> str:
    """
    Decodes a base64 string, saves it to disk, and returns the URL path.
    """
    try:
        if "," in base64_str:
            header, encoded = base64_str.split(",", 1)
        else:
            header = ""
            encoded = base64_str
            
        # Determine extension
        ext = ".png" # Default
        if "image/jpeg" in header:
            ext = ".jpg"
        elif "image/gif" in header:
            ext = ".gif"
        elif "image/webp" in header:
            ext = ".webp"
        elif "image/svg+xml" in header:
            ext = ".svg"
            
        # Generate filename
        filename = f"{uuid.uuid4()}{ext}"
        filepath = UPLOAD_DIR / filename
        
        # Ensure dir exists
        if not UPLOAD_DIR.exists():
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            
        # Decode and save
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(encoded))
            
        return f"{URL_PREFIX}/{filename}"
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        # Return original if failed (fallback behavior) or raise
        # If we return original, it might be too large for DB, so raising might be better
        # But for robustness, let's log and maybe return None?
        # Let's re-raise to handle it in the caller
        raise e

def load_image_to_base64(url_path: str) -> str:
    """
    Loads an image from a local URL path and converts it back to base64.
    Returns the full data URI (e.g., data:image/png;base64,...)
    """
    if not url_path.startswith(URL_PREFIX):
        return url_path # Assume it's already base64 or external URL
        
    try:
        filename = url_path.replace(URL_PREFIX + "/", "")
        filepath = UPLOAD_DIR / filename
        
        if not filepath.exists():
            logger.warning(f"Image file not found: {filepath}")
            return url_path # Return path as is if missing
            
        with open(filepath, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode("utf-8")
            
        # Determine mime type
        ext = filepath.suffix.lower()
        mime = "image/png"
        if ext in [".jpg", ".jpeg"]:
            mime = "image/jpeg"
        elif ext == ".gif":
            mime = "image/gif"
        elif ext == ".webp":
            mime = "image/webp"
        elif ext == ".svg":
            mime = "image/svg+xml"
            
        return f"data:{mime};base64,{encoded}"
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return url_path
