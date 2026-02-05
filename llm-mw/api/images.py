"""
Image generation endpoint with fallback support.
"""

import uuid
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import httpx

from config import LITELLM_BASE, LITELLM_KEY
from core.auth import require_user, assert_model_allowed
from core.quota import maybe_reset_quota, enforce_and_bump_quota
from core.cost import load_prices, calc_image_cost_from_body
from core.audit_state import init_audit_state, set_usage_state, set_counters, set_error_state, mark_audit_logged
from services.litellm import get_cost_from_headers
from utils.helpers import truncate_text, safe_headers
from utils.logging import detail_log, write_audit_line
from utils.media import maybe_materialize_image_items
from datetime import datetime, timezone as dt_timezone


def _extract_provider(model: str) -> str:
    """
    Extract provider from model name.
    
    Args:
        model: Model name (e.g., "gemini-2.5-flash-image", "gpt-image-1")
        
    Returns:
        Provider name ("gemini", "openai", "unknown")
    """
    model_lower = (model or "").lower()
    if model_lower.startswith("gemini-"):
        return "gemini"
    elif model_lower.startswith("gpt-") or model_lower.startswith("dalle-"):
        return "openai"
    return "unknown"


def _write_image_audit(
    request_id: str,
    user_id: str,
    model_requested: str,
    model_effective: str,
    provider: str,
    size: str,
    n: int,
    response_format: str,
    status_code: int,
    cost_usd: float
):
    """
    Write detailed audit log for image generation (control-grade).
    
    This provides enhanced tracking beyond standard audit_state:
    - purpose="image_gen" for filtering
    - model_requested vs model_effective (tracks fallback)
    - provider identification
    - image-specific params (size, n, format)
    - upstream_status for debugging
    
    Args:
        request_id: Request ID
        user_id: User identifier
        model_requested: Originally requested model
        model_effective: Actually used model (after fallback)
        provider: Provider name (gemini/openai/unknown)
        size: Image size (e.g., "1024x1024")
        n: Number of images
        response_format: Output format (url/b64_json)
        status_code: HTTP status code
        cost_usd: Total cost in USD
    """
    try:
        write_audit_line({
            "ts": datetime.now(dt_timezone.utc).isoformat(),
            "rid": request_id,
            "user_id": user_id,
            "endpoint": "/v1/images/generations",
            "purpose": "image_gen",
            "model": model_effective,
            "model_requested": model_requested if model_requested != model_effective else None,
            "provider": provider,
            "status": "ok",
            "status_code": status_code,
            "upstream_status": status_code,
            "latency_ms": None,  # Set by middleware
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_total": 0,
            "cost_usd": cost_usd,
            "image_count": n,
            "image_size": size,
            "image_format": response_format,
            "tts_chars": None,
            "stt_seconds": None,
            "video_count": None,
            "error_type": None,
            "error_message": None
        })
    except Exception:
        pass  # Never break request due to audit failure


