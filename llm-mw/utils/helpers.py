"""
Helper utilities for LLM Middleware.
General-purpose helper functions.
"""

import os
from typing import Any, Dict
from config import SENSITIVE_KEYS


def env_truthy(name: str, default: bool = False) -> bool:
    """
    Check if environment variable is truthy.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        
    Returns:
        True if value is '1', 'true', 'yes', 'y', or 'on' (case-insensitive)
    """
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")


def truncate_text(text: Any, limit: int = 2000) -> Any:
    """
    Truncate text to specified limit.
    
    Args:
        text: Text to truncate
        limit: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if not isinstance(text, str):
        return text
    t = text.strip("\n")
    if len(t) <= limit:
        return t
    return t[:limit] + f"…(truncated {len(t) - limit} chars)"


def redact(obj: Any, *, depth: int = 0, max_depth: int = 6) -> Any:
    """
    Recursively redact sensitive information from objects.
    
    Args:
        obj: Object to redact (dict, list, str, etc.)
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        Redacted copy of object
    """
    if depth > max_depth:
        return "<max_depth>"

    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k).lower()
            if ks in SENSITIVE_KEYS:
                out[k] = "[REDACTED]"
                continue
            # Avoid logging huge base64 payloads
            if ks in ("b64_json", "image", "audio") and isinstance(v, str):
                out[k] = f"<omitted len={len(v)}>"
                continue
            out[k] = redact(v, depth=depth + 1, max_depth=max_depth)
        return out

    if isinstance(obj, list):
        return [redact(v, depth=depth + 1, max_depth=max_depth) for v in obj[:50]]

    if isinstance(obj, str):
        # Avoid logging giant data URLs
        if obj.startswith("data:"):
            return f"<data_url len={len(obj)}>"
        return truncate_text(obj, limit=4000)

    return obj


def safe_headers(headers: Any) -> Dict[str, Any]:
    """
    Redact sensitive headers for logging.
    
    Args:
        headers: Headers dict or dict-like object
        
    Returns:
        Sanitized headers dict
    """
    if not isinstance(headers, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, v in headers.items():
        ks = str(k).lower()
        if ks in SENSITIVE_KEYS:
            out[k] = "[REDACTED]"
        else:
            out[k] = truncate_text(str(v), limit=400)
    return out


def extract_text_from_messages(messages: Any) -> str:
    """
    Extract text content from OpenAI-style messages array.
    
    Args:
        messages: List of message dicts
        
    Returns:
        Concatenated text from all messages
    """
    if not isinstance(messages, list):
        return ""
    
    parts = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            if content.strip():
                parts.append(content.strip())
            continue
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    txt = item.get("text").strip()
                    if txt:
                        parts.append(txt)
                elif isinstance(item.get("text"), str):
                    txt = item.get("text").strip()
                    if txt:
                        parts.append(txt)
    return "\n".join(parts).strip()
