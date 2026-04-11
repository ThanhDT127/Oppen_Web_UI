## Why

Apache Tika (`latest-full`) is causing document upload failures for files >2MB. Tika's Tesseract OCR engine auto-activates on any file containing embedded images (logos, charts, headers), consuming 300+ seconds until it hits the default `taskTimeoutMillis` limit — at which point the forked process is killed, returning empty content to Open WebUI. This results in the error: `400: The content provided is empty`. Users cannot upload standard DOCX business documents (text + tables) to the Knowledge Base.

Docling (`docling-serve`) is a modern, ML-powered document extraction engine that only invokes OCR when necessary, outputs structured Markdown (preserving tables and headings), and processes a 6MB DOCX in ~3-5 seconds instead of timing out.

## What Changes

- **BREAKING**: Replace `apache/tika:latest-full` container with `ds4sd/docling-serve` in `docker-compose.yml`.
- Update Open WebUI environment to switch content extraction engine from Tika to Docling.
- Remove the `tika` service dependency from `open-webui` service in docker-compose.
- Add `docling` service with appropriate resource limits and healthcheck.
- Configure Open WebUI Admin Panel to point to Docling extraction URL.

## Capabilities

### New Capabilities
- `docling-extraction`: Replace Tika with Docling as the document extraction engine. Covers container deployment, Open WebUI integration, OCR configuration, and structured Markdown output for improved RAG quality.

### Modified Capabilities

## Impact

- `docker-compose.yml`: Remove `tika` service, add `docling` service.
- Open WebUI environment variables for content extraction engine configuration.
- RAG pipeline quality: Structured Markdown output from Docling should improve embedding quality for documents with tables and headings.
- No impact on middleware, LiteLLM, or Nginx configuration.
- Existing Knowledge Base documents may need re-indexing to benefit from improved extraction.
