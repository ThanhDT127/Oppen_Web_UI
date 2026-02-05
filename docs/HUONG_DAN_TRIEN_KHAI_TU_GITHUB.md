# HƯỚNG DẪN TRIỂN KHAI OPEN WEBUI STACK TỪ GITHUB

> **Tài liệu này**: Hướng dẫn chi tiết các bước để clone code từ GitHub và khởi chạy hệ thống trên máy ảo (VM).

---

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Yêu Cầu Hệ Thống](#2-yêu-cầu-hệ-thống)
3. [Clone Code Từ GitHub](#3-clone-code-từ-github)
4. [Cấu Hình Environment Variables](#4-cấu-hình-environment-variables)
5. [Khởi Chạy Docker Stack](#5-khởi-chạy-docker-stack)
6. [Kiểm Tra Health](#6-kiểm-tra-health)
7. [Đăng Nhập & Cấu Hình Lần Đầu](#7-đăng-nhập--cấu-hình-lần-đầu)
8. [Chạy Test Suite](#8-chạy-test-suite)
9. [Quản Lý Hệ Thống](#9-quản-lý-hệ-thống)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Tổng Quan Hệ Thống

### Kiến Trúc 3-Tier

```
┌──────────────────────────────────────────────────────────────┐
│                        NGƯỜI DÙNG                              │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Open WebUI (UI)                                    Port 3000  │
│  - Giao diện chat                                              │
│  - Knowledge Base / RAG                                        │
│  - User management                                             │
└────────────────────────────┬─────────────────────────────────┘
                             │ OpenAI-Compatible API
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Middleware (FastAPI)                              Port 5000   │
│  - Xác thực subkey                                             │
│  - Quản lý quota & cost                                        │
│  - Audit logging                                               │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  LiteLLM Proxy                                     Port 4000   │
│  - Model routing                                               │
│  - Provider adapters (OpenAI, Gemini)                          │
└────────────────────────────┬─────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
┌─────────────────────┐          ┌─────────────────────┐
│   OpenAI APIs       │          │   Google Gemini     │
└─────────────────────┘          └─────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  PostgreSQL + PGVector                             Port 5432   │
│  - User data, Chat history                                     │
│  - Vector embeddings (RAG)                                     │
└──────────────────────────────────────────────────────────────┘
```

### Docker Services

| Container | Port | Image | Chức Năng |
|-----------|------|-------|-----------|
| openwebui-postgres | 5432 | pgvector/pgvector:0.8.0-pg16 | Database + Vector |
| openwebui-litellm | 4000 | ghcr.io/berriai/litellm:main-latest | LLM Proxy |
| openwebui-middleware | 5000 | Custom Dockerfile | Auth & Quota |
| openwebui-app | 3000 | ghcr.io/open-webui/open-webui:main | UI Layer |

---

## 2. Yêu Cầu Hệ Thống

### Hardware (Tối Thiểu)
- **CPU**: 2 cores
- **RAM**: 4GB (khuyến nghị 8GB)
- **Disk**: 20GB free space

### Software
- **OS**: Ubuntu 20.04+ / Windows Server 2019+ / VM với Docker support
- **Docker**: 20.10+
- **Docker Compose**: v2.0+
- **Git**: 2.30+

### Kiểm Tra Cài Đặt

```bash
# Kiểm tra Docker
docker --version
# Expected: Docker version 20.10.x hoặc cao hơn

# Kiểm tra Docker Compose
docker compose version
# Expected: Docker Compose version v2.x.x

# Kiểm tra Git
git --version
# Expected: git version 2.30.x hoặc cao hơn
```

### Cài Đặt Docker (Nếu Chưa Có)

**Ubuntu/Debian:**
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (logout/login sau đó)
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y
```

**Windows:**
- Download và cài [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Enable WSL2 backend

---

## 3. Clone Code Từ GitHub

### 3.1 Clone Repository

```bash
# SSH (nếu đã setup SSH key)
git clone git@github.com:YOUR_USERNAME/Oppen_Web_UI.git

# HOẶC HTTPS
git clone https://github.com/YOUR_USERNAME/Oppen_Web_UI.git

# Di chuyển vào thư mục
cd Oppen_Web_UI
```

### 3.2 Checkout Branch Docker Deployment

```bash
# Checkout branch có Docker config
git checkout docker-deployment-with-tests

# Verify files
ls -la
# Phải thấy: docker-compose.yml, .env.example, llm-mw/, litellm/, scripts/
```

### 3.3 Cấu Trúc Thư Mục

```
Oppen_Web_UI/
├── docker-compose.yml      # Docker orchestration
├── .env.example            # Template environment variables
├── .env                    # (Tạo từ .env.example) - KHÔNG commit lên Git
│
├── llm-mw/                 # Middleware service
│   ├── Dockerfile          # Build middleware container
│   ├── main.py             # FastAPI application (977 lines)
│   ├── users.json          # User credentials & quotas
│   ├── prices.json         # Fallback pricing
│   └── requirements.txt    # Python dependencies
│
├── litellm/                # LiteLLM configuration
│   ├── litellm_config.yaml # Model routing config
│   └── litellm.log         # LiteLLM logs
│
├── scripts/                # Management scripts
│   ├── start_all.ps1       # Start stack (PowerShell)
│   ├── stop_all.ps1        # Stop stack
│   ├── logs.ps1            # View logs
│   ├── migrate_sqlite_to_postgres.py
│   ├── verify_migration.py
│   └── init_middleware_tables.sql  # DB tables for logging
│
├── tests/                  # Playwright test suite
│   ├── health.spec.ts      # Service health tests
│   ├── auth.spec.ts        # Authentication tests
│   ├── rag.spec.ts         # RAG functionality tests
│   └── playwright.config.ts
│
├── docs/                   # Documentation
│   ├── TAI_LIEU_TONG_QUAN_DU_AN.md
│   └── BAO_CAO_HIEN_TRANG_HE_THONG_LLM_GATEWAY.md
│
├── HUONG_DAN_TEST.md       # Testing guide
└── README.md               # Project overview
```

---

## 4. Cấu Hình Environment Variables

### 4.1 Tạo File .env

```bash
# Copy template
cp .env.example .env

# Chỉnh sửa file
nano .env  # hoặc vim, code, notepad
```

### 4.2 Nội Dung File .env

```bash
# ==============================================================================
# OPEN WEBUI STACK - ENVIRONMENT CONFIGURATION
# ==============================================================================

# PostgreSQL
POSTGRES_USER=openwebui_user
POSTGRES_PASSWORD=your_secure_password_here    # ĐỔI MẬT KHẨU!
POSTGRES_DB=openwebui

# LiteLLM
LITELLM_KEY=your_litellm_master_key_here       # Tạo key ngẫu nhiên

# LLM Provider API Keys
OPENAI_API_KEY=sk-your-openai-api-key          # Lấy từ platform.openai.com
GEMINI_API_KEY=AIza-your-gemini-api-key        # Lấy từ console.cloud.google.com

# Middleware
ADMIN_KEY=your_admin_key_here                  # Key để quản lý middleware
SUBKEY_ADMIN=subkey_admin_123                  # Subkey cho admin user

# Open WebUI
WEBUI_SECRET_KEY=your_random_32_char_secret    # JWT signing key
```

### 4.3 Tạo Keys

```bash
# Tạo random key (Linux/Mac)
openssl rand -hex 32

# Hoặc Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4.4 Lấy API Keys

| Key | Nguồn | Link |
|-----|-------|------|
| OPENAI_API_KEY | OpenAI Platform | https://platform.openai.com/api-keys |
| GEMINI_API_KEY | Google AI Studio | https://aistudio.google.com/apikey |

---

## 5. Khởi Chạy Docker Stack

### 5.1 Build & Start Services

```bash
# Build middleware image và start tất cả services
docker compose up -d --build

# Xem logs real-time (Ctrl+C để thoát)
docker compose logs -f
```

### 5.2 Verify Containers

```bash
# Liệt kê containers
docker compose ps

# Expected output:
# NAME                    STATUS          PORTS
# openwebui-postgres      Up (healthy)    0.0.0.0:5432->5432/tcp
# openwebui-litellm       Up (healthy)    0.0.0.0:4000->4000/tcp
# openwebui-middleware    Up (healthy)    0.0.0.0:5000->5000/tcp
# openwebui-app           Up (healthy)    0.0.0.0:3000->8080/tcp
```

### 5.3 Thời Gian Khởi Động

| Service | Thời Gian | Ghi Chú |
|---------|-----------|---------|
| PostgreSQL | ~5s | Khởi tạo database |
| LiteLLM | ~10s | Load model configs |
| Middleware | ~3s | FastAPI startup |
| Open WebUI | ~30-60s | Lần đầu download models, init DB |

> **Lưu ý**: Lần đầu tiên Open WebUI có thể mất 1-2 phút để download embedding model (`all-MiniLM-L6-v2`).

---

## 6. Kiểm Tra Health

### 6.1 Health Check Commands

```bash
# PostgreSQL
docker exec openwebui-postgres pg_isready -U openwebui_user
# Expected: accepting connections

# LiteLLM
curl http://localhost:4000/health
# Expected: {"status":"healthy"}

# Middleware
curl http://localhost:5000/health
# Expected: {"status":"ok"}

# Open WebUI
curl http://localhost:3000/health
# Expected: true
```

### 6.2 Script Health Check (Tất Cả)

```bash
#!/bin/bash
echo "=== Health Check ==="

echo -n "PostgreSQL: "
docker exec openwebui-postgres pg_isready -U openwebui_user -q && echo "✅ OK" || echo "❌ FAIL"

echo -n "LiteLLM:    "
curl -sf http://localhost:4000/health > /dev/null && echo "✅ OK" || echo "❌ FAIL"

echo -n "Middleware: "
curl -sf http://localhost:5000/health > /dev/null && echo "✅ OK" || echo "❌ FAIL"

echo -n "Open WebUI: "
curl -sf http://localhost:3000/health > /dev/null && echo "✅ OK" || echo "❌ FAIL"
```

---

## 7. Đăng Nhập & Cấu Hình Lần Đầu

### 7.1 Truy Cập Web UI

Mở browser và truy cập: **http://localhost:3000**

### 7.2 Tạo Tài Khoản Admin

Lần đầu tiên truy cập, bạn sẽ thấy màn hình **Sign Up**:

1. Click **"Sign up"**
2. Nhập thông tin:
   - **Name**: Admin
   - **Email**: admin@example.com
   - **Password**: (mật khẩu mạnh)
3. Click **"Create Account"**

> **Quan trọng**: User đầu tiên đăng ký sẽ tự động trở thành Admin!

### 7.3 Cấu Hình Connection (Quan Trọng!)

Sau khi đăng nhập:

1. Click **avatar** (góc phải trên) → **Admin Panel**
2. Vào tab **Settings** → **Connections**
3. Trong phần **OpenAI API**:
   ```
   API Base URL: http://middleware:5000/v1
   API Key:      subkey_admin_123  (hoặc SUBKEY_ADMIN trong .env)
   ```
4. Click **Save**

### 7.4 Verify Models

1. Vào **Settings** → **Models**
2. Click **Refresh** (icon reload)
3. Phải thấy danh sách models: `gpt-4o`, `gpt-4o-mini`, `gemini-2.5-flash`, ...

---

## 8. Chạy Test Suite

### 8.1 Cài Đặt Dependencies

```bash
# Di chuyển vào thư mục tests
cd tests

# Cài đặt Node.js dependencies
npm install

# Cài đặt Playwright browsers
npx playwright install --with-deps chromium
```

### 8.2 Chạy Tests

```bash
# Chạy tất cả tests
npx playwright test

# Chạy test cụ thể
npx playwright test health.spec.ts
npx playwright test auth.spec.ts

# Chạy với UI mode (xem browser)
npx playwright test --headed

# Xem report HTML
npx playwright show-report
```

### 8.3 Expected Results

```
Running 14 tests using 4 workers

  ✓ health.spec.ts:10:5 › Health Checks › PostgreSQL is healthy (1.2s)
  ✓ health.spec.ts:20:5 › Health Checks › LiteLLM is healthy (0.8s)
  ✓ health.spec.ts:30:5 › Health Checks › Middleware is healthy (0.5s)
  ✓ health.spec.ts:40:5 › Health Checks › Open WebUI is healthy (0.6s)
  ✓ auth.spec.ts:15:5 › Authentication › Can access login page (2.1s)
  ✓ auth.spec.ts:25:5 › Authentication › API auth with subkey works (1.3s)
  ... (8 more tests)

  14 passed (45.2s)
```

---

## 9. Quản Lý Hệ Thống

### 9.1 Commands Thường Dùng

```bash
# Xem logs
docker compose logs -f                    # Tất cả
docker compose logs -f middleware         # Middleware only
docker compose logs -f open-webui         # Open WebUI only

# Restart services
docker compose restart                    # Tất cả
docker compose restart middleware         # Chỉ middleware

# Stop stack
docker compose down

# Stop và xóa volumes (MẤT DỮ LIỆU!)
docker compose down -v

# Rebuild sau khi sửa code
docker compose up -d --build middleware
```

### 9.2 Thêm User Middleware

Chỉnh sửa file `llm-mw/users.json`:

```json
{
  "user_id": "new_user",
  "subkey": "subkey_newuser_xyz",
  "active": true,
  "allowed_models": ["gpt-4o-mini", "gemini-2.5-flash"],
  "quota": {
    "period": "weekly",
    "timezone": "Asia/Bangkok",
    "limit_tokens": 100000,
    "limit_cost_usd": 10.0,
    "limit_image_requests": 50,
    "limit_tts_requests": 100,
    "limit_stt_requests": 50,
    "limit_video_requests": 5,
    "used_tokens": 0,
    "used_cost_usd": 0,
    "period_start": 0
  }
}
```

Sau đó restart middleware:
```bash
docker compose restart middleware
```

### 9.3 Xem Usage Stats

```bash
# Qua API
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" \
     http://localhost:5000/admin/usage

# Reset quota cho user
curl -X POST \
     -H "Authorization: Bearer YOUR_ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user1"}' \
     http://localhost:5000/admin/reset
```

### 9.4 Backup Database

```bash
# Backup PostgreSQL
docker exec openwebui-postgres pg_dump -U openwebui_user openwebui > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20260205.sql | docker exec -i openwebui-postgres psql -U openwebui_user openwebui
```

---

## 10. Troubleshooting

### Container Không Start

```bash
# Xem logs chi tiết
docker compose logs [service_name]

# Kiểm tra disk space
df -h

# Kiểm tra memory
free -m
```

### 401 Unauthorized

- Kiểm tra subkey trong `llm-mw/users.json`
- Đảm bảo user có `"active": true`
- Kiểm tra API Base URL trong Open WebUI Settings

### 429 Too Many Requests

- Quota đã hết → Reset qua `/admin/reset` API
- Hoặc chờ đến period tiếp theo (weekly/monthly)

### Models Không Hiển Thị

1. Kiểm tra LiteLLM health: `curl http://localhost:4000/health`
2. Kiểm tra Middleware health: `curl http://localhost:5000/health`
3. Verify API keys trong `.env`
4. Xem logs: `docker compose logs litellm`

### RAG Không Hoạt Động

1. Kiểm tra embedding model đã download:
   ```bash
   docker compose logs open-webui | grep -i embedding
   ```
2. Verify PGVector extension:
   ```bash
   docker exec openwebui-postgres psql -U openwebui_user -d openwebui -c "SELECT * FROM pg_extension WHERE extname='vector';"
   ```

### Port Đã Bị Sử Dụng

```bash
# Kiểm tra port
netstat -tlnp | grep 3000

# Kill process
sudo kill -9 <PID>

# Hoặc đổi port trong docker-compose.yml
ports:
  - "3001:8080"  # Đổi 3000 thành 3001
```

---

## 📊 Tóm Tắt Các Bước

| # | Bước | Command/Action |
|---|------|----------------|
| 1 | Clone repo | `git clone ...` |
| 2 | Checkout branch | `git checkout docker-deployment-with-tests` |
| 3 | Tạo .env | `cp .env.example .env && nano .env` |
| 4 | Start stack | `docker compose up -d --build` |
| 5 | Health check | `curl localhost:3000/health` |
| 6 | Đăng ký admin | Browser → localhost:3000 → Sign up |
| 7 | Cấu hình connection | Admin Panel → Settings → Connections |
| 8 | Chạy tests | `cd tests && npm install && npx playwright test` |

---

## 📞 Hỗ Trợ

- **Documentation**: `docs/TAI_LIEU_TONG_QUAN_DU_AN.md`
- **Testing Guide**: `HUONG_DAN_TEST.md`
- **API Reference**: `docs/BAO_CAO_HIEN_TRANG_HE_THONG_LLM_GATEWAY.md`

---

*Tài liệu được tạo: 2026-02-05*
*Version: 1.0*
