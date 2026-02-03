import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from pathlib import Path
from app.api import chat, agents, mcp, models, config, notebook
from app.mcp.manager import mcp_manager
from app.observability import TRACE_HEADER, new_trace_id, reset_trace_id, set_trace_id, setup_logging

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Loading env from: %s", env_path.absolute())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MCP Manager
    await mcp_manager.initialize()
    yield
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
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(notebook.router, prefix="/api/notebook", tags=["notebook"])

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
    uvicorn.run("app.main:app", host="127.0.0.1", port=8003, reload=True)
