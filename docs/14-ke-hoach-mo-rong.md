# 14. Kế hoạch Mở rộng Hệ thống — 200 Users

## Mục lục

1. [Tổng quan](#tổng-quan)
2. [Hiện trạng hệ thống](#hiện-trạng-hệ-thống)
3. [Các vấn đề cần giải quyết](#các-vấn-đề-cần-giải-quyết)
4. [Phase 1 — Tối ưu 1 Server](#phase-1--tối-ưu-1-server)
5. [Phase 2 — Scale Ngang (Docker Replicas)](#phase-2--scale-ngang-docker-replicas)
6. [Phase 3 — Multi-Server (Docker Swarm)](#phase-3--multi-server-docker-swarm)
7. [Chiến lược Load Balancing](#chiến-lược-load-balancing)
8. [Bảo mật](#bảo-mật)
9. [Checklist thực thi](#checklist-thực-thi)

---

## 1. Tổng quan

**Server mục tiêu:** 18 CPU / 32GB RAM
**Yêu cầu:** 200 users đăng ký, 50+ người dùng đồng thời

### Tóm tắt 3 Phase

| STT | Phase | Users | Đồng thời | Chi phí thêm   | Phức tạp      | Thời gian |
| --- | ----- | ----- | --------- | -------------- | ------------- | --------- |
| 01  | **1** | 200   | 50-80     | $0             | ⭐ Thấp        | 1-2 ngày  |
| 02  | **2** | 500   | 100-150   | $0             | ⭐⭐ Trung bình | 1 tuần    |
| 03  | **3** | 1000+ | 200+      | +$50-300/tháng | ⭐⭐⭐ Cao       | 2-4 tuần  |

---

## 2. Hiện trạng hệ thống

### Kiến trúc hiện tại

```
Internet (KHÔNG CÓ NGINX)
    │
    ├── :3000  → Open WebUI   (1 container, 1 worker mặc định)
    ├── :5000  → Middleware    (1 container, 1 uvicorn worker)
    ├── :4000  → LiteLLM      (1 container, 1 process)
    ├── :5432  → PostgreSQL   (EXPOSED ra ngoài!)
    └── (internal) SearXNG    (limiter TẮT)
```

### Thông số hiện tại

| STT | Service    | Workers      | DB pool       | RAM limit      | Vấn đề               |
| --- | ---------- | ------------ | ------------- | -------------- | -------------------- |
| 01  | Open WebUI | 1 (mặc định) | —             | Không giới hạn | Chậm khi nhiều user  |
| 02  | Middleware | 1            | min=2, max=10 | Không giới hạn | Bottleneck DB        |
| 03  | LiteLLM    | 1            | —             | Không giới hạn | Không rate limit     |
| 04  | PostgreSQL | —            | max_conn=100  | Không giới hạn | Không đủ connections |
| 05  | SearXNG    | 1            | —             | Không giới hạn | Google sẽ ban        |

---

## 3. Các vấn đề cần giải quyết

| #  | Vấn đề                                        | Mức độ     | Loại      |
| -- | --------------------------------------------- | ---------- | --------- |
| 1  | PostgreSQL port 5432 EXPOSED                  | 🔴 Critical | Bảo mật   |
| 2  | LiteLLM port 4000 EXPOSED (bypass middleware) | 🔴 Critical | Bảo mật   |
| 3  | Không có Nginx / HTTPS                        | 🔴 Critical | Bảo mật   |
| 4  | Middleware 1 worker                           | 🟡 High     | Hiệu năng |
| 5  | LiteLLM 1 worker, không rate limit            | 🟡 High     | Hiệu năng |
| 6  | DB pool max=10                                | 🟡 High     | Hiệu năng |
| 7  | PostgreSQL max_connections=100                | 🟡 High     | Hiệu năng |
| 8  | SearXNG limiter TẮT                           | 🟡 Medium   | Ổn định   |
| 9  | ENABLE_SIGNUP=true                            | 🟡 Medium   | Bảo mật   |
| 10 | Không có Docker resource limits               | 🟡 Medium   | Ổn định   |

---

## 4. Phase 1 — Tối ưu 1 Server

**Mục tiêu:** 200 users, 50-80 đồng thời trên 1 server 18 CPU / 32GB

### 4.1 Kiến trúc mục tiêu Phase 1

```
Internet
    │
    ▼
┌──────────────────────────────────────────────────┐
│  Nginx (:443 HTTPS, :80 redirect)                │
│  ├── Rate limiting (30 req/phút per IP)          │
│  ├── Gzip compression                            │
│  ├── Static file caching                         │
│  └── SSL termination                             │
│       │                                          │
│  ┌────┴──────────────────────────┐               │
│  ▼                               ▼               │
│  Open WebUI (:8080)      Middleware (:5000)       │
│  6 workers               4 workers               │
│       │                       │                  │
│       │                LiteLLM (:4000)           │
│       │                4 workers                 │
│       │                rpm per model             │
│       │                       │                  │
│       └──────────┬────────────┘                  │
│                  ▼                               │
│  PostgreSQL (INTERNAL ONLY)                      │
│  max_connections=300, shared_buffers=4GB          │
│                                                  │
│  SearXNG (INTERNAL) + Redis (limiter)            │
└──────────────────────────────────────────────────┘
```

### 4.2 Phân bổ tài nguyên (18 CPU / 32GB)

| STT | Service        | Workers | CPU limit | RAM limit      | RAM reserve |
| --- | -------------- | ------- | --------- | -------------- | ----------- |
| 01  | **Open WebUI** | **6**   | 6         | 10GB           | 4GB         |
| 02  | **Middleware** | **4**   | 4         | 2GB            | 512MB       |
| 03  | **LiteLLM**    | **4**   | 4         | 4GB            | 1GB         |
| 04  | **PostgreSQL** | —       | 2         | 8GB            | 4GB         |
| 05  | **SearXNG**    | —       | 1         | 1GB            | 256MB       |
| 06  | **Nginx**      | auto    | 1         | 512MB          | 128MB       |
| 07  | **Redis**      | —       | 0.5       | 256MB          | 64MB        |
| 08  | **Tổng**       | **14**  | **18.5**  | **~26GB/32GB** | **~10GB**   |

### 4.3 Nginx — Reverse Proxy + HTTPS

**Tạo file:** `nginx/nginx.conf`

```nginx
worker_processes auto;
events { worker_connections 2048; }

http {
    # ─── Rate Limiting ───
    limit_req_zone $binary_remote_addr zone=chat:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # ─── Gzip ───
    gzip on;
    gzip_types text/css application/javascript application/json text/plain;
    gzip_min_length 1000;

    # ─── Upstreams ───
    upstream webui  { server open-webui:8080; }
    upstream mw_api { server middleware:5000; }

    # ─── HTTPS Server ───
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate     /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Streaming timeout (LLM response lâu)
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_connect_timeout 10s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # ─── Open WebUI ───
        location / {
            proxy_pass http://webui;
            limit_req zone=chat burst=20 nodelay;
        }

        # ─── Middleware Dashboard ───
        location /v1/_mw/ {
            proxy_pass http://mw_api;
            limit_req zone=api burst=10;
        }

        # ─── Login — chống brute force ───
        location /api/v1/auths/ {
            proxy_pass http://webui;
            limit_req zone=login burst=3;
        }

        # ─── Static files caching ───
        location ~* \.(css|js|png|jpg|ico|woff2)$ {
            proxy_pass http://webui;
            expires 7d;
            add_header Cache-Control "public, immutable";
        }
    }

    # ─── Redirect HTTP → HTTPS ───
    server {
        listen 80;
        return 301 https://$host$request_uri;
    }
}
```

**Thêm vào docker-compose.yml:**

```yaml
nginx:
  image: nginx:alpine
  container_name: openwebui-nginx
  ports:
    - "443:443"
    - "80:80"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/ssl:/etc/nginx/ssl:ro
  depends_on:
    - open-webui
    - middleware
  restart: unless-stopped
  networks:
    - openwebui-network
  deploy:
    resources:
      limits: { memory: 512M, cpus: '1' }
```

### 4.4 Đóng Ports (Bảo mật)

**Thay đổi trong docker-compose.yml:**

```diff
  postgres:
-   ports:
-     - "5432:5432"
+   # ports: REMOVED — internal only

  litellm:
-   ports:
-     - "4000:4000"
+   # ports: REMOVED — internal only

  middleware:
-   ports:
-     - "5000:5000"
+   # ports: REMOVED — accessed via Nginx

  open-webui:
-   ports:
-     - "3000:8080"
+   # ports: REMOVED — accessed via Nginx
```

### 4.5 Middleware — Tăng Workers + DB Pool

**Dockerfile (llm-mw/Dockerfile):**

```diff
- CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
+ CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
```

**core/db.py:**

```diff
- init_pool(database_url, minconn=2, maxconn=10)
+ init_pool(database_url, minconn=10, maxconn=50)
```

### 4.6 LiteLLM — Workers + Rate Limiting

**docker-compose.yml:**

```diff
  litellm:
-   command: ["--config", "/app/config.yaml", "--port", "4000", "--detailed_debug"]
+   command: ["--config", "/app/config.yaml", "--port", "4000", "--num_workers", "4"]
```

**litellm/litellm_config.yaml — thêm:**

```yaml
litellm_settings:
  num_workers: 4
  request_timeout: 120        # Timeout 2 phút

general_settings:
  max_parallel_requests: 50   # Tối đa 50 requests đồng thời
  verbose: false              # Tắt verbose ở production
  master_key: os.environ/LITELLM_KEY
```

**Rate limit per model (thêm vào model_list):**

```yaml
model_list:
  - model_name: chat-gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
      rpm: 400               # Giới hạn 400/phút (provider limit: 500)
      tpm: 25000              # Giới hạn 25K tokens/phút

  - model_name: chat-gpt-5
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY
      rpm: 80                 # Giới hạn 80/phút (provider limit: 100)
      tpm: 8000

  - model_name: chat-gemini-2.5-pro
    litellm_params:
      model: gemini/gemini-2.5-pro
      api_key: os.environ/GEMINI_API_KEY
      rpm: 800                # Giới hạn 800/phút (provider limit: 1000)
```

### 4.7 Open WebUI — Workers + Bảo mật

**docker-compose.yml:**

```diff
  open-webui:
    environment:
+     - UVICORN_WORKERS=6
+     - ENABLE_SIGNUP=false
+     - DEFAULT_USER_ROLE=pending
+     - ENABLE_COMMUNITY_SHARING=false
```

### 4.8 PostgreSQL — Tuning

**docker-compose.yml:**

```diff
  postgres:
+   command: >
+     postgres
+     -c max_connections=300
+     -c shared_buffers=4GB
+     -c work_mem=16MB
+     -c effective_cache_size=8GB
+     -c maintenance_work_mem=256MB
+     -c wal_buffers=64MB
+     -c random_page_cost=1.1
+     -c checkpoint_completion_target=0.9
+   deploy:
+     resources:
+       limits: { memory: 8G, cpus: '2' }
```

**Tính toán DB connections:**

```
Middleware:   4 workers × 50 pool = 200
Open WebUI:  ~30 connections
LiteLLM:     ~20 connections
Tổng:        ~250 → max_connections = 300 ✅
```

### 4.9 SearXNG + Redis

**docker-compose.yml — thêm Redis:**

```yaml
redis:
  image: redis:7-alpine
  container_name: openwebui-redis
  restart: unless-stopped
  deploy:
    resources:
      limits: { memory: 256M, cpus: '0.5' }
  networks:
    - openwebui-network
```

**SearXNG environment — thêm:**

```yaml
searxng:
  environment:
    - SEARXNG_BASE_URL=http://searxng:8080
    - SEARXNG_REDIS_URL=redis://redis:6379/0
```

**searxng/settings.yml — sửa:**

```yaml
server:
  limiter: true               # BẬT rate limiter
  public_instance: false

engines:
  - name: google
    engine: google
    disabled: true            # TẮT (hay bị ban nhất)
  - name: duckduckgo
    engine: duckduckgo
    disabled: false
  - name: bing
    engine: bing
    disabled: false
  - name: brave
    engine: brave
    disabled: false
```

### 4.10 Docker Resource Limits

**Tất cả services trong docker-compose.yml:**

```yaml
open-webui:
  deploy:
    resources:
      limits:       { memory: 10G, cpus: '6' }
      reservations: { memory: 4G }

middleware:
  deploy:
    resources:
      limits:       { memory: 2G, cpus: '4' }
      reservations: { memory: 512M }

litellm:
  deploy:
    resources:
      limits:       { memory: 4G, cpus: '4' }
      reservations: { memory: 1G }

postgres:
  deploy:
    resources:
      limits:       { memory: 8G, cpus: '2' }
      reservations: { memory: 4G }

searxng:
  deploy:
    resources:
      limits:       { memory: 1G, cpus: '1' }
      reservations: { memory: 256M }
```

### 4.11 Năng lực Phase 1

| STT | Chỉ số          | Hiện tại (1 worker) | Phase 1 (tối ưu) |
| --- | --------------- | ------------------- | ---------------- |
| 01  | Users đăng ký   | ~50                 | **200-300**      |
| 02  | Online cùng lúc | ~20                 | **100-150**      |
| 03  | Chat đồng thời  | ~10                 | **50-80**        |
| 04  | Web search/giờ  | ~10                 | **~60**          |
| 05  | Throughput      | ~10 req/s           | **~60-80 req/s** |

### 4.12 Giới hạn API Provider (không liên quan server)

| STT | Provider         | RPM (trả phí) | 50 user đồng thời | Đủ?    |
| --- | ---------------- | ------------- | ----------------- | ------ |
| 01  | OpenAI GPT-4o    | 500           | ~50 req cùng lúc  | ✅      |
| 02  | OpenAI GPT-5     | 100           | ~50 req cùng lúc  | ⚠️ Sát |
| 03  | Gemini 2.5 Pro   | 1000          | ~50 req cùng lúc  | ✅      |
| 04  | Gemini 2.5 Flash | 2000          | ~50 req cùng lúc  | ✅      |

> **Lưu ý:** Nếu 50 người cùng dùng GPT-5, có thể vượt rate limit 100 RPM. Giải pháp: phân tải giữa các model hoặc tăng API tier.

---

## 5. Phase 2 — Scale Ngang (Docker Replicas)

**Khi nào cần:** Vượt 300 users hoặc 80 đồng thời thường xuyên

### 5.1 Kiến trúc Phase 2

```
                        Nginx (Load Balancer)
                        ┌────────┤────────┐
                        ▼        ▼        ▼
                   WebUI #1  WebUI #2  WebUI #3   ← 3 replicas
                        │        │        │
                        └────────┤────────┘
                                 ▼
                     Redis (Sessions + Cache)
                                 │
                        ┌────────┤────────┐
                        ▼        ▼        ▼
                     MW #1    MW #2    MW #3       ← 3 replicas
                        │        │        │
                        └────────┤────────┘
                                 ▼
                   LiteLLM #1  LiteLLM #2          ← 2 replicas
                        │        │
                        └────────┤
                                 ▼
                            PostgreSQL
```

### 5.2 Yêu cầu thêm cho Phase 2

| STT | Yêu cầu                     | Mục đích                              | Trạng thái               |
| --- | --------------------------- | ------------------------------------- | ------------------------ |
| 01  | **Redis**                   | Session management giữa các instances | ✅ Đã thêm Phase 1        |
| 02  | **Shared WEBUI_SECRET_KEY** | Đồng bộ JWT token                     | ✅ Đã có                  |
| 03  | **PostgreSQL (external)**   | Shared database                       | ✅ Đang dùng              |
| 04  | **PGVector (external)**     | Shared vector DB                      | ✅ Đang dùng              |
| 05  | **Shared storage**          | Upload files, cache                   | ⚠️ Cần NFS/shared volume |

### 5.3 Docker-compose Phase 2

```yaml
open-webui:
  deploy:
    replicas: 3                    # ← 3 instances
    resources:
      limits: { memory: 4G, cpus: '2' }
  environment:
    - UVICORN_WORKERS=2            # 2 workers × 3 replicas = 6 tổng
    - REDIS_URL=redis://redis:6379/0
    - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}

middleware:
  deploy:
    replicas: 2
    resources:
      limits: { memory: 1G, cpus: '2' }

litellm:
  deploy:
    replicas: 2
    resources:
      limits: { memory: 2G, cpus: '2' }
```

### 5.4 Nginx Load Balancing Phase 2

```nginx
upstream webui {
    least_conn;                    # Gửi đến instance ít connection nhất
    server open-webui:8080;        # Docker DNS tự resolve replicas
}

upstream mw_api {
    least_conn;
    server middleware:5000;
}
```

### 5.5 Năng lực Phase 2

| STT | Chỉ số          | Phase 1 | Phase 2            |
| --- | --------------- | ------- | ------------------ |
| 01  | Chat đồng thời  | 50-80   | **100-150**        |
| 02  | Online cùng lúc | 100-150 | **300-400**        |
| 03  | Users đăng ký   | 200-300 | **500+**           |
| 04  | Fault tolerance | ❌       | ✅ (1 chết → còn 2) |

---

## 6. Phase 3 — Multi-Server (Docker Swarm)

**Khi nào cần:** Vượt 500 users, cần high availability (99.9% uptime)

### 6.1 Kiến trúc Multi-Server

```
                    DNS / CDN (Cloudflare)
                            │
                    ┌───────┤───────┐
                    ▼               ▼
            ┌── Server 1 ──┐  ┌── Server 2 ──┐
            │ Nginx (LB)   │  │              │
            │ WebUI ×2     │  │ WebUI ×2     │
            │ Middleware ×1│  │ Middleware ×1│
            │ LiteLLM ×1  │  │ LiteLLM ×1  │
            └──────┬───────┘  └──────┬───────┘
                   │                 │
                   └────────┬────────┘
                            ▼
                    ┌── Server 3 ──┐
                    │ PostgreSQL   │
                    │ Redis        │
                    │ SearXNG      │
                    └──────────────┘
```

### 6.2 Công nghệ lựa chọn

| STT | Công nghệ           | Phức tạp | Khi nào dùng             |
| --- | ------------------- | -------- | ------------------------ |
| 01  | **Docker Swarm**    | ⭐⭐       | 200-1000 users, team nhỏ |
| 02  | **Kubernetes**      | ⭐⭐⭐⭐     | 1000+ users, team DevOps |
| 03  | **Cloud (AWS/GCP)** | ⭐⭐       | Có budget, cần nhanh     |

### 6.3 Docker Swarm Setup

```bash
# Server 1 — Manager node
docker swarm init --advertise-addr 192.168.20.66

# Server 2 — Worker node
docker swarm join --token <TOKEN> 192.168.20.66:2377

# Deploy
docker stack deploy -c docker-stack.yml openwebui
```

### 6.4 Năng lực Phase 3

| STT | Chỉ số          | Phase 2 | Phase 3 (2 servers) | Phase 3 (4 servers) |
| --- | --------------- | ------- | ------------------- | ------------------- |
| 01  | Chat đồng thời  | 100-150 | **200-300**         | **500+**            |
| 02  | Users đăng ký   | 500     | **1000**            | **2000+**           |
| 03  | Fault tolerance | Partial | ✅ Full              | ✅ Full              |
| 04  | Chi phí thêm    | $0      | +$50-100/tháng      | +$150-300/tháng     |

---

## 7. Chiến lược Load Balancing

### 7.1 Các phương pháp

| STT | Chiến lược            | Cách hoạt động                   | Khi nào dùng          |
| --- | --------------------- | -------------------------------- | --------------------- |
| 01  | **Round Robin**       | Luân phiên đều giữa các instance | Đơn giản, tải đều     |
| 02  | **Least Connections** | Gửi đến instance ít việc nhất    | **Tốt nhất cho chat** |
| 03  | **IP Hash**           | Cùng IP → cùng instance          | Khi KHÔNG có Redis    |
| 04  | **Weighted**          | Instance mạnh nhận nhiều hơn     | Khi server khác spec  |

### 7.2 Khuyến nghị

**`least_conn`** — vì chat streaming giữ connection 5-30 giây. Round Robin có thể dồn hết vào 1 instance đang bận streaming.

### 7.3 Load Balancing ở từng tầng

```
Tầng 1: DNS Load Balancing (Phase 3)
    → Cloudflare/Route53 phân tải giữa servers
    → Giá: $0-20/tháng

Tầng 2: Nginx Load Balancing (Phase 1-2)
    → Phân tải giữa container replicas
    → Giá: $0

Tầng 3: LiteLLM Model Routing (Phase 1)
    → Phân tải giữa API providers
    → Ví dụ: GPT-4o overload → fallback Gemini
    → Giá: $0

Tầng 4: Application-level (Phase 1)
    → Open WebUI: WebSocket connection pool
    → Middleware: async request handling
    → Giá: $0
```

### 7.4 So sánh với mô hình Facebook

| STT | Khía cạnh     | Facebook          | Hệ thống này         |
| --- | ------------- | ----------------- | -------------------- |
| 01  | Quy mô        | 3 tỷ users        | 200 users            |
| 02  | Servers       | 100,000+          | 1-3                  |
| 03  | Load Balancer | Custom L4/L7      | Nginx                |
| 04  | Database      | Sharded MySQL     | 1 PostgreSQL         |
| 05  | Cache         | Memcached cluster | Redis (1 instance)   |
| 06  | CDN           | Tự xây            | Cloudflare (nếu cần) |

→ **Nguyên lý giống nhau** (phân tầng, replicas, load balancing), chỉ khác quy mô.

---

## 8. Bảo mật

### 8.1 Các vector tấn công và giải pháp

| STT | Vector             | Hiện trạng | Giải pháp                | Phase |
| --- | ------------------ | ---------- | ------------------------ | ----- |
| 01  | PostgreSQL exposed | ❌ Mở       | Đóng port, internal only | 1     |
| 02  | LiteLLM exposed    | ❌ Mở       | Đóng port, internal only | 1     |
| 03  | Không HTTPS        | ❌          | Nginx + SSL certificate  | 1     |
| 04  | Không rate limit   | ❌          | Nginx limit_req zones    | 1     |
| 05  | ENABLE_SIGNUP=true | ❌          | Đổi false, admin tạo TK  | 1     |
| 06  | Brute force login  | ❌          | Nginx rate limit 5r/m    | 1     |
| 07  | DDoS               | ❌          | Nginx + Cloudflare       | 2-3   |
| 08  | API key sniffing   | ❌          | HTTPS                    | 1     |

### 8.2 SSL Certificate

| STT | Loại            | Giá        | Phù hợp            |
| --- | --------------- | ---------- | ------------------ |
| 01  | Self-signed     | $0         | ✅ Nội bộ công ty   |
| 02  | Let's Encrypt   | $0         | ✅ Có domain public |
| 03  | Mua certificate | $10-50/năm | ✅ Production       |

**Tạo self-signed (nội bộ):**

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/CN=openwebui.company.local"
```

---

## 9. Checklist thực thi

### Phase 1 (ĐÃ HOÀN THÀNH ✅ — 24/03/2026)

**Bảo mật:**

- [x] Xóa `ports` của postgres trong docker-compose
- [x] Xóa `ports` của litellm trong docker-compose
- [x] Xóa `ports` của middleware trong docker-compose
- [x] Xóa `ports` của open-webui trong docker-compose
- [x] Tạo `nginx/nginx.conf`
- [x] SSL certificate (wildcard *.rangdong.com.vn)
- [x] Thêm Nginx service vào docker-compose
- [x] `DEFAULT_USER_ROLE=pending`

**Hiệu năng:**

- [x] Middleware Dockerfile: thêm `--workers 4`
- [x] Middleware config.py: tăng `maxconn=30`
- [x] LiteLLM command: thêm `--num_workers 4`, bỏ `--detailed_debug`
- [x] LiteLLM config: thêm `max_parallel_requests: 50`
- [x] Open WebUI: thêm `UVICORN_WORKERS=6`
- [x] PostgreSQL: thêm tuning parameters trong command

**Ổn định:**

- [x] Thêm Redis service vào docker-compose
- [x] SearXNG: disable Google engine
- [x] SearXNG: thêm `SEARXNG_REDIS_URL`
- [x] Thêm `deploy.resources.limits` cho tất cả services

**Kiểm tra:**

- [x] `docker compose build`
- [x] `docker compose up -d`
- [x] Test login, chat, web search, dashboard
- [x] Kiểm tra logs: `docker logs openwebui-nginx`
- [x] Verify HTTPS hoạt động

### Phase 2 (Khi cần)

- [ ] Cấu hình Open WebUI dùng Redis cho sessions
- [ ] Tăng replicas cho open-webui, middleware, litellm
- [ ] Cấu hình shared storage (NFS) nếu cần
- [ ] Test failover (kill 1 instance, verify vẫn hoạt động)

### Phase 3 (Tương lai)

- [ ] Chuẩn bị server thứ 2
- [ ] Setup Docker Swarm
- [ ] Migrate sang docker-stack.yml
- [ ] Setup DNS load balancing (Cloudflare)
- [ ] Test cross-server communication
