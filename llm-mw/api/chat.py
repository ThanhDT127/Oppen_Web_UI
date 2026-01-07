"""
Chat completions endpoint with streaming support.
"""

import uuid
import json
import asyncio
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from config import LITELLM_BASE, LITELLM_KEY, logger
from core.auth import require_user, assert_model_allowed, load_users, save_users, get_lock
from core.quota import maybe_reset_quota, enforce_and_bump_quota
from core.cost import calc_cost_usd, append_pending, remove_pending, load_prices
from core.audit_state import init_audit_state, set_usage_state, set_error_state
from services.litellm import get_cost_from_headers, find_usage_in_log
from utils.helpers import truncate_text, extract_text_from_messages, safe_headers
from utils.logging import detail_log, write_audit_line


async def _finalize_streaming(request: Request, user: dict, model: str, request_id: str, usage_data: dict):
    """
    Finalize streaming request: Calculate cost, bump quota, write reconciled audit.
    
    Args:
        request: FastAPI Request
        user: User dict
        model: Model name
        request_id: Request ID
        usage_data: Usage dict from stream (if stream_options.include_usage), or None
    """
    try:
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        cost_usd = 0.0
        
        # Method 1: Extract from stream (if stream_options.include_usage was set)
        if usage_data:
            prompt_tokens = int(usage_data.get("prompt_tokens", 0))
            completion_tokens = int(usage_data.get("completion_tokens", 0))
            total_tokens = int(usage_data.get("total_tokens", prompt_tokens + completion_tokens))
            logger.info("stream_finalize rid=%s tokens=%d (from stream)", request_id, total_tokens)
        
        # Method 2: Fallback to LiteLLM log parsing
        else:
            await asyncio.sleep(1)  # Wait for LiteLLM to write log
            usage = find_usage_in_log(request_id)
            if usage:
                prompt_tokens = int(usage.get("prompt_tokens", 0))
                completion_tokens = int(usage.get("completion_tokens", 0))
                total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
                logged_cost = usage.get("response_cost")
                if logged_cost:
                    try:
                        cost_usd = float(logged_cost)
                    except Exception:
                        pass
                logger.info("stream_finalize rid=%s tokens=%d (from litellm log)", request_id, total_tokens)
        
        # Calculate cost if not from LiteLLM
        if cost_usd == 0.0 and total_tokens > 0:
            prices = load_prices()
            cost_usd = calc_cost_usd(model, prompt_tokens, completion_tokens, prices)
        
        # Bump quota (CRITICAL for billing)
        if total_tokens > 0 or cost_usd > 0:
            lock = get_lock()
            with lock:
                users = load_users()
                for u in users:
                    if u.get("user_id") == user["user_id"]:
                        maybe_reset_quota(u)
                        u["used_tokens"] = u.get("used_tokens", 0) + total_tokens
                        u["used_cost_usd"] = u.get("used_cost_usd", 0.0) + cost_usd
                        quota = u.setdefault("quota", {})
                        quota["used_tokens"] = quota.get("used_tokens", 0) + total_tokens
                        quota["used_cost_usd"] = quota.get("used_cost_usd", 0.0) + cost_usd
                        break
                save_users(users)
        
        # Write reconciled audit line
        write_audit_line({
            "ts": datetime.now(timezone.utc).isoformat(),
            "rid": request_id,
            "user_id": user["user_id"],
            "endpoint": "/v1/chat/completions",
            "model": model,
            "status": "reconciled",
            "status_code": 200,
            "latency_ms": None,
            "tokens_in": prompt_tokens,
            "tokens_out": completion_tokens,
            "tokens_total": total_tokens,
            "cost_usd": cost_usd,
            "image_count": None,
            "tts_chars": None,
            "stt_seconds": None,
            "video_count": None,
            "error_type": None,
            "error_message": None
        })
        
        logger.info("stream_finalize_complete rid=%s tokens=%d cost=$%.6f", request_id, total_tokens, cost_usd)
    
    except Exception as e:
        logger.error("stream_finalize_error rid=%s: %s", request_id, str(e))