async def generate_images(request: Request):
    """
    Generate images via LiteLLM with quota enforcement and automatic fallback.
    Defaults to Gemini to avoid OpenAI org-verification restrictions.
    """
    user = require_user(request)
    body = await request.json()
    # Default to Gemini image model to avoid OpenAI org-verification restrictions in many accounts.
    model = body.get("model") or "gemini-2.5-flash-image"
    assert_model_allowed(user, model)
    
    # Initialize audit state
    rid = init_audit_state(request, user["user_id"], "/v1/images/generations", model)

    detail_log(
        "images.request",
        request=request,
        user_id=user.get("user_id"),
        model=model,
        prompt=truncate_text(body.get("prompt"), limit=2000),
        body=body,
    )

    maybe_reset_quota(user)
    # Use rid from audit_state (already generated)
    request_id = rid
    body["user"] = user["user_id"]
    metadata = body.get("metadata") or {}
    metadata["mw_request_id"] = request_id
    body["metadata"] = metadata

    # Enforce count quotas before calling provider (do not charge unless call succeeds).
    enforce_and_bump_quota(user["user_id"], apply=False, add_image_requests=1)

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    # Some providers/models reject certain OpenAI-style params. Keep the middleware permissive
    # but drop params that LiteLLM flags as unsupported for specific models.
    forward_body = dict(body)
    if isinstance(model, str) and model.startswith("gpt-image-1"):
        forward_body.pop("response_format", None)
    # Gemini image models reject the OpenAI `user` parameter.
    if isinstance(model, str) and model.startswith("gemini-"):
        forward_body.pop("user", None)
        forward_body.pop("metadata", None)

    def _looks_like_org_verification_error(text: str) -> bool:
        t = (text or "").lower()
        return "organization must be verified" in t or "verify organization" in t

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        detail_log(
            "upstream.request",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            upstream=f"{LITELLM_BASE}/images/generations",
            method="POST",
            headers=safe_headers(headers),
            body=forward_body,
        )
        resp = await client.post(f"{LITELLM_BASE}/images/generations", headers=headers, json=forward_body, timeout=600)
    except httpx.RequestError as e:
        detail_log(
            "upstream.error",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            upstream=f"{LITELLM_BASE}/images/generations",
            error=f"{e.__class__.__name__}",
        )
        set_error_state(request, "provider", f"Upstream LiteLLM unavailable: {e.__class__.__name__}")
        raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")
    
    if resp.status_code >= 400 and isinstance(model, str) and model == "gpt-image-1":
        # If OpenAI image access is restricted, transparently fall back to Gemini.
        error_text = ""
        try:
            error_text = json.dumps(resp.json())
        except Exception:
            try:
                error_text = resp.text
            except Exception:
                error_text = ""

        if _looks_like_org_verification_error(error_text):
            fallback_model = "gemini-2.5-flash-image"
            assert_model_allowed(user, fallback_model)
            model = fallback_model
            forward_body["model"] = fallback_model
            # Gemini image models reject the OpenAI `user` parameter.
            forward_body.pop("user", None)
            forward_body.pop("metadata", None)
            try:
                resp = await client.post(f"{LITELLM_BASE}/images/generations", headers=headers, json=forward_body, timeout=600)
            except httpx.RequestError as e:
                set_error_state(request, "provider", f"Upstream LiteLLM unavailable (fallback): {e.__class__.__name__}")
                raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")

    if resp.status_code >= 400:
        set_error_state(request, "provider", f"LiteLLM returned {resp.status_code}")
        try:
            raise HTTPException(resp.status_code, resp.json())
        except Exception:
            raise HTTPException(resp.status_code, resp.text)
    data = resp.json()

    detail_log(
        "upstream.response",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        status=resp.status_code,
        headers=dict(resp.headers),
        body=data,
    )

    # Help UIs that only know how to render image URLs by synthesizing a data URL
    # when the provider returns only base64.
    try:
        output_format = str(data.get("output_format") or body.get("output_format") or "png").lower()
        mime = "image/png" if output_format in ("png", "") else f"image/{output_format}"
        items = data.get("data") or []
        if isinstance(items, list):
            maybe_materialize_image_items(request, items, fallback_mime=mime)
    except Exception as e:
        # Log but don't fail the request if materialization fails
        detail_log("image.materialize_error", request=request, error=str(e))
    
    litellm_cost = get_cost_from_headers(resp.headers)
    enforce_and_bump_quota(user["user_id"], add_image_requests=1)

    prices = load_prices()
    cost_usd = litellm_cost if litellm_cost > 0 else calc_image_cost_from_body(model, body, prices)
    if cost_usd > 0:
        enforce_and_bump_quota(user["user_id"], add_cost_usd=cost_usd)
    
    # Set usage state for audit
    image_count = body.get("n", 1)
    set_usage_state(request, 0, 0, 0, cost_usd)
    set_counters(request, image_count=image_count)
    
    # Store image-specific fields in request state for audit enhancement
    model_requested = body.get("model") or "gemini-2.5-flash-image"
    request.state.image_size = body.get("size", "1024x1024")
    request.state.image_format = body.get("response_format", "url")
    request.state.provider = _extract_provider(model)
    request.state.model_requested = model_requested if model_requested != model else None
    request.state.upstream_status = resp.status_code
    
    # Write detailed audit log for control-grade tracking (single source of truth)
    _write_image_audit(
        request_id=request_id,
        user_id=user["user_id"],
        model_requested=model_requested,
        model_effective=model,
        provider=_extract_provider(model),
        size=body.get("size", "1024x1024"),
        n=image_count,
        response_format=body.get("response_format", "url"),
        status_code=resp.status_code,
        cost_usd=cost_usd
    )
    
    # Mark audit as logged to prevent middleware from writing duplicate entry
    mark_audit_logged(request)

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    if cost_usd > 0:
        data["_mw_added_cost_usd"] = round(cost_usd, 6)
    return JSONResponse(status_code=200, content=data)
