# TAI LIEU VAN HANH HE THONG AI NOI BO (OPEN WEBUI STACK)

**Ma tai lieu:** DOC-02  
**Phien ban:** 1.0  
**Ngay lap:** 06/03/2026  
**Doi tuong:** Quan tri vien hệ thống, Doi ky thuat  
**Phan loai:** NOI BO - KY THUAT

---

## MUC LUC

0. Thong tin tai lieu
1. Kiến trúc va so do thuc te
2. Cai dat va triển khai
3. Quản lý Scheduled Tasks
4. Quản lý Database
5. Quản lý Logs
6. Quản lý người dùng
7. Monitoring va Health Check
8. Bảo mật
9. Troubleshooting
10. Maintenance
11. Scaling
12. Disaster Recovery
13. Source Code va Repository
14. Infrastructure / DevOps

---

## 0. THONG TIN TAI LIEU

### 0.1. Tong quan hệ thống (System Overview)

Hệ thống AI nội bộ gom 4 services chay tren Docker:

| Service    | Container            | Port | Vai tro                        |
| ---------- | -------------------- | ---- | ------------------------------ |
| Open WebUI | openwebui-app        | 3000 | Giao diện chat, RAG, knowledge |
| Middleware | openwebui-middleware | 5000 | Auth, quota, cost, dashboard   |
| LiteLLM    | openwebui-litellm    | 4000 | LLM proxy (OpenAI + Gemini)    |
| PostgreSQL | openwebui-postgres   | 5432 | Database + PGVector            |

### 0.2. Scope va Deliverables

| Pham vi             | Chi tiet                                      |
| ------------------- | --------------------------------------------- |
| He dieu hanh server | Windows Server 2019+ / Ubuntu 20.04+          |
| Docker              | Docker Engine 24.0+, Compose v2.20+           |
| Databases           | PostgreSQL 16 + PGVector 0.8.0 (2 databases)  |
| API Providers       | OpenAI API, Google Gemini API                 |
| Models              | 20 models (14 chat + 3 image + 1 TTS + 2 STT) |
| Users               | 200+ concurrent                               |

### 0.3. Danh muc tai san (Asset List)

| Tai san        | Duong dan                   | Mo ta                     |
| -------------- | --------------------------- | ------------------------- |
| Source code    | Oppen_Web_UI/               | Root project              |
| Middleware     | llm-mw/                     | Python FastAPI middleware |
| Dashboard      | llm-mw/dashboard/           | HTML/CSS/JS SPA           |
| LiteLLM config | litellm/litellm_config.yaml | Model definitions         |
| Docker config  | docker-compose.yml          | Stack orchestration       |
| Environment    | .env                        | API keys, secrets         |
| Scripts        | scripts/                    | Management scripts        |
| Documentation  | docs/                       | 12 tai lieu (01-12)       |

---

## 1. KIEN TRUC VA SO DO THUC TE

### 1.1. Kiến trúc hệ thống

```
            Internet
               |
    +----------v----------+
    |   Windows Server    |
    |   (Docker Host)     |
    |                     |
    |  +-----------------------------------------------+
    |  |        Docker Compose Stack                    |
    |  |                                                |
    |  |  +--------------+   +----------------------+   |
    |  |  | Open WebUI   |   |  Middleware           |   |
    |  |  | :3000        |-->|  :5000                |   |
    |  |  | (Frontend)   |   |  (Auth+Quota+         |   |
    |  |  +--------------+   |   Dashboard)          |   |
    |  |                     +----------+------------+   |
    |  |                                |                |
    |  |  +--------------+   +---------v---------+      |
    |  |  | PostgreSQL   |   |  LiteLLM          |      |
    |  |  | + PGVector   |   |  :4000            |      |
    |  |  | :5432        |   |  (LLM Proxy)      |      |
    |  |  +--------------+   +---------+---------+      |
    |  |                               |                 |
    |  +-------------------------------|-----------------+
    |                                  |
    +----------------------------------|------------------+
                                       |
                            +----------+----------+
                            |                     |
                            v                     v
                      +----------+          +----------+
                      | OpenAI   |          | Google   |
                      | API      |          | Gemini   |
                      +----------+          +----------+
```

