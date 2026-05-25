"""
Image generation endpoint with fallback support.
"""

import uuid
import json
import base64
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
import time


# Model name → LiteLLM model mapping for image generation
_IMAGE_MODEL_MAP = {
    # Gemini image models
    "img-gemini-flash": "gemini/gemini-2.5-flash-image",
    "img-gemini-pro": "gemini/gemini-3-pro-image-preview",
    "img-gemini-3.1-flash": "gemini/gemini-3.1-flash-image-preview",
    "img-gemini-3-pro": "gemini/gemini-3-pro-image-preview",
    # OpenAI GPT Image models
    "img-gpt-1.5": "openai/gpt-image-1.5",
    "img-gpt-1": "openai/gpt-image-1",
    "img-gpt-1-mini": "openai/gpt-image-1-mini",
    # OpenAI DALL-E models
    "img-gpt-dalle-3": "openai/dall-e-3",
    # xAI Grok Imagine models
    "img-grok-imagine": "xai/grok-imagine-image",
    "img-grok-imagine-pro": "xai/grok-imagine-image-pro",
}


async def _generate_image_via_chat(client: httpx.AsyncClient, headers: dict, messages, model: str) -> dict:
    """
    Generate image using ANY image model via LiteLLM chat/completions endpoint.
    
    All image models (Gemini, GPT Image, DALL-E) support chat/completions,
    enabling full conversation context, image editing, and multi-turn generation.
    
    Accepts full conversation messages for context-aware image generation/editing.
    Response format: choices[0].message.content contains image data as:
    - Array with image_url parts: [{"type": "image_url", "image_url": {"url": "data:..."}}]
    - Or direct base64/URL strings
    
    This function converts that to OpenAI images/generations format.
    
    Args:
        client: HTTP client
        headers: Auth headers
        messages: Full conversation messages (list) or single prompt (str for backward compat)
        model: Middleware model name (e.g., "img-gemini-flash", "img-gpt-1.5")
    """
    # Map middleware model name to LiteLLM model
    litellm_model = _IMAGE_MODEL_MAP.get(model)
    if not litellm_model:
        # Fallback: try to use the model name directly
        litellm_model = model
    
    # Handle backward compatibility: string prompt → wrap in message
    if isinstance(messages, str):
        chat_messages = [{"role": "user", "content": f"Generate an image: {messages}"}]
    elif isinstance(messages, list) and len(messages) > 0:
        chat_messages = messages
    else:
        chat_messages = [{"role": "user", "content": "Generate an image"}]
    
    chat_body = {
        "model": litellm_model,
        "messages": chat_messages,
        "max_tokens": 4096,
        "stream": False  # MUST disable streaming for image generation
    }
    
    resp = await client.post(
        f"{LITELLM_BASE}/chat/completions",
        headers=headers,
        json=chat_body,
        timeout=120
    )
    
    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise HTTPException(resp.status_code, err)
    
    chat_data = resp.json()
    
    # Extract images from LiteLLM response
    # Format: choices[0].message.content = [{"type": "image_url", "image_url": {"url": "data:..."}}]
    images = []
    if "choices" in chat_data and len(chat_data["choices"]) > 0:
        message = chat_data["choices"][0].get("message", {})
        content = message.get("content", "")
        
        # LiteLLM v1.81.8: content is an array with text and image_url parts
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    img_url_obj = part.get("image_url", {})
                    url = img_url_obj.get("url", "")
                    if url:
                        # Extract base64 from data URL if present
                        b64 = None
                        if url.startswith("data:"):
                            try:
                                b64 = url.split(",", 1)[1]
                            except (IndexError, ValueError):
                                pass
                        images.append({"url": url, "b64_json": b64})
        
        # Content is a string with a URL (some OpenAI responses)
        elif isinstance(content, str) and (content.startswith("http") or content.startswith("data:")):
            b64 = None
            if content.startswith("data:"):
                try:
                    b64 = content.split(",", 1)[1]
                except (IndexError, ValueError):
                    pass
            images.append({"url": content, "b64_json": b64})
        
        # Also check message.images (older LiteLLM versions)
        if not images and "images" in message:
            msg_images = message["images"]
            if isinstance(msg_images, list):
                for img in msg_images:
                    if isinstance(img, dict):
                        url = img.get("image_url", {}).get("url", "") or img.get("url", "")
                        if url:
                            images.append({"url": url})
                    elif isinstance(img, str):
                        if img.startswith("data:"):
                            images.append({"url": img})
                        else:
                            images.append({"url": f"data:image/png;base64,{img}", "b64_json": img})
    
    if not images:
        return {
            "created": int(time.time()),
            "data": [],
            "_debug": "No images found in model response",
            "_raw_keys": list(chat_data.get("choices", [{}])[0].get("message", {}).keys()) if chat_data.get("choices") else []
        }
    
    return {
        "created": int(time.time()),
        "data": images
    }


