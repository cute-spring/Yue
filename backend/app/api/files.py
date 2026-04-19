import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.utils.upload_storage import (
    build_dated_upload_subdir,
    build_files_url,
    build_storage_path,
    ensure_upload_dir,
)


router = APIRouter()

DEFAULT_MAX_FILES = 10
DEFAULT_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
}


class UploadedFileMeta(BaseModel):
    id: str
    kind: str = "file"
    display_name: str
    storage_path: str
    url: str
    mime_type: str
    size_bytes: int
    extension: str
    source: str = "upload"
    status: str = "ready"


class UploadFilesResponse(BaseModel):
    files: list[UploadedFileMeta]


class UploadPolicyResponse(BaseModel):
    max_files: int
    max_file_size_bytes: int
    allowed_mime_types: list[str]
    allowed_extensions: list[str]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _sanitize_display_name(name: str) -> str:
    base = Path(name or "file").name
    return re.sub(r"[^\w.\- ]+", "_", base).strip() or "file"


def _validate_file_type(mime_type: str, extension: str) -> None:
    if mime_type not in ALLOWED_MIME_TYPES or extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsupported_file_type",
                "message": "unsupported_file_type",
                "allowed_mime_types": sorted(ALLOWED_MIME_TYPES),
                "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
            },
        )


def _get_upload_policy() -> UploadPolicyResponse:
    return UploadPolicyResponse(
        max_files=_env_int("YUE_MAX_UPLOAD_FILES", DEFAULT_MAX_FILES),
        max_file_size_bytes=_env_int("YUE_MAX_UPLOAD_FILE_SIZE_BYTES", DEFAULT_MAX_FILE_SIZE_BYTES),
        allowed_mime_types=sorted(ALLOWED_MIME_TYPES),
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
    )


@router.get("/policy", response_model=UploadPolicyResponse)
async def get_upload_policy():
    return _get_upload_policy()


@router.post("", response_model=UploadFilesResponse)
async def upload_files(files: list[UploadFile] = File(...)):
    policy = _get_upload_policy()
    max_files = policy.max_files
    max_file_size = policy.max_file_size_bytes

    if not files:
        raise HTTPException(status_code=400, detail={"code": "no_files", "message": "no_files"})
    if len(files) > max_files:
        raise HTTPException(
            status_code=400,
            detail={"code": "too_many_files", "message": "too_many_files", "max_files": max_files},
        )

    date_subdir = build_dated_upload_subdir("chat")
    target_dir = ensure_upload_dir(date_subdir)
    uploaded: list[UploadedFileMeta] = []

    for file in files:
        display_name = _sanitize_display_name(file.filename or "file")
        extension = Path(display_name).suffix.lower()
        mime_type = (file.content_type or "").lower()
        _validate_file_type(mime_type, extension)

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail={"code": "empty_file", "message": "empty_file"})
        size_bytes = len(content)
        if size_bytes > max_file_size:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "file_too_large",
                    "message": "file_too_large",
                    "max_file_size_bytes": max_file_size,
                },
            )

        attachment_id = f"att_{uuid.uuid4().hex[:12]}"
        stored_name = f"{attachment_id}{extension}"
        absolute_path = target_dir / stored_name
        absolute_path.write_bytes(content)

        relative_path = f"{date_subdir}/{stored_name}"
        uploaded.append(
            UploadedFileMeta(
                id=attachment_id,
                display_name=display_name,
                storage_path=build_storage_path(relative_path),
                url=build_files_url(relative_path),
                mime_type=mime_type,
                size_bytes=size_bytes,
                extension=extension,
            )
        )

    return UploadFilesResponse(files=uploaded)
