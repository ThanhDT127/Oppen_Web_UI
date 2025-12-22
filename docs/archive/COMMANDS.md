# 🚀 CÚ PHÁP KHỞI CHẠY CHƯƠNG TRÌNH

## ⚡ CÁCH ĐƠN GIẢN NHẤT (1 lệnh duy nhất):
```bash
# Trong thư mục D:\Works\Oppen_Web_UI_fresh
scripts\start.bat
```

---

## 📝 KHỞI CHẠY THỦ CÔNG (3 Terminals)

### **Terminal 1: LiteLLM (Port 4000)**
```powershell
# Kích hoạt venv
D:\Works\.venv\Scripts\Activate.ps1

# Khởi động LiteLLM
cd D:\Works\Oppen_Web_UI_fresh
litellm --config litellm/litellm_config.yaml --port 4000
```

### **Terminal 2: Middleware (Port 5000)**
```powershell
# Kích hoạt venv
D:\Works\.venv\Scripts\Activate.ps1

# Khởi động Middleware
cd D:\Works\Oppen_Web_UI_fresh\llm-mw
python main.py
```

### **Terminal 3: OpenWebUI (Port 3000)**
```powershell
# Kích hoạt venv
D:\Works\.venv\Scripts\Activate.ps1

# Khởi động OpenWebUI
cd D:\Works\Oppen_Web_UI_fresh
open-webui serve --port 3000
```

---

## 🎯 CÚ PHÁP NGẮN GỌN (Copy-Paste)

**Terminal 1:**
```powershell
D:\Works\.venv\Scripts\Activate.ps1; cd D:\Works\Oppen_Web_UI_fresh; litellm --config litellm/litellm_config.yaml --port 4000
```

**Terminal 2:**
```powershell
D:\Works\.venv\Scripts\Activate.ps1; cd D:\Works\Oppen_Web_UI_fresh\llm-mw; python main.py
```

**Terminal 3:**
```powershell
D:\Works\.venv\Scripts\Activate.ps1; cd D:\Works\Oppen_Web_UI_fresh; open-webui serve --port 3000
```

---

## 🛑 DỪNG TẤT CẢ SERVICES
```powershell
# Trong PowerShell
scripts\stop.ps1
```

---

## 🔍 KIỂM TRA TRẠNG THÁI
```powershell
# Kiểm tra ports đang chạy
Get-NetTCPConnection -LocalPort 4000,5000,3000 -ErrorAction SilentlyContinue | Format-Table LocalPort, State

# Kiểm tra health
curl http://localhost:5000/health
```

---

## 📦 CÁC URL TRUY CẬP
- **LiteLLM:** http://localhost:4000
- **Middleware:** http://localhost:5000
- **OpenWebUI:** http://localhost:3000
