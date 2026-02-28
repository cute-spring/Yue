from fastapi import APIRouter
from typing import Dict, Any, List
import time
import psutil
import os
from app.mcp.manager import mcp_manager
from app.services.llm.factory import list_providers
from app.services.health_monitor import health_monitor

router = APIRouter()

START_TIME = time.time()

@router.get("/")
async def health_check():
    """
    Comprehensive health check for the service.
    """
    # 1. Basic Info
    uptime = time.time() - START_TIME
    
    # 2. Get status from health monitor (periodically updated in background)
    health_data = health_monitor.get_health_data()
    mcp_status = health_data["mcp_servers"]
    llm_providers = health_data["llm_providers"]
    mcp_initializing = health_data.get("mcp_initializing", False)
    
    mcp_ok = all(s["status"] == "online" for s in mcp_status)
    llm_ok = any(p["status"] == "online" for p in llm_providers if p["configured"])
    
    # 3. System Resources
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    status = "ok"
    if mcp_initializing:
        status = "initializing"
    elif not mcp_ok or not llm_ok:
        status = "degraded"
        
    return {
        "status": status,
        "uptime_seconds": int(uptime),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_background_check": health_data["timestamp"],
        "mcp": {
            "status": "initializing" if mcp_initializing else ("ok" if mcp_ok else "error"),
            "initializing": mcp_initializing,
            "servers": mcp_status
        },
        "llm": {
            "status": "ok" if llm_ok else "warning",
            "providers": llm_providers
        },
        "system": {
            "memory_rss_mb": int(memory_info.rss / 1024 / 1024),
            "cpu_percent": process.cpu_percent()
        }
    }