async def chat_completions(request: Request):
    """
    Proxy chat completions to LiteLLM with quota enforcement.
    Supports both streaming and non-streaming modes.
    """
    user = require_user(request)

    body = await request.json()
    model = body.get("model")
    if not model:
        raise HTTPException(400, "Missing model")
    
    # Initialize audit state early
    rid = init_audit_state(request, user["user_id"], "/v1/chat/completions", model)

    # Process multimodal content (images, documents, and other file attachments in messages)
    messages = body.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    
                    # Handle image_url content type
                    if item.get("type") == "image_url":
                        image_url_obj = item.get("image_url")
                        if isinstance(image_url_obj, dict):
                            url = image_url_obj.get("url")
                            if isinstance(url, str) and url.startswith("data:"):
                                # Keep data URLs inline - don't materialize 
                                # LiteLLM has issues downloading from localhost
                                pass
                    
                    # Handle file attachments (documents, PDFs, etc.)
                    # Some models accept file content in various formats
                    elif item.get("type") in ("file", "document", "attachment"):
                        # Check for data URL in various fields
                        for url_field in ["url", "file_url", "data"]:
                            url = item.get(url_field)
                            if isinstance(url, str) and url.startswith("data:"):
                                # Keep data URLs inline
                                pass
                                break
                    
                    # Handle generic data URLs in any content item
                    elif "url" in item:
                        url = item.get("url")
                        if isinstance(url, str) and url.startswith("data:"):
                            # Keep data URLs inline
                            pass

    prompt_preview = extract_text_from_messages(body.get("messages"))
    detail_log(
        "chat.request",
        request=request,
        user_id=user.get("user_id"),
        model=model,
        stream=bool(body.get("stream")),
        prompt=truncate_text(prompt_preview, limit=2000),
        body=body,
    )

    assert_model_allowed(user, model)

    maybe_reset_quota(user)
    quota = user.get("quota", {})
    limit_tokens = int(quota.get("limit_tokens", 0))
    used_tokens = int(quota.get("used_tokens", 0))
    limit_cost = float(quota.get("limit_cost_usd", 0.0))
    used_cost = float(quota.get("used_cost_usd", 0.0))

    # OpenAI's newest reasoning-first models may treat `max_tokens` differently.
    # When users chat via OpenWebUI, it often sends `max_tokens`.
    # For gpt-5*, translate to `max_completion_tokens` to avoid responses that spend all tokens
    # on reasoning and return empty visible content.
    if isinstance(model, str) and model.startswith("gpt-5"):
        if "max_tokens" in body and "max_completion_tokens" not in body:
            body["max_completion_tokens"] = body.get("max_tokens")
            body.pop("max_tokens", None)

    # Use rid from audit_state (already generated)
    request_id = rid
    body["user"] = user["user_id"]
    metadata = body.get("metadata") or {}
    metadata["mw_request_id"] = request_id
    body["metadata"] = metadata

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    is_stream = bool(body.get("stream"))

    if is_stream:
        return await _handle_streaming(request, user, model, body, headers, request_id)
    else:
        return await _handle_non_streaming(request, user, model, body, headers, request_id, limit_tokens, used_tokens, limit_cost, used_cost)


