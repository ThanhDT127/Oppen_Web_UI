## Context

Hệ thống Open WebUI hiện tại:
- **Content Extraction**: Mặc định `pypdf` → chỉ đọc text-native PDF, KHÔNG có OCR
- **Tika container**: `apache/tika:latest` chạy standalone (không trong docker-compose), KHÔNG có Tesseract
- **Network**: Container Tika cũ có thể không cùng network `openwebui-network` → Open WebUI không truy cập được

## Goals / Non-Goals

**Goals:**
- Xử lý PDF scan (image-based) → extract text qua OCR
- Đưa Tika vào docker-compose để quản lý lifecycle, network, resource limits
- Cấu hình Open WebUI sử dụng Tika thay vì pypdf mặc định

**Non-Goals:**
- Không triển khai Docling (phức tạp hơn, cần config riêng)
- Không thay đổi chunking strategy (giữ nguyên CHUNK_SIZE=1500)
- Không thêm Video/Audio processing (riêng biệt, scope khác)

## Decisions

### D1: Dùng `apache/tika:latest-full` thay vì `latest`

**Decision**: Image `latest-full` (~1.2GB) bao gồm Tesseract OCR + tất cả parsers.

**Rationale**: Image `latest` (~300MB) KHÔNG có OCR → vô nghĩa cho PDF scan. `latest-full` là lựa chọn duy nhất hỗ trợ OCR.

**Trade-off**: Image lớn hơn 4x nhưng đây là one-time download.

### D2: Cấu hình qua Admin UI, không qua ENV

**Decision**: Set `CONTENT_EXTRACTION_ENGINE=tika` và Tika URL qua Admin Panel → Settings → Documents (PersistentConfig).

**Rationale**: Open WebUI dùng PersistentConfig system — UI settings override ENV sau lần khởi tạo đầu tiên. Cấu hình qua UI đơn giản hơn và persisted trong DB.

**Alternative**: Set ENV `CONTENT_EXTRACTION_ENGINE=tika` trong docker-compose → bị override bởi PersistentConfig nên không reliable.

### D3: Resource limits cho Tika

**Decision**: `memory: 2G, cpus: 1` — Tika OCR cần RAM cho Tesseract processing.

**Rationale**: Server hiện tại 32GB RAM. Tika std chỉ cần ~256MB nhưng OCR cần ~1-2GB cho file lớn. 2GB limit an toàn.

## Risks / Trade-offs

- **[Disk space]** → Image `latest-full` ~1.2GB. Kiểm tra disk trước khi pull.
- **[OCR quality]** → Tesseract OCR accuracy phụ thuộc chất lượng scan. PDF scan xấu → text sai.
- **[Processing time]** → OCR chậm hơn text extraction (~5-30s cho file 10MB). User cần chờ.
- **[Tika cũ conflict]** → Container `openwebui-tika` cũ chạy ngoài compose có thể conflict port. Cần stop/remove trước.
