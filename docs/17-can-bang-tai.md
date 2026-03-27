# 17. Cân bằng Tải và Quản lý Request

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Phân bổ tài nguyên Server](#2-phân-bổ-tài-nguyên-server)
3. [Cân bằng tại Nginx](#3-cân-bằng-tại-nginx)
4. [Cân bằng tại LiteLLM](#4-cân-bằng-tại-litellm)
5. [Cân bằng tại Middleware](#5-cân-bằng-tại-middleware)
6. [Tăng RPM API Provider](#6-tăng-rpm-api-provider)
7. [Bottleneck thực tế](#7-bottleneck-thực-tế)

---

## 1. Tổng quan

Hệ thống cân bằng tải ở **4 tầng**:

```
Tầng 1: Nginx (Rate limiting + routing)
    │
    ▼
Tầng 2: Open WebUI (6 workers xử lý HTTP requests)
    │
    ▼
Tầng 3: Middleware (4 workers check quota + proxy)
    │
    ▼
Tầng 4: LiteLLM (4 workers + rpm/tpm per model → API providers)
```

### Năng lực hiện tại (Phase 1 — ĐÃ TRIỂN KHAI)

| Chỉ số | Giá trị |
|--------|:-------:|
| Users đăng ký | 200-300 |
| Online cùng lúc | 100-150 |
| **Chat đồng thời** | **50-80** |
| Web search/giờ | ~60 |
| Throughput | ~60-80 req/s |

---

## 2. Phân bổ tài nguyên Server

**Server:** 20 CPU / 32GB RAM

| Service | Workers | CPU | RAM limit | RAM reserved |
|---------|:-------:|:---:|:---------:|:------------:|
| **Open WebUI** | 6 | 6 | 10GB | 4GB |
| **Middleware** | 4 | 4 | 2GB | 512MB |
| **LiteLLM** | 4 | 4 | 4GB | 1GB |
| **PostgreSQL** | — | 2 | 8GB | 4GB |
| **SearXNG** | — | 1 | 1GB | — |
| **Redis** | — | 0.5 | 256MB | — |
| **Nginx** | auto | 1 | 512MB | — |
| **Tổng** | **14** | **18.5** | **25.8GB** | **9.5GB** |
| **Còn dư (cho OS)** | — | **1.5** | **6.2GB** | — |

### Tại sao phân bổ như vậy?

| Service | Lý do CPU | Lý do RAM |
|---------|-----------|-----------|
| WebUI 6 CPU | Nặng nhất: chạy ML embedding model + serve HTML | 10GB: model ~2GB + 6 workers ×1GB |
| MW 4 CPU | 4 workers async, check quota DB | 2GB đủ (chỉ proxy + DB query) |
| LiteLLM 4 CPU | 4 workers gọi API, I/O bound | 4GB dự phòng cho nhiều model configs |
| PG 2 CPU | DB queries, index scan | 8GB: shared_buffers=4GB + query cache |
| Nginx 1 CPU | Chỉ forward, **10,000+ req/s với 1 CPU** | 512MB quá đủ |

---

## 3. Cân bằng tại Nginx

### Rate Limiting

| Zone | Rate | Burst | Áp dụng cho | Mục đích |
|------|:----:|:-----:|------------|---------|
| `chat` | 10 req/s | 50 | `/` (trang chính) | Chống spam |
| `login` | 5 req/phút | 3 | `/api/v1/auths/` | Chống brute force |
| Không limit | — | — | `/_app/`, `/static/`, `/ws/` | Static files, WebSocket |

### Cách hoạt động

```
User gửi request quá nhanh (> 10 req/s):
    Request 1-10:  ✅ Xử lý ngay
    Request 11-50: ✅ Xử lý (burst buffer, có delay nhỏ)
    Request 51+:   ❌ Nginx trả 503 "Try again later"
```

> **Lưu ý:** Mỗi lần mở trang cần 20-30 requests (HTML + JS + CSS + API). Rate limit 10 req/s + burst 50 = đủ cho page load. Static files (`/_app/`, `/static/`) **không bị rate limit**.

---

## 4. Cân bằng tại LiteLLM

### RPM/TPM per model

LiteLLM hỗ trợ giới hạn **requests per minute (RPM)** và **tokens per minute (TPM)** cho từng model:

```yaml
# litellm/litellm_config.yaml
general_settings:
  max_parallel_requests: 50       # Tối đa 50 requests đồng thời (tất cả model)
  verbose: false                  # Tắt log verbose (production)

litellm_settings:
  request_timeout: 120            # Timeout 2 phút per request
  num_retries: 2                  # Retry 2 lần nếu lỗi
```

### Giới hạn API Provider

| Provider | Model | RPM (provider limit) | Chiến lược |
|----------|-------|:--------------------:|-----------|
| OpenAI | GPT-5 | 100 | ⚠️ Bottleneck — cần fallback |
| OpenAI | GPT-4o | 500 | ✅ Đủ |
| Google | Gemini 2.5 Pro | 1000 | ✅ Dư thừa |
| Google | Gemini 2.5 Flash | 2000 | ✅ Rất dư |

### Load Balancing giữa nhiều API key

Nếu cần tăng RPM, thêm nhiều API key cho cùng model:

```yaml
# 2 key OpenAI = 200 RPM (thay vì 100)
- model_name: chat-gpt-5           # CÙNG tên
  litellm_params:
    model: openai/gpt-5
    api_key: os.environ/OPENAI_API_KEY      # Key 1
    rpm: 90

- model_name: chat-gpt-5           # CÙNG tên → LiteLLM tự load balance
  litellm_params:
    model: openai/gpt-5
    api_key: os.environ/OPENAI_API_KEY_2    # Key 2
    rpm: 90
```

### Fallback giữa providers

```yaml
# User chọn "chat-smart" → GPT-5 ưu tiên, hết quota → Claude tự động
- model_name: chat-smart
  litellm_params:
    model: openai/gpt-5
    rpm: 80

- model_name: chat-smart            # Cùng tên = fallback
  litellm_params:
    model: anthropic/claude-sonnet-4-6-20260205
    rpm: 40
```

---

## 5. Cân bằng tại Middleware

### Connection Pool

```python
# config.py
init_pool(DATABASE_URL, minconn=5, maxconn=30)
```

| Tham số | Giá trị | Ý nghĩa |
|---------|:-------:|---------|
| `minconn` | 5 | Luôn giữ sẵn 5 kết nối DB (không cần tạo mới) |
| `maxconn` | 30 | Tối đa 30 kết nối đồng thời |
| Workers | 4 | 4 tiến trình, mỗi worker có pool riêng |
| **Tổng max** | **120** | 4 workers × 30 connections = 120 DB connections |

### PostgreSQL connections

```
PostgreSQL max_connections = 300

Middleware:   4 workers × 30 pool = 120 connections
Open WebUI:  ~30 connections
LiteLLM:     ~20 connections
────────────────────────────────────
Tổng:        ~170 / 300 → CÒN DƯ 130 ✅
```

---

## 6. Tăng RPM API Provider

### 4 cách tăng RPM

| # | Cách | Tăng | Chi phí | Phức tạp |
|:-:|------|:----:|:-------:|:--------:|
| 1 | **Nâng tier** (deposit thêm) | ×5-100 | $40-400 | ⭐ |
| 2 | **Nhiều API key** (cùng provider) | ×2-3 | $0 | ⭐ |
| 3 | **Fallback** (multi-provider) | ×2-3 | $0 | ⭐⭐ |
| 4 | **Phân nhóm user** (model khác nhau) | Không giới hạn | $0 | ⭐⭐ |

### Khuyến nghị

```
Đa số user → Gemini Flash (2000 RPM, giá rẻ)     → KHÔNG bao giờ hết
VIP/Admin  → GPT-5 hoặc Claude (100-500 RPM)       → Chỉ ít người dùng
```

---

## 7. Bottleneck thực tế

### Đâu là bottleneck?

```
Nginx:    10,000+ req/s     → KHÔNG BAO GIỜ là bottleneck     ✅
WebUI:    ~60 req/s         → Đủ cho 50-80 chat đồng thời      ✅
MW:       ~40 req/s         → Đủ                                ✅
LiteLLM:  ~50 req/s         → Đủ                                ✅
PostgreSQL: ~1000 query/s   → Dư thừa                           ✅

BOTTLENECK THẬT:
  OpenAI GPT-5: 100 RPM     → 50 user dùng cùng lúc = HẾT     ⚠️
```

### Kết luận

- **Server không phải vấn đề** — 20 CPU / 32GB RAM dư cho 200 users
- **Bottleneck = API rate limit** — đặc biệt OpenAI GPT-5 (100 RPM)
- **Giải pháp:** phân tải user sang Gemini (2000 RPM) hoặc thêm API key
