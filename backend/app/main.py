import os
import sys

# Workaround for WeasyPrint on macOS Apple Silicon (Homebrew)
# Must be set before any other imports that might load cffi/glib
if sys.platform == "darwin":
    homebrew_lib = "/opt/homebrew/lib"
    if os.path.exists(homebrew_lib) and "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = homebrew_lib

import logging
import asyncio
import shutil
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from pathlib import Path
from app.api import chat, agents, mcp, models, config, notebook, health, skills, skill_groups, export
from app.mcp.manager import mcp_manager
from app.services.skill_service import skill_registry, SkillDirectoryResolver
from app.observability import TRACE_HEADER, new_trace_id, reset_trace_id, set_trace_id, setup_logging

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Loading env from: %s", env_path.absolute())

from app.services.health_monitor import health_monitor

@asynccontextmanager
async def lifespan(app: FastAPI):
    resolver = SkillDirectoryResolver()
    layered_dirs = resolver.resolve()
    for item in layered_dirs:
        if item.layer in {"workspace", "user"}:
            Path(item.path).mkdir(parents=True, exist_ok=True)
    skill_registry.set_layered_skill_dirs(layered_dirs)
    skill_registry.skill_dirs = [item.path for item in layered_dirs]
    skill_registry.load_all()
    watch_enabled = os.getenv("YUE_SKILLS_WATCH_ENABLED", "true").lower() not in {"0", "false", "off"}
    debounce_ms = int(os.getenv("YUE_SKILLS_RELOAD_DEBOUNCE_MS", "2000"))
    if watch_enabled:
        skill_registry.start_runtime_watch(layer="user", debounce_ms=debounce_ms)
    
    # Initialize MCP Manager first
    await mcp_manager.initialize()
    # Start Health Monitor
    await health_monitor.start()
    yield
    # Stop Health Monitor
    await health_monitor.stop()
    skill_registry.stop_runtime_watch()
    # Cleanup MCP Manager
    await mcp_manager.cleanup()

app = FastAPI(title="Yue Agent Platform API", lifespan=lifespan)

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get(TRACE_HEADER) or new_trace_id()
    token = set_trace_id(trace_id)
    try:
        response = await call_next(request)
    finally:
        reset_trace_id(token)
    response.headers[TRACE_HEADER] = trace_id
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(skill_groups.router, prefix="/api/skill-groups", tags=["skill-groups"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(notebook.router, prefix="/api/notebook", tags=["notebook"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(export.router, prefix="/api", tags=["export"])

# Mount Uploads & Exports Directory
data_dir = Path(os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data")))
uploads_dir = data_dir / "uploads"
exports_dir = data_dir / "exports"
for d in [uploads_dir, exports_dir]:
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)

app.mount("/files", StaticFiles(directory=str(uploads_dir)), name="uploads")

@app.get("/exports/{file_path:path}")
async def get_export_file(file_path: str):
    if not file_path or file_path.startswith(("/", "\\")) or ".." in file_path:
        raise HTTPException(status_code=400, detail="invalid_path")
    exports_root = exports_dir.resolve()
    candidate = (exports_root / file_path).resolve()
    if str(candidate).startswith(str(exports_root)) and candidate.is_file():
        return FileResponse(str(candidate))
    requested_name = Path(file_path).name
    if requested_name:
        def normalize_name(name: str) -> str:
            base = Path(name).stem
            return re.sub(r"[^a-zA-Z0-9]+", "", base).lower()
        requested_norm = normalize_name(requested_name)
        if requested_norm:
            for child in exports_root.iterdir():
                if child.is_file() and normalize_name(child.name) == requested_norm:
                    return FileResponse(str(child))
    fallback_root = Path("/mnt/data")
    fallback_name = Path(file_path).name
    fallback = (fallback_root / fallback_name).resolve()
    if fallback_root.exists() and fallback.is_file():
        exports_root.mkdir(parents=True, exist_ok=True)
        dest = exports_root / fallback_name
        try:
            shutil.copy2(str(fallback), str(dest))
        except Exception:
            logger.exception("Failed to copy export fallback file")
            raise HTTPException(status_code=500, detail="export_copy_failed")
        return FileResponse(str(dest))
    raise HTTPException(status_code=404, detail="export_not_found")

# Mount Static Files (Frontend)
# In production, we expect the frontend build to be in 'static' folder
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
else:
    @app.get("/")
    async def root():
        return {"message": "Welcome to Yue Agent Platform API. Static files not found."}

if __name__ == "__main__":
    import uvicorn
    # 增加超时时间以支持长时间生成的 LLM 请求
    # timeout_keep_alive: 保持连接活跃的时间
    # timeout_graceful_shutdown: 优雅停机等待时间
    # 注意：uvicorn 本身没有直接限制 HTTP 请求处理时间的参数（由 FastAPI/程序控制）
    # 但我们可以通过增加 keep-alive 超时来防止网络层面的断连
    uvicorn.run("app.main:app", host="127.0.0.1", port=8003, reload=False, timeout_keep_alive=600)
