## Tasks

### 1. Chuẩn bị Rollback
- [x] Backup file `docker-compose.yml`: `copy docker-compose.yml docker-compose.yml.bak`
- [x] Backup file `litellm/litellm_config.yaml`: `copy litellm\litellm_config.yaml litellm\litellm_config.yaml.bak`
- [x] Ghi lại cấu hình Embedding hiện tại trong Admin Panel → Settings → Documents

### 2. Thêm Gemini Embedding vào LiteLLM Config
- [x] Thêm model `gemini-embedding-001` vào `litellm/litellm_config.yaml`
- [x] Thêm pricing `gemini-embedding-001` vào `prices.json` ($0.15/1M tokens)

### 3. Thêm /v1/embeddings endpoint vào Middleware
- [x] Tạo `api/embeddings.py` — proxy với auth, quota, cost tracking, audit
- [x] Register route `/v1/embeddings` trong `main.py`
- [x] Embedding requests đi qua middleware → dashboard hiển thị chi phí ✓

### 4. Cập nhật docker-compose.yml
- [x] Đổi `RAG_EMBEDDING_ENGINE=openai`
- [x] Đổi `RAG_EMBEDDING_MODEL=gemini-embedding-001`
- [x] Đổi `RAG_EMBEDDING_BATCH_SIZE=50` (giảm tránh rate limit)
- [x] `RAG_EMBEDDING_OPENAI_API_BASE_URL=http://middleware:5000/v1` (qua middleware)
- [x] `RAG_EMBEDDING_OPENAI_API_KEY=${SUBKEY_ADMIN}`

### 5. Deploy
- [x] `docker-compose up --build -d`
- [x] Verify LiteLLM load embedding model — ✓ `gemini-embedding-001` loaded
- [x] Verify Middleware healthy — ✓ health checks passing

### 6. Cấu hình Admin UI
- [x] Admin Panel → Settings → Documents → Embedding Model Engine: `openai`
- [x] Embedding API URL: `http://middleware:5000/v1` (qua middleware)
- [x] Embedding Model: `gemini-embedding-001`
- [ ] Nhấn "Reset Vector Storage" để clear old 384-dim vectors
- [ ] Nhấn "Reindex" để tạo embeddings mới 3072-dim

### 7. Test End-to-End
- [ ] Upload file mới → verify embedding được tạo và audit logged
- [ ] Kiểm tra dashboard — verify embedding cost hiển thị
