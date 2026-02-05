"""
LiteLLM service integration for log parsing and cost extraction.
"""

import os
import re
from typing import Dict, Any, Optional
import httpx

from config import LITELLM_LOG_FILE


def get_cost_from_headers(headers: httpx.Headers) -> float:
    """
    Extract cost from LiteLLM response headers.
    
    Args:
        headers: HTTP response headers from LiteLLM
        
    Returns:
        Cost in USD (0.0 if not found)
    """
    # LiteLLM sometimes returns a cost header; if missing, we treat as 0.
    for key in ("x-litellm-response-cost", "x-litellm-cost"):
        value = headers.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            return 0.0
    return 0.0


def find_usage_in_log(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Find usage information in LiteLLM log file by request ID.
    Searches last 5MB of log file for efficiency.
    
    Args:
        request_id: Request ID to search for
        
    Returns:
        Dictionary with usage info (prompt_tokens, completion_tokens, model, cost) or None
    """
    if not os.path.exists(LITELLM_LOG_FILE):
        return None
    
    try:
        with open(LITELLM_LOG_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            back = min(size, 5 * 1024 * 1024)
            f.seek(max(size - back, 0))
            chunk = f.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    lines = chunk.strip().splitlines()[::-1]
    tokens_pattern = re.compile(r"(prompt_tokens|completion_tokens|total_tokens)\D+(\d+)", re.IGNORECASE)
    model_pattern = re.compile(r"model\W+([A-Za-z0-9._/\-]+)")
    cost_pattern = re.compile(r"(response_cost|x-litellm-response-cost)\D+([0-9.eE+\-]+)", re.IGNORECASE)

    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": None, "response_cost": None}
    hit = False

    for line in lines:
        if request_id in line:
            hit = True
            model_match = model_pattern.search(line)
            if model_match:
                usage["model"] = model_match.group(1)
            cost_match = cost_pattern.search(line)
            if cost_match:
                try:
                    usage["response_cost"] = float(cost_match.group(2))
                except Exception:
                    pass
            for key, value in tokens_pattern.findall(line):
                usage[key.lower()] = int(value)
            if usage.get("total_tokens", 0) > 0:
                if not usage["model"]:
                    for neighbour in lines:
                        if request_id in neighbour:
                            neighbour_match = model_pattern.search(neighbour)
                            if neighbour_match:
                                usage["model"] = neighbour_match.group(1)
                                break
                return usage

    if hit and (usage["prompt_tokens"] or usage["completion_tokens"]):
        if not usage["model"]:
            for line in lines:
                if request_id in line:
                    model_match = model_pattern.search(line)
                    if model_match:
                        usage["model"] = model_match.group(1)
                        break
        if not usage.get("total_tokens"):
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        return usage

    return None
