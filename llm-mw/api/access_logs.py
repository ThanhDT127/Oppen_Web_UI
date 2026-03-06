"""
Access log summary and stream endpoints for HTTP access monitoring.
Primary: queries mw_request_log DB table. Fallback: reads middleware.requests.log file.
"""

import os
import json
import datetime as dt
from typing import Dict, Any, Optional, List
from collections import defaultdict
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio

from config import MW_DETAIL_LOG_FILE, LOG_DIR


def _db_available() -> bool:
    try:
        from core.db import _pool
        return _pool is not None
    except Exception:
        return False


def get_access_summary(
    request: Request,
    minutes: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None
):
    """
    Access log summary: Aggregate from mw_request_log DB or middleware.requests.log file.
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)

    # Determine time range
    now_utc = dt.datetime.now(tz=dt.timezone.utc)

    if start and end:
        try:
            start_n = start.replace('Z', '+00:00') if start.endswith('Z') else start
            end_n = end.replace('Z', '+00:00') if end.endswith('Z') else end
            cutoff = dt.datetime.fromisoformat(start_n)
            end_time = dt.datetime.fromisoformat(end_n)
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=dt.timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=dt.timezone.utc)
            if cutoff >= end_time:
                raise HTTPException(400, "Start time must be before end time")
        except ValueError as e:
            raise HTTPException(400, f"Invalid datetime format: {e}")
    else:
        if minutes is None:
            minutes = 60
        cutoff = now_utc - dt.timedelta(minutes=minutes)
        end_time = now_utc

    # Try DB first
    if _db_available():
        try:
            return _access_summary_db(cutoff, end_time)
        except Exception:
            pass

    return _access_summary_file(cutoff, end_time)


def _access_summary_db(cutoff, end_time):
    """Aggregate access stats from mw_request_log table."""
    from core.db import db_conn

    by_path: Dict[str, int] = defaultdict(int)
    by_status: Dict[int, int] = defaultdict(int)
    by_method: Dict[str, int] = defaultdict(int)
    latencies: List[float] = []
    requests_total = 0
    error_count = 0

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT payload FROM mw_request_log
            WHERE ts >= %s AND ts <= %s
        """, (cutoff, end_time))
        rows = cur.fetchall()
        cur.close()

    for (payload,) in rows:
        if not isinstance(payload, dict):
            continue
        event_type = payload.get("event")
        if event_type != "outbound":
            continue

        requests_total += 1
        path = payload.get("path", "unknown")
        status = payload.get("status", 500)
        method = payload.get("method", "unknown")
        ms = payload.get("ms")

        by_path[path] += 1
        by_status[status] += 1
        by_method[method] += 1

        if ms:
            latencies.append(ms)
        if isinstance(status, int) and status >= 400:
            error_count += 1

    return _format_access_result(cutoff, end_time, requests_total, error_count, latencies, by_path, by_status, by_method, "database")


def _access_summary_file(cutoff, end_time):
    """Fallback: aggregate from middleware.requests.log files."""
    if not os.path.exists(MW_DETAIL_LOG_FILE):
        return {"error": "middleware.requests.log not found", "data": []}

    by_path: Dict[str, int] = defaultdict(int)
    by_status: Dict[int, int] = defaultdict(int)
    by_method: Dict[str, int] = defaultdict(int)
    latencies: List[float] = []
    requests_total = 0
    error_count = 0

    try:
        for log_file in _get_access_log_files():
            if not os.path.exists(log_file):
                continue
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        event_type = entry.get("event")
                        if event_type not in ("inbound", "outbound"):
                            continue
                        ts_str = entry.get("ts", "")
                        if not ts_str:
                            continue
                        entry_time = dt.datetime.fromisoformat(ts_str)
                        if entry_time < cutoff or entry_time > end_time:
                            continue
                        if event_type == "outbound":
                            requests_total += 1
                            path = entry.get("path", "unknown")
                            status = entry.get("status", 500)
                            method = entry.get("method", "unknown")
                            ms = entry.get("ms")
                            by_path[path] += 1
                            by_status[status] += 1
                            by_method[method] += 1
                            if ms:
                                latencies.append(ms)
                            if isinstance(status, int) and status >= 400:
                                error_count += 1
                    except Exception:
                        continue
    except Exception as e:
        return {"error": str(e)}

    return _format_access_result(cutoff, end_time, requests_total, error_count, latencies, by_path, by_status, by_method, "file")


