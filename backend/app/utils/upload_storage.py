import os
from datetime import datetime
from pathlib import Path


FILES_URL_PREFIX = "/files"


def get_uploads_root() -> Path:
    data_dir = Path(os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")))
    return data_dir / "uploads"


def ensure_upload_dir(relative_dir: str) -> Path:
    safe_relative = relative_dir.strip("/").replace("\\", "/")
    target = get_uploads_root() / safe_relative
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_dated_upload_subdir(namespace: str, now: datetime | None = None) -> str:
    dt = now or datetime.utcnow()
    return f"{namespace}/{dt:%Y/%m/%d}"


def build_files_url(relative_path: str) -> str:
    normalized = relative_path.strip("/").replace("\\", "/")
    return f"{FILES_URL_PREFIX}/{normalized}"


def build_storage_path(relative_path: str) -> str:
    normalized = relative_path.strip("/").replace("\\", "/")
    return f"uploads/{normalized}"
