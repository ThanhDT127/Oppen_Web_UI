## Context

The Open WebUI stack currently uses Apache Tika (`apache/tika:latest-full`) for document extraction in the RAG pipeline. This image bundles Tesseract OCR which auto-activates on any file containing embedded images, causing 300-second timeouts and extraction failures for standard business documents (DOCX with logos, charts, tables). The error manifests as `400: The content provided is empty`.

Current extraction flow:
```
File Upload → Open WebUI → PUT http://tika:9998/tika/text → Tika (Tesseract OCR) → Text
```

## Goals / Non-Goals

**Goals:**
- Replace Tika with Docling for faster, more reliable document extraction
- Eliminate OCR-induced timeouts for text-based DOCX/PDF files
- Preserve OCR capability for genuinely scanned documents (Docling uses EasyOCR on-demand)
- Improve RAG quality through structured Markdown output (preserving tables, headings)

**Non-Goals:**
- Re-index existing Knowledge Base documents (can be done manually later)
- Change the embedding engine or PGVector configuration
- Modify the middleware or LiteLLM proxy

## Decisions

- **Image choice: `ghcr.io/ds4sd/docling-serve-cpu:latest`** (CPU-only variant)
  - *Rationale:* Server has no GPU. The `-cpu` variant is smaller and sufficient for text-heavy documents. If GPU becomes available, switch to `docling-serve-cu128`.
  - *Alternative considered:* `ds4sd/docling-serve` (generic) — less predictable behavior without explicit CPU/GPU designation.

- **Port: 5001 (internal only)**
  - *Rationale:* Same pattern as Tika (internal Docker network, no exposed ports). Open WebUI connects via `http://docling:5001`.

- **UVICORN_WORKERS=1 for Docling**
  - *Rationale:* Docling documentation explicitly warns that workers > 1 causes "Task Not Found" routing errors. Single worker is sufficient for our 10-50 user base.

- **Configuration via environment variables + Admin Panel**
  - Set `CONTENT_EXTRACTION_ENGINE=docling` in docker-compose
  - Set extraction URL to `http://docling:5001` in docker-compose or Admin Panel
  - *Rationale:* Environment variable ensures persistence across container restarts. Admin Panel provides override capability.

- **Keep Tika service definition commented out (not deleted)**
  - *Rationale:* Easy rollback if Docling has issues with specific file formats.

## Risks / Trade-offs

- **[Risk] Docling may not support as many file formats as Tika (1000+ vs ~20)**
  - *Mitigation:* Our users primarily upload DOCX, PDF, and XLSX. Docling handles all three. Keep Tika config commented for quick rollback.

- **[Risk] Docling startup is slower (ML model loading)**
  - *Mitigation:* Set `start_period: 60s` in healthcheck to allow model warm-up. Container restart is infrequent.

- **[Risk] EasyOCR model download on first use**
  - *Mitigation:* First OCR request may be slow (~30s) while models download. Subsequent requests use cached models in the container volume.

- **[Trade-off] Slightly higher RAM usage (~2GB vs 1.5GB for Tika)**
  - *Acceptable:* Server has 32GB RAM. The 500MB difference is negligible.

## Migration Plan

1. Stop current stack: `docker compose down`
2. Update `docker-compose.yml` (add docling, comment out tika)
3. Start stack: `docker compose up -d`
4. Verify Docling health: `curl http://localhost:5001/health`
5. Configure Admin Panel > Settings > Documents > Engine = Docling
6. Test upload: upload the same 6MB DOCX that previously failed
7. **Rollback:** Uncomment tika, comment docling, restart. Change Admin Panel back to Tika.
