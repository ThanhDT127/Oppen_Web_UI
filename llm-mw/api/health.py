"""
Health check endpoint for middleware monitoring.
"""

import time
import shutil
from fastapi import Request
from fastapi.responses import JSONResponse
import httpx

from config import LITELLM_BASE, LITELLM_KEY, LOG_DIR
from core.auth import load_users


async def health_check(request: Request):
    """
    Health check endpoint with comprehensive system status.
    Returns 200 if healthy, 503 if degraded.
    """
    status = {"ok": True, "time": int(time.time())}
    
    # Uptime
    start_time = getattr(request.app.state, "start_time", None)
    if start_time:
        status["uptime_seconds"] = int(time.time() - start_time)
    
    # LiteLLM connectivity check
    try:
        client: httpx.AsyncClient = request.app.state.http_client
        resp = await client.get(
            f"{LITELLM_BASE}/health",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            timeout=5.0
        )
        status["litellm"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception as e:
        status["litellm"] = f"error: {str(e)[:100]}"
        status["ok"] = False
    
    # Disk space check (logs directory)
    try:
        disk = shutil.disk_usage(LOG_DIR)
        free_gb = disk.free / (1024 ** 3)
        status["disk_free_gb"] = round(free_gb, 2)
        if free_gb < 1.0:
            status["ok"] = False
            status["warning"] = "Low disk space"
    except Exception:
        pass
    
    # Active users count
    try:
        users = load_users()
        status["active_users"] = sum(1 for u in users if u.get("active", True))
    except Exception:
        pass
    
    return JSONResponse(
        status_code=200 if status["ok"] else 503,
        content=status
    )
