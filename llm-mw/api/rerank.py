"""
Rerank endpoint - Proxy with auth, quota, and cost tracking.
Routes reranking requests through middleware to LiteLLM for monitoring via dashboard.
"""

import uuid
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import httpx

from config import LITELLM_BASE, LITELLM_KEY, logger
from core.auth import require_user, update_user_quota
from core.quota import maybe_reset_quota
from core.cost import load_prices
from core.audit_state import init_audit_state, set_usage_state, set_error_state
from services.litellm import get_cost_from_headers
from utils.logging import write_audit_line


# Default rerank cost fallback: $2.0 / 1M tokens (if not in prices.json)
RERANK_COST_PER_1M = 2.0


def _calc_rerank_cost(model: str, total_tokens: int, prices: dict) -> float:
    """
    Calculate rerank cost.
    Uses prices.json if available, otherwise falls back to default rate.
    """
    price = prices.get(model, {})
    
    # Support input_per_1m format
    if "input_per_1m" in price:
        rate = float(price.get("input_per_1m", 0.0) or 0.0)
        return (total_tokens / 1_000_000.0) * rate
    
    # Default: $2/1M tokens
    return (total_tokens / 1_000_000.0) * RERANK_COST_PER_1M


async def rerank(request: Request):
    """
    POST /v1/rerank
    Proxies rerank requests to LiteLLM with auth, quota enforcement, and cost tracking.
    """
    # ── Auth ──
    user = require_user(request)
    user_id = user["user_id"]
    
    # ── Quota reset check ──
    maybe_reset_quota(user)
    
    # ── Parse body ──
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")
    
    model = body.get("model", "unknown")
    rid = f"rrk-{uuid.uuid4().hex[:12]}"
    request.state.mw_request_id = rid
    
    # ── Init audit state ──
    init_audit_state(request, user_id=user_id, model=model, endpoint="/v1/rerank")
    
    logger.info(
        "rerank_request rid=%s user=%s model=%s",
        rid, user_id, model
    )
    
    # ── Forward to LiteLLM ──
    # LiteLLM handles /rerank endpoint which is Cohere-compatible
    url = f"{LITELLM_BASE}/rerank"
    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": rid,
    }
    
    try:
        client: httpx.AsyncClient = request.app.state.http_client
        resp = await client.post(url, json=body, headers=headers, timeout=60.0)
    except httpx.TimeoutException:
        set_error_state(request, "timeout", "LiteLLM rerank timeout")
        raise HTTPException(504, "Rerank request timeout")
    except Exception as e:
        set_error_state(request, "connection", str(e))
        raise HTTPException(502, f"LiteLLM connection error: {e}")
    
    if resp.status_code != 200:
        error_text = resp.text[:500]
        logger.warning(
            "rerank_error rid=%s status=%s error=%s",
            rid, resp.status_code, error_text
        )
        set_error_state(request, "upstream", error_text)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    
    # ── Parse response ──
    result = resp.json()
    
    # LiteLLM usage in rerank response might differ or be in headers
    usage = result.get("meta", {}).get("billed_units", {})
    # For rerank, sometimes tokens are used, sometimes units (documents * search)
    # We'll use billed_units if available, or estimate
    total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    if total_tokens == 0:
        # Fallback: estimate based on documents
        num_docs = len(body.get("documents", []))
        total_tokens = num_docs * 100 # Rough estimate
    
    # ── Cost calculation ──
    cost_usd = get_cost_from_headers(resp.headers)
    if cost_usd <= 0:
        prices = load_prices()
        cost_usd = _calc_rerank_cost(model, total_tokens, prices)
    
    # ── Update user quota ──
    update_user_quota(
        user_id,
        add_tokens=total_tokens,
        add_cost_usd=cost_usd,
    )
    
    # ── Audit ──
    set_usage_state(
        request,
        tokens_in=total_tokens,
        tokens_out=0,
        tokens_total=total_tokens,
        cost_usd=cost_usd,
    )
    
    write_audit_line({
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user_id,
        "model": model,
        "endpoint": "rerank",
        "rid": rid,
        "prompt_tokens": total_tokens,
        "completion_tokens": 0,
        "cost_usd": cost_usd,
        "status": "ok",
    })
    
    logger.info(
        "rerank_done rid=%s user=%s model=%s tokens=%d cost=%.6f",
        rid, user_id, model, total_tokens, cost_usd
    )
    
    return JSONResponse(content=result)
