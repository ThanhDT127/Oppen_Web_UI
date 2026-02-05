# 🚀 HƯỚNG DẪN TRIỂN KHAI - OPEN WEBUI STACK

> **Phiên bản:** 2.0 | **Cập nhật:** 05/02/2026

Hướng dẫn chi tiết cách cài đặt và triển khai Open WebUI Stack từ GitHub.

---

## 📋 Mục Lục

1. [Yêu Cầu Hệ Thống](#1-yêu-cầu-hệ-thống)
2. [Cài Đặt Nhanh](#2-cài-đặt-nhanh)
3. [Cấu Hình Chi Tiết](#3-cấu-hình-chi-tiết)
4. [Database Setup](#4-database-setup)
5. [Khởi Động & Xác Minh](#5-khởi-động--xác-minh)
6. [Backup & Maintenance](#6-backup--maintenance)

---

## 1. Yêu Cầu Hệ Thống

### Hardware
- **RAM**: 8GB+ (16GB khuyến nghị)
- **Storage**: 20GB+ free space
- **CPU**: 4 cores+

### Software
- Docker Engine 24.0+
- Docker Compose v2.20+
- Git

### API Keys
- **OpenAI API Key**: [platform.openai.com](https://platform.openai.com)
- **Gemini API Key**: [aistudio.google.com](https://aistudio.google.com)

---

## 2. Cài Đặt Nhanh

```bash
# 1. Clone repository
git clone https://github.com/your-org/oppen-web-ui.git
cd oppen-web-ui

# 2. Checkout deployment branch
git checkout docker-deployment-with-tests

# 3. Copy và cấu hình .env
cp .env.example .env
# Chỉnh sửa .env với API keys của bạn

# 4. Khởi động
docker compose up -d

# 5. Verify
curl http://localhost:5000/health
```

Truy cập: **http://localhost:3000**

---

## 3. Cấu Hình Chi Tiết

### 3.1 File .env

```bash
# API Keys (BẮT BUỘC)
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...

# LiteLLM
LITELLM_KEY=your_master_key_here

# Middleware Security
MW_SECRET=random_32_char_string
JWT_SECRET=another_random_string

# Database
POSTGRES_USER=openwebui_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=openwebui

# Open WebUI
WEBUI_SECRET_KEY=another_random_secret
```

### 3.2 Middleware Users (llm-mw/data/users.json)

```json
[
  {
    "user_id": "admin",
    "subkey": "YOUR_SUBKEY_ADMIN",
    "active": true,
    "allowed_models": ["*"],
    "quota": {
      "period": "monthly",
      "limit_cost_usd": 100.0,
      "limit_image_requests": 500
    }
  },
  {
    "user_id": "user1",
    "subkey": "YOUR_SUBKEY_USER1",
    "active": true,
    "allowed_models": ["mm-gemini-2.5-flash", "img-gemini-flash"],
    "quota": {
      "period": "monthly",
      "limit_cost_usd": 10.0,
      "limit_image_requests": 50
    }
  }
]
```

### 3.3 LiteLLM Config (litellm/litellm_config.yaml)

Models được đặt tên với prefix theo chức năng:
- `mm-*`: Multimodal (text + vision)
- `img-*`: Image generation
- `tts-*`: Text-to-speech
- `stt-*`: Speech-to-text

---

## 4. Database Setup

### 4.1 PostgreSQL + PGVector

Database được tự động khởi tạo bởi Docker. Schema bao gồm:
- **User data**: Sessions, preferences
- **Chat history**: Messages, conversations
- **Vector embeddings**: RAG documents via PGVector

### 4.2 Manual Initialization (nếu cần)

```bash
docker exec -it openwebui-postgres psql -U openwebui_user -d openwebui

-- Verify PGVector
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check tables
\dt
```

### 4.3 Connection String

```
postgresql://openwebui_user:password@postgres:5432/openwebui
```

---

## 5. Khởi Động & Xác Minh

### 5.1 Khởi Động

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5.2 Health Checks

```bash
# Middleware
curl http://localhost:5000/health
# Expected: {"ok": true, "litellm": "ok", ...}

# LiteLLM
curl http://localhost:4000/health

# Open WebUI
curl http://localhost:3000/api/health
```

### 5.3 Test API

```bash
# List models
curl http://localhost:5000/v1/models \
  -H "Authorization: Bearer YOUR_SUBKEY_ADMIN"

# Test chat
curl http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_SUBKEY_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mm-gemini-2.5-flash",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## 6. Backup & Maintenance

### 6.1 Backup Database

```bash
# Backup
docker exec openwebui-postgres pg_dump -U openwebui_user openwebui > backup.sql

# Restore
docker exec -i openwebui-postgres psql -U openwebui_user openwebui < backup.sql
```

### 6.2 Backup Volumes

```bash
# List volumes
docker volume ls | grep openwebui

# Backup volume
docker run --rm -v openwebui_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/openwebui_data.tar.gz /data
```

### 6.3 Update Services

```bash
# Pull latest images
docker compose pull

# Rebuild custom images
docker compose build --no-cache

# Restart
docker compose up -d
```

### 6.4 Logs Management

```bash
# View specific service logs
docker compose logs middleware --tail 100

# Clear old logs
find logs/ -name "*.log" -mtime +30 -delete
```

---

## 📌 Quick Commands

| Task | Command |
|------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Restart | `docker compose restart` |
| Rebuild | `docker compose up -d --build` |
| Logs | `docker compose logs -f` |
| Status | `docker compose ps` |

---

## 🔗 Service URLs

| Service | URL |
|---------|-----|
| Open WebUI | http://localhost:3000 |
| Middleware | http://localhost:5000 |
| Dashboard | http://localhost:5000/dashboard |
| LiteLLM | http://localhost:4000 |
| PostgreSQL | localhost:5432 |

---

*Tài liệu gộp từ: HUONG_DAN_TRIEN_KHAI_TU_GITHUB.md, DATABASE_CONFIG.md*