### 1.2. Cac thanh phan chinh

| #   | Thanh phan | Cong nghe          | Version | Image                               |
| --- | ---------- | ------------------ | ------- | ----------------------------------- |
| 1   | Open WebUI | Python + SvelteKit | latest  | ghcr.io/open-webui/open-webui:main  |
| 2   | Middleware | Python + FastAPI   | custom  | ./llm-mw/Dockerfile                 |
| 3   | LiteLLM    | Python             | latest  | ghcr.io/berriai/litellm:main-latest |
| 4   | PostgreSQL | C                  | 16      | pgvector/pgvector:0.8.0-pg16        |

### 1.3. Phan chia modules trong Middleware

```
llm-mw/
  main.py                  # FastAPI app, route registration
  config.py                # Environment variables, constants
  requirements.txt         # Python dependencies
  Dockerfile               # Container build
  core/
    auth.py                # Subkey auth, user lookup, HMAC-SHA256
    cost.py                # Price lookup, cost calculation, quota
    db.py                  # PostgreSQL pool, schema, CRUD
    alerting.py            # Quota alerts, notifications
  api/
    user_admin.py          # User CRUD, rotate key, delete
    summary.py             # Metrics aggregation (v1)
    summary_v2.py          # Metrics aggregation (v2, DB-based)
    stream.py              # SSE real-time events
    access_logs.py         # Paginated access logs
    audit_query.py         # Admin audit trail
    models.py              # Model listing
  dashboard/
    index.html             # SPA entry point
    css/dashboard.css      # Styles
    js/
      main.js              # App orchestrator
      charts.js            # Chart.js visualizations
      filters.js           # Date/user/model filters
      logs.js              # Log table & pagination
      usage.js             # Usage metrics
      users.js             # User CRUD UI
  data/
    users.json             # User backup (source: DB)
    prices.json            # Price backup (source: DB)
```

---

## 2. CAI DAT VA TRIEN KHAI

### 2.1. Yeu cau hệ thống

| Tai nguyen | Toi thieu    | Khuyen nghi |
| ---------- | ------------ | ----------- |
| RAM        | 8 GB         | 16 GB       |
| CPU        | 4 cores      | 8 cores     |
| Storage    | 20 GB free   | 50 GB free  |
| Docker     | Engine 24.0+ | Latest      |
| Compose    | v2.20+       | Latest      |
| Network    | LAN access   | Firewall    |

### 2.2. Cai dat dependencies

```
# 1. Cai Docker Desktop (Windows)
# Download tu https://docker.com/products/docker-desktop

# 2. Clone repository
git clone https://github.com/ThanhDT127/Oppen_Web_UI.git
cd Oppen_Web_UI
git checkout dashboard

# 3. Verify Docker
docker --version        # >= 24.0
docker compose version  # >= 2.20
```

### 2.3. Cấu hình moi truong

Tao file .env tu template:

```
cp .env.example .env
```

#### Bien moi truong bat buoc

```
# API Keys (BAT BUOC)
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...

# LiteLLM
LITELLM_KEY=sk-litellm-master-key-change-me

# Middleware Security
MW_SECRET=random_32_char_string_for_subkey_hashing
JWT_SECRET=another_random_string_for_jwt_signing
ADMIN_KEY=admin_master_key_456

# PostgreSQL
POSTGRES_USER=openwebui_user
POSTGRES_PASSWORD=your_secure_password_min_16_chars
POSTGRES_DB=openwebui

# Open WebUI
WEBUI_SECRET_KEY=webui_secret_min_32_chars
```

#### Mo ta tung bien

| Bien              | Vai tro                                | Sử dụng boi |
| ----------------- | -------------------------------------- | ----------- |
| OPENAI_API_KEY    | Xác thực OpenAI API (GPT, DALL-E, TTS) | LiteLLM     |
| GEMINI_API_KEY    | Xác thực Google Gemini API             | LiteLLM     |
| LITELLM_KEY       | Master key cho LiteLLM admin API       | LiteLLM     |
| MW_SECRET         | Salt cho HMAC-SHA256 hash subkey       | Middleware  |
| JWT_SECRET        | Secret cho JWT token signing           | Middleware  |
| ADMIN_KEY         | Key đăng nhập Dashboard admin          | Middleware  |
| POSTGRES_PASSWORD | Mật khẩu PostgreSQL                    | PostgreSQL  |
| WEBUI_SECRET_KEY  | Secret cho Open WebUI sessions         | Open WebUI  |

### 2.4. Khởi động hệ thống

```
# Khởi động toan bo
docker compose up -d

# Kiểm tra trang thai
docker compose ps

# Xem logs (theo doi)
docker compose logs -f

# Chi khởi động middleware
docker compose up -d middleware

# Restart hệ thống
docker compose restart

# Dung hệ thống (giu data)
docker compose down

# Dung + xoa volumes (MAT DU LIEU)
docker compose down -v
```

### 2.5. Cập nhật code moi

```
# 1. Pull code moi
git pull origin dashboard

# 2. Rebuild containers (neu co thay doi Dockerfile)
docker compose build --no-cache middleware

# 3. Restart
docker compose up -d

# 4. Verify
docker compose ps
curl http://localhost:5000/health
```

---

## 3. QUAN LY SCHEDULED TASKS

### 3.1. Reconcile Scheduler

Muc dich: Dong bo pending requests voi LiteLLM logs (tinh cost chinh xac cho streaming).

- Tan suat: Tự động, triggered sau moi streaming response
- Endpoint: POST /v1/_mw/admin/reconcile
- Method: Doc LiteLLM logs > match rid > cập nhật tokens/cost

### 3.2. Quota Reset

Muc dich: Reset used_tokens, used_cost_usd ve 0 theo chu ky.

- Tan suat: Monthly (dau moi thang) hoac Weekly
- Logic: Kiểm tra mw_users.quota.period > reset neu den ky
- Config: Tung user cấu hình period rieng (monthly/weekly)

### 3.3. Alert Scheduler

Muc dich: Gui cảnh báo khi user gan het quota.

- Tan suat: Moi 5 phut kiểm tra
- Nguong: 80% quota > warning, 95% > critical
- Action: Log cảnh báo, co the webhook notification

### 3.4. Quản lý Scheduler

```
# Xem logs scheduler
docker compose logs middleware | findstr "scheduler"

# Reconcile thu cong
curl -X POST http://localhost:5000/v1/_mw/admin/reconcile -H "X-Admin-Key: admin_master_key_456"

# Reset quota thu cong cho 1 user
curl -X POST http://localhost:5000/admin/reset -H "X-Admin-Key: admin_master_key_456" -H "Content-Type: application/json" -d "{\"user_id\": \"user1\"}"
```

---

## 4. QUAN LY DATABASE

### 4.1. PostgreSQL - 2 Databases

#### Database openwebui - 26 bang

| Nhom      | Bang chinh                      | Muc dich               |
| --------- | ------------------------------- | ---------------------- |
| User      | user, auth                      | Tài khoản, credentials |
| Chat      | chat, message, channel          | Hội thoại              |
| Knowledge | knowledge, file, knowledge_file | Tai lieu               |
| RAG       | document, document_chunk        | Vector embeddings      |
| Config    | config, feedback, tag           | Cấu hình               |

#### Database middleware - 6 bang

| Bang           | Columns                                   | Muc dich         |
| -------------- | ----------------------------------------- | ---------------- |
| mw_users       | user_id, subkey_hash, role, active, quota | Quản lý user API |
| mw_prices      | model, input_per_1m, output_per_1m        | Bảng giá         |
| mw_config      | key, value                                | Config runtime   |
| mw_pending     | rid, user_id, model                       | Pending requests |
| mw_audit_log   | ts, user_id, model, status, cost          | Audit log        |
| mw_request_log | ts, method, path, status_code, latency    | HTTP access log  |

### 4.2. Kết nối Database

```
# Kết nối truc tiep
docker exec -it openwebui-postgres psql -U openwebui_user -d openwebui

# Kiểm tra database middleware
docker exec -it openwebui-postgres psql -U openwebui_user -d middleware

# Connection string (trong docker network)
# postgresql://openwebui_user:<password>@postgres:5432/openwebui
# postgresql://openwebui_user:<password>@postgres:5432/middleware
```

### 4.3. Monitoring Database

```sql
-- Xem kich thuoc database
SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname))
FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC;

-- Xem kich thuoc tung bang
SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::regclass))
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;

-- Dem records trong middleware tables
SELECT 'mw_users' as tbl, COUNT(*) FROM mw_users
UNION ALL SELECT 'mw_audit_log', COUNT(*) FROM mw_audit_log
UNION ALL SELECT 'mw_pending', COUNT(*) FROM mw_pending
UNION ALL SELECT 'mw_request_log', COUNT(*) FROM mw_request_log;

-- Xem index usage
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes ORDER BY idx_scan DESC;
```

### 4.4. Maintenance Database

```sql
-- VACUUM (don dep dead tuples)
VACUUM ANALYZE mw_audit_log;
VACUUM ANALYZE mw_request_log;

-- REINDEX (rebuild index)
REINDEX TABLE mw_audit_log;

-- Data retention: xoa log cu hon 90 ngay
DELETE FROM mw_audit_log WHERE ts < NOW() - INTERVAL '90 days';
DELETE FROM mw_request_log WHERE ts < NOW() - INTERVAL '90 days';
```

---

## 5. QUAN LY LOGS

### 5.1. Cau truc log

| Log file       | Location               | Format        | Rotation            |
| -------------- | ---------------------- | ------------- | ------------------- |
| Audit log      | DB mw_audit_log        | JSONB payload | 90 ngay retention   |
| Request log    | DB mw_request_log      | JSONB         | 90 ngay retention   |
| Admin audit    | logs/admin_audit.jsonl | JSONL         | 20MB max, 5 backups |
| Container logs | Docker stdout          | Text          | Docker log driver   |

### 5.2. API quản lý logs

```
# Xem audit trail (24h gan nhat)
curl "http://localhost:5000/v1/_mw/admin/audit?minutes=1440" -H "X-Admin-Key: admin_master_key_456"

# Xem access logs (phan trang)
curl "http://localhost:5000/v1/_mw/admin/access-logs?page=1&page_size=50" -H "X-Admin-Key: admin_master_key_456"

# Xem summary metrics
curl "http://localhost:5000/v1/_mw/summary?minutes=60" -H "X-Admin-Key: admin_master_key_456"
```

### 5.3. Monitoring logs

```
# Xem logs container real-time
docker compose logs -f middleware --tail 100
docker compose logs -f litellm --tail 100

# Tim loi trong logs
docker compose logs middleware 2>&1 | findstr "ERROR"
docker compose logs middleware 2>&1 | findstr "500"

# Export logs
docker compose logs middleware > middleware_logs.txt 2>&1
```

### 5.4. Tìm kiếm trong DB logs

```sql
-- Tim requests loi
SELECT ts, user_id, model, status, payload->>'error' as error
FROM mw_audit_log WHERE status = 'error'
ORDER BY ts DESC LIMIT 20;

-- Tim requests cua 1 user
SELECT ts, model, status, tokens_total, cost_usd
FROM mw_audit_log WHERE user_id = 'admin'
ORDER BY ts DESC LIMIT 50;

-- Thống kê request theo model (24h)
SELECT model, COUNT(*) as calls, SUM(cost_usd) as total_cost
FROM mw_audit_log
WHERE ts > NOW() - INTERVAL '24 hours' AND status IN ('ok','reconciled')
GROUP BY model ORDER BY total_cost DESC;
```

