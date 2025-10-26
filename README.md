# OpenWebUI + Middleware + LiteLLM (Groq/OpenAI/Gemini)

This repo sets up the full chain under a single path:

D:\\ktlt\\Works\\Open_Web_UI

OpenWebUI → Middleware (FastAPI) → LiteLLM (Proxy) → Groq/OpenAI/Gemini

## What gets created

- litellm/litellm_config.yaml: LiteLLM proxy config (port 4000)
- llm-mw/main.py: FastAPI middleware for auth/quota (port 5000)
- llm-mw/.env: Connection to LiteLLM + admin key
- llm-mw/users.json: Users, subkeys, allowed models, quotas
- requirements.txt: Python deps for both services

## 0) Create and activate a virtual environment (Windows PowerShell)

```powershell
cd D:\ktlt\Works\Open_Web_UI
# Option A (python on PATH)
python -m venv .venv
# Option B (py launcher)
# py -3 -m venv .venv

.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r .\requirements.txt
```

## I) Configure and run LiteLLM (proxy)

1) Put your Groq key in an env var for this session:

```powershell
$env:GROQ_API_KEY = "gsk_..."  # replace with your key
```

2) Config lives at `D:\ktlt\Works\Open_Web_UI\litellm\litellm_config.yaml` (already created). It exposes:

- http://0.0.0.0:4000/v1
- master key: `YOUR_LITELLM_KEY`
- logs to: `D:\ktlt\Works\Open_Web_UI\litellm\litellm.log`

3) Start LiteLLM (Terminal 1):

```powershell
litellm --config D:\ktlt\Works\Open_Web_UI\litellm\litellm_config.yaml
```

Expected:

```
LiteLLM Proxy initialized...
Running on http://0.0.0.0:4000/v1
```

Verify models:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:4000/v1/models" -Headers @{ "Authorization" = "Bearer YOUR_LITELLM_KEY" }
```

## II) Configure and run Middleware (auth/quota)

1) The `.env` is at `llm-mw/.env` and defaults to:

```
LITELLM_BASE=http://127.0.0.1:4000/v1
LITELLM_KEY=YOUR_LITELLM_KEY
ADMIN_KEY=YOUR_ADMIN_KEY
```

2) Users live in `llm-mw/users.json` (sample admin/user1/user2 already present).

3) Start middleware (Terminal 2):

```powershell
cd D:\ktlt\Works\Open_Web_UI\llm-mw
uvicorn main:app --host 0.0.0.0 --port 5000
```

Health check and admin list:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/health"
Invoke-RestMethod -Uri "http://127.0.0.1:5000/admin/users" -Headers @{ "Authorization" = "Bearer YOUR_ADMIN_KEY" }
```

Optional: quick chat test via middleware:

```powershell
$body = @{ model = "deepseek-70b"; messages = @(@{ role = "user"; content = "Hello from MW" }) } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/v1/chat/completions" -Headers @{ "Authorization" = "Bearer YOUR_SUBKEY_USER1"; "Content-Type" = "application/json" } -Body $body
```

## III) Connect OpenWebUI

In OpenWebUI Settings → Connection:

- Base URL: `http://<YOUR_IP_OR_HOST>:5000/v1` (e.g., `http://127.0.0.1:5000/v1`)
- API Key: `YOUR_SUBKEY_USER1`
- Model: `deepseek-70b` or `gpt-oss-20b`

Flow: OpenWebUI → Middleware checks auth/quota → calls LiteLLM → LiteLLM calls Groq → returns result → Middleware records usage in `users.json`.

## IV) Operations

- Admin users list:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/admin/users" -Headers @{ "Authorization" = "Bearer YOUR_ADMIN_KEY" }
```

- LiteLLM spend log: `D:\ktlt\Works\Open_Web_UI\litellm\litellm.log`

## V) Notes and tips

- Run LiteLLM and the middleware in two separate terminals.
- Ensure ports 4000 and 5000 are allowed by Windows Firewall for local usage.
- If Groq requests fail, re-check `$env:GROQ_API_KEY` and that your models are available to your Groq account.
- You can add more providers/models in `litellm_config.yaml` later.
- To reset quotas, edit `llm-mw/users.json` and set `used_tokens` back to 0 (no restart required).