# Backward compatibility alias
_generate_via_gemini_chat = _generate_image_via_chat


async def _generate_via_gpt_image_edit(
    client: httpx.AsyncClient,
    headers: dict,
    image_urls: list[str],
    prompt: str,
    model: str,
    size: str = "1024x1024",
) -> dict:
    """
    Edit/modify an existing image using GPT Image models via /images/edits.
    
    This is used when the user uploads an image and asks to modify it.
    GPT Image models (gpt-image-1, gpt-image-1.5, gpt-image-1-mini) support
    receiving images via the /images/edits endpoint for inpainting and editing.
    
    Images are sent as base64-encoded files via multipart/form-data.
    
    Args:
        client: HTTP client
        headers: Auth headers (will extract Authorization only)
        image_urls: List of image URLs (data:image/...;base64,... or http URLs)
        prompt: Text description of the desired edit
        model: Middleware model name
        size: Output image size
    """
    litellm_model = _IMAGE_MODEL_MAP.get(model, model)
    
    # Build multipart form data
    # Authorization header only (Content-Type will be set by httpx for multipart)
    edit_headers = {
        "Authorization": headers.get("Authorization", f"Bearer {LITELLM_KEY}"),
    }
    if "X-Request-ID" in headers:
        edit_headers["X-Request-ID"] = headers["X-Request-ID"]
    
    # Prepare image files from URLs/base64
    files = []
    for i, url in enumerate(image_urls[:4]):  # Max 4 images to avoid huge requests
        if url.startswith("data:"):
            # Extract base64 data from data URI: data:image/png;base64,....
            try:
                header_part, b64_data = url.split(",", 1)
                # Determine file extension from MIME type
                mime = header_part.split(":")[1].split(";")[0]  # e.g., "image/png"
                ext = mime.split("/")[1] if "/" in mime else "png"
                if ext == "jpeg":
                    ext = "jpg"
                img_bytes = base64.b64decode(b64_data)
                files.append(("image", (f"image_{i}.{ext}", img_bytes, mime)))
            except Exception:
                continue
        elif url.startswith("http"):
            # Download the image first
            try:
                img_resp = await client.get(url, timeout=30)
                if img_resp.status_code == 200:
                    content_type = img_resp.headers.get("content-type", "image/png")
                    ext = content_type.split("/")[1] if "/" in content_type else "png"
                    if ext == "jpeg":
                        ext = "jpg"
                    files.append(("image", (f"image_{i}.{ext}", img_resp.content, content_type)))
            except Exception:
                continue
    
    if not files:
        # No valid images extracted, fall back to generation
        return None
    
    # Form data fields
    data = {
        "model": litellm_model,
        "prompt": prompt,
        "n": "1",
        "size": size,
    }
    
    resp = await client.post(
        f"{LITELLM_BASE}/images/edits",
        headers=edit_headers,
        data=data,
        files=files,
        timeout=120,
    )
    
    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise HTTPException(resp.status_code, err)
    
    return resp.json()