---

## 6. QUAN LY NGƯỜI DÙNG

### 6.1. Hai hệ thống user

| Hệ thống   | Database            | Muc dich                | Quản lý qua         |
| ---------- | ------------------- | ----------------------- | ------------------- |
| Open WebUI | openwebui.user      | Đăng nhập web, chat     | Admin Panel (:3000) |
| Middleware | middleware.mw_users | Auth API, quota, subkey | Dashboard (:5000)   |

Luu y: Hai hệ thống độc lập - can tao user o CA HAI noi.

### 6.2. CRUD qua Dashboard

Truy cap: http://<server>:5000/dashboard > Tab Users

| Thao tac       | Hướng dẫn                                                           |
| -------------- | ------------------------------------------------------------------- |
| Tao user       | Add User > Dien user_id, role, quota, models > Create > Copy subkey |
| Sua user       | Edit > Sua truong can > Save                                        |
| Xoa user       | Delete > Confirm 2 lan (permanent)                                  |
| Rotate key     | Rotate > Confirm > Copy subkey moi                                  |
| Enable/Disable | Toggle > disabled user bi 403                                       |

### 6.3. CRUD qua API

```
# Tao user
curl -X POST http://localhost:5000/v1/_mw/admin/users \
  -H "X-Admin-Key: admin_master_key_456" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"alice\",\"role\":\"user\",\"limit_cost_usd\":5.0,\"allowed_models\":[\"*\"]}"

# Sua user
curl -X PATCH http://localhost:5000/v1/_mw/admin/users/alice \
  -H "X-Admin-Key: admin_master_key_456" \
  -H "Content-Type: application/json" \
  -d "{\"limit_cost_usd\":10.0,\"active\":true}"

# Xoa user
curl -X DELETE http://localhost:5000/v1/_mw/admin/users/alice \
  -H "X-Admin-Key: admin_master_key_456"

# Rotate key
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/rotate_key \
  -H "X-Admin-Key: admin_master_key_456"

# Disable user
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/disable \
  -H "X-Admin-Key: admin_master_key_456"

# Enable user
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/enable \
  -H "X-Admin-Key: admin_master_key_456"

# List all users
curl http://localhost:5000/v1/_mw/admin/users \
  -H "X-Admin-Key: admin_master_key_456"
```

### 6.4. Phân quyền (RBAC)

| Role    | Middleware API | Dashboard   | Admin Panel (WebUI) |
| ------- | -------------- | ----------- | ------------------- |
| admin   | Full CRUD      | Full access | Full admin          |
| manager | API access     | Read-only   | -                   |
| user    | API (limited)  | No access   | Standard user       |
| pending | No access      | No access   | Wait for approval   |

---

## 7. MONITORING VA HEALTH CHECK

### 7.1. Health Check API

```
# Middleware health
curl http://localhost:5000/health
# Expected: {"ok":true, "litellm":"ok", "database":"ok", ...}

# LiteLLM health
curl http://localhost:4000/health
# Expected: {"status":"healthy"}

# PostgreSQL
docker exec openwebui-postgres pg_isready -U openwebui_user -d openwebui
# Expected: accepting connections
```

### 7.2. Dashboard Metrics (7 Cards)

| Card         | Mo ta                            | Cảnh báo          |
| ------------ | -------------------------------- | ----------------- |
| LLM Calls    | Tong requests (chat+image+audio) | -                 |
| Admin Ops    | Thao tac admin                   | -                 |
| Pending      | Requests chua hoan thanh         | >10: kiểm tra     |
| Error Rate   | % loi                            | >5%: dieu tra     |
| P95 Latency  | 95th percentile ms               | >5000ms: kiểm tra |
| Total Tokens | Tokens da xu ly                  | -                 |
| Total Cost   | Chi phí USD                      | Theo budget       |

