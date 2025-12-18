import os
import json
import threading
import time
import uuid
import datetime as dt
import re
import csv
import asyncio
import logging
import base64
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List, Optional

from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

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

# Prefer a single .env at the repo root (D:\ktlt\Works\oppenwebui2\.env),
# but keep compatibility if someone uses llm-mw/.env.
_env_candidates = [
    os.path.join(BASE_DIR, ".env"),
    os.path.abspath(os.path.join(BASE_DIR, "..", ".env")),
]
for _env_path in _env_candidates:
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        break
else:
    load_dotenv()

USERS_FILE = os.path.join(BASE_DIR, "users.json")
PRICES_FILE = os.path.join(BASE_DIR, "prices.json")
PENDING_CSV = os.path.join(BASE_DIR, "pending.csv")
LITELLM_LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "litellm", "litellm.log"))

LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
MW_LOG_FILE = os.path.join(LOG_DIR, "middleware.log")
MW_DETAIL_LOG_FILE = os.path.join(LOG_DIR, "middleware.requests.log")

MW_MEDIA_DIR = os.path.join(LOG_DIR, "mw_media")
os.makedirs(MW_MEDIA_DIR, exist_ok=True)

logger = logging.getLogger("llm_mw")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = RotatingFileHandler(MW_LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_h)

detail_logger = logging.getLogger("llm_mw_detail")
if not detail_logger.handlers:
    detail_logger.setLevel(logging.INFO)
    _dh = RotatingFileHandler(MW_DETAIL_LOG_FILE, maxBytes=20_000_000, backupCount=5, encoding="utf-8")
    _dh.setFormatter(logging.Formatter("%(message)s"))
    detail_logger.addHandler(_dh)

_lock = threading.Lock()

LITELLM_BASE = os.getenv("LITELLM_BASE", "http://127.0.0.1:4000/v1")
LITELLM_KEY = os.getenv("LITELLM_KEY", "")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")


def _env_truthy(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")


_RESTRICTED_MODELS = {"gpt-image-1", "sora-2", "sora-2-pro"}


_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "token",
    "secret",
    "password",
    "openai_api_key",
    "gemini_api_key",
    "litellm_key",
}


def _truncate_text(text: Any, limit: int = 2000) -> Any:
    if not isinstance(text, str):
        return text
    t = text.strip("\n")
    if len(t) <= limit:
        return t
    return t[:limit] + f"…(truncated {len(t) - limit} chars)"


def _redact(obj: Any, *, depth: int = 0, max_depth: int = 6) -> Any:
    if depth > max_depth:
        return "<max_depth>"

    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k).lower()
            if ks in _SENSITIVE_KEYS:
                out[k] = "[REDACTED]"
                continue
            # Avoid logging huge base64 payloads.
            if ks in ("b64_json", "image", "audio") and isinstance(v, str):
                out[k] = f"<omitted len={len(v)}>"
                continue
            out[k] = _redact(v, depth=depth + 1, max_depth=max_depth)
        return out

    if isinstance(obj, list):
        return [_redact(v, depth=depth + 1, max_depth=max_depth) for v in obj[:50]]

    if isinstance(obj, str):
        # Avoid logging giant data URLs.
        if obj.startswith("data:"):
            return f"<data_url len={len(obj)}>"
        return _truncate_text(obj, limit=4000)

    return obj


def _safe_headers(headers: Any) -> Dict[str, Any]:
    if not isinstance(headers, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, v in headers.items():
        ks = str(k).lower()
        if ks in _SENSITIVE_KEYS:
            out[k] = "[REDACTED]"
        else:
            out[k] = _truncate_text(str(v), limit=400)
    return out


def _detail(event: str, *, request: Optional[Request] = None, rid: Optional[str] = None, user_id: Optional[str] = None, **fields: Any):
    if not _env_truthy("MW_DETAILED_LOG", default=True):
        return
    try:
        payload: Dict[str, Any] = {
            "ts": dt.datetime.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
            "event": event,
        }
        if request is not None:
            payload.update(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "client": getattr(request.client, "host", None),
                }
            )
        rid_val = rid or (getattr(request.state, "mw_request_id", None) if request is not None else None)
        if rid_val:
            payload["rid"] = rid_val
        uid_val = user_id or (getattr(request.state, "mw_user_id", None) if request is not None else None)
        if uid_val:
            payload["user"] = uid_val

        for k, v in fields.items():
            payload[k] = _redact(v)

        detail_logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        # Never break API behavior due to logging failures.
        return


def _mime_to_ext(mime: str) -> str:
    m = (mime or "").lower().strip()
    if m == "image/png":
        return "png"
    if m in ("image/jpeg", "image/jpg"):
        return "jpg"
    if m == "image/webp":
        return "webp"
    if m == "image/gif":
        return "gif"
    return "bin"


