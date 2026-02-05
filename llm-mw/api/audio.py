"""
Audio transcription endpoint for speech-to-text.
"""

import uuid
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import httpx

from config import LITELLM_BASE, LITELLM_KEY
from core.auth import require_user, assert_model_allowed
from core.quota import enforce_and_bump_quota
from core.audit_state import init_audit_state, set_usage_state, set_counters, set_error_state
from services.litellm import get_cost_from_headers


async def transcribe_audio(request: Request):
    """
    Transcribe audio via LiteLLM with quota enforcement.
    """
    user = require_user(request)
    form = await request.form()

    file_obj = form.get("file")
    if not file_obj:
        raise HTTPException(400, "Missing 'file' in multipart form")

    model = form.get("model") or "gpt-4o-mini-transcribe"
    assert_model_allowed(user, str(model))
    
    # Initialize audit state
    rid = init_audit_state(request, user["user_id"], "/v1/audio/transcriptions", model)

    # Enforce request quotas before provider call (do not charge unless call succeeds).
    enforce_and_bump_quota(user["user_id"], apply=False, add_stt_requests=1)

    # Use rid from audit_state (already generated)
    request_id = rid

    # Build multipart
    filename = getattr(file_obj, "filename", "audio")
    content_type = getattr(file_obj, "content_type", None) or "application/octet-stream"
    file_bytes = await file_obj.read()
    files = {"file": (filename, file_bytes, content_type)}

    data = {}
    for key in form.keys():
        if key == "file":
            continue
        val = form.get(key)
        if val is None:
            continue
        data[key] = str(val)

    # Attach OpenAI-compatible user + metadata in a best-effort way.
    data.setdefault("user", user["user_id"])
    # 'metadata' isn't standard on this endpoint, but LiteLLM may accept it.
    if "metadata" not in data:
        data["metadata"] = json.dumps({"mw_request_id": request_id})

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "X-Request-ID": request_id,
    }

    client: httpx.AsyncClient = request.app.state.http_client
    resp = await client.post(f"{LITELLM_BASE}/audio/transcriptions", headers=headers, data=data, files=files, timeout=600)
    if resp.status_code >= 400:
        set_error_state(request, "provider", f"LiteLLM returned {resp.status_code}")
        raise HTTPException(resp.status_code, resp.text)
    out = resp.json()
    litellm_cost = get_cost_from_headers(resp.headers)

    enforce_and_bump_quota(user["user_id"], add_stt_requests=1)

    # STT fallback (minutes) is hard to compute from raw audio here; only charge cost if LiteLLM provides it.
    if litellm_cost > 0:
        enforce_and_bump_quota(user["user_id"], add_cost_usd=litellm_cost)
    
    # Set usage state for audit (approximate duration from file size if possible)
    # For now, just set cost and stt_requests counter
    set_usage_state(request, 0, 0, 0, litellm_cost if litellm_cost > 0 else 0.0)
    set_counters(request, stt_seconds=None)  # TODO: Calculate from audio file duration

    out["_mw_user"] = user["user_id"]
    out["_mw_request_id"] = request_id
    if litellm_cost > 0:
        out["_mw_added_cost_usd"] = round(litellm_cost, 6)
    return JSONResponse(status_code=200, content=out)
