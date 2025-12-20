"""
Admin endpoints for user management and usage reconciliation.
"""

from fastapi import Request, HTTPException

from config import ADMIN_KEY
from core.auth import load_users, save_users, get_lock
from core.quota import maybe_reset_quota
from core.cost import load_prices, calc_cost_usd
from services.litellm import find_usage_in_log


def get_usage(request: Request):
    """
    Admin endpoint to view user usage statistics.
    Scrubs sensitive data (subkey, subkey_hash) for security.
    """
    if request.headers.get("X-Admin-Key", "") != ADMIN_KEY:
        raise HTTPException(403, "Invalid admin key")
    
    users = load_users()
    # Scrub sensitive fields before returning
    scrubbed = []
    for user in users:
        safe_user = {k: v for k, v in user.items() if k not in ("subkey", "subkey_hash")}
        scrubbed.append(safe_user)
    return scrubbed


async def reset_quota(request: Request):
    """
    Admin endpoint to reset quota for specific user or all users.
    """
    if request.headers.get("X-Admin-Key", "") != ADMIN_KEY:
        raise HTTPException(403, "Invalid admin key")
    
    body = await request.json()
    target_user = body.get("user_id")
    lock = get_lock()
    with lock:
        users = load_users()
        for stored_user in users:
            if target_user is None or stored_user.get("user_id") == target_user:
                maybe_reset_quota(stored_user)
        save_users(users)
    return {"ok": True}


async def reconcile_usage(request: Request):
    """
    Admin endpoint to manually reconcile usage from LiteLLM logs.
    Searches LiteLLM log for request_id and updates user usage accordingly.
    """
    if request.headers.get("X-Admin-Key", "") != ADMIN_KEY:
        raise HTTPException(403, "Invalid admin key")

    body = await request.json()
    request_id = body.get("request_id")
    user_id = body.get("user_id")
    if not request_id or not user_id:
        raise HTTPException(400, "Missing request_id or user_id")

    usage = find_usage_in_log(request_id)
    if not usage:
        raise HTTPException(404, f"No usage found in LiteLLM log for request_id={request_id}")

    model = usage.get("model") or body.get("model") or ""
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    logged_cost = usage.get("response_cost")
    try:
        logged_cost_f = float(logged_cost) if logged_cost is not None else 0.0
    except Exception:
        logged_cost_f = 0.0
    
    prices = load_prices()
    cost_usd = logged_cost_f if logged_cost_f > 0 else calc_cost_usd(model, prompt_tokens, completion_tokens, prices)

    lock = get_lock()
    with lock:
        users = load_users()
        for stored_user in users:
            if stored_user.get("user_id") == user_id:
                maybe_reset_quota(stored_user)
                quota_info = stored_user.setdefault("quota", {})
                stored_user["used_tokens"] = int(stored_user.get("used_tokens", 0)) + total_tokens
                stored_user["used_cost_usd"] = float(stored_user.get("used_cost_usd", 0.0)) + cost_usd
                quota_info["used_tokens"] = int(quota_info.get("used_tokens", 0)) + total_tokens
                quota_info["used_cost_usd"] = float(quota_info.get("used_cost_usd", 0.0)) + cost_usd
                break
        else:
            raise HTTPException(404, f"user_id={user_id} not found")
        save_users(users)

    from core.cost import remove_pending
    remove_pending(request_id)

    return {
        "ok": True,
        "request_id": request_id,
        "user_id": user_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }
