# 🚀 QUICK START - OPPEN WEB UI

## ⚡ Khởi Động Nhanh (1 lệnh)

### Windows - Batch Script
```bash
scripts\start.bat
```

### Windows - PowerShell
```powershell
.\scripts\start.ps1
```

---

## 📝 Khởi Động Thủ Công (3 Terminals)

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

## 🛑 Dừng Tất Cả Services

```powershell
.\scripts\stop.ps1
```

---

## 🔗 URLs Truy Cập

- **OpenWebUI:** http://localhost:3000 (Web Chat Interface)
- **Middleware:** http://localhost:5000/health (API Health Check)
- **LiteLLM:** http://localhost:4000/health (Proxy Health)

---

## 📁 Cấu Trúc Project

```
Oppen_Web_UI_fresh/
├── scripts/        # Khởi chạy & quản lý
├── docs/           # Tài liệu
├── llm-mw/         # Middleware (refactored 15 modules)
├── litellm/        # LiteLLM config
├── logs/           # Log files
└── openwebui_data/ # OpenWebUI database
```

Xem chi tiết: [README.md](../README.md)
