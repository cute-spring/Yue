import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from pathlib import Path
from app.api import chat, agents, mcp, models, config
from app.mcp.manager import mcp_manager

# Load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
print(f"Loading env from: {env_path.absolute()}")
load_dotenv(dotenv_path=env_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MCP Manager
    await mcp_manager.initialize()
    yield
    # Cleanup MCP Manager
    await mcp_manager.cleanup()

app = FastAPI(title="Yue Agent Platform API", lifespan=lifespan)

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
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
