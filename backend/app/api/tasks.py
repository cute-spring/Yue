import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.task_service import TaskSpec, task_service, TaskToolResult


router = APIRouter()


class TaskRunRequest(BaseModel):
    parent_chat_id: str
    tasks: list[TaskSpec]

class TaskCancelRequest(BaseModel):
    parent_chat_id: str
    task_id: str

@router.post("/cancel")
async def tasks_cancel(request: TaskCancelRequest):
    ok = await task_service.cancel_task(request.parent_chat_id, request.task_id)
    return {"ok": ok}


@router.post("/run", response_model=TaskToolResult)
async def tasks_run(request: TaskRunRequest):
    try:
        return await task_service.run_tasks(request.parent_chat_id, request.tasks)
    except ValueError as e:
        if str(e) == "parent_chat_not_found":
            raise HTTPException(status_code=404, detail="Parent chat not found")
        raise


@router.post("/stream")
async def tasks_stream(request: TaskRunRequest):
    q: asyncio.Queue = asyncio.Queue()

    async def emit(evt):
        await q.put(evt.model_dump(mode="json"))

    async def runner():
        try:
            result = await task_service.run_tasks(request.parent_chat_id, request.tasks, emit=emit)
            await q.put({"type": "task_result", "result": result.model_dump(mode="json")})
        except ValueError as e:
            if str(e) == "parent_chat_not_found":
                await q.put({"type": "task_error", "error": "parent_chat_not_found"})
            else:
                await q.put({"type": "task_error", "error": str(e)})
        except Exception as e:
            await q.put({"type": "task_error", "error": str(e)})
        finally:
            await q.put(None)

    asyncio.create_task(runner())

    async def event_generator():
        while True:
            item = await q.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
