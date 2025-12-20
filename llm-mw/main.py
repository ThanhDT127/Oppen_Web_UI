"""
LLM Middleware - Modular FastAPI Application
Provides authentication, quota management, and proxying for LLM requests.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

from config import logger
from utils.logging import detail_log, audit_log

# Import route handlers
from api.health import health_check
from api.models import list_models
from api.chat import chat_completions
from api.images import generate_images
from api.audio import transcribe_audio
from api.media import serve_media
from api.admin import get_usage, reset_quota, reconcile_usage
from api.summary import get_summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=100)
    timeout = httpx.Timeout(300.0, connect=10.0)
    app.state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
    app.state.start_time = time.time()
    logger.info("startup: http_client created")
    
    yield
    
    # Shutdown
    client = getattr(app.state, "http_client", None)
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass
    logger.info("shutdown: http_client closed")


# Create FastAPI app with lifespan
app = FastAPI(
    title="LLM Middleware (Quota+Auth+Stream+Reconcile)", 
    version="4.0-modular",
    lifespan=lifespan
)

# CORS middleware - Allow calls from local tools/UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing and audit trail"""
    t0 = time.perf_counter()
    status_code: int = 500
    detail_log("inbound", request=request)
    try:
        response = await call_next(request)
        status_code = getattr(response, "status_code", 200)
        return response
    except Exception:
        raise
    finally:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        rid = getattr(request.state, "mw_request_id", None) or request.headers.get("X-Request-ID") or "-"
        logger.info(
            "req rid=%s method=%s path=%s status=%s ms=%.1f",
            rid,
            request.method,
            request.url.path,
            status_code,
            dt_ms,
        )
        detail_log("outbound", request=request, status=status_code, ms=round(dt_ms, 1))
        
        # Audit log: record completion if user authenticated
        user_id = getattr(request.state, "mw_user_id", None)
        if user_id and request.url.path.startswith("/v1/"):
            audit_log(
                user_id=user_id,
                request_id=rid,
                endpoint=request.url.path,
                duration_ms=int(dt_ms),
                status="success" if status_code < 400 else "error",
            )


# Register routes
# Health & Models
app.add_api_route("/health", health_check, methods=["GET"])
app.add_api_route("/v1/models", list_models, methods=["GET"])

# Chat, Images, Audio
app.add_api_route("/v1/chat/completions", chat_completions, methods=["POST"])
app.add_api_route("/v1/images/generations", generate_images, methods=["POST"])
app.add_api_route("/v1/audio/transcriptions", transcribe_audio, methods=["POST"])

# Media serving
app.add_api_route("/v1/_mw/media/{name}", serve_media, methods=["GET"])

# Admin endpoints
app.add_api_route("/admin/usage", get_usage, methods=["GET"])
app.add_api_route("/admin/reset", reset_quota, methods=["POST"])
app.add_api_route("/admin/reconcile", reconcile_usage, methods=["POST"])

# Summary endpoint
app.add_api_route("/v1/_mw/summary", get_summary, methods=["GET"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=False)
