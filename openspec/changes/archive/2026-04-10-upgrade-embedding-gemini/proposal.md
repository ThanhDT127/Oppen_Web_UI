## Why

Hệ thống RAG hiện dùng embedding model local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`:
- **384 dimensions** — vector space nhỏ, hạn chế semantic accuracy
- **Chạy trên CPU** — batch embedding chậm, tốn 4-6GB RAM của container Open WebUI 
- **Multilingual quality trung bình** — model nhỏ (118M params), không optimized cho tiếng Việt

Gemini `gemini-embedding-001`:
- **3072 dimensions** — vector space lớn gấp 8x, semantic accuracy cao hơn đáng kể
- **API-based** — không tốn CPU/RAM server, response nhanh
- **Multilingual tốt hơn** — trained trên corpus lớn hơn nhiều, hỗ trợ tiếng Việt tốt
- **Chi phí cực thấp** — $0.15/1M tokens (~$0.75/tháng cho 100 files)

## What Changes

- Đổi `RAG_EMBEDDING_ENGINE` từ `(empty/local)` sang `openai` (Gemini qua LiteLLM)
- Đổi `RAG_EMBEDDING_MODEL` sang `gemini-embedding-001`
- Thêm embedding model vào `litellm_config.yaml` để route qua middleware (track chi phí)
- Re-index toàn bộ documents trong PGVector (bắt buộc vì dimension thay đổi)

## Capabilities

### Modified Capabilities
- `rag-embedding`: Nâng cấp từ local 384-dim lên Gemini 3072-dim, cải thiện search relevance

## Impact

- **Code affected**: `docker-compose.yml` (env vars), `litellm/litellm_config.yaml` (thêm embedding model), Admin UI settings
- **APIs**: Embedding requests sẽ đi qua: Open WebUI → LiteLLM → Gemini API
- **Dependencies**: Phụ thuộc Gemini API availability (nếu Gemini down → embedding fail)
- **Data migration**: Phải re-index toàn bộ documents (vector dimensions khác nhau, PGVector cần rebuild)
- **Chi phí**: ~$0.15/1M tokens → ~$0.75/tháng (100 files)

## Rollback Plan

> ⚠️ **QUAN TRỌNG**: Rollback cần re-index lại documents LẦN NỮA vì vector dimensions khác nhau.

1. **Rollback ENV**: Revert `RAG_EMBEDDING_ENGINE=` (trống) và `RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` trong docker-compose
2. **Rollback Admin UI**: Settings → Documents → Embedding Engine: default, Model: `paraphrase-multilingual-MiniLM-L12-v2`  
3. **Re-index documents**: Admin → Settings → Documents → Reset Vector DB + Re-index
4. **Thời gian rollback**: ~5-10 phút (bao gồm re-index), mất embedding quality nhưng an toàn
5. **Dữ liệu**: Documents gốc không bị mất, chỉ embeddings cần tạo lại
