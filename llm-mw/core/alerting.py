"""
Quota alert system — checks thresholds and sends email notifications.

After each request, check_and_send_alerts() compares current usage
against configured milestones (50/70/90/100%) and sends admin emails
via SMTP when a new milestone is reached.

Alert tracking is stored per-user in alerts_sent{} and reset
each quota period by maybe_reset_quota().
"""

import os
import json
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from config import DATA_DIR, logger
from core.auth import load_users, save_users, get_lock


# ─── File paths ───────────────────────────────────────────────

ALERT_CONFIG_FILE = os.path.join(DATA_DIR, "alert_config.json")
SYSTEM_ALERTS_FILE = os.path.join(DATA_DIR, "system_alerts.json")


# ─── Config helpers ───────────────────────────────────────────

def load_alert_config() -> dict:
    """Load alert configuration from data/alert_config.json."""
    if not os.path.exists(ALERT_CONFIG_FILE):
        return {"smtp": {"enabled": False}}
    with open(ALERT_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_alert_config(config: dict):
    """Save alert config back to file."""
    with open(ALERT_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_system_alerts() -> dict:
    """Load system-level alert tracking (budget milestones)."""
    if not os.path.exists(SYSTEM_ALERTS_FILE):
        return {}
    with open(SYSTEM_ALERTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_system_alerts(alerts: dict):
    """Save system alert tracking."""
    with open(SYSTEM_ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2, ensure_ascii=False)


# ─── Main alert check ────────────────────────────────────────

async def check_and_send_alerts(user_id: str, add_cost_usd: float = 0.0):
    """
    Check quota thresholds and send admin emails if new milestones reached.
    
    Runs ASYNC after quota bump — does NOT block user response.
    Two checks:
      1. Per-user quota vs their limit
      2. Total system spend vs monthly budget
    
    Args:
        user_id: The user who just made a request
        add_cost_usd: Cost of the request (for logging context)
    """
    try:
        config = load_alert_config()
        if not config.get("smtp", {}).get("enabled"):
            # SMTP disabled — only log threshold crossings
            _check_thresholds_log_only(user_id, config)
            return

        admin_alerts_cfg = config.get("admin_alerts", {})
        admin_emails = admin_alerts_cfg.get("emails", [])
        if not admin_emails:
            return

        lock = get_lock()
        with lock:
            users = load_users()

            # ═══════════════════════════════════════════
            # CHECK 1: Per-user quota thresholds
            # ═══════════════════════════════════════════
            per_user_cfg = admin_alerts_cfg.get("per_user_quota", {})
            if per_user_cfg.get("enabled"):
                user = next((u for u in users if u.get("user_id") == user_id), None)
                if user:
                    _check_per_user_alerts(config, user, admin_emails)

            # ═══════════════════════════════════════════
            # CHECK 2: Total system budget
            # ═══════════════════════════════════════════
            budget_cfg = admin_alerts_cfg.get("api_budget", {})
            if budget_cfg.get("enabled"):
                _check_system_budget_alerts(config, users, admin_emails)

            save_users(users)

    except Exception as e:
        logger.error("alert_check_failed user=%s: %s", user_id, str(e))
        # NEVER raise — alert failures must not block users


def _check_thresholds_log_only(user_id: str, config: dict):
    """Log threshold crossings without sending emails (SMTP disabled mode)."""
    try:
        users = load_users()
        user = next((u for u in users if u.get("user_id") == user_id), None)
        if not user:
            return

        quota = user.get("quota", {})
        limit = float(quota.get("limit_cost_usd", 0) or 0)
        used = float(quota.get("used_cost_usd", 0) or 0)

        if limit > 0:
            percent = (used / limit) * 100
            thresholds = config.get("admin_alerts", {}).get("per_user_quota", {}).get("thresholds", [50, 70, 90, 100])
            alerts_sent = user.setdefault("alerts_sent", {})

            for threshold in thresholds:
                milestone_key = f"cost_usd_{threshold}"
                if percent >= threshold and milestone_key not in alerts_sent:
                    logger.info(
                        "alert_threshold_crossed user=%s threshold=%d%% used=$%.2f limit=$%.2f (email disabled)",
                        user_id, threshold, used, limit
                    )
                    alerts_sent[milestone_key] = datetime.now(timezone.utc).isoformat()

            lock = get_lock()
            with lock:
                all_users = load_users()
                for u in all_users:
                    if u.get("user_id") == user_id:
                        u["alerts_sent"] = alerts_sent
                        break
                save_users(all_users)
    except Exception as e:
        logger.error("alert_log_only_failed user=%s: %s", user_id, str(e))


def _check_per_user_alerts(config: dict, user: dict, admin_emails: list):
    """Check per-user quota thresholds and send admin emails."""
    quota = user.get("quota", {})
    limit = float(quota.get("limit_cost_usd", 0) or 0)
    used = float(quota.get("used_cost_usd", 0) or 0)

    if limit <= 0:
        return  # No cost limit set — skip

    percent = (used / limit) * 100
    alerts_sent = user.setdefault("alerts_sent", {})
    thresholds = config["admin_alerts"]["per_user_quota"].get("thresholds", [50, 70, 90, 100])
    user_id = user.get("user_id", "unknown")

    for threshold in thresholds:
        milestone_key = f"cost_usd_{threshold}"

        if percent >= threshold and milestone_key not in alerts_sent:
            logger.info(
                "alert_sending user=%s threshold=%d%% used=$%.2f limit=$%.2f",
                user_id, threshold, used, limit
            )
            # Send email (async in thread)
            try:
                _send_admin_email_per_user(
                    config, user_id,
                    percent=percent, used=used, limit=limit,
                    threshold=threshold
                )
            except Exception as e:
                logger.error("alert_email_failed user=%s threshold=%d: %s", user_id, threshold, str(e))

            # Mark as sent regardless (prevent retry flooding)
            alerts_sent[milestone_key] = datetime.now(timezone.utc).isoformat()


def _check_system_budget_alerts(config: dict, users: list, admin_emails: list):
    """Check total system budget thresholds."""
    budget_cfg = config["admin_alerts"]["api_budget"]
    monthly_budget = float(budget_cfg.get("monthly_budget_usd", 0) or 0)

    if monthly_budget <= 0:
        return

    total_spend = sum(
        float(u.get("quota", {}).get("used_cost_usd", 0) or 0)
        for u in users
    )
    total_percent = (total_spend / monthly_budget) * 100

    system_alerts = load_system_alerts()
    thresholds = budget_cfg.get("thresholds", [50, 70, 90, 100])

    for threshold in thresholds:
        key = f"budget_{threshold}"
        if total_percent >= threshold and key not in system_alerts:
            logger.info(
                "alert_system_budget threshold=%d%% spend=$%.2f budget=$%.2f",
                threshold, total_spend, monthly_budget
            )
            try:
                _send_admin_email_system_budget(
                    config,
                    total_spend=total_spend,
                    budget=monthly_budget,
                    percent=total_percent,
                    threshold=threshold,
                    users=users
                )
            except Exception as e:
                logger.error("alert_budget_email_failed threshold=%d: %s", threshold, str(e))

            system_alerts[key] = datetime.now(timezone.utc).isoformat()

    save_system_alerts(system_alerts)


# ─── Email sending ────────────────────────────────────────────

LEVEL_MAP = {
    50: "ℹ️ INFO",
    70: "⚠️ WARNING",
    90: "🔴 CRITICAL",
    100: "🚨 EMERGENCY"
}


def _send_admin_email_per_user(config: dict, user_id: str, *,
                                percent: float, used: float, limit: float,
                                threshold: int):
    """Send per-user quota alert email to admins (blocking, run in thread)."""
    smtp_cfg = config["smtp"]
    admin_emails = config["admin_alerts"]["emails"]
    level = LEVEL_MAP.get(threshold, "INFO")

    subject = f"{level} — User {user_id} đạt {threshold}% quota"
    body = f"""\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{level} — Per-User Quota Alert
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User:       {user_id}
Quota:      ${used:.2f} / ${limit:.2f} ({percent:.0f}%)
Còn lại:    ${limit - used:.2f}
Mốc:        {threshold}%
Thời gian:  {datetime.now().strftime('%Y-%m-%d %H:%M')}

Quick Action:
• Tăng quota: PATCH /v1/_mw/admin/users/{user_id}
• Xem usage:  GET  /v1/_mw/summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    _smtp_send(smtp_cfg, admin_emails, subject, body)


def _send_admin_email_system_budget(config: dict, *,
                                     total_spend: float, budget: float,
                                     percent: float, threshold: int,
                                     users: list):
    """Send system budget alert with per-user breakdown."""
    smtp_cfg = config["smtp"]
    admin_emails = config["admin_alerts"]["emails"]
    level = LEVEL_MAP.get(threshold, "INFO")

    # Build user breakdown  
    breakdown_lines = []
    for u in sorted(users, key=lambda x: float(x.get("quota", {}).get("used_cost_usd", 0) or 0), reverse=True):
        uid = u.get("user_id", "?")
        u_cost = float(u.get("quota", {}).get("used_cost_usd", 0) or 0)
        if u_cost > 0:
            breakdown_lines.append(f"  • {uid}: ${u_cost:.2f}")

    breakdown = "\n".join(breakdown_lines) if breakdown_lines else "  (no usage)"

    subject = f"{level} — Tổng chi phí API đạt {threshold}% budget (${total_spend:.2f}/${budget:.2f})"
    body = f"""\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{level} — System Budget Alert
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Budget:     ${budget:.2f}/tháng
Đã dùng:    ${total_spend:.2f} ({percent:.0f}%)
Còn lại:    ${budget - total_spend:.2f}
Mốc:        {threshold}%
Thời gian:  {datetime.now().strftime('%Y-%m-%d %H:%M')}

Chi tiết theo user:
{breakdown}

Action:
• Dashboard: /dashboard
• Summary:   GET /v1/_mw/summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    _smtp_send(smtp_cfg, admin_emails, subject, body)


def _smtp_send(smtp_cfg: dict, to_emails: list, subject: str, body: str):
    """
    Send email via SMTP. This is BLOCKING I/O.
    Should be called from asyncio.to_thread() or directly in sync context.
    """
    password = os.environ.get(smtp_cfg.get("password_env", "SMTP_PASSWORD"), "")

    msg = MIMEMultipart()
    msg["From"] = smtp_cfg.get("from_email", "noreply@localhost")
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=10) as server:
            if smtp_cfg.get("use_tls"):
                server.starttls()
            if smtp_cfg.get("username") and password:
                server.login(smtp_cfg["username"], password)
            server.send_message(msg)
        logger.info("alert_email_sent to=%s subject=%s", to_emails, subject)
    except Exception as e:
        logger.error("alert_smtp_error: %s", str(e))
        raise


# ─── Quota status helper (for API endpoint) ──────────────────

def get_user_quota_status(user_id: str) -> dict:
    """
    Get quota usage status for a user.
    Used by /v1/_mw/quota-status endpoint (lightweight, no auth required).
    
    Returns:
        Dict with percent_used, remaining_usd, unlimited flag
    """
    from core.quota import maybe_reset_quota

    users = load_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)

    if not user:
        return {"found": False}

    maybe_reset_quota(user)
    quota = user.get("quota", {})
    limit = float(quota.get("limit_cost_usd", 0) or 0)
    used = float(quota.get("used_cost_usd", 0) or 0)

    if limit <= 0:
        return {
            "found": True,
            "user_id": user_id,
            "percent_used": 0,
            "remaining_usd": None,
            "unlimited": True,
            "alert_level": None
        }

    percent = round(used / limit * 100, 1)
    remaining = round(max(0, limit - used), 2)

    # Determine alert level
    alert_level = None
    if percent >= 95:
        alert_level = "critical"
    elif percent >= 80:
        alert_level = "warning"

    return {
        "found": True,
        "user_id": user_id,
        "percent_used": percent,
        "used_cost_usd": round(used, 4),
        "limit_cost_usd": round(limit, 2),
        "remaining_usd": remaining,
        "unlimited": False,
        "alert_level": alert_level
    }
