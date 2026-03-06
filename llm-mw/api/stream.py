"""
SSE Stream endpoint for realtime audit events.
Primary: polls mw_audit_log DB table. Fallback: tails audit.jsonl file.
"""

import os
import time
import json
import asyncio
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

from config import ADMIN_KEY, AUDIT_LOG_FILE


def _db_available() -> bool:
    try:
        from core.db import _pool
        return _pool is not None
    except Exception:
        return False


async def stream_audit(request: Request):
    """
    Admin endpoint: Stream realtime audit events via Server-Sent Events (SSE).
    Uses DB polling if available, falls back to file tailing.
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)

    if _db_available():
        return StreamingResponse(
            _db_event_generator(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    return StreamingResponse(
        _file_event_generator(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


async def _db_event_generator(request: Request):
    """Poll mw_audit_log table for new events."""
    from core.db import db_conn

    # Fetch last 50 entries first
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, ts, rid, user_id, endpoint, model, purpose, status,
                       status_code, latency_ms, tokens_in, tokens_out, tokens_total,
                       cost_usd, image_count, tts_chars, stt_seconds, video_count,
                       error_type, error_message
                FROM mw_audit_log ORDER BY id DESC LIMIT 50
            """)
            rows = cur.fetchall()
            cur.close()

        # Send in chronological order
        last_id = 0
        for r in reversed(rows):
            last_id = max(last_id, r[0])
            entry = _row_to_dict(r)
            yield f"event: audit\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        return

    # Poll for new entries
    while True:
        if await request.is_disconnected():
            break

        try:
            with db_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, ts, rid, user_id, endpoint, model, purpose, status,
                           status_code, latency_ms, tokens_in, tokens_out, tokens_total,
                           cost_usd, image_count, tts_chars, stt_seconds, video_count,
                           error_type, error_message
                    FROM mw_audit_log WHERE id > %s ORDER BY id ASC
                """, (last_id,))
                new_rows = cur.fetchall()
                cur.close()

            for r in new_rows:
                last_id = max(last_id, r[0])
                entry = _row_to_dict(r)
                yield f"event: audit\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"

        except Exception:
            pass

        yield ": keepalive\n\n"
        await asyncio.sleep(2)


def _row_to_dict(r):
    """Convert a DB row tuple to dict."""
    return {
        "ts": r[1].isoformat() if r[1] else None, "rid": r[2], "user_id": r[3],
        "endpoint": r[4], "model": r[5], "purpose": r[6], "status": r[7],
        "status_code": r[8], "latency_ms": r[9], "tokens_in": r[10],
        "tokens_out": r[11], "tokens_total": r[12], "cost_usd": r[13],
        "image_count": r[14], "tts_chars": r[15], "stt_seconds": r[16],
        "video_count": r[17], "error_type": r[18], "error_message": r[19],
    }


async def _file_event_generator(request: Request):
    """Fallback: tail audit.jsonl file."""
    if not os.path.exists(AUDIT_LOG_FILE):
        yield f"event: error\ndata: {json.dumps({'error': 'audit.jsonl not found'})}\n\n"
        return

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-50:]:
                if line.strip():
                    yield f"event: audit\ndata: {line.strip()}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    last_size = os.path.getsize(AUDIT_LOG_FILE)

    while True:
        if await request.is_disconnected():
            break

        try:
            current_size = os.path.getsize(AUDIT_LOG_FILE)
            if current_size < last_size:
                last_size = 0
                with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                    for line in f.readlines():
                        if line.strip():
                            yield f"event: audit\ndata: {line.strip()}\n\n"
                last_size = current_size
            elif current_size > last_size:
                with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                    f.seek(last_size)
                    for line in f.readlines():
                        if line.strip():
                            yield f"event: audit\ndata: {line.strip()}\n\n"
                last_size = current_size
        except FileNotFoundError:
            yield f"event: error\ndata: {json.dumps({'error': 'audit.jsonl not found'})}\n\n"
            break
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            break

        yield ": keepalive\n\n"
        await asyncio.sleep(2)
