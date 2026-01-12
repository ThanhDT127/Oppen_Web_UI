"""
Audit Log Query API - Full-text search with filters
Reads from audit.jsonl and supports pagination, filtering, and sorting
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Query, Request
from config import AUDIT_LOG_FILE


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
    sort_by: str = Query("timestamp", regex="^(timestamp|cost|tokens|duration)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """
    Query audit.jsonl with filters and pagination.
    
    Supports:
    - Full-text search (via user_id, model, endpoint)
    - Cost range filtering
    - Time range filtering
    - Status filtering (success/error)
    - Sorting by timestamp/cost/tokens/duration
    - Pagination (limit/offset)
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    if not os.path.exists(AUDIT_LOG_FILE):
        return {
            "total": 0,
            "limit": limit,
            "offset": offset,
            "results": []
        }
    
    # Parse time range
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    
    if start:
        try:
            # Parse ISO timestamp (e.g., "2025-01-15T10:00:00")
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
    
    # Read and filter logs
    matching_records: List[Dict[str, Any]] = []
    
    try:
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    
                    # Parse timestamp
                    ts_str = record.get("timestamp", record.get("ts"))
                    if not ts_str:
                        continue
                    
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=tz)
                    
                    # Filter by time range
                    if ts < cutoff or ts > end_time:
                        continue
                    
                    # Filter by user_id
                    if user_id and record.get("user_id") != user_id:
                        continue
                    
                    # Filter by model (partial match)
                    if model and model.lower() not in record.get("model", "").lower():
                        continue
                    
                    # Filter by status
                    if status and record.get("status") != status:
                        continue
                    
                    # Filter by endpoint (partial match)
                    if endpoint and endpoint.lower() not in record.get("endpoint", "").lower():
                        continue
                    
                    # Filter by cost range
                    cost = record.get("cost_usd", 0)
                    if min_cost is not None and cost < min_cost:
                        continue
                    if max_cost is not None and cost > max_cost:
                        continue
                    
                    # Add record with parsed timestamp
                    record["_ts_parsed"] = ts
                    matching_records.append(record)
                
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
    
    except Exception as e:
        return {
            "error": f"Failed to read audit log: {str(e)}",
            "total": 0,
            "results": []
        }
    
    # Sort records
    reverse = (sort_order == "desc")
    
    if sort_by == "timestamp":
        matching_records.sort(key=lambda r: r.get("_ts_parsed", datetime.min), reverse=reverse)
    elif sort_by == "cost":
        matching_records.sort(key=lambda r: r.get("cost_usd", 0), reverse=reverse)
    elif sort_by == "tokens":
        matching_records.sort(key=lambda r: r.get("tokens_total", 0), reverse=reverse)
    elif sort_by == "duration":
        matching_records.sort(key=lambda r: r.get("duration_ms", 0), reverse=reverse)
    
    # Pagination
    total = len(matching_records)
    paginated = matching_records[offset:offset + limit]
    
    # Clean up internal fields
    for record in paginated:
        record.pop("_ts_parsed", None)
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": paginated,
        "filters_applied": {
            "user_id": user_id,
            "model": model,
            "status": status,
            "endpoint": endpoint,
            "min_cost": min_cost,
            "max_cost": max_cost,
            "time_range": {
                "start": cutoff.isoformat(),
                "end": end_time.isoformat()
            }
        }
    }