### 7.3. SSE Real-time Stream

Dashboard tự động kết nối SSE endpoint /v1/_mw/stream.
Events: audit (moi request moi). Auto-reconnect: 5 seconds.

### 7.4. Alerting

| Nguong       | Muc      | Hanh dong                  |
| ------------ | -------- | -------------------------- |
| Quota 80%    | WARNING  | Log cảnh báo               |
| Quota 95%    | CRITICAL | Log cảnh báo               |
| Quota 100%   | BLOCKED  | 403 Forbidden (auto-block) |
| Error > 5%   | WARNING  | Investigation needed       |
| Pending > 10 | WARNING  | LiteLLM check needed       |

---

## 8. BAO MAT

### 8.1. Authentication va Authorization

| Component      | Method                 | Secret                 |
| -------------- | ---------------------- | ---------------------- |
| Open WebUI     | Email/Password + JWT   | WEBUI_SECRET_KEY       |
| Middleware API | Subkey HMAC-SHA256     | MW_SECRET              |
| Dashboard      | Admin key + JWT cookie | ADMIN_KEY + JWT_SECRET |
| LiteLLM        | Master key             | LITELLM_KEY            |

### 8.2. Network Security (Docker)

Docker Compose sử dụng bridge network nội bộ. Cac services goi nhau bang container name.
LiteLLM (4000) va PostgreSQL (5432) KHONG bat buoc expose ra ngoai.

Firewall rules can thiet: Chi mo 2 ports ra ngoai:
- Port 3000: Open WebUI (giao diện người dùng)
- Port 5000: Middleware (API + Dashboard admin)

### 8.3. Data Security

| Dữ liệu          | Bao ve                     | Chi tiet                       |
| ---------------- | -------------------------- | ------------------------------ |
| Subkey           | HMAC-SHA256 (one-way hash) | Plaintext chi hien 1 lan       |
| JWT token        | HMAC-SHA256 signature      | 4h expiry, HttpOnly cookie     |
| Password (WebUI) | Bcrypt hash                | Salt + rounds                  |
| Database         | Docker volume              | Khong cloud, on-premise        |
| RAG embedding    | Local processing           | Tai lieu KHONG gui ra ngoai    |
| Chat content     | Gui qua API                | Gui toi OpenAI/Google de xu ly |

### 8.4. Security Best Practices

1. Rotate subkey moi 90 ngay hoac khi nghi ngo lo
2. Doi ADMIN_KEY sau khi deploy lan dau
3. Khong share file .env - them vao .gitignore
4. Backup database dinh ky (it nhat hang tuan)
5. Monitor audit logs cho hoat dong bat thuong
6. Tat dang ky tu do khi khong can: ENABLE_SIGNUP=false

---

## 9. TROUBLESHOOTING

### 9.1. Common Issues

| #   | Loi                     | Nguyen nhan                   | Giai phap                             |
| --- | ----------------------- | ----------------------------- | ------------------------------------- |
| 1   | Container khong start   | Port da bi chiem              | Kiểm tra port, kill process           |
| 2   | 401 Missing sub-key     | Thieu Authorization header    | Them Bearer <subkey>                  |
| 3   | 403 Invalid sub-key     | Subkey sai hoac user disabled | Rotate key hoac enable user           |
| 4   | 403 Quota exceeded      | Het quota                     | Reset quota hoac tang limit           |
| 5   | 502 LiteLLM unavailable | LiteLLM container down        | docker compose restart litellm        |
| 6   | Dashboard trang         | Session expired               | Reload, nhap lai admin key            |
| 7   | RAG khong tim thay      | File chua index xong          | Cho indexing, kiểm tra document_chunk |
| 8   | Image gen loi           | API key sai hoac model sai    | Kiểm tra .env va litellm_config.yaml  |

### 9.2. Debug Commands