def _save_bytes_to_media(data: bytes, *, mime: str) -> str:
    ext = _mime_to_ext(mime)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(MW_MEDIA_DIR, name)
    with open(path, "wb") as f:
        f.write(data)
    return name


def _public_media_url(request: Request, name: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/v1/_mw/media/{name}"


def _maybe_materialize_image_url(request: Request, *, url: str, fallback_mime: str = "image/png") -> str:
    if not isinstance(url, str) or not url:
        return url
    if not url.startswith("data:"):
        return url

    # Format: data:<mime>;base64,<b64>
    try:
        header, b64 = url.split(",", 1)
        mime = fallback_mime
        m = re.match(r"^data:([^;]+);base64$", header)
        if m:
            mime = m.group(1)
        raw = base64.b64decode(b64)
        name = _save_bytes_to_media(raw, mime=mime)
        return _public_media_url(request, name)
    except Exception:
        return url


def _maybe_materialize_image_items(request: Request, items: Any, *, fallback_mime: str = "image/png"):
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        b64 = item.get("b64_json")

        if isinstance(url, str) and url.startswith("data:"):
            item["url"] = _maybe_materialize_image_url(request, url=url, fallback_mime=fallback_mime)
            continue

        if b64 and (not url):
            try:
                raw = base64.b64decode(b64)
                name = _save_bytes_to_media(raw, mime=fallback_mime)
                item["url"] = _public_media_url(request, name)
            except Exception:
                # Leave as-is; callers may still use b64_json.
                pass


@app.get("/v1/_mw/media/{name}")
async def mw_media_get(name: str):
    # Constrain to our generated filenames.
    if not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg|jpeg|webp|gif|bin)", name, flags=re.IGNORECASE):
        raise HTTPException(404, "Not found")
    path = os.path.join(MW_MEDIA_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")

    ext = name.rsplit(".", 1)[-1].lower()
    mime = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type=mime, headers={"Cache-Control": "public, max-age=31536000"})


def _is_image_model(model: Optional[str]) -> bool:
    if not isinstance(model, str) or not model:
        return False
    # Keep this conservative: only treat obvious image models as image generators.
    if model in ("gpt-image-1", "gemini-2.5-flash-image"):
        return True
    return "-image" in model or model.endswith("image")


