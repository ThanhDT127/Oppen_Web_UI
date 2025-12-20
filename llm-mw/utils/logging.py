"""
Logging utilities for detailed and audit logging.
"""

import json
import datetime as dt
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
from fastapi import Request

from config import detail_logger, audit_logger
from utils.helpers import env_truthy, redact


def detail_log(
    event: str, 
    *, 
    request: Optional[Request] = None, 
    rid: Optional[str] = None, 
    user_id: Optional[str] = None, 
    **fields: Any
):
    """
    Log detailed event information to detail logger.
    
    Args:
        event: Event name/type
        request: Optional FastAPI request object
        rid: Optional request ID
        user_id: Optional user ID
        **fields: Additional fields to log (will be redacted)
    """
    if not env_truthy("MW_DETAILED_LOG", default=True):
        return
    
    try:
        payload: Dict[str, Any] = {
            "ts": dt.datetime.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
            "event": event,
        }
        
        if request is not None:
            payload.update(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "client": getattr(request.client, "host", None),
                }
            )
        
        rid_val = rid or (getattr(request.state, "mw_request_id", None) if request is not None else None)
        if rid_val:
            payload["rid"] = rid_val
        
        uid_val = user_id or (getattr(request.state, "mw_user_id", None) if request is not None else None)
        if uid_val:
            payload["user"] = uid_val

        for k, v in fields.items():
            payload[k] = redact(v)

        detail_logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        # Never break API behavior due to logging failures.
        return


def audit_log(
    user_id: str,
    request_id: str,
    endpoint: str,
    model: Optional[str] = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    image_requests: int = 0,
    stt_requests: int = 0,
    tts_chars: int = 0,
    duration_ms: int = 0,
    status: str = "success",
):
    """
    Write structured audit log entry to audit.jsonl.
    One line per request for aggregation and analysis.
    
    Args:
        user_id: User identifier
        request_id: Unique request ID
        endpoint: API endpoint path
        model: Model name (if applicable)
        tokens_in: Input tokens
        tokens_out: Output tokens
        cost_usd: Cost in USD
        image_requests: Number of image requests
        stt_requests: Speech-to-text requests
        tts_chars: Text-to-speech characters
        duration_ms: Request duration in milliseconds
        status: Request status (success/error)
    """
    try:
        entry = {
            "timestamp": dt.datetime.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
            "request_id": request_id,
            "user_id": user_id,
            "endpoint": endpoint,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost_usd, 6),
            "image_requests": image_requests,
            "stt_requests": stt_requests,
            "tts_chars": tts_chars,
            "duration_ms": duration_ms,
            "status": status,
        }
        audit_logger.info(json.dumps(entry, ensure_ascii=False))
    except Exception:
        return
