# 📘 HƯỚNG DẪN SỬ DỤNG - OPEN WEBUI STACK

> **Phiên bản:** 3.0 | **Cập nhật:** 06/03/2026

Tài liệu hướng dẫn sử dụng hệ thống Open WebUI với Middleware, bao gồm kiến trúc, RAG, tạo ảnh, quản lý user, và troubleshooting.

---

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Các Model Hỗ Trợ](#2-các-model-hỗ-trợ)
3. [Sử Dụng RAG](#3-sử-dụng-rag)
4. [Tạo Ảnh (Image Generation)](#4-tạo-ảnh-image-generation)
5. [Quản Lý Quota & Chi Phí](#5-quản-lý-quota--chi-phí)
6. [Quản Lý User & Subkey](#6-quản-lý-user--subkey)
7. [Xuất File (Export Tool)](#7-xuất-file-export-tool)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Tổng Quan Hệ Thống

### 1.1 Kiến Trúc 3-Tier

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGƯỜI DÙNG                               │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: Open WebUI (Port 3000)                                  │
│  - Giao diện chat đa phương thức                                │
│  - Quản lý Knowledge Base & RAG                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: Middleware (Port 5000)                                  │
│  - Xác thực subkey                                               │
│  - Quản lý quota & cost                                          │
│  - Audit logging                                                 │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: LiteLLM (Port 4000) + PostgreSQL (Port 5432)           │
│  - Model routing (OpenAI, Gemini)                                │
│  - Vector embeddings (PGVector)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Docker Services

| Service        | Port | Chức Năng            |
| -------------- | ---- | -------------------- |
| **Open WebUI** | 3000 | Giao diện người dùng |
| **Middleware** | 5000 | Xác thực + Quota     |
| **LiteLLM**    | 4000 | LLM Proxy            |
| **PostgreSQL** | 5432 | Database + Vector DB |

---

## 2. Các Model Hỗ Trợ

### Quy Ước Đặt Tên

| Prefix | Chức Năng                                    |
| ------ | -------------------------------------------- |
| `mm-`  | **Multimodal** - Chat text + hiểu ảnh        |
| `img-` | **Image Generation** - Tạo ảnh từ text       |
| `tts-` | **Text-to-Speech** - Chuyển text thành audio |
| `stt-` | **Speech-to-Text** - Chuyển audio thành text |

### Danh Sách Model

#### Multimodal (Text + Vision)
| Model                 | Provider | Ghi Chú                       |
| --------------------- | -------- | ----------------------------- |
| `mm-gpt-5`            | OpenAI   | Flagship, reasoning mạnh nhất |
| `mm-gpt-5-mini`       | OpenAI   | Cân bằng                      |
| `mm-gpt-5-nano`       | OpenAI   | Nhanh, tiết kiệm              |
| `mm-gpt-4.1`          | OpenAI   | 1M context window             |
| `mm-gpt-4o`           | OpenAI   | Multimodal + audio            |
| `mm-gemini-2.5-pro`   | Google   | 1M context, reasoning         |
| `mm-gemini-2.5-flash` | Google   | Nhanh, khuyến nghị            |
| `mm-gemini-3-pro`     | Google   | Latest flagship               |

#### Image Generation
| Model              | Provider | Ghi Chú                                |
| ------------------ | -------- | -------------------------------------- |
| `img-dalle-3`      | OpenAI   | Chất lượng cao, cần org verification   |
| `img-gemini-flash` | Google   | ✅ Khuyến nghị, không cần verification |

#### Audio
| Model             | Provider | Chức Năng                 |
| ----------------- | -------- | ------------------------- |
| `tts-gpt-4o-mini` | OpenAI   | Text → Audio              |
| `stt-gpt-4o`      | OpenAI   | Audio → Text (transcribe) |
| `stt-gpt-4o-mini` | OpenAI   | Transcribe nhanh          |

---

## 3. Sử Dụng RAG

### 3.1 RAG Là Gì?

**RAG = Retrieval-Augmented Generation**

Cho phép AI truy xuất thông tin từ tài liệu của bạn để trả lời câu hỏi.

```
Câu hỏi → Tìm chunks liên quan → Ghép vào context → LLM trả lời
```

### 3.2 Cách Sử Dụng

#### Cách 1: Gắn Knowledge Base vào Model (Khuyến nghị)

1. **Workspace** → **Models** → Click **[+]**
2. Điền:
   - **Name**: Tên model (vd: "Tài Liệu Dự Án")
   - **Base Model**: `mm-gemini-2.5-flash`
   - **Knowledge**: Chọn KB của bạn
3. **Save**
4. Chat với model này → AI tự động tìm trong KB

#### Cách 2: Dùng # trong Chat

```
# Truy vấn file cụ thể
#my_document.pdf Tóm tắt nội dung chính

# Truy vấn Knowledge Base
#TenKnowledgeBase Giải thích về kiến trúc

# Truy vấn URL (real-time)
#https://example.com Tóm tắt trang này
```

### 3.3 Cấu Hình RAG

**Admin Panel → Settings → Documents**

| Tham Số       | Mặc Định | Mô Tả                   |
| ------------- | -------- | ----------------------- |
| Top K         | 5        | Số chunks retrieve      |
| Chunk Size    | 1000     | Kích thước mỗi chunk    |
| Chunk Overlap | 200      | Độ chồng lấp            |
| Hybrid Search | On       | Vector + Keyword search |

---

## 4. Tạo Ảnh (Image Generation)

### 4.1 Cấu Hình

**Admin Settings → Images:**
- **Engine**: OpenAI
- **API Base URL**: `http://middleware:5000/v1`
- **API Key**: Subkey của bạn
- **Model**: `img-gemini-flash` (khuyến nghị)

### 4.2 Test Tạo Ảnh

```bash
curl -X POST http://localhost:5000/v1/images/generations \
  -H "Authorization: Bearer subkey_admin_123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "img-gemini-flash",
    "prompt": "A futuristic city at sunset",
    "size": "1024x1024"
  }'
```

### 4.3 Response

```json
{
  "data": [{"url": "http://localhost:5000/v1/_mw/media/abc123.png"}],
  "_mw_user": "admin",
  "_mw_added_cost_usd": 0.002
}
```

---

## 5. Quản Lý Quota & Chi Phí

### 5.1 Schema Quota

```json
{
  "user_id": "admin",
  "subkey": "subkey_admin_123",
  "allowed_models": ["*"],
  "quota": {
    "period": "monthly",
    "limit_cost_usd": 50.0,
    "limit_image_requests": 100,
    "used_cost_usd": 5.25,
    "used_image_requests": 25
  }
}
```

### 5.2 Kiểm Tra Quota

```bash
curl -H "X-Admin-Key: admin_key" \
  http://localhost:5000/admin/usage | jq '.[] | select(.user_id=="admin")'
```

### 5.3 Reset Quota

```bash
curl -X POST -H "X-Admin-Key: admin_key" \
  http://localhost:5000/admin/reset \
  -d '{"user_id":"admin"}'
```

---

## 6. Quản Lý User & Subkey

### 6.1 Kiến Trúc — 2 Hệ Thống User

| Hệ thống       | Database                       | Vai trò                              |
| -------------- | ------------------------------ | ------------------------------------ |
| **Open WebUI** | `openwebui` → bảng `user`      | Đăng nhập web, phân quyền Admin/User |
| **Middleware** | `middleware` → bảng `mw_users` | Xác thực API, quản lý quota, subkey  |

> ⚠️ Hai hệ thống **độc lập** — user_id trong middleware không liên kết với user_id trong Open WebUI.

### 6.2 Quản Lý qua Dashboard (Giao Diện)

Truy cập: `http://<server>:5000/dashboard` → Tab **Users**

| Thao tác           | Cách làm                                            |
| ------------------ | --------------------------------------------------- |
| **Tạo user**       | Nhấn ➕ Add User → Điền form → Create → Copy subkey |
| **Sửa user**       | Nhấn ✏️ → Sửa quota/model/role → Save               |
| **Xóa user**       | Nhấn 🗑️ → Confirm 2 lần                             |
| **Rotate key**     | Nhấn 🔑 → Confirm → Copy subkey mới                 |
| **Enable/Disable** | Nhấn 🔴/🟢 toggle                                   |

### 6.3 Subkey — Bảo Mật

- Subkey là **mã xác thực API** (dạng `sk_abc123...`)
- Mã hóa **HMAC-SHA256** — không thể dịch ngược
- Plaintext chỉ hiện **1 lần** khi tạo/rotate → phải copy ngay
- Dashboard chỉ hiện hash rút gọn (`abc...xyz`)

### 6.4 Quản Lý qua API

```bash
# Tạo user
curl -X POST http://localhost:5000/v1/_mw/admin/users \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "role": "user", "limit_cost_usd": 5.0}'

# Sửa user
curl -X PATCH http://localhost:5000/v1/_mw/admin/users/alice \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"limit_cost_usd": 10.0}'

# Xóa user
curl -X DELETE http://localhost:5000/v1/_mw/admin/users/alice \
  -H "X-Admin-Key: $ADMIN_KEY"

# Rotate key
curl -X POST http://localhost:5000/v1/_mw/admin/users/alice/rotate_key \
  -H "X-Admin-Key: $ADMIN_KEY"
```

---

## 7. Xuất File (Export Tool)

### 7.1 Các Định Dạng

| Công cụ                | Mô Tả                                           |
| ---------------------- | ----------------------------------------------- |
| **Xuất Excel** (.xlsx) | Trích xuất bảng biểu, auto-format số/ngày/tiền  |
| **Xuất PDF**           | Xuất hội thoại, hỗ trợ tiếng Việt (font DejaVu) |
| **Xuất Word** (.docx)  | Xuất hội thoại dạng Word                        |

### 7.2 Cách Sử Dụng

1. Mở chat → gõ gì đó để bot trả lời
2. Nhấn icon ⚡ (Action) bên dưới tin nhắn bot
3. Chọn **Xuất File**
4. Chọn format: 1=Excel, 2=PDF, 3=Word
5. File tự tải xuống

> 💡 Tool Excel tự nhận dạng: số, ngày tháng, %, tiền VNĐ/$/€ và format đúng.

---

## 8. Troubleshooting

### 8.1 Lỗi Thường Gặp

| Lỗi                     | Nguyên Nhân                     | Giải Pháp                   |
| ----------------------- | ------------------------------- | --------------------------- |
| 401 Missing sub-key     | Thiếu Authorization header      | Thêm `Bearer <subkey>`      |
| 403 Invalid sub-key     | Subkey sai hoặc user bị disable | Kiểm tra DB hoặc rotate key |
| 403 Model not allowed   | Model bị chặn                   | Thêm vào allowed_models     |
| 403 Quota exceeded      | Hết quota                       | Reset hoặc tăng limit       |
| 502 LiteLLM unavailable | LiteLLM chưa chạy               | Kiểm tra container          |

### 8.2 Kiểm Tra Service

```bash
# Health check
curl http://localhost:5000/health

# Kiểm tra logs
docker compose logs middleware --tail 50
docker compose logs litellm --tail 50

# Kiểm tra models
curl http://localhost:5000/v1/models \
  -H "Authorization: Bearer <subkey>"
```

### 8.3 RAG Không Hoạt Động

1. **Verify file đã index**: Workspace → Knowledge → Click KB
2. **Check embedding model**: `docker compose logs open-webui | grep embedding`
3. **Verify PGVector**: 
   ```bash
   docker exec openwebui-postgres psql -U openwebui_user -d openwebui \
     -c "SELECT COUNT(*) FROM document_chunk;"
   ```

---

## 📌 Quick Reference

### URLs

| Service        | URL                             |
| -------------- | ------------------------------- |
| Open WebUI     | http://localhost:3000           |
| Middleware API | http://localhost:5000           |
| LiteLLM        | http://localhost:4000           |
| Dashboard      | http://localhost:5000/dashboard |

### Commands

```bash
# Start stack
docker compose up -d

# Restart sau khi đổi config
docker compose down && docker compose up -d --build

# Xem logs
docker compose logs -f middleware
```

---

*Tài liệu gộp từ: TAI_LIEU_TONG_QUAN_DU_AN.md, HUONG_DAN_SU_DUNG_RAG.md, IMAGE_GENERATION.md, HUONG_DAN_IMAGE_GENERATION.md, HUONG_DAN_TRIEN_KHAI_EXPORT.md, huong-dan-thao-tac-he-thong.md*

