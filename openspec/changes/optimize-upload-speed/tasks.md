## 1. Config Changes

- [x] 1.1 Thêm `RAG_EMBEDDING_BATCH_SIZE=100` vào docker-compose.yml service open-webui
- [x] 1.2 Thay `CHUNK_SIZE=1000` → `CHUNK_SIZE=1500` trong docker-compose.yml
- [x] 1.3 Thay `CHUNK_OVERLAP=200` → `CHUNK_OVERLAP=100` trong docker-compose.yml
- [x] 1.4 Thay `RAG_FILE_MAX_COUNT=10` → `RAG_FILE_MAX_COUNT=20` trong docker-compose.yml

## 2. Verification

- [x] 2.1 Restart container (`docker compose up -d open-webui`)
- [x] 2.2 Verify env vars đã thay đổi — confirmed all 4 values in container
- [ ] 2.3 Upload test files và so sánh thời gian xử lý — **cần user test thủ công**
