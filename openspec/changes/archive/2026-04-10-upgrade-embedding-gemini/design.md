## Context

Hiện tại embedding flow:
```
Open WebUI → [local Sentence Transformers] → PGVector (384-dim HNSW index)
```

Sau thay đổi:
```
Open WebUI → LiteLLM (route) → Gemini API → PGVector (3072-dim HNSW index)
```

Key constraint: Open WebUI dùng `OPENAI_API_BASE_URL=http://middleware:5000/v1` cho LLM. Embedding cũng cần đi qua cùng endpoint hoặc direct tới LiteLLM.

## Goals / Non-Goals

**Goals:**
- Nâng cấp chất lượng embedding (384-dim → 3072-dim, better multilingual)
- Route embedding qua LiteLLM để track chi phí
- Re-index toàn bộ documents với new embedding
- Giữ tương thích với existing RAG pipeline (PGVector HNSW)

**Non-Goals:**
- Không thay đổi chunking strategy
- Không thay đổi vector DB engine (giữ PGVector)
- Không implement embedding fallback (nếu Gemini down → tạm thời không embed)

## Decisions

### D1: Route embedding qua LiteLLM (không trực tiếp Gemini API)

**Decision**: Thêm `gemini-embedding-001` vào `litellm_config.yaml`, Open WebUI connect qua `http://middleware:5000/v1` hoặc `http://litellm:4000/v1`.

**Rationale**: 
- LiteLLM chuẩn hóa API → Open WebUI dùng `openai` engine
- Chi phí embedding sẽ được track qua middleware audit
- Không cần expose thêm API key

**Trade-off**: Thêm 1 hop network (Open WebUI → Middleware → LiteLLM → Gemini) nhưng latency < 100ms.

**Lưu ý quan trọng**: Middleware hiện tại chỉ route `/v1/chat/completions` và một số endpoints. Cần kiểm tra xem middleware có forward `/v1/embeddings` không. Nếu không, Open WebUI nên connect trực tiếp tới LiteLLM (`http://litellm:4000/v1`).

### D2: PGVector dimension migration

**Decision**: Reset vector DB và re-index toàn bộ documents.

**Rationale**: PGVector HNSW index với 384 dimensions không tương thích với 3072 dimensions. Phải drop và rebuild.

**Risk**: Downtime embedding search trong lúc re-index (~5-15 phút tùy số documents).

### D3: Cấu hình qua docker-compose ENV + Admin UI

**Decision**: Set ENV trong docker-compose làm initial config, confirm/override qua Admin UI.

```yaml
# docker-compose.yml open-webui environment
- RAG_EMBEDDING_ENGINE=openai
- RAG_EMBEDDING_MODEL=gemini-embedding-001
- RAG_EMBEDDING_BATCH_SIZE=50  # giảm từ 100 → tránh rate limit Gemini
```

## Risks / Trade-offs

- **[API dependency]** → Nếu Gemini API down → embedding fail → upload file fail. Mitigation: Gemini uptime > 99.9%.
- **[Re-index downtime]** → Search sẽ không hoạt động trong ~5-15 phút. Mitigation: Thực hiện ngoài giờ.
- **[Rate limits]** → Gemini embedding RPM limit. Mitigation: Giảm batch size xuống 50.
- **[Cost]** → ~$0.75/tháng. Rất thấp nhưng cần monitor. Embedding cost không đi qua middleware quota hiện tại.
- **[Vector dimension change]** → Không rollback "instant" — cần re-index lại nếu rollback.
