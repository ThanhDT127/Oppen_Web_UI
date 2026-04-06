## Context

Open WebUI container (`Dockerfile.openwebui`) kế thừa image `ghcr.io/open-webui/open-webui:main` và chạy `USER 1000` (non-root). Khi user upload file, Open WebUI sử dụng thư viện `unstructured` để parse documents. Thư viện này gọi `nltk.download("averaged_perceptron_tagger_eng")` tại runtime, mặc định ghi vào `/root/nltk_data`. User 1000 không có quyền ghi `/root/` → `PermissionError` → file processing fail.

Hiện tại Dockerfile đã có pattern tương tự: pre-install pip packages (`fpdf2`, `openpyxl`, `python-docx`) và tạo cache directories. NLTK data cũng cần cùng pattern.

## Goals / Non-Goals

**Goals:**
- NLTK data packages có sẵn trong Docker image (no runtime download)
- File upload/RAG hoạt động bình thường cho tất cả file types
- Không thay đổi user permissions model (vẫn chạy USER 1000)

**Non-Goals:**
- Upgrade Open WebUI base image
- Thay đổi RAG config (chunk size, embedding model, etc.)
- Fix các issues khác ngoài NLTK permission

## Decisions

### 1. Pre-download NLTK trong Dockerfile (chọn) vs. Runtime download vào writable dir

**Chọn: Pre-download trong Dockerfile**

- **Rationale**: Deterministic, không phụ thuộc network tại runtime, không cần volume mount thêm
- **Alternative**: Set `NLTK_DATA=/app/backend/data/nltk_data` để download runtime → rủi ro network, chậm cold start, tăng volume size

### 2. Download location: `/usr/local/nltk_data` (chọn) vs. `/app/backend/data/nltk_data`

**Chọn: `/usr/local/nltk_data`**

- **Rationale**: Đây là một trong các default search paths của NLTK (`nltk.data.path`), không cần set env var thêm. Nằm trong image layer (immutable), không ảnh hưởng volume `openwebui_data`.
- **Alternative**: Custom path cần thêm `NLTK_DATA` env var trong docker-compose.yml

### 3. Packages cần download: `averaged_perceptron_tagger_eng` + `punkt_tab`

- Xác định từ stack trace (`averaged_perceptron_tagger_eng`) và `unstructured` requirements (`punkt_tab`)
- Chỉ download packages thực sự cần, theo nguyên tắc YAGNI

## Risks / Trade-offs

- **[Risk] Image size tăng** (~20MB cho NLTK data) → Chấp nhận được vì stability quan trọng hơn
- **[Risk] NLTK packages bị outdated** → Khi rebuild image sẽ lấy bản mới nhất; có thể pin version nếu cần
- **[Risk] `unstructured` upgrade cần thêm packages** → Monitor logs, thêm packages vào Dockerfile khi cần
