# 15. Nginx Reverse Proxy + HTTPS

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Kiến trúc mạng](#2-kiến-trúc-mạng)
3. [Cấu hình Nginx](#3-cấu-hình-nginx)
4. [SSL Certificate](#4-ssl-certificate)
5. [Routing URL](#5-routing-url)
6. [Bảo mật](#6-bảo-mật)
7. [Vận hành](#7-vận-hành)

---

## 1. Tổng quan

**Nginx** đóng vai trò **Reverse Proxy** — cửa duy nhất từ internet vào hệ thống.

### Trước và Sau khi có Nginx

| STT |                 | Trước                               | Sau                               |
| --- | --------------- | ----------------------------------- | --------------------------------- |
| 01  | **Entry point** | 4 ports mở (3000, 5000, 4000, 5432) | **1 port duy nhất** (3000 HTTPS)  |
| 02  | **Mã hóa**      | ❌ HTTP plaintext                    | ✅ HTTPS (TLS 1.2/1.3)             |
| 03  | **Rate limit**  | ❌ Không có                          | ✅ 10 req/s chat, 10 req/phút login, 30 req/s API |
| 04  | **Nén dữ liệu** | ❌                                   | ✅ Gzip (nhanh hơn ~60%)           |
| 05  | **Database**    | ⚠️ Port 5432 mở                     | ✅ Ẩn hoàn toàn                    |

### Triển khai thực tế

| STT | Thông số                | Giá trị                                                |
| --- | ----------------------- | ------------------------------------------------------ |
| 01  | **Domain**              | `openwebui.rangdong.com.vn`                            |
| 02  | **Port ngoài (public)** | 51122                                                  |
| 03  | **Port trong (server)** | 3000                                                   |
| 04  | **NAT**                 | Firewall: 51122 → Server: 3000 → Nginx container: 3000 |
| 05  | **SSL cert**            | Wildcard `*.rangdong.com.vn` (công ty cung cấp)        |
| 06  | **Container**           | `openwebui-nginx` (image: nginx:alpine)                |
| 07  | **Tài nguyên**          | 1 CPU, 512MB RAM (dư thừa cho 200 users)               |

---

## 2. Kiến trúc mạng

```
Internet
    │
    ▼
Firewall công ty (do IT quản lý)
    │  NAT: port 51122 → 192.168.20.66:3000
    ▼
┌────────────────────────────────────────────────────────┐
│  Server 192.168.20.66 (20 CPU / 32GB RAM)              │
│                                                        │
│  ┌── Nginx (:3000 HTTPS) ──────────────────────────┐   │
│  │  SSL cert: *.rangdong.com.vn                    │   │
│  │  Gzip compression                               │   │
│  │  Rate limiting                                  │   │
│  │                                                 │   │
│  │  URL routing:                                   │   │
│  │  ├── /_app/*, /static/* → WebUI :8080 (cache)   │   │
│  │  ├── /ws/*          → WebUI :8080 (WS/SSE 24h)  │   │
│  │  ├── /api/*         → WebUI :8080 (30r/s)       │   │
│  │  ├── /api/v1/auths/ → WebUI :8080 (10r/phút)    │   │
│  │  ├── /dashboard     → Middleware :5000           │   │
│  │  ├── /v1/_mw/media/ → Middleware :5000 (cache)  │   │
│  │  ├── /v1/_mw/*      → Middleware :5000 (SSE)    │   │
│  │  ├── /v1/*          → Middleware :5000 (stream) │   │
│  │  └── /*             → WebUI :8080 (10r/s)       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                        │
│  Ports ĐÓNG: 5000, 5001, 4000, 5432, 6379, 8080        │
└────────────────────────────────────────────────────────┘
```

---

## 3. Cấu hình Nginx

**File:** `nginx/nginx.conf`

### 3.1 Cấu hình chung

| STT | Tham số                | Giá trị | Ý nghĩa                                        |
| --- | ---------------------- | ------- | ---------------------------------------------- |
| 01  | `worker_processes`     | auto    | Số tiến trình = số CPU                         |
| 02  | `worker_connections`   | 2048    | Mỗi worker xử lý tối đa 2048 kết nối           |
| 03  | `gzip on`              | —       | Nén response (JS, CSS, JSON) → nhanh hơn ~60%  |
| 04  | `client_max_body_size` | 100M    | Upload file tối đa 100MB                       |
| 05  | `http2 on`             | —       | HTTP/2 enabled — giảm latency, multiplex       |

### 3.2 Rate Limiting

| STT | Zone    | Rate        | Burst | Áp dụng                   | Mục đích                   |
| --- | ------- | ----------- | ----- | ------------------------- | -------------------------- |
| 01  | `chat`  | 10 req/s    | 50    | `/`, `/v1/_mw/*`          | Chống spam chat / MW API   |
| 02  | `login` | 10 req/phút | 5     | `/api/v1/auths/`          | Chống brute force login    |
| 03  | `api`   | 30 req/s    | 60    | `/api/*` (Open WebUI API) | Rate limit API nội bộ WebUI|

### 3.3 Timeout

| STT | Tham số                 | Giá trị        | Áp dụng              | Lý do                                        |
| --- | ----------------------- | -------------- | -------------------- | -------------------------------------------- |
| 01  | `proxy_read_timeout`    | 300s           | `/v1/*`, mặc định    | LLM response có thể mất 1-2 phút (câu dài)   |
| 02  | `proxy_send_timeout`    | 300s           | Mặc định             | Upload file lớn cần thời gian                |
| 03  | `proxy_connect_timeout` | 10s            | Mặc định             | Kết nối backend nhanh (cùng Docker network)  |
| 04  | `proxy_read_timeout`    | **86400s (24h)** | `/ws/` (WebSocket) | Socket.IO persistent connection (lâu dài)    |

> **Timeout không tốn tài nguyên** — chỉ là "chờ tối đa bao lâu". Nếu LLM trả lời trong 5s thì gửi ngay, không chờ 300s.

### 3.4 SSL

| STT | Tham số               | Giá trị                        | Ý nghĩa                           |
| --- | --------------------- | ------------------------------ | --------------------------------- |
| 01  | `ssl_protocols`       | TLSv1.2 TLSv1.3                | Chỉ dùng bản mã hóa mới (bảo mật) |
| 02  | `ssl_ciphers`         | HIGH:!aNULL:!MD5               | Cấm thuật toán yếu                |
| 03  | `ssl_certificate`     | `/etc/nginx/ssl/fullchain.pem` | Cert + CA bundle                  |
| 04  | `ssl_certificate_key` | `/etc/nginx/ssl/privkey.pem`   | Private key                       |

### 3.5 SSE/Streaming

Dashboard middleware dùng **Server-Sent Events** (SSE) để cập nhật real-time. Cấu hình đặc biệt:

```nginx
proxy_buffering off;             # Gửi thẳng, không buffer → real-time
proxy_cache off;                 # Không cache stream data
proxy_set_header Connection '';  # SSE không cần upgrade
chunked_transfer_encoding off;   # Tắt chunked cho SSE
```

---

## 4. SSL Certificate

### Nguồn gốc

Cert **wildcard `*.rangdong.com.vn`** do công ty mua, IT (anh Huy) cung cấp.

### File cert

| STT | File            | Nguồn                                            | Vị trí                    |
| --- | --------------- | ------------------------------------------------ | ------------------------- |
| 01  | `fullchain.pem` | Gộp từ `STAR.rangdong.com.vn.crt` + `.ca-bundle` | `nginx/ssl/fullchain.pem` |
| 02  | `privkey.pem`   | Copy từ `STAR.rangdong.com.vn_key.txt`           | `nginx/ssl/privkey.pem`   |

### Gộp cert chuẩn

```
fullchain.pem = Server cert (.crt) + Intermediate CA (.ca-bundle)
              = "Ổ khóa" mà browser dùng để mã hóa

privkey.pem   = Private key
              = "Chìa khóa" chỉ server giữ để giải mã
```

### Gia hạn

Cert có thời hạn (thường 1 năm). Khi hết hạn, yêu cầu IT cung cấp cert mới → copy đè → restart Nginx.

---

## 5. Routing URL

### Bảng routing chi tiết

| STT | URL                | Location          | Backend     | Rate Limit   | Ghi chú                                  |
| --- | ------------------ | ----------------- | ----------- | ------------ | ---------------------------------------- |
| 01  | `/_app/*`          | `/_app/`          | WebUI :8080 | ❌ Không      | Static JS/CSS (cache 1h)                 |
| 02  | `/static/*`        | `/static/`        | WebUI :8080 | ❌ Không      | Hình ảnh, fonts (cache 1h)               |
| 03  | `/ws/*`            | `/ws/`            | WebUI :8080 | ❌ Không      | Socket.IO (WS + polling, timeout **24h**)|
| 04  | `/api/v1/auths/*`  | `/api/v1/auths/`  | WebUI :8080 | **10 req/phút** (burst 5) | Login (chống brute force)  |
| 05  | `/api/*`           | `/api/`           | WebUI :8080 | 30 req/s (burst 60)       | Open WebUI API nội bộ     |
| 06  | `/dashboard*`      | `/dashboard`      | MW :5000    | ❌ Không      | Admin dashboard SPA                      |
| 07  | `/v1/_mw/media/*`  | `/v1/_mw/media/`  | MW :5000    | ❌ Không      | AI-generated images (cache 1d, CORS)     |
| 08  | `/v1/_mw/*`        | `/v1/_mw/`        | MW :5000    | 10 req/s (burst 20)       | MW API + SSE stream       |
| 09  | `/v1/*`            | `/v1/`            | MW :5000    | ❌ Không      | LLM chat API (streaming, no rate limit)  |
| 10  | `/*`               | `/`               | WebUI :8080 | 10 req/s (burst 50)       | Trang chính, catch-all    |

### Thứ tự ưu tiên

Nginx kiểm tra URL từ **cụ thể → chung**. URL `/dashboard/js/main.js` khớp `/dashboard` (không phải `/`).

---

## 6. Bảo mật

### Ports đã đóng

| STT | Service    | Port cũ (mở) | Port mới | Trạng thái     |
| --- | ---------- | ------------ | -------- | -------------- |
| 01  | PostgreSQL | 5432         | Internal | ✅ Đóng         |
| 02  | LiteLLM    | 4000         | Internal | ✅ Đóng         |
| 03  | Middleware | 5000         | Internal | ✅ Đóng         |
| 04  | Open WebUI | 3000→8080    | Internal | ✅ Đóng         |
| 05  | **Nginx**  | —            | **3000** | 🔓 Cửa duy nhất |

### Cookie Security

Dashboard middleware dùng cookie session với `secure=True` → chỉ gửi qua HTTPS.

---

## 7. Vận hành

### Lệnh thường dùng

```bash
# Kiểm tra config Nginx (không cần restart)
docker exec openwebui-nginx nginx -t

# Reload config (không downtime)
docker exec openwebui-nginx nginx -s reload

# Xem log truy cập
docker logs openwebui-nginx --tail 50

# Xem log lỗi
docker logs openwebui-nginx --tail 50 2>&1 | findstr "error"

# Restart toàn bộ
docker compose restart nginx
```

### Gia hạn SSL cert

```bash
# 1. Copy cert mới
copy "fullchain_moi.pem" nginx\ssl\fullchain.pem
copy "privkey_moi.pem" nginx\ssl\privkey.pem

# 2. Reload (không restart)
docker exec openwebui-nginx nginx -s reload
```

### Troubleshooting

| STT | Lỗi                          | Nguyên nhân        | Fix                              |
| --- | ---------------------------- | ------------------ | -------------------------------- |
| 01  | 502 Bad Gateway              | Backend chưa start | `docker compose restart`         |
| 02  | 503 Service Unavailable      | Rate limit vượt    | Tăng `burst` hoặc `rate`         |
| 03  | 413 Request Entity Too Large | File > 100MB       | Tăng `client_max_body_size`      |
| 04  | SSL cert expired             | Hết hạn cert       | Yêu cầu IT cung cấp cert mới     |
| 05  | ERR_CONNECTION_REFUSED       | NAT chưa đúng      | Kiểm tra firewall NAT 51122→3000 |
