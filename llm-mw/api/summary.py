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
    from utils.auth_guard import require_admin_or_session
    require_admin_or_session(request)
    
    if not os.path.exists(AUDIT_LOG_FILE):
        return {"error": "audit.jsonl not found", "data": []}
    
    # Calculate cutoff time
    cutoff = dt.datetime.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")) - dt.timedelta(minutes=minutes)
    
    # Define LLM endpoints
    LLM_ENDPOINTS = {
        "/v1/chat/completions": "chat",
        "/v1/images/generations": "image",
        "/v1/audio/transcriptions": "audio",
        "/v1/audio/speech": "audio",
        "/v1/video/generations": "video",
    }
    
    # Aggregate data
    requests_total = 0
    llm_calls_total = 0
    admin_ops_total = 0
    pending_count = 0
    error_count = 0
    
    # Breakdown by type
    chat_calls = 0
    image_calls = 0
    audio_calls = 0
    video_calls = 0
    
    latencies = []
    tokens_total = 0
    cost_total = 0.0
    user_costs: Dict[str, float] = {}  # user_id -> cost
    model_costs: Dict[str, float] = {}  # model -> cost
    
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
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
                    if entry_time < cutoff:
                        continue
                    
                    # Get endpoint and status
                    endpoint = entry.get("endpoint", "")
                    status = entry.get("status", "ok")
                    
                    # Classify request type
                    is_llm_call = endpoint in LLM_ENDPOINTS
                    is_admin_op = endpoint in ["/admin/reconcile", "/admin/usage", "/admin/reset"]
                    
                    # Count by type (including pending for breakdown)
                    if is_llm_call:
                        call_type = LLM_ENDPOINTS[endpoint]
                        
                        # Count completed LLM calls only
                        if status in ["ok", "error", "reconciled"]:
                            llm_calls_total += 1
                            
                            if call_type == "chat":
                                chat_calls += 1
                            elif call_type == "image":
                                image_calls += 1
                            elif call_type == "audio":
                                audio_calls += 1
                            elif call_type == "video":
                                video_calls += 1
                    
                    if is_admin_op:
                        admin_ops_total += 1
                    
                    # Aggregate by status
                    if status in ["ok", "error", "reconciled"]:
                        requests_total += 1
                    if status == "pending":
                        pending_count += 1
                    if status == "error":
                        error_count += 1
                    
                    # Aggregate latency (exclude pending)
                    if status != "pending":
                        latency = entry.get("latency_ms")
                        if latency is not None and latency > 0:
                            latencies.append(latency)
                    
                    # Aggregate tokens and cost (exclude pending)
                    if status in ["ok", "reconciled"]:
                        tokens = entry.get("tokens_total", 0)
                        cost = entry.get("cost_usd", 0.0)
                        tokens_total += tokens
                        cost_total += cost
                        
                        # Top users by cost
                        user_id = entry.get("user_id", "unknown")
                        user_costs[user_id] = user_costs.get(user_id, 0.0) + cost
                        
                        # Top models by cost
                        model = entry.get("model", "unknown")
                        model_costs[model] = model_costs.get(model, 0.0) + cost
                    
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
        
        # Calculate P95 latency
        p95_latency = None
        if latencies:
            latencies.sort()
            p95_idx = int(len(latencies) * 0.95)
            p95_latency = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
        
        # Calculate error rate
        error_rate = (error_count / requests_total * 100) if requests_total > 0 else 0.0
        
        # Top 10 users by cost
        top_users = sorted(user_costs.items(), key=lambda x: x[1], reverse=True)[:10]
        top_users_list = [{"user_id": uid, "cost_usd": round(cost, 6)} for uid, cost in top_users]
        
        # Top 10 models by cost
        top_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)[:10]
        top_models_list = [{"model": m, "cost_usd": round(cost, 6)} for m, cost in top_models]
        
        return {
            "time_window_minutes": minutes,
            "cutoff_time": cutoff.isoformat(),
            
            # Overall metrics
            "requests_total": requests_total,
            "llm_calls_total": llm_calls_total,
            "admin_ops_total": admin_ops_total,
            "pending_count": pending_count,
            "error_count": error_count,
            "error_rate_percent": round(error_rate, 2),
            
            # Breakdown by LLM type
            "chat_calls": chat_calls,
            "image_calls": image_calls,
            "audio_calls": audio_calls,
            "video_calls": video_calls,
            
            # Performance metrics
            "p95_latency_ms": round(p95_latency, 2) if p95_latency else None,
            "tokens_total": tokens_total,
            "cost_total_usd": round(cost_total, 6),
            
            # Top lists
            "top_users": top_users_list,
            "top_models": top_models_list
        }
    
    except Exception as e:
        return {"error": str(e)}
