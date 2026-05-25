## 1. Docker Compose Changes

- [x] 1.1 Comment out the `tika` service block in `docker-compose.yml` (lines 146-160)
- [x] 1.2 Add `docling` service block with image `ghcr.io/ds4sd/docling-serve-cpu:latest`, port 5001, healthcheck on `/health`, `UVICORN_WORKERS=1`, resource limits (2GB RAM, 2 CPU)
- [x] 1.3 Update `open-webui` service: replace `tika` dependency with `docling`, add environment variables `CONTENT_EXTRACTION_ENGINE=docling` and `DOCLING_API_BASE_URL=http://docling:5001`
- [x] 1.4 Remove the `tika` condition from `open-webui.depends_on`

## 2. Deploy & Verify Infrastructure

- [x] 2.1 Run `docker compose up -d` and verify all containers start healthy
- [x] 2.2 Verify Docling container health: `docker exec openwebui-docling curl http://localhost:5001/health`
- [x] 2.3 Verify no `openwebui-tika` container is running

## 3. Configure Open WebUI Admin Panel

- [ ] 3.1 Navigate to Admin Panel > Settings > Documents
- [ ] 3.2 Set Default content extraction engine to "Docling"
- [ ] 3.3 Set Extraction engine URL to `http://docling:5001`
- [ ] 3.4 Save and verify settings persist after page refresh

## 4. Testing

- [ ] 4.1 Upload the same 6MB DOCX file that previously failed — verify success (no timeout, no empty content error)
- [ ] 4.2 Upload a standard PDF file — verify text extraction works
- [ ] 4.3 Upload a file with tables — verify table content is preserved in Knowledge Base search results
- [ ] 4.4 Test chat with uploaded knowledge — verify RAG retrieval returns relevant content
