# 16. Web Search — Kiến trúc và Cấu hình

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Kiến trúc](#2-kiến-trúc)
3. [SearXNG — Cấu hình](#3-searxng--cấu-hình)
4. [Xác định Thời gian và Địa điểm](#4-xác-định-thời-gian-và-địa-điểm)
5. [Hạn chế và Giải pháp](#5-hạn-chế-và-giải-pháp)

---

## 1. Tổng quan

Hệ thống sử dụng **SearXNG** — công cụ tìm kiếm meta tự host — để cung cấp tính năng **Web Search cho AI**.

### Luồng xử lý

```
User hỏi: "Giá vàng hôm nay?"
    │
    ▼
Open WebUI phát hiện cần tìm kiếm (RAG Web Search)
    │
    ▼
Gửi query đến SearXNG (nội bộ Docker)
    │
    ▼
SearXNG truy vấn đồng thời nhiều search engine:
    ├── DuckDuckGo
    ├── Bing
    ├── Brave
    ├── Wikipedia
    └── (Google — ĐÃ TẮT vì hay bị ban)
    │
    ▼
Trả về top 5 kết quả (JSON)
    │
    ▼
Open WebUI inject kết quả vào context → gửi cho LLM
    │
    ▼
LLM trả lời có thông tin mới nhất từ internet
```

---

## 2. Kiến trúc

### Các thành phần

| STT | Thành phần     | Vai trò                                  | Container           |
| --- | -------------- | ---------------------------------------- | ------------------- |
| 01  | **Open WebUI** | Trigger web search, inject kết quả       | `openwebui-app`     |
| 02  | **SearXNG**    | Meta search engine, truy vấn nhiều nguồn | `openwebui-searxng` |
| 03  | **Redis**      | Cache kết quả, rate limiter cho SearXNG  | `openwebui-redis`   |

### Cấu hình trong docker-compose.yml

```yaml
# Open WebUI — kích hoạt web search
ENABLE_RAG_WEB_SEARCH=true
RAG_WEB_SEARCH_ENGINE=searxng
SEARXNG_QUERY_URL=http://searxng:8080/search?q=<query>&format=json
RAG_WEB_SEARCH_RESULT_COUNT=5           # Lấy top 5 kết quả
RAG_WEB_SEARCH_CONCURRENT_REQUESTS=1    # 1 request tại 1 thời điểm (tránh overload)
```

---

## 3. SearXNG — Cấu hình

**File:** `searxng/settings.yml`

### Cấu hình hiện tại

```yaml
use_default_settings: true          # Kế thừa cấu hình mặc định

server:
  port: 8080
  limiter: false                    # TẮT (cần Nginx X-Forwarded-For để bật)
  public_instance: false            # Không cho truy cập công khai
  image_proxy: true                 # Proxy hình ảnh qua SearXNG

search:
  safe_search: 0                    # Không lọc nội dung
  default_lang: "auto"              # Tự phát hiện ngôn ngữ
  formats:
    - html
    - json                          # Open WebUI dùng JSON format

# Search engines
engines:
  - name: google
    disabled: true                  # ĐÃ TẮT — Google hay block scraper
  - name: google news
    disabled: true
  - name: google images
    disabled: true

# Cache
valkey:
  url: "redis://redis:6379/0"      # Redis cache cho kết quả
```

### Tại sao tắt Google?

| STT | Engine     | Ưu điểm              | Nhược điểm                | Trạng thái |
| --- | ---------- | -------------------- | ------------------------- | ---------- |
| 01  | Google     | Kết quả tốt nhất     | **Hay block/ban** scraper | ❌ Tắt      |
| 02  | DuckDuckGo | Ổn định, không track | Kết quả trung bình        | ✅ Bật      |
| 03  | Bing       | Kết quả tốt          | Ổn định                   | ✅ Bật      |
| 04  | Brave      | Nhanh, riêng tư      | Ít phổ biến               | ✅ Bật      |
| 05  | Wikipedia  | Thông tin chính xác  | Chỉ bách khoa             | ✅ Bật      |

### Redis — Cache và Rate Limiter

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  resources:
    limits: { memory: 256M, cpus: '0.5' }    # Rất nhẹ
```

**Vai trò Redis:**
- **Cache** kết quả search → không query lại cùng câu hỏi
- **Rate limiter** (khi bật) → chống abuse SearXNG

---

## 4. Xác định Thời gian và Địa điểm

### Vấn đề

Khi hỏi "Thời tiết hôm nay ở Hà Nội?", LLM cần biết **hôm nay là ngày nào** và **người dùng ở đâu** để tìm kiếm chính xác.

### Giải pháp hiện tại — Filter Function (inlet)

Đã cài **Filter Function** (upload qua Admin → Functions) để inject thông tin vào system message TRƯỚC khi gửi cho LLM:

```python
# Chạy server-side (Python)
# Inject vào mọi request khi web search được bật

current_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
system_message = f"""
Current date/time: {current_time}
Timezone: UTC+7 (Vietnam)
Default location: Việt Nam
"""
```

### Kết quả

| STT | Trước                        | Sau                         |
| --- | ---------------------------- | --------------------------- |
| 01  | LLM không biết ngày hiện tại | ✅ Biết: "25/03/2026 08:30"  |
| 02  | LLM không biết timezone      | ✅ Biết: UTC+7               |
| 03  | Web search không kèm ngày    | ✅ Search query có thêm ngày |

### Tính năng mở rộng (chưa triển khai)

| STT | Tính năng                 | Yêu cầu        | Trạng thái           |
| --- | ------------------------- | -------------- | -------------------- |
| 01  | `{{USER_LOCATION}}` (GPS) | HTTPS          | ✅ Có HTTPS, chưa bật |
| 02  | Geolocation chính xác     | JavaScript API | 📋 Có kế hoạch        |
| 03  | IP-based location         | GeoIP database | 📋 Có kế hoạch        |

---

## 5. Hạn chế và Giải pháp

### Hạn chế hiện tại

| # | Hạn chế                            | Mức độ | Giải pháp                                |
| - | ---------------------------------- | ------ | ---------------------------------------- |
| 1 | SearXNG limiter TẮT                | 🟡      | Bật khi Nginx proxy X-Forwarded-For      |
| 2 | Google engine TẮT                  | 🟡      | Dùng Brave API (có kế hoạch)             |
| 3 | Giới hạn ~60 search/giờ            | 🟡      | Đủ cho 200 users (ít ai search liên tục) |
| 4 | Không có fallback khi SearXNG down | 🟡      | Thêm Brave API làm backup                |

### Kế hoạch nâng cấp

| STT | Kế hoạch         | Mô tả                                   | File                   |
| --- | ---------------- | --------------------------------------- | ---------------------- |
| 01  | **Search Proxy** | Thêm Brave API làm fallback cho SearXNG | `search_proxy_plan.md` |
| 02  | **Geolocation**  | GPS chính xác qua HTTPS                 | `geolocation_plan.md`  |
