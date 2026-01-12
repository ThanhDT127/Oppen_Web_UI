"""
Access log summary and stream endpoints for HTTP access monitoring.
Separate from usage audit to avoid noise in dashboard.
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


def get_access_summary(
    request: Request,
    minutes: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None
):
    """
    Access log summary: Aggregate from middleware.requests.log
    
    Query parameters:
    - minutes: Time window in minutes (default 60)
    - start: ISO datetime string
    - end: ISO datetime string
    
    Returns:
        Access metrics by path, status, method
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    if not os.path.exists(MW_DETAIL_LOG_FILE):
        return {"error": "middleware.requests.log not found", "data": []}
    
    # Determine time range
    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    
    if start and end:
        # Normalize 'Z' to '+00:00' for fromisoformat compatibility
        try:
            start_normalized = start.replace('Z', '+00:00') if start.endswith('Z') else start
            end_normalized = end.replace('Z', '+00:00') if end.endswith('Z') else end
            
            cutoff = dt.datetime.fromisoformat(start_normalized)
            end_time = dt.datetime.fromisoformat(end_normalized)
            
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=dt.timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=dt.timezone.utc)
            
            # Validate: start < end
            if cutoff >= end_time:
                raise HTTPException(400, "Start time must be before end time")
        except ValueError as e:
            raise HTTPException(400, f"Invalid datetime format: {e}")
    else:
        if minutes is None:
            minutes = 60
        cutoff = now_utc - dt.timedelta(minutes=minutes)
        end_time = now_utc
    
    # Aggregation structures
    requests_total = 0
    by_path: Dict[str, int] = defaultdict(int)
    by_status: Dict[int, int] = defaultdict(int)
    by_method: Dict[str, int] = defaultdict(int)
    latencies: List[float] = []
    error_count = 0
    
    # Read access log (including rotated files)
    log_files = _get_access_log_files()
    
    try:
        for log_file in log_files:
            if not os.path.exists(log_file):
                continue
                
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        
                        # Filter by event type (only inbound/outbound)
                        event_type = entry.get("event")
                        if event_type not in ["inbound", "outbound"]:
                            continue
                        
                        # Parse timestamp
                        timestamp_str = entry.get("ts", "")
                        if not timestamp_str:
                            continue
                        
                        entry_time = dt.datetime.fromisoformat(timestamp_str)
                        
                        # Filter by time range
                        if entry_time < cutoff or entry_time > end_time:
                            continue
                        
                        # Only count outbound events (completed requests)
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
                            
                            if status >= 400:
                                error_count += 1
                        
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
        
        # Calculate metrics
        error_rate = (error_count / requests_total * 100) if requests_total > 0 else 0.0
        
        # Calculate latency stats
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = None
        if latencies:
            latencies.sort()
            p95_idx = int(len(latencies) * 0.95)
            p95_latency = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
        
        # Format breakdown by path (top 20)
        breakdown_by_path = [
            {"path": path, "count": count}
            for path, count in sorted(by_path.items(), key=lambda x: x[1], reverse=True)[:20]
        ]
        
        # Format breakdown by status
        breakdown_by_status = [
            {"status": status, "count": count}
            for status, count in sorted(by_status.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Format breakdown by method
        breakdown_by_method = [
            {"method": method, "count": count}
            for method, count in sorted(by_method.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return {
            "time_range": {
                "start": cutoff.isoformat(),
                "end": end_time.isoformat()
            },
            "totals": {
                "requests_total": requests_total,
                "error_count": error_count,
                "error_rate_percent": round(error_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2) if p95_latency else None
            },
            "breakdown_by_path": breakdown_by_path,
            "breakdown_by_status": breakdown_by_status,
            "breakdown_by_method": breakdown_by_method
        }
    
    except Exception as e:
        return {"error": str(e)}


async def stream_access(request: Request):
    """
    SSE Stream for access log (middleware.requests.log).
    Similar to audit stream but for HTTP access logs.
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    async def event_generator():
        """Generator function that yields SSE events"""
        if not os.path.exists(MW_DETAIL_LOG_FILE):
            yield f"event: error\ndata: {json.dumps({'error': 'middleware.requests.log not found'})}\n\n"
            return
        
        # Read existing lines first (last 50)
        try:
            with open(MW_DETAIL_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                for line in recent_lines:
                    if line.strip():
                        yield f"event: access\ndata: {line.strip()}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        # Keep connection alive and tail new lines
        last_size = os.path.getsize(MW_DETAIL_LOG_FILE)
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            try:
                current_size = os.path.getsize(MW_DETAIL_LOG_FILE)
                
                # Detect log rotation: file shrunk (rotated/truncated)
                if current_size < last_size:
                    # File was rotated, reset to beginning and read all
                    last_size = 0
                    with open(MW_DETAIL_LOG_FILE, "r", encoding="utf-8") as f:
                        new_lines = f.readlines()
                        for line in new_lines:
                            if line.strip():
                                yield f"event: access\ndata: {line.strip()}\n\n"
                    last_size = current_size
                elif current_size > last_size:
                    # File has grown, read new content
                    with open(MW_DETAIL_LOG_FILE, "r", encoding="utf-8") as f:
                        f.seek(last_size)
                        new_lines = f.readlines()
                        
                        for line in new_lines:
                            if line.strip():
                                yield f"event: access\ndata: {line.strip()}\n\n"
                    
                    last_size = current_size
                
                # Send keepalive ping every 30 seconds
                yield f": keepalive\n\n"
                
            except FileNotFoundError:
                yield f"event: error\ndata: {json.dumps({'error': 'middleware.requests.log not found'})}\n\n"
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


def _get_access_log_files() -> List[str]:
    """
    Get list of access log files to read (main + rotated).
    Returns up to 10 most recent files.
    """
    files = [MW_DETAIL_LOG_FILE]
    
    # Check for rotated files
    for i in range(1, 11):
        rotated_file = f"{MW_DETAIL_LOG_FILE}.{i}"
        if os.path.exists(rotated_file):
            files.append(rotated_file)
    
    # Sort by modification time (newest first)
    files.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    
    return files[:10]