def _extract_provider(model: str) -> str:
    """
    Extract provider from model name.
    
    Args:
        model: Model name (e.g., "img-gemini-flash", "img-gpt-dalle-3", "img-grok-imagine")
        
    Returns:
        Provider name ("gemini", "openai", "xai", "unknown")
    """
    model_lower = (model or "").lower()
    if "gemini" in model_lower:
        return "gemini"
    elif "grok" in model_lower or "xai" in model_lower:
        return "xai"
    elif "dalle" in model_lower or "gpt" in model_lower:
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
    model = body.get("model") or "img-gemini-flash"
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
    if isinstance(model, str) and model == "img-gpt-dalle-3":
        forward_body.pop("response_format", None)
    # Gemini image models reject the OpenAI `user` parameter.
    if isinstance(model, str) and "gemini" in model.lower():
        forward_body.pop("user", None)
        forward_body.pop("metadata", None)

    def _looks_like_org_verification_error(text: str) -> bool:
        t = (text or "").lower()
        return "organization must be verified" in t or "verify organization" in t

    def _is_xai_provider(m: str) -> bool:
        ml = (m or "").lower()
        return "grok" in ml or "xai" in ml

    client: httpx.AsyncClient = request.app.state.http_client
    
    # Route based on provider - Gemini uses chat/completions, others use images/generations
    provider = _extract_provider(model)
    
    try:
        if provider == "gemini":
            # Gemini image gen must go through chat/completions
            detail_log(
                "upstream.request.gemini",
                request=request,
                rid=request_id,
                user_id=user.get("user_id"),
                upstream=f"{LITELLM_BASE}/chat/completions",
                method="POST",
                model=model,
                prompt=truncate_text(body.get("prompt"), limit=200),
            )
            data = await _generate_via_gemini_chat(client, headers, body.get("prompt", ""), model)
            resp = None  # No direct response object for Gemini path
        else:
            # OpenAI DALL-E / xAI Grok uses standard images/generations endpoint
            # xAI Grok Imagine does NOT support 'size' param
            if _is_xai_provider(model):
                forward_body.pop("size", None)
            
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
            
            if resp.status_code >= 400 and isinstance(model, str) and model == "img-gpt-dalle-3":
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
                    # Fall back to Gemini
                    fallback_model = "img-gemini-flash"
                    assert_model_allowed(user, fallback_model)
                    model = fallback_model
                    detail_log("upstream.fallback", request=request, rid=request_id, from_model="img-gpt-dalle-3", to_model=fallback_model)
                    data = await _generate_via_gemini_chat(client, headers, body.get("prompt", ""), fallback_model)
                    resp = None
                else:
                    # Not a fallback case, propagate error
                    set_error_state(request, "provider", f"LiteLLM returned {resp.status_code}")
                    raise HTTPException(resp.status_code, resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text)
            elif resp.status_code >= 400:
                set_error_state(request, "provider", f"LiteLLM returned {resp.status_code}")
                try:
                    raise HTTPException(resp.status_code, resp.json())
                except Exception:
                    raise HTTPException(resp.status_code, resp.text)
            else:
                data = resp.json()
                
    except httpx.RequestError as e:
        detail_log(
            "upstream.error",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            upstream=f"{LITELLM_BASE}",
            error=f"{e.__class__.__name__}",
        )
        set_error_state(request, "provider", f"Upstream LiteLLM unavailable: {e.__class__.__name__}")
        raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")

    detail_log(
        "upstream.response",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        status=resp.status_code if resp else 200,
        headers=dict(resp.headers) if resp else {},
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
    
    litellm_cost = get_cost_from_headers(resp.headers) if resp else 0

    prices = load_prices()
    cost_usd = litellm_cost if litellm_cost > 0 else calc_image_cost_from_body(model, body, prices)

    # Single call to bump both image_requests and cost_usd — reduces lock contention 3x → 1x
    enforce_and_bump_quota(user["user_id"], add_image_requests=1, add_cost_usd=cost_usd)
    
    # Set usage state for audit
    image_count = body.get("n", 1)
    set_usage_state(request, 0, 0, 0, cost_usd)
    set_counters(request, image_count=image_count)
    
    # Store image-specific fields in request state for audit enhancement
    model_requested = body.get("model") or "img-gemini-flash"
    request.state.image_size = body.get("size", "1024x1024")
    request.state.image_format = body.get("response_format", "url")
    request.state.provider = _extract_provider(model)
    request.state.model_requested = model_requested if model_requested != model else None
    request.state.upstream_status = resp.status_code if resp else 200
    
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
        status_code=resp.status_code if resp else 200,
        cost_usd=cost_usd
    )
    
    # Mark audit as logged to prevent middleware from writing duplicate entry
    mark_audit_logged(request)

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    if cost_usd > 0:
        data["_mw_added_cost_usd"] = round(cost_usd, 6)
    return JSONResponse(status_code=200, content=data)
