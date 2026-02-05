"""
Cost calculation and request tracking utilities.
"""

import os
import csv
import time
from typing import Dict, Any

from config import PRICES_FILE, PENDING_CSV


def load_prices() -> Dict[str, Any]:
    """
    Load pricing data from prices.json file.
    
    Returns:
        Dictionary of model prices
    """
    if not os.path.exists(PRICES_FILE):
        return {}
    import json
    with open(PRICES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def calc_cost_usd(model: str, prompt_tokens: int, completion_tokens: int, prices: Dict[str, Any]) -> float:
    """
    Calculate cost in USD for token usage.
    Supports both legacy (per-1K tokens) and newer (per-1M tokens) pricing formats.
    
    Args:
        model: Model name
        prompt_tokens: Input token count
        completion_tokens: Output token count
        prices: Pricing dictionary from prices.json
        
    Returns:
        Cost in USD
    """
    price = prices.get(model, {})
    
    # Support both legacy (per-1K tokens) and newer (per-1M tokens) formats.
    # - Legacy: {"in": <usd_per_1k>, "out": <usd_per_1k>}
    # - New: {"input_per_1m": <usd_per_1m>, "output_per_1m": <usd_per_1m>}
    if "input_per_1m" in price or "output_per_1m" in price:
        price_in_1m = float(price.get("input_per_1m", 0.0) or 0.0)
        price_out_1m = float(price.get("output_per_1m", 0.0) or 0.0)
        return (prompt_tokens / 1_000_000.0) * price_in_1m + (completion_tokens / 1_000_000.0) * price_out_1m

    price_in = float(price.get("in", 0.0) or 0.0)
    price_out = float(price.get("out", 0.0) or 0.0)
    return (prompt_tokens / 1000.0) * price_in + (completion_tokens / 1000.0) * price_out


def calc_image_cost(model: str, n: int, size: str, quality: str, prices: Dict[str, Any]) -> float:
    """
    Calculate cost for image generation.
    
    Args:
        model: Model name (e.g., "dall-e-3")
        n: Number of images
        size: Image size (e.g., "1024x1024")
        quality: Image quality ("standard" or "hd")
        prices: Pricing dictionary from prices.json
        
    Returns:
        Cost in USD
    """
    model_prices = prices.get(model, {})
    size_prices = model_prices.get(size, {})
    per_image = float(size_prices.get(quality, 0.0) or 0.0)
    return per_image * n


def calc_image_cost_from_body(model: str, body: Dict[str, Any], prices: Dict[str, Any]) -> float:
    """
    Calculate image generation cost from request body.
    Supports both flat per-image pricing and quality/size-based pricing.
    
    Args:
        model: Model name
        body: Request body with n, size, quality
        prices: Pricing dictionary from prices.json
        
    Returns:
        Cost in USD
    """
    price = prices.get(model, {})
    per_image = price.get("per_image_usd")
    
    # Support both:
    # - dict pricing (OpenAI: quality->size->usd or {"flat": usd})
    # - numeric flat per-image pricing (Gemini)
    flat_per_image: float = 0.0
    if isinstance(per_image, (int, float)):
        try:
            flat_per_image = float(per_image)
        except Exception:
            flat_per_image = 0.0
    elif not isinstance(per_image, dict):
        return 0.0

    n = body.get("n", 1)
    try:
        n_int = int(n)
    except Exception:
        n_int = 1
    if n_int <= 0:
        n_int = 1

    if flat_per_image > 0:
        return max(0.0, flat_per_image) * float(n_int)

    size = body.get("size") or "1024x1024"
    if not isinstance(size, str) or "x" not in size:
        size = "1024x1024"

    quality = body.get("quality") or "standard"
    if not isinstance(quality, str):
        quality = "standard"
    quality = str(quality).lower().strip()
    if quality not in ("standard", "hd"):
        quality = "standard"

    q_map = per_image.get(quality)
    if isinstance(q_map, dict):
        try:
            per = float(q_map.get(size, 0.0) or 0.0)
        except Exception:
            per = 0.0
        return max(0.0, per) * float(n_int)

    # Some providers expose flat per-image pricing.
    try:
        per = float(per_image.get("flat", 0.0) or 0.0)
    except Exception:
        per = 0.0
    return max(0.0, per) * float(n_int)


def append_pending(request_id: str, user_id: str):
    """
    Append request to pending.csv for tracking incomplete requests.
    
    Args:
        request_id: Unique request identifier
        user_id: User identifier
    """
    try:
        newfile = not os.path.exists(PENDING_CSV)
        with open(PENDING_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if newfile:
                writer.writerow(["request_id", "user_id", "ts"])
            writer.writerow([request_id, user_id, int(time.time())])
    except Exception:
        pass


def remove_pending(request_id: str):
    """
    Remove request from pending.csv after completion.
    
    Args:
        request_id: Request identifier to remove
    """
    if not os.path.exists(PENDING_CSV):
        return
    temp_path = PENDING_CSV + ".tmp"
    with open(PENDING_CSV, "r", encoding="utf-8") as inp, open(temp_path, "w", encoding="utf-8", newline="") as out:
        reader = csv.reader(inp)
        writer = csv.writer(out)
        rows = list(reader)
        if rows:
            writer.writerow(rows[0])
            for row in rows[1:]:
                if len(row) >= 1 and row[0] != request_id:
                    writer.writerow(row)
    os.replace(temp_path, PENDING_CSV)
