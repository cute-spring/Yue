import asyncio
import logging
import time
from typing import Dict, Any, List
from app.mcp.manager import mcp_manager
from app.services.llm.factory import list_providers

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self.running = False
        self._task = None
        self.last_check_time = 0
        self.provider_status: List[Dict[str, Any]] = []
        self.mcp_status: List[Dict[str, Any]] = []

    async def start(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor background task started.")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor background task stopped.")

    async def _monitor_loop(self):
        while self.running:
            try:
                await self._perform_checks()
                self.last_check_time = time.time()
            except Exception as e:
                logger.exception("Error during health check cycle")
            
            await asyncio.sleep(self.interval)

    async def _perform_checks(self):
        # 1. Check MCP Servers - try to reconnect disconnected but enabled ones
        configs = mcp_manager.load_config()
        mcp_status = []
        for cfg in configs:
            name = cfg.get("name")
            if not name or not cfg.get("enabled", True):
                continue
            
            is_connected = name in mcp_manager.sessions and not getattr(mcp_manager.sessions[name], "is_closed", False)
            info = mcp_manager.server_info.get(name, {})
            
            mcp_status.append({
                "name": name,
                "status": "online" if is_connected else "offline",
                "version": info.get("version", "unknown"),
                "error": mcp_manager.last_errors.get(name)
            })
            
            # If not connected, attempt a background reconnection
            if not is_connected:
                logger.info("Reconnecting to MCP server: %s", name)
                # Use a separate task for reconnection to not block the monitor loop
                asyncio.create_task(mcp_manager.connect_to_server(cfg))
        
        self.mcp_status = mcp_status
        
        # 2. Check LLM Providers (deep check)
        self.provider_status = await list_providers(refresh=False, check_connectivity=True)
        
    def get_health_data(self):
        return {
            "timestamp": time.time(),
            "mcp_servers": self.mcp_status,
            "mcp_initializing": getattr(mcp_manager, "is_initializing", False),
            "llm_providers": self.provider_status
        }

health_monitor = HealthMonitor()
