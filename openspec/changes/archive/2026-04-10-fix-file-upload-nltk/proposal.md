## Why

File upload và RAG trong Open WebUI bị lỗi hoàn toàn. Khi user upload file (PDF, DOCX, TXT, ...), quá trình xử lý file fail với `PermissionError: [Errno 13] Permission denied: '/root/nltk_data'`. Nguyên nhân: container chạy user 1000 (non-root) nhưng thư viện `unstructured` gọi NLTK download `averaged_perceptron_tagger_eng` vào `/root/nltk_data` — user 1000 không có quyền ghi. Cần fix ngay vì đây là tính năng core của hệ thống.

## What Changes

- Pre-download tất cả NLTK packages cần thiết (`averaged_perceptron_tagger_eng`, `punkt_tab`) trong Dockerfile build stage (chạy as root)
- Set `NLTK_DATA` environment variable trỏ về thư mục `/app/backend/data/nltk_data` mà user 1000 có quyền đọc
- Đảm bảo file permissions đúng cho NLTK data directory

## Capabilities

### New Capabilities
- `nltk-data-provisioning`: Pre-download và bundle NLTK data packages trong Docker image để tránh runtime download failures

### Modified Capabilities
_Không có thay đổi spec-level cho capabilities hiện tại._

## Impact

- **File**: `Dockerfile.openwebui` — thêm NLTK download steps
- **File**: `docker-compose.yml` — thêm `NLTK_DATA` env var (nếu cần)
- **Dependencies**: Không thêm dependency mới, chỉ pre-download NLTK data
- **Breaking changes**: Không có — chỉ fix bug, không thay đổi behavior
- **Rebuild required**: Cần rebuild Docker image (`docker compose build open-webui`)
