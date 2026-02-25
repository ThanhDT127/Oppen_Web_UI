"""
Quota management and enforcement for user limits.
"""

import datetime as dt
from typing import Dict, Any
from zoneinfo import ZoneInfo
from fastapi import HTTPException

from core.auth import load_users, save_users, get_lock


def period_anchor_ms(period: str, tz: str) -> int:
    """
    Calculate period start timestamp in milliseconds.
    
    Args:
        period: "weekly" or "monthly"
        tz: Timezone name (e.g., "Asia/Ho_Chi_Minh")
        
    Returns:
        Timestamp in milliseconds
    """
    zone = ZoneInfo(tz) if tz else ZoneInfo("UTC")
    now = dt.datetime.now(zone)
    if period == "weekly":
        start = now - dt.timedelta(days=now.weekday())
        start = dt.datetime(start.year, start.month, start.day, tzinfo=zone)
    else:
        start = dt.datetime(now.year, now.month, 1, tzinfo=zone)
    return int(start.timestamp() * 1000)


def maybe_reset_quota(user: Dict[str, Any]):
    """
    Reset period-based quota tracking when period boundary crossed.
    IMPORTANT: Only resets quota["used_*"], NOT user["used_*"] (lifetime data).
    
    Args:
        user: User dictionary (modified in-place)
    """
    quota = user.setdefault("quota", {})
    period = quota.get("period", "monthly")
    tz = quota.get("timezone", "UTC")
    current_anchor = period_anchor_ms(period, tz)
    if int(quota.get("period_start", 0)) < current_anchor:
        quota["period_start"] = current_anchor
        # Reset period metrics only
        quota["used_tokens"] = 0
        quota["used_cost_usd"] = 0.0
        quota["used_image_requests"] = 0
        # Reset alert tracking for the new period
        user["alerts_sent"] = {}
        # DO NOT reset user["used_*"] - those are lifetime counters


def enforce_and_bump_quota(
    user_id: str,
    *,
    apply: bool = True,
    add_image_requests: int = 0,
    add_stt_requests: int = 0,
    add_tokens: int = 0,
    add_cost_usd: float = 0.0,
):
    """
    Enforce quota limits and update usage counters.
    
    Args:
        user_id: User identifier
        apply: Whether to actually increment counters
        add_image_requests: Image requests to add
        add_stt_requests: Speech-to-text requests to add
        add_tokens: Tokens to add
        add_cost_usd: Cost to add
        
    Raises:
        HTTPException: 403 if quota exceeded, 404 if user not found
    """
    lock = get_lock()
    with lock:
        users = load_users()
        for stored_user in users:
            if stored_user.get("user_id") != user_id:
                continue

            maybe_reset_quota(stored_user)
            quota = stored_user.setdefault("quota", {})

            def _enforce_limit(limit_key: str, used_key: str, add_value: float, label: str):
                """Check if adding value would exceed limit"""
                limit_val = float(quota.get(limit_key, 0) or 0)
                if limit_val <= 0:
                    return
                used_val = float(quota.get(used_key, 0) or 0)
                if used_val + add_value > limit_val + 1e-9:
                    raise HTTPException(
                        403,
                        f"{label} quota exceeded for {stored_user['user_id']} ({used_val + add_value}/{limit_val})",
                    )

            # Enforce task-specific quotas (best-effort; costs may be unknown until after provider call).
            if add_image_requests:
                _enforce_limit("limit_image_requests", "used_image_requests", float(add_image_requests), "Image requests")
            if add_stt_requests:
                _enforce_limit("limit_stt_requests", "used_stt_requests", float(add_stt_requests), "STT requests")

            # Existing token/cost quotas.
            if add_tokens:
                _enforce_limit("limit_tokens", "used_tokens", float(add_tokens), "Token")
            if add_cost_usd:
                _enforce_limit("limit_cost_usd", "used_cost_usd", float(add_cost_usd), "Cost USD")

            if not apply:
                return

            # Apply increments.
            if add_image_requests:
                quota["used_image_requests"] = int(quota.get("used_image_requests", 0) or 0) + int(add_image_requests)
            if add_stt_requests:
                quota["used_stt_requests"] = int(quota.get("used_stt_requests", 0) or 0) + int(add_stt_requests)

            if add_tokens:
                stored_user["used_tokens"] = int(stored_user.get("used_tokens", 0) or 0) + int(add_tokens)
                quota["used_tokens"] = int(quota.get("used_tokens", 0) or 0) + int(add_tokens)
            if add_cost_usd:
                stored_user["used_cost_usd"] = float(stored_user.get("used_cost_usd", 0.0) or 0.0) + float(add_cost_usd)
                quota["used_cost_usd"] = float(quota.get("used_cost_usd", 0.0) or 0.0) + float(add_cost_usd)

            save_users(users)
            return

        raise HTTPException(404, f"user_id={user_id} not found")
