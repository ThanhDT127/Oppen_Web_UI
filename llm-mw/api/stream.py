"""
SSE Stream endpoint for realtime audit events.
"""

import os
import time
import json
import asyncio
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

from config import ADMIN_KEY, AUDIT_LOG_FILE


async def stream_audit(request: Request):
    """
    Admin endpoint: Stream realtime audit events via Server-Sent Events (SSE).
    
    Tails audit.jsonl and emits new lines as they appear.
    Format: event: audit\ndata: {json}\n\n
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    async def event_generator():
        """Generator function that yields SSE events"""
        if not os.path.exists(AUDIT_LOG_FILE):
            yield f"event: error\ndata: {json.dumps({'error': 'audit.jsonl not found'})}\n\n"
            return
        
        # Read existing lines first (last 50)
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                for line in recent_lines:
                    if line.strip():
                        yield f"event: audit\ndata: {line.strip()}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        # Keep connection alive and tail new lines
        last_size = os.path.getsize(AUDIT_LOG_FILE)
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            try:
                current_size = os.path.getsize(AUDIT_LOG_FILE)
                
                if current_size > last_size:
                    # File has grown, read new content
                    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                        f.seek(last_size)
                        new_lines = f.readlines()
                        
                        for line in new_lines:
                            if line.strip():
                                yield f"event: audit\ndata: {line.strip()}\n\n"
                    
                    last_size = current_size
                
                # Send keepalive ping every 30 seconds
                yield f": keepalive\n\n"
                
            except FileNotFoundError:
                # File was deleted/rotated
                yield f"event: error\ndata: {json.dumps({'error': 'audit.jsonl not found'})}\n\n"
                break
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break
            
            # Sleep for 2 seconds before checking again
            await asyncio.sleep(2)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
