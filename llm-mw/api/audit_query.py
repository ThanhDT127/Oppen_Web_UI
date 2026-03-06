"""
Audit Log Query API - Full-text search with filters
Primary: queries mw_audit_log DB table. Fallback: reads audit.jsonl file.
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Query, Request
from config import AUDIT_LOG_FILE


def _db_available() -> bool:
    try:
        from core.db import _pool
        return _pool is not None
    except Exception:
        return False


def _query_db(
    limit, offset, user_id, model, status, endpoint,
    min_cost, max_cost, cutoff, end_time, sort_by, sort_order
):
    """Query mw_audit_log table with filters."""
    from core.db import db_conn

    conditions = ["ts >= %s", "ts <= %s"]
    params: list = [cutoff, end_time]

    if user_id:
        conditions.append("user_id = %s")
        params.append(user_id)
    if model:
        conditions.append("model ILIKE %s")
        params.append(f"%{model}%")
    if status:
        conditions.append("status = %s")
        params.append(status)
    if endpoint:
        conditions.append("endpoint ILIKE %s")
        params.append(f"%{endpoint}%")
    if min_cost is not None:
        conditions.append("cost_usd >= %s")
        params.append(min_cost)
    if max_cost is not None:
        conditions.append("cost_usd <= %s")
        params.append(max_cost)

    where_sql = " AND ".join(conditions)
    sort_col_map = {"timestamp": "ts", "cost": "cost_usd", "tokens": "tokens_total", "duration": "latency_ms"}
    sort_col = sort_col_map.get(sort_by, "ts")
    order = "DESC" if sort_order == "desc" else "ASC"

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT count(*) FROM mw_audit_log WHERE {where_sql}", params)
        total = cur.fetchone()[0]

        cur.execute(f"""
            SELECT ts, rid, user_id, endpoint, model, purpose, status,
                   status_code, latency_ms, tokens_in, tokens_out, tokens_total,
                   cost_usd, image_count, tts_chars, stt_seconds, video_count,
                   error_type, error_message
            FROM mw_audit_log WHERE {where_sql}
            ORDER BY {sort_col} {order}
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cur.fetchall()

        # Fetch DISTINCT users/models in time range (independent of filters)
        time_params = [cutoff, end_time]
        cur.execute("SELECT DISTINCT user_id FROM mw_audit_log WHERE ts >= %s AND ts <= %s AND user_id IS NOT NULL ORDER BY user_id", time_params)
        distinct_users = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT model FROM mw_audit_log WHERE ts >= %s AND ts <= %s AND model IS NOT NULL ORDER BY model", time_params)
        distinct_models = [r[0] for r in cur.fetchall()]
        # Fetch distinct statuses too
        cur.execute("SELECT DISTINCT status FROM mw_audit_log WHERE ts >= %s AND ts <= %s AND status IS NOT NULL ORDER BY status", time_params)
        distinct_statuses = [r[0] for r in cur.fetchall()]
        cur.close()

    results = []
    for r in rows:
        results.append({
            "ts": r[0].isoformat() if r[0] else None, "rid": r[1], "user_id": r[2],
            "endpoint": r[3], "model": r[4], "purpose": r[5], "status": r[6],
            "status_code": r[7], "latency_ms": r[8], "tokens_in": r[9],
            "tokens_out": r[10], "tokens_total": r[11], "cost_usd": r[12],
            "image_count": r[13], "tts_chars": r[14], "stt_seconds": r[15],
            "video_count": r[16], "error_type": r[17], "error_message": r[18],
        })
    return total, results, distinct_users, distinct_models, distinct_statuses


def _query_file(
    limit, offset, user_id, model, status, endpoint,
    min_cost, max_cost, cutoff, end_time, sort_by, sort_order
):
    """Fallback: read audit.jsonl file with filters."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return 0, []

    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    matching: List[Dict[str, Any]] = []

    try:
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts_str = rec.get("timestamp", rec.get("ts"))
                    if not ts_str:
                        continue
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=tz)
                    if ts < cutoff or ts > end_time:
                        continue
                    if user_id and rec.get("user_id") != user_id:
                        continue
                    if model and model.lower() not in rec.get("model", "").lower():
                        continue
                    if status and rec.get("status") != status:
                        continue
                    if endpoint and endpoint.lower() not in rec.get("endpoint", "").lower():
                        continue
                    cost = rec.get("cost_usd", 0)
                    if min_cost is not None and cost < min_cost:
                        continue
                    if max_cost is not None and cost > max_cost:
                        continue
                    rec["_ts_parsed"] = ts
                    matching.append(rec)
                except Exception:
                    continue
    except Exception:
        return 0, []

    reverse = (sort_order == "desc")
    key_map = {"timestamp": "_ts_parsed", "cost": "cost_usd", "tokens": "tokens_total", "duration": "duration_ms"}
    key = key_map.get(sort_by, "_ts_parsed")
    matching.sort(key=lambda r: r.get(key, 0) or 0, reverse=reverse)

    total = len(matching)
    page = matching[offset:offset + limit]
    for rec in page:
        rec.pop("_ts_parsed", None)

    # Collect distinct values from ALL matching records (not just page)
    all_users = sorted(set(r.get("user_id", "") for r in matching if r.get("user_id")))
    all_models = sorted(set(r.get("model", "") for r in matching if r.get("model")))
    all_statuses = sorted(set(r.get("status", "") for r in matching if r.get("status")))

    return total, page, all_users, all_models, all_statuses


def parse_audit_filters(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    endpoint: Optional[str] = Query(None),
    min_cost: Optional[float] = Query(None, ge=0),
    max_cost: Optional[float] = Query(None, ge=0),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    sort_by: str = Query("timestamp", pattern="^(timestamp|cost|tokens|duration)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
):
    """
    Query audit log with filters and pagination.
    Uses DB if available, falls back to audit.jsonl file.
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)

    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    if start:
        try:
            cutoff = datetime.fromisoformat(start.replace('Z', '+00:00'))
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=tz)
        except ValueError:
            cutoff = datetime.now(tz) - timedelta(hours=24)
    else:
        cutoff = datetime.now(tz) - timedelta(hours=24)

    if end:
        try:
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=tz)
        except ValueError:
            end_time = datetime.now(tz)
    else:
        end_time = datetime.now(tz)

    filters_info = {
        "user_id": user_id, "model": model, "status": status,
        "endpoint": endpoint, "min_cost": min_cost, "max_cost": max_cost,
        "time_range": {"start": cutoff.isoformat(), "end": end_time.isoformat()}
    }

    if _db_available():
        try:
            total, results, d_users, d_models, d_statuses = _query_db(
                limit, offset, user_id, model, status, endpoint,
                min_cost, max_cost, cutoff, end_time, sort_by, sort_order
            )
            return {"total": total, "limit": limit, "offset": offset,
                    "results": results, "source": "database",
                    "distinct_users": d_users, "distinct_models": d_models,
                    "distinct_statuses": d_statuses,
                    "filters_applied": filters_info}
        except Exception:
            pass

    total, results, d_users, d_models, d_statuses = _query_file(
        limit, offset, user_id, model, status, endpoint,
        min_cost, max_cost, cutoff, end_time, sort_by, sort_order
    )
    return {"total": total, "limit": limit, "offset": offset,
            "results": results, "source": "file",
            "distinct_users": d_users, "distinct_models": d_models,
            "distinct_statuses": d_statuses,
            "filters_applied": filters_info}
