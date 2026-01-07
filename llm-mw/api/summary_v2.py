"""
Enhanced summary endpoint with time range, breakdown, and timeseries support.
"""

import os
import json
import datetime as dt
from typing import Dict, Any, Optional, List, Tuple
from zoneinfo import ZoneInfo
from fastapi import Request, HTTPException
from collections import defaultdict

from config import AUDIT_LOG_FILE, LOG_DIR


def get_summary_v2(
    request: Request,
    minutes: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    bucket: str = "auto"
):
    """
    Enhanced admin endpoint: Aggregate usage statistics from audit.jsonl with time range support.
    
    Query parameters:
    - minutes: Time window in minutes (legacy fallback)
    - start: ISO datetime string (e.g., "2026-01-07T00:00:00+07:00")
    - end: ISO datetime string
    - bucket: "auto" | "minute" | "hour" | "day" (for timeseries)
    
    Returns:
        Aggregated metrics with breakdown by user/model and timeseries data
    """
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    if not os.path.exists(AUDIT_LOG_FILE):
        return {"error": "audit.jsonl not found", "data": []}
    
    # Determine time range
    now_utc = dt.datetime.now(tz=dt.timezone.utc)
    
    if start and end:
        # Parse custom range
        try:
            cutoff = dt.datetime.fromisoformat(start)
            end_time = dt.datetime.fromisoformat(end)
            # Ensure timezone aware
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=dt.timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=dt.timezone.utc)
        except ValueError as e:
            raise HTTPException(400, f"Invalid datetime format: {e}")
    else:
        # Fallback to minutes
        if minutes is None:
            minutes = 60
        cutoff = now_utc - dt.timedelta(minutes=minutes)
        end_time = now_utc
    
    # Auto-determine bucket size if "auto"
    time_range_seconds = (end_time - cutoff).total_seconds()
    if bucket == "auto":
        if time_range_seconds <= 3600:  # <= 1 hour
            bucket_size = "minute"
        elif time_range_seconds <= 86400 * 2:  # <= 2 days
            bucket_size = "hour"
        else:
            bucket_size = "day"
    else:
        bucket_size = bucket
    
    # Define LLM endpoints
    LLM_ENDPOINTS = {
        "/v1/chat/completions": "chat",
        "/v1/images/generations": "image",
        "/v1/audio/transcriptions": "audio",
        "/v1/audio/speech": "audio",
        "/v1/video/generations": "video",
    }
    
    # Data structures for rid-based tracking (control-grade)
    rid_status: Dict[str, Tuple[float, str]] = {}  # rid -> (timestamp, status)
    rid_data: Dict[str, Dict[str, Any]] = {}  # rid -> {last event data}
    
    # Timeseries buckets
    timeseries_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "requests": set(),  # Use set for distinct rids
        "tokens_total": 0,
        "cost_total": 0.0,
        "errors": 0
    })
    
    # Breakdown data (use sets for distinct rid counting)
    user_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "requests": set(),
        "requests_ok": set(),
        "errors": 0,
        "tokens_total": 0,
        "cost_total": 0.0,
        "latencies": []
    })
    
    model_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "requests": set(),
        "requests_ok": set(),
        "errors": 0,
        "tokens_total": 0,
        "cost_total": 0.0,
        "latencies": []
    })
    
    # Breakdown by LLM type
    llm_type_counts = {"chat": 0, "image": 0, "audio": 0, "video": 0}
    
    # Read audit log (including rotated files)
    log_files = _get_audit_log_files()
    
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
                        timestamp_str = entry.get("ts", "")
                        if not timestamp_str:
                            continue
                        
                        # Parse timestamp
                        entry_time = dt.datetime.fromisoformat(timestamp_str)
                        
                        # Filter by time range
                        if entry_time < cutoff or entry_time > end_time:
                            continue
                        
                        rid = entry.get("rid", "")
                        if not rid:
                            continue
                        
                        endpoint = entry.get("endpoint", "")
                        status = entry.get("status", "ok")
                        user_id = entry.get("user_id", "unknown")
                        model = entry.get("model", "unknown")
                        
                        # Track last status per rid (control-grade)
                        entry_ts = entry_time.timestamp()
                        if rid not in rid_status or entry_ts > rid_status[rid][0]:
                            rid_status[rid] = (entry_ts, status)
                            rid_data[rid] = entry
                        
                        # Timeseries bucketing
                        bucket_key = _get_bucket_key(entry_time, bucket_size)
                        timeseries_data[bucket_key]["requests"].add(rid)
                        
                        # Only aggregate tokens/cost from final status (ok/reconciled)
                        if status in ["ok", "reconciled"]:
                            tokens = entry.get("tokens_total", 0)
                            cost = entry.get("cost_usd", 0.0)
                            latency = entry.get("latency_ms")
                            
                            timeseries_data[bucket_key]["tokens_total"] += tokens
                            timeseries_data[bucket_key]["cost_total"] += cost
                            
                            # User breakdown
                            user_data[user_id]["requests"].add(rid)
                            user_data[user_id]["requests_ok"].add(rid)
                            user_data[user_id]["tokens_total"] += tokens
                            user_data[user_id]["cost_total"] += cost
                            if latency:
                                user_data[user_id]["latencies"].append(latency)
                            
                            # Model breakdown
                            model_data[model]["requests"].add(rid)
                            model_data[model]["requests_ok"].add(rid)
                            model_data[model]["tokens_total"] += tokens
                            model_data[model]["cost_total"] += cost
                            if latency:
                                model_data[model]["latencies"].append(latency)
                        
                        elif status == "error":
                            timeseries_data[bucket_key]["errors"] += 1
                            user_data[user_id]["requests"].add(rid)
                            user_data[user_id]["errors"] += 1
                            model_data[model]["requests"].add(rid)
                            model_data[model]["errors"] += 1
                        
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
        
        # Calculate totals from rid_status (control-grade: last status per rid)
        requests_total = len(rid_status)
        pending_open_count = sum(1 for _, (_, status) in rid_status.items() if status == "pending")
        error_count = sum(1 for _, (_, status) in rid_status.items() if status == "error")
        requests_ok = sum(1 for _, (_, status) in rid_status.items() if status in ["ok", "reconciled"])
        
        # Calculate LLM type breakdown
        for rid, data in rid_data.items():
            endpoint = data.get("endpoint", "")
            status = rid_status.get(rid, (0, ""))[1]
            if status in ["ok", "reconciled"] and endpoint in LLM_ENDPOINTS:
                call_type = LLM_ENDPOINTS[endpoint]
                llm_type_counts[call_type] += 1
        
        # Calculate totals from final events
        total_tokens = sum(d["tokens_total"] for d in user_data.values())
        total_cost = sum(d["cost_total"] for d in user_data.values())
        
        # Calculate P95 latency from all final events
        all_latencies = []
        for user_stats in user_data.values():
            all_latencies.extend(user_stats["latencies"])
        
        p95_latency = None
        if all_latencies:
            all_latencies.sort()
            p95_idx = int(len(all_latencies) * 0.95)
            p95_latency = all_latencies[p95_idx] if p95_idx < len(all_latencies) else all_latencies[-1]
        
        # Calculate error rate
        error_rate = (error_count / requests_total * 100) if requests_total > 0 else 0.0
        
        # Format breakdown by user
        breakdown_by_user = []
        for user_id, stats in user_data.items():
            user_requests_total = len(stats["requests"])
            user_requests_ok = len(stats["requests_ok"])
            user_error_rate = (stats["errors"] / user_requests_total * 100) if user_requests_total > 0 else 0.0
            
            user_p95 = None
            if stats["latencies"]:
                sorted_lat = sorted(stats["latencies"])
                p95_idx = int(len(sorted_lat) * 0.95)
                user_p95 = sorted_lat[p95_idx] if p95_idx < len(sorted_lat) else sorted_lat[-1]
            
            breakdown_by_user.append({
                "user_id": user_id,
                "requests_total": user_requests_total,
                "requests_ok": user_requests_ok,
                "errors": stats["errors"],
                "error_rate_percent": round(user_error_rate, 2),
                "tokens_total": stats["tokens_total"],
                "cost_usd": round(stats["cost_total"], 6),
                "p95_latency_ms": round(user_p95, 2) if user_p95 else None
            })
        
        # Sort by cost descending
        breakdown_by_user.sort(key=lambda x: x["cost_usd"], reverse=True)
        
        # Format breakdown by model
        breakdown_by_model = []
        for model, stats in model_data.items():
            model_requests_total = len(stats["requests"])
            model_requests_ok = len(stats["requests_ok"])
            model_error_rate = (stats["errors"] / model_requests_total * 100) if model_requests_total > 0 else 0.0
            
            model_p95 = None
            if stats["latencies"]:
                sorted_lat = sorted(stats["latencies"])
                p95_idx = int(len(sorted_lat) * 0.95)
                model_p95 = sorted_lat[p95_idx] if p95_idx < len(sorted_lat) else sorted_lat[-1]
            
            breakdown_by_model.append({
                "model": model,
                "requests_total": model_requests_total,
                "requests_ok": model_requests_ok,
                "errors": stats["errors"],
                "error_rate_percent": round(model_error_rate, 2),
                "tokens_total": stats["tokens_total"],
                "cost_usd": round(stats["cost_total"], 6),
                "p95_latency_ms": round(model_p95, 2) if model_p95 else None
            })
        
        # Sort by cost descending
        breakdown_by_model.sort(key=lambda x: x["cost_usd"], reverse=True)
        
        # Format timeseries
        timeseries = []
        for bucket_key in sorted(timeseries_data.keys()):
            data = timeseries_data[bucket_key]
            timeseries.append({
                "ts": bucket_key,
                "requests_total": len(data["requests"]),
                "tokens_total": data["tokens_total"],
                "cost_usd": round(data["cost_total"], 6),
                "errors": data["errors"]
            })
        
        return {
            "time_range": {
                "start": cutoff.isoformat(),
                "end": end_time.isoformat(),
                "bucket_size": bucket_size
            },
            "totals": {
                "requests_total": requests_total,
                "requests_ok": requests_ok,
                "pending_open_count": pending_open_count,
                "error_count": error_count,
                "error_rate_percent": round(error_rate, 2),
                "tokens_total": total_tokens,
                "cost_total_usd": round(total_cost, 6),
                "p95_latency_ms": round(p95_latency, 2) if p95_latency else None,
                "chat_calls": llm_type_counts["chat"],
                "image_calls": llm_type_counts["image"],
                "audio_calls": llm_type_counts["audio"],
                "video_calls": llm_type_counts["video"]
            },
            "breakdown_by_user": breakdown_by_user[:20],  # Top 20
            "breakdown_by_model": breakdown_by_model[:20],  # Top 20
            "timeseries": timeseries
        }
    
    except Exception as e:
        return {"error": str(e)}


