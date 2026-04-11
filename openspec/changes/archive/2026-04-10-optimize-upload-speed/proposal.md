## Why

Upload file vào Open WebUI rất chậm (~15-25s/file). Benchmark cho thấy embedding model (sentence-transformers) xử lý 100 items chỉ mất 0.80s trên CPU, nhưng `RAG_EMBEDDING_BATCH_SIZE=1` (mặc định) khiến từng chunk được embed riêng lẻ thay vì batch. Kết hợp với `CHUNK_SIZE=1000` và `CHUNK_OVERLAP=200` tạo ra số lượng chunks lớn (30-125 chunks/file), pipeline bị chậm đáng kể.

## What Changes

- Tăng `RAG_EMBEDDING_BATCH_SIZE` từ `1` → `100` để batch embedding thay vì one-by-one
- Tăng `CHUNK_SIZE` từ `1000` → `1500` để giảm số chunks cần embed
- Giảm `CHUNK_OVERLAP` từ `200` → `100` để giảm redundancy
- Tăng `RAG_FILE_MAX_COUNT` từ `10` → `20` cho phép upload nhiều file hơn

## Capabilities

### New Capabilities
- `rag-performance-tuning`: Tối ưu RAG pipeline performance qua batch embedding và chunk size tuning

### Modified Capabilities
_Không có thay đổi spec-level cho capabilities hiện tại._

## Impact

- **File**: `docker-compose.yml` — thay đổi env vars cho service `open-webui`
- **Performance**: Embedding speed tăng ~10-50x (batch vs one-by-one)
- **Quality tradeoff**: Chunk lớn hơn có thể giảm precision nhẹ nhưng tăng context, chấp nhận được cho documents
- **Breaking changes**: Không — chỉ thay đổi config, không ảnh hưởng dữ liệu hiện tại
- **Restart required**: `docker compose up -d open-webui`
