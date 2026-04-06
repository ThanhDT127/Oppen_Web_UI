## 1. Dockerfile Fix

- [x] 1.1 Thêm NLTK data download vào `Dockerfile.openwebui` — download `averaged_perceptron_tagger_eng` và `punkt_tab` vào `/usr/local/nltk_data/` (chạy as root trước `USER 1000`)
- [x] 1.2 Verify Dockerfile build thành công (`docker compose build open-webui`)

## 2. Verification

- [x] 2.1 Restart container (`docker compose up -d open-webui`)
- [x] 2.2 Verify NLTK data tồn tại trong container (`docker compose exec open-webui ls -la /usr/local/nltk_data/`)
- [x] 2.3 Upload test file qua UI và verify processing thành công (không còn PermissionError trong logs) — **cần user test thủ công**
- [x] 2.4 Verify RAG hoạt động — hỏi AI về nội dung file đã upload — **cần user test thủ công**