```
# Kiểm tra containers
docker compose ps

# Kiểm tra ports
netstat -ano | findstr ":3000 :4000 :5000 :5432"

# Kiểm tra logs (error only)
docker compose logs middleware 2>&1 | findstr "ERROR CRITICAL"

# Kiểm tra database connectivity
docker exec openwebui-postgres pg_isready -U openwebui_user

# Kiểm tra disk space
docker system df

# Kiểm tra resource usage
docker stats --no-stream

# Test middleware health
curl http://localhost:5000/health

# Test LiteLLM
curl http://localhost:4000/health
```

---

## 10. MAINTENANCE

### 10.1. Daily Tasks

| Task                | Command / Action                 |
| ------------------- | -------------------------------- |
| Duyet user pending  | Admin Panel > Users > Approve    |
| Kiểm tra chi phí    | Dashboard > Overview tab         |
| Kiểm tra error rate | Dashboard > Error Rate card < 5% |

### 10.2. Weekly Tasks

| Task                    | Command / Action                 |
| ----------------------- | -------------------------------- |
| Review chi phí per user | Dashboard > Filter by user       |
| Backup database         | pg_dump command (xem section 12) |
| Kiểm tra disk space     | docker system df                 |
| Kiểm tra container      | docker compose ps - tat ca Up    |
| Review audit logs       | Dashboard > Logs tab             |

### 10.3. Monthly Tasks

| Task                 | Command / Action                     |
| -------------------- | ------------------------------------ |
| Update Docker images | docker compose pull && up -d         |
| Vacuum database      | VACUUM ANALYZE (xem section 4.4)     |
| Review quotas        | Dieu chinh theo actual usage         |
| Rotate admin key     | Doi ADMIN_KEY trong .env > restart   |
| Clean old logs       | Xoa mw_audit_log > 90 ngay           |
| Security review      | Kiểm tra .env, firewall, user access |

---

## 11. SCALING

### 11.1. Horizontal Scaling

```
# Scale middleware replicas
docker compose up -d --scale middleware=3

# Can load balancer (nginx/traefik) phia truoc
```

Luu y: Middleware stateless (DB-backed) - scale horizontally de dang.

### 11.2. Vertical Scaling

Tang resources trong docker-compose.yml:

| Service    | Parameter      | Gia tri khuyen nghi |
| ---------- | -------------- | ------------------- |
| middleware | memory limit   | 2G                  |
| middleware | cpus limit     | 2.0                 |
| postgres   | memory limit   | 4G                  |
| postgres   | cpus limit     | 4.0                 |
| postgres   | shared_buffers | 1GB                 |
| postgres   | work_mem       | 16MB                |

---

## 12. DISASTER RECOVERY

### 12.1. RTO / RPO

| Metric | Target    | Giai phap                |
| ------ | --------- | ------------------------ |
| RTO    | < 30 phut | Docker rebuild tu backup |
| RPO    | < 24 gio  | Daily database backup    |

### 12.2. Backup Strategy

```
# === DAILY BACKUP SCRIPT ===

# 1. Backup databases
docker exec openwebui-postgres pg_dump -U openwebui_user -d openwebui > backup\openwebui_%date%.sql
docker exec openwebui-postgres pg_dump -U openwebui_user -d middleware > backup\middleware_%date%.sql

# 2. Backup .env va config
copy .env backup\.env_backup
copy litellm\litellm_config.yaml backup\litellm_config_backup.yaml

# 3. Cleanup old backups (> 30 days)
forfiles /P backup /D -30 /C "cmd /c del @file"
```

### 12.3. Recovery Steps

