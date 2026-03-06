"""
Summary endpoint for aggregated usage statistics.
Primary: queries mw_audit_log DB table. Fallback: reads audit.jsonl file.
"""

import os
import json
import datetime as dt
from typing import Dict, Any
from zoneinfo import ZoneInfo
from fastapi import Request, HTTPException

from config import ADMIN_KEY, AUDIT_LOG_FILE


def _db_available() -> bool:
    try:
        from core.db import _pool
        return _pool is not None
    except Exception:
        return False


def _summary_from_db(cutoff):
    """Aggregate usage statistics from mw_audit_log table."""
    from core.db import db_conn

    LLM_ENDPOINTS = {
        "/v1/chat/completions": "chat",
        "/v1/images/generations": "image",
        "/v1/audio/transcriptions": "audio",
        "/v1/audio/speech": "audio",
        "/v1/video/generations": "video",
    }

    with db_conn() as conn:
        cur = conn.cursor()

        # Overall counts
        cur.execute("""
            SELECT
                count(*) FILTER (WHERE status IN ('ok','error','reconciled')) as requests_total,
                count(*) FILTER (WHERE status = 'error') as error_count,
                count(*) FILTER (WHERE status = 'pending') as pending_count,
                coalesce(sum(tokens_total) FILTER (WHERE status IN ('ok','reconciled')), 0) as tokens_total,
                coalesce(sum(cost_usd) FILTER (WHERE status IN ('ok','reconciled')), 0) as cost_total,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
                    FILTER (WHERE status != 'pending' AND latency_ms > 0) as p95_latency
            FROM mw_audit_log WHERE ts >= %s
        """, (cutoff,))
        row = cur.fetchone()
        requests_total = row[0] or 0
        error_count = row[1] or 0
        pending_count = row[2] or 0
        tokens_total = row[3] or 0
        cost_total = float(row[4] or 0)
        p95_latency = float(row[5]) if row[5] else None

        # Breakdown by endpoint type
        cur.execute("""
            SELECT endpoint,
                   count(*) FILTER (WHERE status IN ('ok','error','reconciled'))
            FROM mw_audit_log WHERE ts >= %s
            GROUP BY endpoint
        """, (cutoff,))
        chat_calls = image_calls = audio_calls = video_calls = 0
        admin_ops_total = 0
        llm_calls_total = 0
        for ep, cnt in cur.fetchall():
            if ep in LLM_ENDPOINTS:
                llm_calls_total += cnt
                t = LLM_ENDPOINTS[ep]
                if t == "chat": chat_calls += cnt
                elif t == "image": image_calls += cnt
                elif t == "audio": audio_calls += cnt
                elif t == "video": video_calls += cnt
            elif ep in ("/admin/reconcile", "/admin/usage", "/admin/reset"):
                admin_ops_total += cnt

        # Top users by cost
        cur.execute("""
            SELECT user_id, sum(cost_usd) as total_cost
            FROM mw_audit_log WHERE ts >= %s AND status IN ('ok','reconciled')
            GROUP BY user_id ORDER BY total_cost DESC LIMIT 10
        """, (cutoff,))
        top_users = [{"user_id": uid, "cost_usd": round(c, 6)} for uid, c in cur.fetchall()]

        # Top models by cost
        cur.execute("""
            SELECT model, sum(cost_usd) as total_cost
            FROM mw_audit_log WHERE ts >= %s AND status IN ('ok','reconciled')
            GROUP BY model ORDER BY total_cost DESC LIMIT 10
        """, (cutoff,))
        top_models = [{"model": m, "cost_usd": round(c, 6)} for m, c in cur.fetchall()]

        # Pending open count (latest status per rid)
        cur.execute("""
            SELECT count(*) FROM (
                SELECT DISTINCT ON (rid) status FROM mw_audit_log
                WHERE ts >= %s AND rid IS NOT NULL
                ORDER BY rid, ts DESC
            ) sub WHERE status = 'pending'
        """, (cutoff,))
        pending_open = cur.fetchone()[0] or 0

        cur.close()

    error_rate = (error_count / requests_total * 100) if requests_total > 0 else 0.0

    return {
        "requests_total": requests_total,
        "llm_calls_total": llm_calls_total,
        "admin_ops_total": admin_ops_total,
        "pending_open_count": pending_open,
        "error_count": error_count,
        "error_rate_percent": round(error_rate, 2),
        "chat_calls": chat_calls,
        "image_calls": image_calls,
        "audio_calls": audio_calls,
        "video_calls": video_calls,
        "p95_latency_ms": round(p95_latency, 2) if p95_latency else None,
        "tokens_total": tokens_total,
        "cost_total_usd": round(cost_total, 6),
        "top_users": top_users,
        "top_models": top_models,
        "source": "database",
    }


