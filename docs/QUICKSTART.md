# 🚀 QUICK START - OPPEN WEB UI

Quick startup guide for running the 3-tier LLM chat platform.

---

## ⚡ One-Command Startup

### Prerequisites
- Python 3.10+ with virtual environment at `D:\Works\.venv`
- Environment variables configured in `.env` file
- API keys for OpenAI and/or Gemini

### Windows - PowerShell (Recommended)
```powershell
.\scripts\start.ps1
```

### Windows - Batch Script
```bash
scripts\start.bat
```

This will start:
1. **LiteLLM Proxy** (Port 4000)
2. **Middleware** (Port 5000)
3. **OpenWebUI** (Port 3000)

---

## 📝 Manual Startup (3 Terminals)

### Terminal 1 - LiteLLM (Port 4000)
```powershell
D:\Works\.venv\Scripts\Activate.ps1
cd D:\Works\Oppen_Web_UI_fresh
litellm --config litellm/litellm_config.yaml --port 4000
```

### Terminal 2 - Middleware (Port 5000)
```powershell
D:\Works\.venv\Scripts\Activate.ps1
cd D:\Works\Oppen_Web_UI_fresh\llm-mw
python main.py
```

### Terminal 3 - OpenWebUI (Port 3000)
```powershell
D:\Works\.venv\Scripts\Activate.ps1
cd D:\Works\Oppen_Web_UI_fresh
open-webui serve --port 3000
```

---

## 🛑 Stop All Services

```powershell
.\scripts\stop.ps1
```

---

## 🔗 Access URLs

- **OpenWebUI (Chat Interface):** http://localhost:3000
- **Admin Dashboard:** http://localhost:5000/dashboard
- **Middleware Health:** http://localhost:5000/health
- **LiteLLM Health:** http://localhost:4000/health

---

## 🔑 First Time Setup

### 1. Configure Environment Variables

Ensure `.env` file exists with all required keys:

```bash
# .env
LITELLM_KEY=your-litellm-admin-key
ADMIN_KEY=your-admin-master-key
JWT_SECRET=<secure-random-32-chars>
MW_SECRET=<secure-random-32-chars>

OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-key
```

See [.env.example](.env.example) for full template.

### 2. Create Your First User

**Method A: Use example file**
```powershell
Copy-Item llm-mw\users.example.json llm-mw\data\users.json
```

Then edit `llm-mw\data\users.json` with your subkey:
```json
[
  {
    "user_id": "myuser",
    "subkey": "sk_my_secure_subkey_12345",
    "active": true,
    "allowed_models": ["*"],
    "used_tokens": 0,
    "used_cost_usd": 0.0,
    "quota": {
      "period": "monthly",
      "timezone": "Asia/Bangkok",
      "limit_tokens": 1000000,
      "limit_cost_usd": 50.0,
      "period_start": 0,
      "used_tokens": 0,
      "used_cost_usd": 0.0
    }
  }
]
```

**Method B: Manually create users.json**

Create file at `llm-mw\data\users.json` with the structure above.

**Important:** Subkey is stored in plaintext here. System will hash it on first use.

### 3. Configure OpenWebUI

1. Open http://localhost:3000
2. Register/login (first user becomes admin)
3. Go to **Settings** → **Connections**
4. Set:
   - **API Base URL:** `http://127.0.0.1:5000/v1`
   - **API Key:** `sk_my_secure_subkey_12345` (your subkey from users.json)
5. Save and start chatting!

---

## 📁 Project Structure

```
Oppen_Web_UI_fresh/
├── .env                # Environment variables (DO NOT COMMIT)
├── .env.example        # Template for environment setup
├── scripts/            # Startup & management scripts
│   ├── start.ps1       # Start all services
│   └── stop.ps1        # Stop all services
├── docs/               # Documentation
│   ├── README.md       # Project overview (master doc)
│   ├── QUICKSTART.md   # This file
│   ├── ARCHITECTURE.md # System design & data flow
│   ├── API_REFERENCE.md# Complete endpoint docs
│   └── DASHBOARD.md    # Admin dashboard guide
├── llm-mw/             # Middleware (modular architecture)
│   ├── api/            # 11 endpoint handlers
│   ├── core/           # Business logic (auth, quota, cost)
│   ├── utils/          # Helpers (jwt, logging, guards)
│   ├── services/       # External clients (litellm)
│   ├── dashboard/      # Admin UI (HTML/CSS/JS)
│   ├── data/           # Runtime data (users.json, prices.json)
│   ├── main.py         # FastAPI entry point
│   └── config.py       # Environment & logging setup
├── litellm/            # LiteLLM proxy config
│   └── litellm_config.yaml
├── logs/               # Application logs
│   ├── middleware.log  # Main log
│   ├── audit.jsonl     # Audit trail
│   └── mw_media/       # Uploaded media
└── openwebui_data/     # OpenWebUI database & files
```

---

## 🐛 Troubleshooting

**Services won't start:**
```powershell
# Kill processes using ports
Get-Process | Where-Object {$_.ProcessName -like "*python*" -or $_.ProcessName -like "*litellm*"} | Stop-Process -Force

# Restart
.\scripts\start.ps1
```

**Dashboard login fails:**
- Verify `ADMIN_KEY` in `.env`
- Check logs: `logs/middleware.log`
- Look for JWT_SECRET warnings

**Can't access OpenWebUI:**
- Ensure all 3 services are running
- Check health endpoints
- Review terminal outputs for errors

---

## 📚 Learn More

- **Full Documentation:** [README.md](../README.md)
- **System Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Reference:** [API_REFERENCE.md](API_REFERENCE.md)
- **Dashboard Guide:** [DASHBOARD.md](DASHBOARD.md)

---

**Last Updated:** December 22, 2025
