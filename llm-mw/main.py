import os
import json
import threading
import time
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="LLM Middleware (Quota+Auth)", version="2.0")

# Allow calls from local tools/UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve users.json path relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
_lock = threading.Lock()


def _load_users() -> List[Dict[str, Any]]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)



def _save_users(users: List[Dict[str, Any]]):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _find_user(subkey: str) -> Optional[Dict[str, Any]]:
    for u in _load_users():
        if u.get("subkey") == subkey:
            return u
    return None


def _update_usage(user_id: str, add_tokens: int):
    if add_tokens <= 0:
        return
    with _lock:
        users = _load_users()
        for u in users:
            if u.get("user_id") == user_id:
                u["used_tokens"] = int(u.get("used_tokens", 0)) + int(add_tokens)
                break
        _save_users(users)


LITELLM_BASE = os.getenv("LITELLM_BASE", "http://127.0.0.1:4000/v1")
LITELLM_KEY = os.getenv("LITELLM_KEY", "")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")


from fastapi.responses import JSONResponse, StreamingResponse
import httpx

@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    # 1) auth
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

    allowed = user.get("allowed_models", [])
    if allowed != ["*"] and model not in allowed:
        raise HTTPException(403, f"Model '{model}' not allowed for {user['user_id']}")

    max_tokens = int(user.get("max_tokens", 0))
    used_tokens = int(user.get("used_tokens", 0))
    if max_tokens > 0 and used_tokens >= max_tokens:
        raise HTTPException(403, f"Token quota exceeded for {user['user_id']}")

    headers = {
        "Authorization": f"Bearer {LITELLM_KEY}",
        "Content-Type": "application/json",
        # "Accept": will be set by httpx automatically
    }

    # 2) streaming?
    is_stream = bool(body.get("stream"))

    if is_stream:
        async def _iter():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{LITELLM_BASE}/chat/completions",
                    headers=headers,
                    json=body,
                ) as r:
                    # propagate error status for streams
                    if r.status_code >= 400:
                        # read whole body once and raise as JSON/text
                        err_text = await r.aread()
                        raise HTTPException(r.status_code, err_text.decode("utf-8", errors="ignore"))
                    async for chunk in r.aiter_bytes():
                        yield chunk
        # trả đúng MIME để Open WebUI đọc được
        return StreamingResponse(_iter(), media_type="text/event-stream")

    # 3) non-stream (JSON)
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{LITELLM_BASE}/chat/completions", headers=headers, json=body)
        if r.status_code >= 400:
            # propagate error chi tiết
            try:
                raise HTTPException(r.status_code, r.json())
            except Exception:
                raise HTTPException(r.status_code, r.text)
        data = r.json()

    # 4) update usage (chỉ khi non-stream; stream thì nhiều provider không trả usage)
    usage = data.get("usage", {}) or {}
    total = int(usage.get("total_tokens", 0))
    _update_usage(user["user_id"], total)

    data["_mw_user"] = user["user_id"]
    data["_mw_added_tokens"] = total
    return JSONResponse(status_code=200, content=data)


@app.get("/v1/models")
def models():
    # Expose union of all allowed models (simple view)
    models: List[str] = []
    for u in _load_users():
        for m in u.get("allowed_models", []):
            models.append(m)
    unique = sorted(set([m for m in models if m != "*"]))
    return {"data": [{"id": m, "object": "model"} for m in unique]}


@app.get("/admin/users")
def list_users(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ADMIN_KEY}":
        raise HTTPException(403, "Invalid admin key")
    users = _load_users()
    # mask subkeys
    for u in users:
        sk = u.get("subkey", "")
        if len(sk) > 8:
            u["subkey"] = sk[:4] + "****" + sk[-4:]
        else:
            u["subkey"] = "****"
    return users


@app.get("/health")
def health():
    return {"ok": True, "time": int(time.time())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=False)
