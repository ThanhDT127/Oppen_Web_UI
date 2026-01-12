# 📍 HƯỚNG DẪN CẤU HÌNH DATABASE VÀ DATA DIRECTORIES

## ✅ CẤU HÌNH HIỆN TẠI (Đã đúng)

### 1. OpenWebUI Database
**Location:** `D:\Works\Oppen_Web_UI_fresh\openwebui_data\webui.db`

**Cấu hình trong `.env`:**
```env
DATA_DIR=D:\Works\Oppen_Web_UI_fresh\openwebui_data
WEBUI_SECRET_KEY=your-secret-key-here
```

**Chứa:**
- User accounts
- Chat history
- Conversations
- Model configurations

### 2. Middleware Data Files
**Location:** `D:\Works\Oppen_Web_UI_fresh\llm-mw\data\`

**Files:**
- `users.json` - User authentication & quota
- `prices.json` - Model pricing
- `pending.csv` - Pending usage tracking

**Cấu hình trong `config.py`:**
```python
DATA_DIR = os.path.join(BASE_DIR, "data")  # llm-mw/data/
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PRICES_FILE = os.path.join(DATA_DIR, "prices.json")
PENDING_CSV = os.path.join(DATA_DIR, "pending.csv")
```

### 3. Log Files
**Location:** `D:\Works\Oppen_Web_UI_fresh\logs\`

**Files:**
- `middleware.log` - Main log
- `middleware.requests.log` - Request log
- `audit.jsonl` - Audit trail
- `mw_media/` - Uploaded media files

**Cấu hình:**
```python
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))
```

---

## 🔍 KIỂM TRA CẤU HÌNH

### PowerShell Script
```powershell
# Kiểm tra tất cả database paths
Write-Host "`nOpenWebUI Database:" -ForegroundColor Yellow
Get-Item D:\Works\Oppen_Web_UI_fresh\openwebui_data\webui.db | Format-List Name, Length, LastWriteTime

Write-Host "`nMiddleware Data Files:" -ForegroundColor Yellow
Get-ChildItem D:\Works\Oppen_Web_UI_fresh\llm-mw\data | Format-Table Name, Length, LastWriteTime

Write-Host "`nLog Files:" -ForegroundColor Yellow
Get-ChildItem D:\Works\Oppen_Web_UI_fresh\logs -File | Format-Table Name, Length, LastWriteTime
```

### Python Script
```python
import os

# Check paths
print("\n=== DATABASE LOCATIONS ===")
print(f"OpenWebUI DB: {os.path.exists('openwebui_data/webui.db')}")
print(f"Users JSON: {os.path.exists('llm-mw/data/users.json')}")
print(f"Prices JSON: {os.path.exists('llm-mw/data/prices.json')}")
print(f"Logs Dir: {os.path.exists('logs')}")
```

---

## 🛠 SCRIPTS ĐÃ CẬP NHẬT

### start.bat
```bat
REM Đã thêm explicit DATA_DIR
start "OpenWebUI" cmd /k "... && set DATA_DIR=%CD%\openwebui_data && open-webui serve --port 3000"
```

### start.ps1
```powershell
# Đã thêm explicit DATA_DIR
$env:DATA_DIR='$PWD\openwebui_data'
$env:WEBUI_SECRET_KEY='your-secret-key-here'
open-webui serve --port 3000
```

---

## 📋 CẤU TRÚC THƯ MỤC

```
D:\Works\Oppen_Web_UI_fresh\
│
├── .env                          # ⭐ Environment config (DATA_DIR here)
├── openwebui_data/               # ⭐ OpenWebUI database
│   └── webui.db                  # SQLite database (452 KB)
│
├── llm-mw/                       # Middleware
│   ├── config.py                 # ⭐ Data paths configured here
│   └── data/                     # ⭐ Middleware data files
│       ├── users.json            # User auth & quota
│       ├── prices.json           # Model pricing
│       └── pending.csv           # Pending tracking
│
└── logs/                         # ⭐ All log files
    ├── audit.jsonl               # Audit log
    ├── middleware.log            # Main log
    ├── middleware.requests.log   # Request log
    └── mw_media/                 # Uploaded files
```

---

## ⚠️ LƯU Ý

### 1. Absolute Paths
- **OpenWebUI:** Cần absolute path cho `DATA_DIR`
- **Middleware:** Tự động resolve từ `BASE_DIR`

### 2. Environment Variables
Thứ tự ưu tiên:
1. `.env` file (highest priority)
2. System environment variables
3. Default values trong code

### 3. Backup Database
```powershell
# Backup OpenWebUI database
Copy-Item openwebui_data\webui.db "openwebui_data\webui.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Backup Middleware data
Copy-Item llm-mw\data\users.json "llm-mw\data\users.json.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
```

---

## ✅ KIỂM TRA NHANH

```powershell
# Kiểm tra tất cả paths
cd D:\Works\Oppen_Web_UI_fresh

Write-Host "`n=== CHECKING ALL DATA PATHS ===" -ForegroundColor Cyan

# OpenWebUI
if (Test-Path "openwebui_data\webui.db") {
    Write-Host "[✓] OpenWebUI DB: OK" -ForegroundColor Green
} else {
    Write-Host "[✗] OpenWebUI DB: NOT FOUND" -ForegroundColor Red
}

# Middleware
if (Test-Path "llm-mw\data\users.json") {
    Write-Host "[✓] Middleware users.json: OK" -ForegroundColor Green
} else {
    Write-Host "[✗] Middleware users.json: NOT FOUND" -ForegroundColor Red
}

# Logs
if (Test-Path "logs") {
    Write-Host "[✓] Logs directory: OK" -ForegroundColor Green
} else {
    Write-Host "[✗] Logs directory: NOT FOUND" -ForegroundColor Red
}
```

**Kết quả mong đợi:**
```
[✓] OpenWebUI DB: OK
[✓] Middleware users.json: OK
[✓] Logs directory: OK
```

---

## 🎯 KẾT LUẬN

✅ **Tất cả database và data files đã trỏ đúng thư mục hiện tại:**
- OpenWebUI: `D:\Works\Oppen_Web_UI_fresh\openwebui_data\`
- Middleware: `D:\Works\Oppen_Web_UI_fresh\llm-mw\data\`
- Logs: `D:\Works\Oppen_Web_UI_fresh\logs\`

✅ **Scripts đã được cập nhật** để đảm bảo `DATA_DIR` được set đúng

✅ **Không cần thay đổi gì thêm** - Everything is working!