async def _handle_streaming(request: Request, user: dict, model: str, body: dict, headers: dict, request_id: str):
    """Handle streaming chat completions"""
    from utils.logging import write_audit_line
    from core.audit_state import mark_audit_logged
    from datetime import datetime, timezone
    
    # Write pending audit line immediately before streaming
    write_audit_line({
        "ts": datetime.now(timezone.utc).isoformat(),
        "rid": request_id,
        "user_id": user["user_id"],
        "endpoint": "/v1/chat/completions",
        "model": model,
        "status": "pending",
        "status_code": None,
        "latency_ms": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0,
        "cost_usd": 0.0,
        "image_count": None,
        "tts_chars": None,
        "stt_seconds": None,
        "video_count": None,
        "error_type": None,
        "error_message": None
    })
    
    # Mark as logged to prevent middleware from logging again
    mark_audit_logged(request)
    
    append_pending(request_id, user["user_id"])

    # Important: like TTS, don't create the upstream stream inside an `async with` that
    # exits before StreamingResponse iterates. We open the stream first, validate status,
    # then stream bytes and always clean up.
    logger.info("stream_start rid=%s model=%s", request_id, model)

    client = httpx.AsyncClient(timeout=600)
    detail_log(
        "upstream.request",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        upstream=f"{LITELLM_BASE}/chat/completions",
        method="POST",
        headers=safe_headers(headers),
        body=body,
    )
    req = client.build_request("POST", f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
    resp = await client.send(req, stream=True)

    if resp.status_code >= 400:
        try:
            error_bytes = await resp.aread()
        finally:
            remove_pending(request_id)
            try:
                await resp.aclose()
            finally:
                await client.aclose()
        error_text = error_bytes.decode("utf-8", errors="ignore")
        logger.warning("stream_error rid=%s status=%s body=%s", request_id, resp.status_code, error_text[:500])
        raise HTTPException(resp.status_code, error_text)

    async def _iter_bytes():
        sampled: bytearray = bytearray()
        usage_data = None  # Track usage from stream_options.include_usage
        
        try:
            async for chunk in resp.aiter_bytes():
                if len(sampled) < 8192:
                    sampled.extend(chunk[: max(0, 8192 - len(sampled))])
                
                # Try to extract usage from SSE data (stream_options.include_usage)
                try:
                    chunk_str = chunk.decode("utf-8", errors="ignore")
                    if chunk_str.startswith("data: ") and not chunk_str.startswith("data: [DONE]"):
                        json_str = chunk_str[6:].strip()
                        if json_str:
                            chunk_data = json.loads(json_str)
                            # Extract usage from final chunk
                            if "usage" in chunk_data:
                                usage_data = chunk_data["usage"]
                except Exception:
                    pass  # Ignore parsing errors
                
                yield chunk
        except (httpx.StreamClosed, httpx.RemoteProtocolError, asyncio.CancelledError):
            return
        finally:
            # Finalize streaming: reconcile usage and bump quota
            await _finalize_streaming(request, user, model, request_id, usage_data)
            
            remove_pending(request_id)
            try:
                await resp.aclose()
            finally:
                await client.aclose()
            logger.info("stream_end rid=%s", request_id)
            if sampled:
                detail_log(
                    "chat.stream.sample",
                    request=request,
                    rid=request_id,
                    user_id=user.get("user_id"),
                    sample_bytes=len(sampled),
                    sample=truncate_text(sampled.decode("utf-8", errors="ignore"), limit=4000),
                )

    return StreamingResponse(
        _iter_bytes(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )


async def _handle_non_streaming(request: Request, user: dict, model: str, body: dict, headers: dict, request_id: str, limit_tokens: int, used_tokens: int, limit_cost: float, used_cost: float):
    """Handle non-streaming chat completions"""
    client: httpx.AsyncClient = request.app.state.http_client
    detail_log(
        "upstream.request",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        upstream=f"{LITELLM_BASE}/chat/completions",
        method="POST",
        headers=safe_headers(headers),
        body=body,
    )
    resp = await client.post(f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
    if resp.status_code >= 400:
        try:
            raise HTTPException(resp.status_code, resp.json())
        except Exception:
            raise HTTPException(resp.status_code, resp.text)
    data = resp.json()
    try:
        content_preview = (((data.get("choices") or [{}])[0].get("message") or {}).get("content"))
    except Exception:
        content_preview = None
    detail_log(
        "chat.response",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        status=resp.status_code,
        model=model,
        content=truncate_text(content_preview, limit=2000),
        usage=data.get("usage"),
    )
    litellm_cost = get_cost_from_headers(resp.headers)

    usage = data.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    
    # Load prices for cost calculation
    from core.cost import load_prices
    prices = load_prices()
    cost_usd = litellm_cost if litellm_cost > 0 else calc_cost_usd(model, prompt_tokens, completion_tokens, prices)
    
    # Set usage state for audit (BEFORE quota check - will be logged even if quota fails)
    set_usage_state(request, prompt_tokens, completion_tokens, total_tokens, cost_usd)

    if limit_tokens > 0 and used_tokens + total_tokens > limit_tokens:
        set_error_state(request, "quota", f"Token quota exceeded")
        raise HTTPException(403, f"Token quota exceeded for {user['user_id']} ({used_tokens + total_tokens}/{limit_tokens})")
    if limit_cost > 0 and used_cost + cost_usd > limit_cost + 1e-9:
        set_error_state(request, "quota", f"Cost quota exceeded")
        raise HTTPException(403, f"Cost quota exceeded for {user['user_id']} (${used_cost + cost_usd:.2f}/${limit_cost:.2f})")

    enforce_and_bump_quota(user["user_id"], add_tokens=total_tokens, add_cost_usd=cost_usd)

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    data["_mw_added_tokens"] = total_tokens
    data["_mw_added_cost_usd"] = round(cost_usd, 6)

    return JSONResponse(status_code=200, content=data)