def _extract_text_prompt_from_messages(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""

    parts: List[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
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


@app.on_event("startup")
async def _startup_http_client():
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=100)
    timeout = httpx.Timeout(300.0, connect=10.0)
    app.state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
    logger.info("startup http_client created")


@app.on_event("shutdown")
async def _shutdown_http_client():
    client = getattr(app.state, "http_client", None)
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass
    logger.info("shutdown http_client closed")


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    status_code: int = 500
    _detail("inbound", request=request)
    try:
        response = await call_next(request)
        status_code = getattr(response, "status_code", 200)
        return response
    except Exception:
        raise
    finally:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        rid = getattr(request.state, "mw_request_id", None) or request.headers.get("X-Request-ID") or "-"
        logger.info(
            "req rid=%s method=%s path=%s status=%s ms=%.1f",
            rid,
            request.method,
            request.url.path,
            status_code,
            dt_ms,
        )
        _detail("outbound", request=request, status=status_code, ms=round(dt_ms, 1))


def _require_user(request: Request) -> Dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing sub-key")
    subkey = auth.split(" ", 1)[1].strip()
    user = _find_user(subkey)
    if not user or not user.get("active", True):
        raise HTTPException(403, "Invalid or inactive sub-key")
    request.state.mw_user_id = user.get("user_id")
    return user


def _assert_model_allowed(user: Dict[str, Any], model: str):
    allowed_models = user.get("allowed_models", [])
    if allowed_models != ["*"] and model not in allowed_models:
        raise HTTPException(403, f"Model '{model}' not allowed for {user['user_id']}")


def _get_litellm_cost_from_headers(headers: httpx.Headers) -> float:
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


def _enforce_and_bump_task_quota(
    user_id: str,
    *,
    apply: bool = True,
    add_image_requests: int = 0,
    add_tts_requests: int = 0,
    add_tts_chars: int = 0,
    add_stt_requests: int = 0,
    add_video_requests: int = 0,
    add_video_seconds: float = 0.0,
    add_tokens: int = 0,
    add_cost_usd: float = 0.0,
):
    with _lock:
        users = _load_users()
        for stored_user in users:
            if stored_user.get("user_id") != user_id:
                continue

            _maybe_reset_quota(stored_user)
            quota = stored_user.setdefault("quota", {})

            def _enforce_limit(limit_key: str, used_key: str, add_value: float, label: str):
                limit_val = float(quota.get(limit_key, 0) or 0)
                if limit_val <= 0:
                    return
                used_val = float(quota.get(used_key, 0) or 0)
                if used_val + add_value > limit_val + 1e-9:
                    raise HTTPException(
                        403,
                        f"{label} quota exceeded for {stored_user['user_id']} ({used_val + add_value}/{limit_val})",
                    )

            # Enforce task-specific quotas (best-effort; costs may be unknown until after provider call).
            if add_image_requests:
                _enforce_limit("limit_image_requests", "used_image_requests", float(add_image_requests), "Image requests")
            if add_tts_requests:
                _enforce_limit("limit_tts_requests", "used_tts_requests", float(add_tts_requests), "TTS requests")
            if add_tts_chars:
                _enforce_limit("limit_tts_chars", "used_tts_chars", float(add_tts_chars), "TTS characters")
            if add_stt_requests:
                _enforce_limit("limit_stt_requests", "used_stt_requests", float(add_stt_requests), "STT requests")
            if add_video_requests:
                _enforce_limit("limit_video_requests", "used_video_requests", float(add_video_requests), "Video requests")
            if add_video_seconds:
                _enforce_limit("limit_video_seconds", "used_video_seconds", float(add_video_seconds), "Video seconds")

            # Existing token/cost quotas.
            if add_tokens:
                _enforce_limit("limit_tokens", "used_tokens", float(add_tokens), "Token")
            if add_cost_usd:
                _enforce_limit("limit_cost_usd", "used_cost_usd", float(add_cost_usd), "Cost USD")

            if not apply:
                return

            # Apply increments.
            if add_image_requests:
                quota["used_image_requests"] = int(quota.get("used_image_requests", 0) or 0) + int(add_image_requests)
            if add_tts_requests:
                quota["used_tts_requests"] = int(quota.get("used_tts_requests", 0) or 0) + int(add_tts_requests)
            if add_tts_chars:
                quota["used_tts_chars"] = int(quota.get("used_tts_chars", 0) or 0) + int(add_tts_chars)
            if add_stt_requests:
                quota["used_stt_requests"] = int(quota.get("used_stt_requests", 0) or 0) + int(add_stt_requests)
            if add_video_requests:
                quota["used_video_requests"] = int(quota.get("used_video_requests", 0) or 0) + int(add_video_requests)
            if add_video_seconds:
                quota["used_video_seconds"] = float(quota.get("used_video_seconds", 0.0) or 0.0) + float(add_video_seconds)

            if add_tokens:
                stored_user["used_tokens"] = int(stored_user.get("used_tokens", 0) or 0) + int(add_tokens)
                quota["used_tokens"] = int(quota.get("used_tokens", 0) or 0) + int(add_tokens)
            if add_cost_usd:
                stored_user["used_cost_usd"] = float(stored_user.get("used_cost_usd", 0.0) or 0.0) + float(add_cost_usd)
                quota["used_cost_usd"] = float(quota.get("used_cost_usd", 0.0) or 0.0) + float(add_cost_usd)

            _save_users(users)
            return

        raise HTTPException(404, f"user_id={user_id} not found")


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


def _calc_image_cost_usd(model: str, body: Dict[str, Any]) -> float:
    price = PRICES.get(model, {})
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

    quality = body.get("quality") or "medium"
    if not isinstance(quality, str):
        quality = "medium"
    quality = quality.lower().strip()
    if quality not in ("low", "medium", "high"):
        quality = "medium"

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


def _calc_tts_cost_usd(model: str, text_in: Any) -> float:
    price = PRICES.get(model, {})
    chars = len(text_in) if isinstance(text_in, str) else 0
    if chars <= 0:
        return 0.0

    # Prefer chars-based pricing for fallback, since we can compute it deterministically.
    try:
        per_1m_chars = float(price.get("tts_usd_per_1m_chars", 0.0) or 0.0)
    except Exception:
        per_1m_chars = 0.0
    if per_1m_chars <= 0:
        return 0.0
    return (chars / 1_000_000.0) * per_1m_chars


def _calc_video_cost_usd(model: str, seconds: float, body: Dict[str, Any]) -> float:
    if seconds <= 0:
        return 0.0
    price = PRICES.get(model, {})

    size = body.get("size") or body.get("resolution")
    if isinstance(size, str):
        size = size.strip()
    else:
        size = None

    # Optional size overrides (e.g. sora-2-pro at higher resolution)
    by_size = price.get("video_usd_per_second_by_size")
    if size and isinstance(by_size, dict) and size in by_size:
        try:
            per_sec = float(by_size.get(size, 0.0) or 0.0)
        except Exception:
            per_sec = 0.0
        return max(0.0, per_sec) * seconds

    try:
        per_sec = float(price.get("video_usd_per_second", 0.0) or 0.0)
    except Exception:
        per_sec = 0.0
    return max(0.0, per_sec) * seconds


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
        quota["used_image_requests"] = 0
        quota["used_tts_requests"] = 0
        quota["used_tts_chars"] = 0
        quota["used_stt_requests"] = 0
        quota["used_video_requests"] = 0
        quota["used_video_seconds"] = 0.0
        user["used_tokens"] = 0
        user["used_cost_usd"] = 0.0


def _calc_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price = PRICES.get(model, {})
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


@app.get("/health")
def health():
    return {"ok": True, "time": int(time.time())}


@app.get("/v1/models")
async def models(request: Request):
    """List available models from LiteLLM"""
    try:
        client: httpx.AsyncClient = request.app.state.http_client
        resp = await client.get(
            f"{LITELLM_BASE}/models",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            payload = resp.json() or {}
            if not _env_truthy("MW_EXPOSE_RESTRICTED_MODELS", default=False):
                data = payload.get("data")
                if isinstance(data, list):
                    filtered = []
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        mid = item.get("id") or item.get("model") or item.get("name")
                        if isinstance(mid, str) and mid in _RESTRICTED_MODELS:
                            continue
                        filtered.append(item)
                    payload["data"] = filtered
            return payload
        return {"data": []}
    except Exception:
        # Fallback to empty list if LiteLLM is down
        return {"data": []}


@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    user = _require_user(request)

    body = await request.json()
    model = body.get("model")
    if not model:
        raise HTTPException(400, "Missing model")

    prompt_preview = _extract_text_prompt_from_messages(body.get("messages"))
    _detail(
        "chat.request",
        request=request,
        user_id=user.get("user_id"),
        model=model,
        stream=bool(body.get("stream")),
        prompt=_truncate_text(prompt_preview, limit=2000),
        body=body,
    )

    # OpenWebUI sometimes routes image generation through chat/completions.
    # To keep the UI functional, detect image models here and translate to an
    # image generation call, returning a chat response containing a Markdown image.
    if _is_image_model(model):
        prompt = _extract_text_prompt_from_messages(body.get("messages"))
        if not prompt:
            prompt = body.get("prompt") if isinstance(body.get("prompt"), str) else ""
        if not prompt:
            raise HTTPException(400, "Missing prompt/messages for image generation")

        request_id = f"mw_{uuid.uuid4().hex}"
        request.state.mw_request_id = request_id

        # Enforce count quotas before provider call (do not charge unless call succeeds).
        _maybe_reset_quota(user)
        _enforce_and_bump_task_quota(user["user_id"], apply=False, add_image_requests=1)

        actual_model = model
        _assert_model_allowed(user, actual_model)
        forward_body = {
            "model": actual_model,
            "prompt": prompt,
            "n": int(body.get("n", 1) or 1),
            "size": body.get("size"),
            "quality": body.get("quality"),
            "background": body.get("background"),
            "output_format": body.get("output_format"),
        }

        headers = {
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        }

        # Drop None values (some providers reject unknown/null params)
        forward_body = {k: v for k, v in forward_body.items() if v is not None}

        def _looks_like_org_verification_error(text: str) -> bool:
            t = (text or "").lower()
            return "organization must be verified" in t or "verify organization" in t

        client: httpx.AsyncClient = request.app.state.http_client
        try:
            _detail(
                "upstream.request",
                request=request,
                rid=request_id,
                user_id=user.get("user_id"),
                upstream=f"{LITELLM_BASE}/images/generations",
                method="POST",
                headers=_safe_headers(headers),
                body=forward_body,
            )
            resp = await client.post(f"{LITELLM_BASE}/images/generations", headers=headers, json=forward_body, timeout=600)
        except httpx.RequestError as e:
            _detail(
                "upstream.error",
                request=request,
                rid=request_id,
                user_id=user.get("user_id"),
                upstream=f"{LITELLM_BASE}/images/generations",
                error=f"{e.__class__.__name__}",
            )
            raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")
        if resp.status_code >= 400 and actual_model == "gpt-image-1":
            # Fallback to Gemini if OpenAI image access is restricted.
            error_text = ""
            try:
                error_text = json.dumps(resp.json())
            except Exception:
                try:
                    error_text = resp.text
                except Exception:
                    error_text = ""

            if _looks_like_org_verification_error(error_text):
                actual_model = "gemini-2.5-flash-image"
                _assert_model_allowed(user, actual_model)
                forward_body["model"] = actual_model
                try:
                    resp = await client.post(f"{LITELLM_BASE}/images/generations", headers=headers, json=forward_body, timeout=600)
                except httpx.RequestError as e:
                    raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")

        if resp.status_code >= 400:
            try:
                raise HTTPException(resp.status_code, resp.json())
            except Exception:
                raise HTTPException(resp.status_code, resp.text)

        data = resp.json() or {}

        _detail(
            "upstream.response",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            status=resp.status_code,
            headers=dict(resp.headers),
            body=data,
        )

        # Materialize image outputs into HTTP URLs that OpenWebUI can render.
        try:
            output_format = (data.get("output_format") or forward_body.get("output_format") or "png").lower()
            mime = "image/png" if output_format in ("png", "") else f"image/{output_format}"
            items = data.get("data")
            _maybe_materialize_image_items(request, items, fallback_mime=mime)
        except Exception:
            pass

        litellm_cost = _get_litellm_cost_from_headers(resp.headers)
        _enforce_and_bump_task_quota(user["user_id"], add_image_requests=1)
        cost_usd = litellm_cost if litellm_cost > 0 else _calc_image_cost_usd(actual_model, forward_body)
        if cost_usd > 0:
            _enforce_and_bump_task_quota(user["user_id"], add_cost_usd=cost_usd)

        url = ""
        try:
            items = data.get("data")
            if isinstance(items, list) and items and isinstance(items[0], dict):
                url = items[0].get("url") or ""
        except Exception:
            url = ""
        if not url:
            raise HTTPException(502, "Image generated but no URL/b64 returned")

        markdown = f"![image]({url})"
        created = int(time.time())
        chat_id = f"chatcmpl_{uuid.uuid4().hex}"

        _detail(
            "chat.image.result",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            model=actual_model,
            image_url=url,
            markdown=_truncate_text(markdown, limit=500),
        )

        # OpenWebUI often streams chat; for image shims, a non-stream response is more reliable
        # (large payloads + markdown/image rendering can be flaky in SSE).
        if bool(body.get("stream")):
            async def _iter_sse():
                # Match OpenAI streaming style: role first, then content.
                chunk_role = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": actual_model,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
                yield ("data: " + json.dumps(chunk_role) + "\n\n").encode("utf-8")

                chunk_content = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": actual_model,
                    "choices": [{"index": 0, "delta": {"content": markdown}, "finish_reason": None}],
                }
                yield ("data: " + json.dumps(chunk_content) + "\n\n").encode("utf-8")

                chunk2 = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": actual_model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield ("data: " + json.dumps(chunk2) + "\n\n").encode("utf-8")
                yield b"data: [DONE]\n\n"

            return StreamingResponse(
                _iter_sse(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "X-Request-ID": request_id,
                },
            )

        payload = {
            "id": chat_id,
            "object": "chat.completion",
            "created": created,
            "model": actual_model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": markdown}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "_mw_user": user["user_id"],
            "_mw_request_id": request_id,
        }
        if cost_usd > 0:
            payload["_mw_added_cost_usd"] = round(cost_usd, 6)
        return JSONResponse(status_code=200, content=payload)

    _assert_model_allowed(user, model)

    _maybe_reset_quota(user)
    quota = user.get("quota", {})
    limit_tokens = int(quota.get("limit_tokens", 0))
    used_tokens = int(quota.get("used_tokens", 0))
    limit_cost = float(quota.get("limit_cost_usd", 0.0))
    used_cost = float(quota.get("used_cost_usd", 0.0))

    # OpenAI's newest reasoning-first models may treat `max_tokens` differently.
    # When users chat via OpenWebUI, it often sends `max_tokens`.
    # For gpt-5*, translate to `max_completion_tokens` to avoid responses that spend all tokens
    # on reasoning and return empty visible content.
    if isinstance(model, str) and model.startswith("gpt-5"):
        if "max_tokens" in body and "max_completion_tokens" not in body:
            body["max_completion_tokens"] = body.get("max_tokens")
            body.pop("max_tokens", None)

    # Clamp output token budget to keep latency/cost predictable.
    token_limit_key = "max_completion_tokens" if "max_completion_tokens" in body else "max_tokens"

    # gpt-5 often spends tokens on reasoning first; if the budget is too low, it can return
    # empty visible content (OpenWebUI looks like it "stops"). Use a safe floor.
    if isinstance(model, str) and model.startswith("gpt-5"):
        try:
            current = int(body.get(token_limit_key, 0) or 0)
        except Exception:
            current = 0
        if current < 10000:
            body[token_limit_key] = 10000

    if body.get(token_limit_key, 100009) > 10000:
        body[token_limit_key] = 10000

    request_id = f"mw_{uuid.uuid4().hex}"
    request.state.mw_request_id = request_id
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

        # Important: like TTS, don't create the upstream stream inside an `async with` that
        # exits before StreamingResponse iterates. We open the stream first, validate status,
        # then stream bytes and always clean up.
        logger.info("stream_start rid=%s model=%s", request_id, model)

        client = httpx.AsyncClient(timeout=600)
        _detail(
            "upstream.request",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            upstream=f"{LITELLM_BASE}/chat/completions",
            method="POST",
            headers=_safe_headers(headers),
            body=body,
        )
        req = client.build_request("POST", f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
        resp = await client.send(req, stream=True)

        if resp.status_code >= 400:
            try:
                error_bytes = await resp.aread()
            finally:
                _remove_pending(request_id)
                try:
                    await resp.aclose()
                finally:
                    await client.aclose()
            error_text = error_bytes.decode("utf-8", errors="ignore")
            logger.warning("stream_error rid=%s status=%s body=%s", request_id, resp.status_code, error_text[:500])
            raise HTTPException(resp.status_code, error_text)

        async def _iter_bytes():
            sampled: bytearray = bytearray()
            try:
                async for chunk in resp.aiter_bytes():
                    if len(sampled) < 8192:
                        sampled.extend(chunk[: max(0, 8192 - len(sampled))])
                    yield chunk
            except (httpx.StreamClosed, httpx.RemoteProtocolError, asyncio.CancelledError):
                return
            finally:
                _remove_pending(request_id)
                try:
                    await resp.aclose()
                finally:
                    await client.aclose()
                logger.info("stream_end rid=%s", request_id)
                if sampled:
                    _detail(
                        "chat.stream.sample",
                        request=request,
                        rid=request_id,
                        user_id=user.get("user_id"),
                        sample_bytes=len(sampled),
                        sample=_truncate_text(sampled.decode("utf-8", errors="ignore"), limit=4000),
                    )

        return StreamingResponse(
            _iter_bytes(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Request-ID": request_id,
            },
        )

    client: httpx.AsyncClient = request.app.state.http_client
    _detail(
        "upstream.request",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        upstream=f"{LITELLM_BASE}/chat/completions",
        method="POST",
        headers=_safe_headers(headers),
        body=body,
    )
    resp = await client.post(f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
    if resp.status_code >= 400:
        try:
            raise HTTPException(resp.status_code, resp.json())
        except Exception:
            raise HTTPException(resp.status_code, resp.text)
    data = resp.json()
    try:
        content_preview = (((data.get("choices") or [{}])[0].get("message") or {}).get("content"))
    except Exception:
        content_preview = None
    _detail(
        "chat.response",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        status=resp.status_code,
        model=model,
        content=_truncate_text(content_preview, limit=2000),
        usage=data.get("usage"),
    )
    litellm_cost = _get_litellm_cost_from_headers(resp.headers)

    usage = data.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    cost_usd = litellm_cost if litellm_cost > 0 else _calc_cost_usd(model, prompt_tokens, completion_tokens)

    if limit_tokens > 0 and used_tokens + total_tokens > limit_tokens:
        raise HTTPException(403, f"Token quota exceeded for {user['user_id']} ({used_tokens + total_tokens}/{limit_tokens})")
    if limit_cost > 0 and used_cost + cost_usd > limit_cost + 1e-9:
        raise HTTPException(403, f"Cost quota exceeded for {user['user_id']} (${used_cost + cost_usd:.2f}/${limit_cost:.2f})")

    _enforce_and_bump_task_quota(user["user_id"], add_tokens=total_tokens, add_cost_usd=cost_usd)

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    data["_mw_added_tokens"] = total_tokens
    data["_mw_added_cost_usd"] = round(cost_usd, 6)

    return JSONResponse(status_code=200, content=data)


@app.post("/v1/images/generations")
async def images_generations(request: Request):
    user = _require_user(request)
    body = await request.json()
    # Default to Gemini image model to avoid OpenAI org-verification restrictions in many accounts.
    model = body.get("model") or "gemini-2.5-flash-image"
    _assert_model_allowed(user, model)

    _detail(
        "images.request",
        request=request,
        user_id=user.get("user_id"),
        model=model,
        prompt=_truncate_text(body.get("prompt"), limit=2000),
        body=body,
    )

    _maybe_reset_quota(user)
    request_id = f"mw_{uuid.uuid4().hex}"
    request.state.mw_request_id = request_id
    body["user"] = user["user_id"]
    metadata = body.get("metadata") or {}
    metadata["mw_request_id"] = request_id
    body["metadata"] = metadata

    # Enforce count quotas before calling provider (do not charge unless call succeeds).
    _enforce_and_bump_task_quota(user["user_id"], apply=False, add_image_requests=1)

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    # Some providers/models reject certain OpenAI-style params. Keep the middleware permissive
    # but drop params that LiteLLM flags as unsupported for specific models.
    forward_body = dict(body)
    if isinstance(model, str) and model.startswith("gpt-image-1"):
        forward_body.pop("response_format", None)
    # Gemini image models reject the OpenAI `user` parameter.
    if isinstance(model, str) and model.startswith("gemini-"):
        forward_body.pop("user", None)
        forward_body.pop("metadata", None)

    def _looks_like_org_verification_error(text: str) -> bool:
        t = (text or "").lower()
        return "organization must be verified" in t or "verify organization" in t

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        _detail(
            "upstream.request",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            upstream=f"{LITELLM_BASE}/images/generations",
            method="POST",
            headers=_safe_headers(headers),
            body=forward_body,
        )
        resp = await client.post(f"{LITELLM_BASE}/images/generations", headers=headers, json=forward_body, timeout=600)
    except httpx.RequestError as e:
        _detail(
            "upstream.error",
            request=request,
            rid=request_id,
            user_id=user.get("user_id"),
            upstream=f"{LITELLM_BASE}/images/generations",
            error=f"{e.__class__.__name__}",
        )
        raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")
    if resp.status_code >= 400 and isinstance(model, str) and model == "gpt-image-1":
        # If OpenAI image access is restricted, transparently fall back to Gemini.
        error_text = ""
        try:
            error_text = json.dumps(resp.json())
        except Exception:
            try:
                error_text = resp.text
            except Exception:
                error_text = ""

        if _looks_like_org_verification_error(error_text):
            fallback_model = "gemini-2.5-flash-image"
            _assert_model_allowed(user, fallback_model)
            model = fallback_model
            forward_body["model"] = fallback_model
            # Gemini image models reject the OpenAI `user` parameter.
            forward_body.pop("user", None)
            forward_body.pop("metadata", None)
            try:
                resp = await client.post(f"{LITELLM_BASE}/images/generations", headers=headers, json=forward_body, timeout=600)
            except httpx.RequestError as e:
                raise HTTPException(503, f"Upstream LiteLLM unavailable: {e.__class__.__name__}")

    if resp.status_code >= 400:
        try:
            raise HTTPException(resp.status_code, resp.json())
        except Exception:
            raise HTTPException(resp.status_code, resp.text)
    data = resp.json()

    _detail(
        "upstream.response",
        request=request,
        rid=request_id,
        user_id=user.get("user_id"),
        status=resp.status_code,
        headers=dict(resp.headers),
        body=data,
    )

    # Help UIs that only know how to render image URLs by synthesizing a data URL
    # when the provider returns only base64.
    try:
        output_format = (data.get("output_format") or body.get("output_format") or "png").lower()
        mime = "image/png" if output_format in ("png", "") else f"image/{output_format}"
        items = data.get("data")
        _maybe_materialize_image_items(request, items, fallback_mime=mime)
    except Exception:
        pass
    litellm_cost = _get_litellm_cost_from_headers(resp.headers)

    _enforce_and_bump_task_quota(user["user_id"], add_image_requests=1)

    cost_usd = litellm_cost if litellm_cost > 0 else _calc_image_cost_usd(model, body)
    if cost_usd > 0:
        _enforce_and_bump_task_quota(user["user_id"], add_cost_usd=cost_usd)

    data["_mw_user"] = user["user_id"]
    data["_mw_request_id"] = request_id
    if cost_usd > 0:
        data["_mw_added_cost_usd"] = round(cost_usd, 6)
    return JSONResponse(status_code=200, content=data)


@app.post("/v1/audio/speech")
async def audio_speech(request: Request):
    user = _require_user(request)
    body = await request.json()
    model = body.get("model") or "gpt-4o-mini-tts"
    _assert_model_allowed(user, model)

    text_in = body.get("input")
    add_chars = len(text_in) if isinstance(text_in, str) else 0

    # Enforce request/char quotas before provider call (do not charge unless call succeeds).
    _enforce_and_bump_task_quota(user["user_id"], apply=False, add_tts_requests=1, add_tts_chars=add_chars)

    request_id = f"mw_{uuid.uuid4().hex}"
    request.state.mw_request_id = request_id
    body["user"] = user["user_id"]
    metadata = body.get("metadata") or {}
    metadata["mw_request_id"] = request_id
    body["metadata"] = metadata

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    # Important: don't use `async with client.stream(...) as resp: return StreamingResponse(...)`
    # because returning inside the context manager will close the upstream stream before the
    # StreamingResponse iterator runs.
    client = httpx.AsyncClient(timeout=600)
    req = client.build_request("POST", f"{LITELLM_BASE}/audio/speech", headers=headers, json=body)
    resp = await client.send(req, stream=True)

    if resp.status_code >= 400:
        try:
            error_bytes = await resp.aread()
        finally:
            await resp.aclose()
            await client.aclose()
        error_text = error_bytes.decode("utf-8", errors="ignore")
        raise HTTPException(resp.status_code, error_text)

    _enforce_and_bump_task_quota(user["user_id"], add_tts_requests=1, add_tts_chars=add_chars)

    litellm_cost = _get_litellm_cost_from_headers(resp.headers)
    cost_usd = litellm_cost if litellm_cost > 0 else _calc_tts_cost_usd(model, text_in)
    if cost_usd > 0:
        _enforce_and_bump_task_quota(user["user_id"], add_cost_usd=cost_usd)

    media_type = resp.headers.get("content-type") or "application/octet-stream"

    async def _iter_bytes():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        except (httpx.StreamClosed, httpx.RemoteProtocolError, asyncio.CancelledError):
            return
        except Exception:
            return
        finally:
            try:
                await resp.aclose()
            finally:
                await client.aclose()

    return StreamingResponse(_iter_bytes(), media_type=media_type)


@app.post("/v1/audio/transcriptions")
async def audio_transcriptions(request: Request):
    user = _require_user(request)
    form = await request.form()

    file_obj = form.get("file")
    if not file_obj:
        raise HTTPException(400, "Missing 'file' in multipart form")

    model = form.get("model") or "gpt-4o-mini-transcribe"
    _assert_model_allowed(user, str(model))

    # Enforce request quotas before provider call (do not charge unless call succeeds).
    _enforce_and_bump_task_quota(user["user_id"], apply=False, add_stt_requests=1)

    request_id = f"mw_{uuid.uuid4().hex}"
    request.state.mw_request_id = request_id

    # Build multipart
    filename = getattr(file_obj, "filename", "audio")
    content_type = getattr(file_obj, "content_type", None) or "application/octet-stream"
    file_bytes = await file_obj.read()
    files = {"file": (filename, file_bytes, content_type)}

    data = {}
    for key in form.keys():
        if key == "file":
            continue
        val = form.get(key)
        if val is None:
            continue
        data[key] = str(val)

    # Attach OpenAI-compatible user + metadata in a best-effort way.
    data.setdefault("user", user["user_id"])
    # 'metadata' isn't standard on this endpoint, but LiteLLM may accept it.
    if "metadata" not in data:
        data["metadata"] = json.dumps({"mw_request_id": request_id})

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "X-Request-ID": request_id,
    }

    client: httpx.AsyncClient = request.app.state.http_client
    resp = await client.post(f"{LITELLM_BASE}/audio/transcriptions", headers=headers, data=data, files=files, timeout=600)
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    out = resp.json()
    litellm_cost = _get_litellm_cost_from_headers(resp.headers)

    _enforce_and_bump_task_quota(user["user_id"], add_stt_requests=1)

    # STT fallback (minutes) is hard to compute from raw audio here; only charge cost if LiteLLM provides it.
    if litellm_cost > 0:
        _enforce_and_bump_task_quota(user["user_id"], add_cost_usd=litellm_cost)

    out["_mw_user"] = user["user_id"]
    out["_mw_request_id"] = request_id
    if litellm_cost > 0:
        out["_mw_added_cost_usd"] = round(litellm_cost, 6)
    return JSONResponse(status_code=200, content=out)


@app.post("/v1/video/generations")
async def video_generations(request: Request):
    user = _require_user(request)
    body = await request.json()
    model = body.get("model") or "sora-2"
    _assert_model_allowed(user, model)

    duration_seconds = body.get("seconds") or body.get("duration_seconds") or body.get("duration")
    add_seconds = 0.0
    try:
        if duration_seconds is not None:
            add_seconds = float(duration_seconds)
    except Exception:
        add_seconds = 0.0

    # Enforce request/seconds quotas before provider call (do not charge unless call succeeds).
    _enforce_and_bump_task_quota(
        user["user_id"],
        apply=False,
        add_video_requests=1,
        add_video_seconds=add_seconds,
    )

    request_id = f"mw_{uuid.uuid4().hex}"
    request.state.mw_request_id = request_id

    # OpenAI videos endpoint doesn't accept the `user` field (unlike chat). Keep tracking via header.
    forward_body = dict(body)
    forward_body.pop("user", None)
    # Be conservative here: metadata is not consistently supported on video endpoints.
    forward_body.pop("metadata", None)

    # Normalize duration fields for OpenAI/LiteLLM: use `seconds`.
    # Clients may send `duration_seconds` or `duration`.
    if add_seconds > 0:
        seconds_val: Any = add_seconds
        try:
            if isinstance(add_seconds, float) and abs(add_seconds - round(add_seconds)) < 1e-9:
                seconds_val = str(int(round(add_seconds)))
            elif isinstance(add_seconds, (int,)):
                seconds_val = str(int(add_seconds))
        except Exception:
            pass
        forward_body.setdefault("seconds", seconds_val)
    forward_body.pop("duration_seconds", None)
    forward_body.pop("duration", None)

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    client: httpx.AsyncClient = request.app.state.http_client
    # LiteLLM exposes OpenAI-style video endpoints under `/videos`.
    resp = await client.post(f"{LITELLM_BASE}/videos", headers=headers, json=forward_body, timeout=900)
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    out = resp.json()
    litellm_cost = _get_litellm_cost_from_headers(resp.headers)

    _enforce_and_bump_task_quota(user["user_id"], add_video_requests=1, add_video_seconds=add_seconds)

    cost_usd = litellm_cost if litellm_cost > 0 else _calc_video_cost_usd(model, add_seconds, body)
    if cost_usd > 0:
        _enforce_and_bump_task_quota(user["user_id"], add_cost_usd=cost_usd)

    out["_mw_user"] = user["user_id"]
    out["_mw_request_id"] = request_id
    if cost_usd > 0:
        out["_mw_added_cost_usd"] = round(cost_usd, 6)
    return JSONResponse(status_code=200, content=out)


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
    logged_cost = usage.get("response_cost")
    try:
        logged_cost_f = float(logged_cost) if logged_cost is not None else 0.0
    except Exception:
        logged_cost_f = 0.0
    cost_usd = logged_cost_f if logged_cost_f > 0 else _calc_cost_usd(model, prompt_tokens, completion_tokens)

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
