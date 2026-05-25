## Context

Server: Intel Xeon Gold 5215 @ 2.50GHz, không có GPU. Embedding model `paraphrase-multilingual-MiniLM-L12-v2` chạy CPU-only. Benchmark: 100 embeddings/0.80s (nhanh). Nhưng `RAG_EMBEDDING_BATCH_SIZE=1` gọi model predict cho từng chunk riêng lẻ, overhead per-call (context switch, memory allocation) lớn hơn computation.

Log timeline phân tích (user upload ~12 files, 8-67KB):
- File 30 chunks: ~1s (embedding) + parsing overhead
- File 125 chunks: ~5s (embedding) + parsing overhead
- Total: ~80s cho 12 files → ~6.7s/file trung bình

## Goals / Non-Goals

**Goals:**
- Giảm thời gian upload+processing ít nhất 3-5x
- Không thay đổi chất lượng RAG đáng kể
- Chỉ config change, không sửa code

**Non-Goals:**
- Chuyển sang GPU embedding
- Thay đổi embedding model
- Refactor Open WebUI source code

## Decisions

### 1. RAG_EMBEDDING_BATCH_SIZE = 100 (chọn) vs. giữ mặc định 1

**Chọn: 100**
- Rationale: Benchmark 100 items/0.80s CPU. Batch 100 tận dụng SIMD/vectorization, giảm overhead per-call
- Alternative: Giá trị cao hơn (256/512) tốn nhiều RAM hơn, diminishing returns trên CPU

### 2. CHUNK_SIZE = 1500 (chọn) vs. giữ 1000

**Chọn: 1500**
- Rationale: Giảm ~33% số chunks → giảm embedding calls tương ứng. Model MiniLM max token 128 nhưng text splitter chia theo character, chunk 1500 chars vẫn tạo embeddings tốt.
- Trade-off: Chunks lớn hơn = context rộng hơn nhưng precision giảm nhẹ → acceptable cho documents

### 3. CHUNK_OVERLAP = 100 (chọn) vs. giữ 200

**Chọn: 100**
- Rationale: Overlap 200 trên chunk 1000 = 20% redundancy. Overlap 100 trên chunk 1500 = 6.7% — vẫn đủ context continuity, giảm total data significantly

## Risks / Trade-offs

- **[Risk] RAG precision giảm nhẹ** với chunks lớn → Acceptable trade-off, có thể tune lại nếu user phàn nàn
- **[Risk] Memory spike** khi batch embed 100 items → MiniLM-L12 nhỏ (384 dim), 100 items ~40KB → negligible
