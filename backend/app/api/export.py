from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.export_service import ExportService
import os
from typing import Literal

router = APIRouter()

class ExportRequest(BaseModel):
    content: str
    format: Literal['pdf', 'docx', 'txt']

def remove_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error removing file {path}: {e}")

@router.post("/export")
async def export_message(req: ExportRequest, background_tasks: BackgroundTasks):
    try:
        if req.format == 'pdf':
            path = ExportService.export_to_pdf(req.content)
            media_type = 'application/pdf'
            filename = 'export.pdf'
        elif req.format == 'docx':
            path = ExportService.export_to_docx(req.content)
            media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            filename = 'export.docx'
        elif req.format == 'txt':
            path = ExportService.export_to_txt(req.content)
            media_type = 'text/plain'
            filename = 'export.txt'
        background_tasks.add_task(remove_file, path)

        return FileResponse(
            path=path, 
            media_type=media_type, 
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