def _summary_from_file(cutoff):
    """Fallback: aggregate from audit.jsonl file."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return {"error": "audit.jsonl not found", "data": []}

    LLM_ENDPOINTS = {
        "/v1/chat/completions": "chat",
        "/v1/images/generations": "image",
        "/v1/audio/transcriptions": "audio",
        "/v1/audio/speech": "audio",
        "/v1/video/generations": "video",
    }

    requests_total = llm_calls_total = admin_ops_total = error_count = 0
    chat_calls = image_calls = audio_calls = video_calls = 0
    latencies = []
    tokens_total = 0
    cost_total = 0.0
    user_costs: Dict[str, float] = {}
    model_costs: Dict[str, float] = {}
    rid_status: Dict[str, tuple] = {}

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    ts_str = entry.get("ts", "")
                    if not ts_str:
                        continue
                    entry_time = dt.datetime.fromisoformat(ts_str)
                    if entry_time < cutoff:
                        continue

                    endpoint = entry.get("endpoint", "")
                    status = entry.get("status", "ok")
                    rid = entry.get("rid", "")

                    if rid:
                        current_ts = entry_time.timestamp()
                        if rid not in rid_status or current_ts > rid_status[rid][0]:
                            rid_status[rid] = (current_ts, status)

                    is_llm = endpoint in LLM_ENDPOINTS
                    if is_llm and status in ("ok", "error", "reconciled"):
                        llm_calls_total += 1
                        t = LLM_ENDPOINTS[endpoint]
                        if t == "chat": chat_calls += 1
                        elif t == "image": image_calls += 1
                        elif t == "audio": audio_calls += 1
                        elif t == "video": video_calls += 1

                    if endpoint in ("/admin/reconcile", "/admin/usage", "/admin/reset"):
                        admin_ops_total += 1

                    if status in ("ok", "error", "reconciled"):
                        requests_total += 1
                    if status == "error":
                        error_count += 1

                    if status != "pending":
                        lat = entry.get("latency_ms")
                        if lat and lat > 0:
                            latencies.append(lat)

                    if status in ("ok", "reconciled"):
                        tokens_total += entry.get("tokens_total", 0)
                        cost = entry.get("cost_usd", 0.0)
                        cost_total += cost
                        uid = entry.get("user_id", "unknown")
                        user_costs[uid] = user_costs.get(uid, 0.0) + cost
                        m = entry.get("model", "unknown")
                        model_costs[m] = model_costs.get(m, 0.0) + cost

                except Exception:
                    continue

        pending_open = sum(1 for _, (_, s) in rid_status.items() if s == "pending")
        p95 = None
        if latencies:
            latencies.sort()
            idx = int(len(latencies) * 0.95)
            p95 = latencies[min(idx, len(latencies) - 1)]

        error_rate = (error_count / requests_total * 100) if requests_total > 0 else 0.0

        top_users = sorted(user_costs.items(), key=lambda x: x[1], reverse=True)[:10]
        top_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "requests_total": requests_total,
            "llm_calls_total": llm_calls_total,
            "admin_ops_total": admin_ops_total,
            "pending_open_count": pending_open,
            "error_count": error_count,
            "error_rate_percent": round(error_rate, 2),
            "chat_calls": chat_calls,
            "image_calls": image_calls,
            "audio_calls": audio_calls,
            "video_calls": video_calls,
            "p95_latency_ms": round(p95, 2) if p95 else None,
            "tokens_total": tokens_total,
            "cost_total_usd": round(cost_total, 6),
            "top_users": [{"user_id": u, "cost_usd": round(c, 6)} for u, c in top_users],
            "top_models": [{"model": m, "cost_usd": round(c, 6)} for m, c in top_models],
            "source": "file",
        }
    except Exception as e:
        return {"error": str(e)}


def get_summary(request: Request, minutes: int = 60):
    """
    Admin endpoint: Aggregate usage statistics.
    Uses DB if available, falls back to audit.jsonl.
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)

    cutoff = dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(minutes=minutes)

    if _db_available():
        try:
            result = _summary_from_db(cutoff)
            result["time_window_minutes"] = minutes
            result["cutoff_time"] = cutoff.isoformat()
            return result
        except Exception:
            pass

    result = _summary_from_file(cutoff)
    result["time_window_minutes"] = minutes
    result["cutoff_time"] = cutoff.isoformat()
    return result
