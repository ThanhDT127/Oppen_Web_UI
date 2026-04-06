## Tasks

### 1. Chuẩn bị Rollback
- [x] Backup file `docker-compose.yml` hiện tại: `copy docker-compose.yml docker-compose.yml.bak`
- [x] Note lại Content Extraction Engine setting hiện tại trong Admin UI

### 2. Xóa Tika container cũ
- [x] Stop và xóa container Tika standalone: `docker stop openwebui-tika && docker rm openwebui-tika`

### 3. Thêm Tika vào docker-compose.yml
- [x] Thêm service `tika` với image `apache/tika:latest-full` vào `docker-compose.yml`
- [x] Network: `openwebui-network`
- [x] Resource limits: `memory: 2G, cpus: 1`
- [x] Healthcheck: `wget --spider -q http://localhost:9998/tika`
- [x] Thêm `tika` vào `depends_on` của `open-webui`

### 4. Deploy và verify container
- [x] `docker-compose up --build -d`
- [x] Verify Tika container healthy: `docker ps | grep tika`
- [x] Tika container healthy ✓

### 5. Cấu hình Open WebUI
- [x] Admin Panel → Settings → Documents → Content Extraction Engine: chọn `tika`
- [x] Tika URL: `http://tika:9998`
- [x] PDF Extract Images (OCR) — not available in v0.7.2, Tika latest-full handles OCR at backend level
- [x] Save settings

### 6. Test End-to-End
- [ ] Upload PDF scan → verify text được extract
- [ ] Upload PDF text thường → verify vẫn hoạt động bình thường
- [ ] Upload DOCX/XLSX → verify extract OK