```
# === DISASTER RECOVERY PROCEDURE ===

# Step 1: Ensure Docker is running
docker --version

# Step 2: Clone repository (neu mat code)
git clone https://github.com/ThanhDT127/Oppen_Web_UI.git
cd Oppen_Web_UI
git checkout dashboard

# Step 3: Restore .env
copy backup\.env_backup .env

# Step 4: Start stack
docker compose up -d

# Step 5: Wait for PostgreSQL to be ready (30 seconds)
timeout /t 30
docker exec openwebui-postgres pg_isready -U openwebui_user

# Step 6: Restore databases
type backup\openwebui_latest.sql | docker exec -i openwebui-postgres psql -U openwebui_user -d openwebui
type backup\middleware_latest.sql | docker exec -i openwebui-postgres psql -U openwebui_user -d middleware

# Step 7: Verify
curl http://localhost:5000/health
curl http://localhost:3000/api/health
```

---

## 13. SOURCE CODE VA REPOSITORY

### 13.1. Cau truc thư mục

```
Oppen_Web_UI/
  docker-compose.yml          # Stack orchestration
  .env                        # Environment secrets (NOT in git)
  .env.example                # Template
  .gitignore                  # Git ignore rules
  llm-mw/                     # Middleware source
    Dockerfile                # Container build
    main.py                   # FastAPI application
    config.py                 # Environment config
    requirements.txt          # Python deps
    core/                     # Core modules
    api/                      # API endpoints
    dashboard/                # Frontend SPA
    data/                     # JSON backups
  litellm/                    # LiteLLM config
    litellm_config.yaml       # 20 model definitions
  scripts/                    # Management scripts
    init_pgvector.sql         # DB initialization
  docs/                       # Documentation (12 files)
    01-tong-quan-he-thong.md
    02-tai-lieu-van-hanh.md
    ...
  function tool/              # Custom tools (export)
    tool_export_all.py        # Excel/PDF/Word export
```

### 13.2. Git Workflow

```
Branches:
  main                        # Production-ready
  dashboard                   # Latest development (User CRUD, docs)
  image                       # Image generation features
  docker-deployment-with-tests # Docker deployment
```

```
# Checkout development
git checkout dashboard

# Create feature branch
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "feat: description of changes"

# Push
git push -u origin feature/my-feature
```

---

## 14. INFRASTRUCTURE / DEVOPS

### 14.1. Docker Configuration

| Service    | Image                               | Healthcheck          | Restart        |
| ---------- | ----------------------------------- | -------------------- | -------------- |
| postgres   | pgvector/pgvector:0.8.0-pg16        | pg_isready every 10s | unless-stopped |
| litellm    | ghcr.io/berriai/litellm:main-latest | -                    | unless-stopped |
| middleware | ./llm-mw (custom build)             | -                    | unless-stopped |
| open-webui | ghcr.io/open-webui/open-webui:main  | -                    | unless-stopped |

### 14.2. Volumes va Persistence

| Volume         | Mounted to               | Data                           |
| -------------- | ------------------------ | ------------------------------ |
| postgres_data  | /var/lib/postgresql/data | All databases, tables, indexes |
| litellm_logs   | /app/logs                | LiteLLM request logs           |
| openwebui_data | /app/backend/data        | Uploaded files, user avatars   |

```
# List volumes
docker volume ls | findstr "oppen"

# Inspect volume
docker volume inspect oppen_web_ui_postgres_data

# Backup volume
docker run --rm -v oppen_web_ui_postgres_data:/data -v %cd%:/backup alpine tar czf /backup/postgres_data.tar.gz /data
```

### 14.3. Monitoring va Logging Stack

Hien tai:
- Docker logs (stdout/stderr)
- Middleware audit log (DB mw_audit_log)
- Admin audit file (logs/admin_audit.jsonl)
- Dashboard UI (real-time metrics)
- SSE stream (real-time events)

Khuyen nghi bo sung:
- Prometheus + Grafana (metrics visualization)
- Loki (centralized log aggregation)
- Alertmanager (email/Slack alerts)
- cAdvisor (container resource monitoring)

---

Tai lieu duoc tao ngay 06/03/2026. Phien ban 1.0.
Dua tren cau truc tham khao tu tai lieu vận hành RALLI AI Chatbot.
