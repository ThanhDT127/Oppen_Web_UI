"""
Summary endpoint for aggregated usage statistics.
"""

import os
import json
import datetime as dt
from typing import Dict, Any
from zoneinfo import ZoneInfo
from fastapi import Request, HTTPException

from config import ADMIN_KEY, AUDIT_LOG_FILE


def get_summary(request: Request, minutes: int = 60):
    """
    Admin endpoint: Aggregate usage statistics from audit.jsonl.
    
    Query parameters:
    - minutes: Time window in minutes (default 60)
    
    Returns aggregated metrics by user and model for the specified time window.
    """
    if request.headers.get("Authorization", "") != f"Bearer {ADMIN_KEY}":
        raise HTTPException(403, "Invalid admin key")
    
    if not os.path.exists(AUDIT_LOG_FILE):
        return {"error": "audit.jsonl not found", "data": []}
    
    # Calculate cutoff time
    cutoff = dt.datetime.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")) - dt.timedelta(minutes=minutes)
    
    # Aggregate data: key = (user_id, model), value = metrics
    aggregates: Dict[tuple, Dict[str, Any]] = {}
    
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    timestamp_str = entry.get("timestamp", "")
                    if not timestamp_str:
                        continue
                    
                    # Parse timestamp
                    entry_time = dt.datetime.fromisoformat(timestamp_str)
                    if entry_time < cutoff:
                        continue
                    
                    user_id = entry.get("user_id", "unknown")
                    model = entry.get("model") or "unknown"
                    key = (user_id, model)
                    
                    if key not in aggregates:
                        aggregates[key] = {
                            "user_id": user_id,
                            "model": model,
                            "total_requests": 0,
                            "success_requests": 0,
                            "error_requests": 0,
                            "tokens_in": 0,
                            "tokens_out": 0,
                            "cost_usd": 0.0,
                            "image_requests": 0,
                            "stt_requests": 0,
                            "tts_chars": 0,
                            "total_duration_ms": 0,
                        }
                    
                    agg = aggregates[key]
                    agg["total_requests"] += 1
                    if entry.get("status") == "success":
                        agg["success_requests"] += 1
                    else:
                        agg["error_requests"] += 1
                    
                    agg["tokens_in"] += entry.get("tokens_in", 0)
                    agg["tokens_out"] += entry.get("tokens_out", 0)
                    agg["cost_usd"] += entry.get("cost_usd", 0.0)
                    agg["image_requests"] += entry.get("image_requests", 0)
                    agg["stt_requests"] += entry.get("stt_requests", 0)
                    agg["tts_chars"] += entry.get("tts_chars", 0)
                    agg["total_duration_ms"] += entry.get("duration_ms", 0)
                    
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
        
        # Convert to list and round costs
        result = []
        for agg in aggregates.values():
            agg["cost_usd"] = round(agg["cost_usd"], 6)
            agg["avg_duration_ms"] = int(agg["total_duration_ms"] / agg["total_requests"]) if agg["total_requests"] > 0 else 0
            result.append(agg)
        
        # Sort by cost descending
        result.sort(key=lambda x: x["cost_usd"], reverse=True)
        
        return {
            "time_window_minutes": minutes,
            "cutoff_time": cutoff.isoformat(),
            "total_entries": len(result),
            "data": result
        }
    
    except Exception as e:
        return {"error": str(e), "data": []}
