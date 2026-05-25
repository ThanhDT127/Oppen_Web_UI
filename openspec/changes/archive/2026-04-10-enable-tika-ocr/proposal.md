## Why

Khi user upload PDF dạng scan (hình ảnh, không có text layer), hệ thống RAG extract ra text trống → model trả lời "không thể phân tích tệp vì nội dung không đọc được". Hiện tại:

1. **Tika container** (`apache/tika:latest`) đang chạy nhưng **không được khai báo trong docker-compose** → không quản lý được lifecycle
2. **Content Extraction Engine** trong Open WebUI chưa được cấu hình → mặc định dùng `pypdf` (không có OCR)
3. Image `apache/tika:latest` **không có Tesseract OCR** → cần `apache/tika:latest-full` để xử lý PDF scan

## What Changes

- Thêm Tika container (image `apache/tika:latest-full` với Tesseract OCR) vào `docker-compose.yml`
- Cấu hình Open WebUI sử dụng Tika làm Content Extraction Engine
- Bật PDF Extract Images (OCR) trong Admin Settings
- Xóa container Tika cũ chạy ngoài docker-compose

## Capabilities

### New Capabilities
- `tika-ocr-extraction`: Open WebUI sử dụng Tika + Tesseract OCR để extract text từ PDF scan, image-based documents. Hỗ trợ >1000 định dạng file (DOC, DOCX, PPTX, XLS, XLSX, v.v.)

### Modified Capabilities
_(Không sửa đổi gì hiện có, chỉ bật thêm engine)_

## Impact

- **Code affected**: `docker-compose.yml` (thêm tika service), Admin UI settings (Content Extraction Engine)
- **APIs**: Không thay đổi API
- **Dependencies**: Thêm `apache/tika:latest-full` image (~1.2GB, lớn hơn `latest` ~300MB)
- **Systems**: Tăng RAM usage ~500MB cho Tika OCR container

## Rollback Plan

1. **Rollback docker-compose**: Revert `docker-compose.yml` về bản backup (xóa tika service block)
2. **Rollback Admin Settings**: Đổi Content Extraction Engine từ `tika` về `(default)` trong Admin → Settings → Documents
3. **Container cleanup**: `docker rm -f openwebui-tika` nếu cần xóa hoàn toàn
4. **Thời gian rollback**: < 2 phút, không ảnh hưởng data (PGVector store không bị mất)