def _get_audit_log_files() -> List[str]:
    """
    Get list of audit log files to read (main + rotated).
    Returns up to 10 most recent files.
    """
    files = [AUDIT_LOG_FILE]
    
    # Check for rotated files: audit.jsonl.1, audit.jsonl.2, etc.
    for i in range(1, 11):  # Check up to 10 rotated files
        rotated_file = f"{AUDIT_LOG_FILE}.{i}"
        if os.path.exists(rotated_file):
            files.append(rotated_file)
    
    # Sort by modification time (newest first)
    files.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=True)
    
    return files[:10]  # Return up to 10 most recent


def _get_bucket_key(dt_obj: dt.datetime, bucket_size: str) -> str:
    """
    Generate bucket key for timeseries grouping.
    
    Args:
        dt_obj: datetime object
        bucket_size: "minute" | "hour" | "day"
        
    Returns:
        ISO format string truncated to bucket granularity
    """
    if bucket_size == "minute":
        return dt_obj.strftime("%Y-%m-%dT%H:%M:00")
    elif bucket_size == "hour":
        return dt_obj.strftime("%Y-%m-%dT%H:00:00")
    elif bucket_size == "day":
        return dt_obj.strftime("%Y-%m-%dT00:00:00")
    else:
        return dt_obj.strftime("%Y-%m-%dT%H:00:00")
