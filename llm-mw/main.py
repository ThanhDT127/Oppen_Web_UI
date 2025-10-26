import os
import json
import threading
import time
import uuid
import datetime as dt
import re
import csv
from typing import Dict, Any, List, Optional

from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="LLM Middleware (Quota+Auth+Stream+Reconcile)", version="3.0")

# Allow calls from local tools/UI. Restrict this in production deployments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
PRICES_FILE = os.path.join(BASE_DIR, "prices.json")
PENDING_CSV = os.path.join(BASE_DIR, "pending.csv")
LITELLM_LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "litellm", "litellm.log"))

_lock = threading.Lock()

LITELLM_BASE = os.getenv("LITELLM_BASE", "http://127.0.0.1:4000/v1")
LITELLM_KEY = os.getenv("LITELLM_KEY", "")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")


def _load_users() -> List[Dict[str, Any]]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _save_users(users: List[Dict[str, Any]]):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _load_prices() -> Dict[str, Any]:
    if not os.path.exists(PRICES_FILE):
        return {}
    with open(PRICES_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


PRICES = _load_prices()


def _find_user(subkey: str) -> Optional[Dict[str, Any]]:
    for u in _load_users():
        if u.get("subkey") == subkey:
            return u
    return None


def _period_anchor_ms(period: str, tz: str) -> int:
    zone = ZoneInfo(tz) if tz else ZoneInfo("UTC")
    now = dt.datetime.now(zone)
    if period == "weekly":
        start = now - dt.timedelta(days=now.weekday())
        start = dt.datetime(start.year, start.month, start.day, tzinfo=zone)
    else:
        start = dt.datetime(now.year, now.month, 1, tzinfo=zone)
    return int(start.timestamp() * 1000)


def _maybe_reset_quota(user: Dict[str, Any]):
    quota = user.setdefault("quota", {})
    period = quota.get("period", "monthly")
    tz = quota.get("timezone", "UTC")
    current_anchor = _period_anchor_ms(period, tz)
    if int(quota.get("period_start", 0)) < current_anchor:
        quota["period_start"] = current_anchor
        quota["used_tokens"] = 0
        quota["used_cost_usd"] = 0.0
        user["used_tokens"] = 0
        user["used_cost_usd"] = 0.0


def _calc_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price = PRICES.get(model, {})
    price_in = float(price.get("in", 0.0))
    price_out = float(price.get("out", 0.0))
    return (prompt_tokens / 1000.0) * price_in + (completion_tokens / 1000.0) * price_out


def _append_pending(request_id: str, user_id: str):
    try:
        newfile = not os.path.exists(PENDING_CSV)
        with open(PENDING_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if newfile:
                writer.writerow(["request_id", "user_id", "ts"])
            writer.writerow([request_id, user_id, int(time.time())])
    except Exception:
        pass


def _remove_pending(request_id: str):
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


def _find_usage_in_litellm_log(request_id: str) -> Optional[Dict[str, Any]]:
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

    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": None}
    hit = False

    for line in lines:
        if request_id in line:
            hit = True
            model_match = model_pattern.search(line)
            if model_match:
                usage["model"] = model_match.group(1)
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


@app.get("/health")
def health():
    return {"ok": True, "time": int(time.time())}


@app.get("/v1/models")
def models():
    available: List[str] = []
    for user in _load_users():
        for model in user.get("allowed_models", []):
            if model != "*":
                available.append(model)
    return {"data": [{"id": m, "object": "model"} for m in sorted(set(available))]}


@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing sub-key")
    subkey = auth.split(" ", 1)[1].strip()
    user = _find_user(subkey)
    if not user or not user.get("active", True):
        raise HTTPException(403, "Invalid or inactive sub-key")

    body = await request.json()
    model = body.get("model")
    if not model:
        raise HTTPException(400, "Missing model")

    allowed_models = user.get("allowed_models", [])
    if allowed_models != ["*"] and model not in allowed_models:
        raise HTTPException(403, f"Model '{model}' not allowed for {user['user_id']}")

    _maybe_reset_quota(user)
    quota = user.get("quota", {})
    limit_tokens = int(quota.get("limit_tokens", 0))
    used_tokens = int(quota.get("used_tokens", 0))
    limit_cost = float(quota.get("limit_cost_usd", 0.0))
    used_cost = float(quota.get("used_cost_usd", 0.0))

    if body.get("max_tokens", 999999) > 512:
        body["max_tokens"] = 512

    request_id = f"mw_{uuid.uuid4().hex}"
    body["user"] = user["user_id"]
    metadata = body.get("metadata") or {}
    metadata["mw_request_id"] = request_id
    body["metadata"] = metadata

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    is_stream = bool(body.get("stream"))

    if is_stream:
        _append_pending(request_id, user["user_id"])

        async def _iter():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{LITELLM_BASE}/chat/completions",
                    headers=headers,
                    json=body,
                ) as resp:
                    if resp.status_code >= 400:
                        error_text = await resp.aread()
                        _remove_pending(request_id)
                        raise HTTPException(resp.status_code, error_text.decode("utf-8", errors="ignore"))
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        return StreamingResponse(_iter(), media_type="text/event-stream")

    limits = httpx.Limits(max_connections=200, max_keepalive_connections=100)
    async with httpx.AsyncClient(timeout=300, limits=limits) as client:
        resp = await client.post(f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
        if resp.status_code >= 400:
            try:
                raise HTTPException(resp.status_code, resp.json())
            except Exception:
                raise HTTPException(resp.status_code, resp.text)
        data = resp.json()

    usage = data.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    cost_usd = _calc_cost_usd(model, prompt_tokens, completion_tokens)

    if limit_tokens > 0 and used_tokens + total_tokens > limit_tokens:
        raise HTTPException(403, f"Token quota exceeded for {user['user_id']} ({used_tokens + total_tokens}/{limit_tokens})")
    if limit_cost > 0 and used_cost + cost_usd > limit_cost + 1e-9:
        raise HTTPException(403, f"Cost quota exceeded for {user['user_id']} (${used_cost + cost_usd:.2f}/${limit_cost:.2f})")

    with _lock:
        users = _load_users()
        for stored_user in users:
            if stored_user.get("user_id") == user["user_id"]:
                _maybe_reset_quota(stored_user)
                quota_info = stored_user.setdefault("quota", {})
                stored_user["used_tokens"] = int(stored_user.get("used_tokens", 0)) + total_tokens
                quota_info["used_tokens"] = int(quota_info.get("used_tokens", 0)) + total_tokens
                quota_info["used_cost_usd"] = float(quota_info.get("used_cost_usd", 0.0)) + cost_usd
                stored_user["used_cost_usd"] = float(stored_user.get("used_cost_usd", 0.0)) + cost_usd
                break
        _save_users(users)

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    data["_mw_added_tokens"] = total_tokens
    data["_mw_added_cost_usd"] = round(cost_usd, 6)

    return JSONResponse(status_code=200, content=data)


@app.get("/admin/usage")
def admin_usage(request: Request):
    if request.headers.get("Authorization", "") != f"Bearer {ADMIN_KEY}":
        raise HTTPException(403, "Invalid admin key")
    return _load_users()


@app.post("/admin/reset")
async def admin_reset(request: Request):
    if request.headers.get("Authorization", "") != f"Bearer {ADMIN_KEY}":
        raise HTTPException(403, "Invalid admin key")
    body = await request.json()
    target_user = body.get("user_id")
    with _lock:
        users = _load_users()
        for stored_user in users:
            if target_user is None or stored_user.get("user_id") == target_user:
                _maybe_reset_quota(stored_user)
        _save_users(users)
    return {"ok": True}


@app.post("/admin/reconcile")
async def admin_reconcile(request: Request):
    if request.headers.get("Authorization", "") != f"Bearer {ADMIN_KEY}":
        raise HTTPException(403, "Invalid admin key")

    body = await request.json()
    request_id = body.get("request_id")
    user_id = body.get("user_id")
    if not request_id or not user_id:
        raise HTTPException(400, "Missing request_id or user_id")

    usage = _find_usage_in_litellm_log(request_id)
    if not usage:
        raise HTTPException(404, f"No usage found in LiteLLM log for request_id={request_id}")

    model = usage.get("model") or body.get("model") or ""
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    cost_usd = _calc_cost_usd(model, prompt_tokens, completion_tokens)

    with _lock:
        users = _load_users()
        for stored_user in users:
            if stored_user.get("user_id") == user_id:
                _maybe_reset_quota(stored_user)
                quota_info = stored_user.setdefault("quota", {})
                stored_user["used_tokens"] = int(stored_user.get("used_tokens", 0)) + total_tokens
                stored_user["used_cost_usd"] = float(stored_user.get("used_cost_usd", 0.0)) + cost_usd
                quota_info["used_tokens"] = int(quota_info.get("used_tokens", 0)) + total_tokens
                quota_info["used_cost_usd"] = float(quota_info.get("used_cost_usd", 0.0)) + cost_usd
                break
        else:
            raise HTTPException(404, f"user_id={user_id} not found")
        _save_users(users)

    _remove_pending(request_id)

    return {
        "ok": True,
        "request_id": request_id,
        "user_id": user_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=False)
