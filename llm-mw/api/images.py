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
from core.audit_state import init_audit_state, set_usage_state, set_counters, set_error_state
from services.litellm import get_cost_from_headers
from utils.helpers import truncate_text, safe_headers
from utils.logging import detail_log
from utils.media import maybe_materialize_image_items


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
                raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")

    if resp.status_code >= 400:
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
        output_format = (data.get("output_format") or body.get("output_format") or "png").lower()
        mime = "image/png" if output_format in ("png", "") else f"image/{output_format}"
        items = data.get("data")
        maybe_materialize_image_items(request, items, fallback_mime=mime)
    except Exception:
        pass
    
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

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    if cost_usd > 0:
        data["_mw_added_cost_usd"] = round(cost_usd, 6)
    return JSONResponse(status_code=200, content=data)