def _format_access_result(cutoff, end_time, requests_total, error_count, latencies, by_path, by_status, by_method, source):
    """Format access summary results."""
    error_rate = (error_count / requests_total * 100) if requests_total > 0 else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = None
    if latencies:
        latencies.sort()
        idx = min(int(len(latencies) * 0.95), len(latencies) - 1)
        p95_latency = latencies[idx]

    return {
        "time_range": {"start": cutoff.isoformat(), "end": end_time.isoformat()},
        "totals": {
            "requests_total": requests_total,
            "error_count": error_count,
            "error_rate_percent": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2) if p95_latency else None
        },
        "breakdown_by_path": [{"path": p, "count": c} for p, c in sorted(by_path.items(), key=lambda x: x[1], reverse=True)[:20]],
        "breakdown_by_status": [{"status": s, "count": c} for s, c in sorted(by_status.items(), key=lambda x: x[1], reverse=True)],
        "breakdown_by_method": [{"method": m, "count": c} for m, c in sorted(by_method.items(), key=lambda x: x[1], reverse=True)],
        "source": source,
    }


async def stream_access(request: Request):
    """
    SSE Stream for access log. Uses DB polling if available, file tailing otherwise.
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)

    if _db_available():
        gen = _db_access_generator(request)
    else:
        gen = _file_access_generator(request)

    return StreamingResponse(
        gen, media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


async def _db_access_generator(request: Request):
    """Poll mw_request_log table for new access events."""
    from core.db import db_conn

    try:
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, payload FROM mw_request_log ORDER BY id DESC LIMIT 50")
            rows = cur.fetchall()
            cur.close()

        last_id = 0
        for r in reversed(rows):
            last_id = max(last_id, r[0])
            yield f"event: access\ndata: {json.dumps(r[1], ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        return

    while True:
        if await request.is_disconnected():
            break
        try:
            with db_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, payload FROM mw_request_log WHERE id > %s ORDER BY id ASC", (last_id,))
                new_rows = cur.fetchall()
                cur.close()
            for r in new_rows:
                last_id = max(last_id, r[0])
                yield f"event: access\ndata: {json.dumps(r[1], ensure_ascii=False)}\n\n"
        except Exception:
            pass
        yield ": keepalive\n\n"
        await asyncio.sleep(2)


async def _file_access_generator(request: Request):
    """Fallback: tail middleware.requests.log."""
    if not os.path.exists(MW_DETAIL_LOG_FILE):
        yield f"event: error\ndata: {json.dumps({'error': 'middleware.requests.log not found'})}\n\n"
        return

    try:
        with open(MW_DETAIL_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-50:]:
                if line.strip():
                    yield f"event: access\ndata: {line.strip()}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    last_size = os.path.getsize(MW_DETAIL_LOG_FILE)
    while True:
        if await request.is_disconnected():
            break
        try:
            current_size = os.path.getsize(MW_DETAIL_LOG_FILE)
            if current_size < last_size:
                last_size = 0
                with open(MW_DETAIL_LOG_FILE, "r", encoding="utf-8") as f:
                    for line in f.readlines():
                        if line.strip():
                            yield f"event: access\ndata: {line.strip()}\n\n"
                last_size = current_size
            elif current_size > last_size:
                with open(MW_DETAIL_LOG_FILE, "r", encoding="utf-8") as f:
                    f.seek(last_size)
                    for line in f.readlines():
                        if line.strip():
                            yield f"event: access\ndata: {line.strip()}\n\n"
                last_size = current_size
        except FileNotFoundError:
            yield f"event: error\ndata: {json.dumps({'error': 'file not found'})}\n\n"
            break
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            break
        yield ": keepalive\n\n"
        await asyncio.sleep(2)


def _get_access_log_files() -> List[str]:
    """Get list of access log files (main + rotated)."""
    files = [MW_DETAIL_LOG_FILE]
    for i in range(1, 11):
        rotated = f"{MW_DETAIL_LOG_FILE}.{i}"
        if os.path.exists(rotated):
            files.append(rotated)
    files.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    return files[:10]
