## ADDED Requirements

### Requirement: Docling container runs as document extraction service
The system SHALL deploy a `docling-serve` container on the internal Docker network, listening on port 5001, accessible to the Open WebUI application at `http://docling:5001`.

#### Scenario: Container starts successfully
- **WHEN** the Docker Compose stack is started
- **THEN** the `docling` container SHALL reach healthy status within 90 seconds
- **THEN** the `/health` endpoint SHALL return HTTP 200

#### Scenario: Container restarts after crash
- **WHEN** the `docling` container exits unexpectedly
- **THEN** Docker SHALL restart the container automatically (restart: unless-stopped)

### Requirement: Open WebUI uses Docling for content extraction
The system SHALL configure Open WebUI to use Docling as the default content extraction engine via the `CONTENT_EXTRACTION_ENGINE=docling` environment variable and extraction URL `http://docling:5001`.

#### Scenario: DOCX file with text and tables uploads successfully
- **WHEN** a user uploads a 6MB DOCX file containing text, tables, and embedded logos
- **THEN** the system SHALL extract text content within 30 seconds (no OCR timeout)
- **THEN** the extracted content SHALL NOT be empty
- **THEN** the document SHALL appear in the Knowledge Base with searchable content

#### Scenario: PDF file uploads successfully
- **WHEN** a user uploads a standard PDF file with text content
- **THEN** the system SHALL extract text using Docling's native parser
- **THEN** table structures SHALL be preserved in the extracted Markdown output

#### Scenario: Scanned PDF triggers OCR automatically
- **WHEN** a user uploads a scanned PDF (image-only, no text layer)
- **THEN** Docling SHALL invoke EasyOCR to extract text from images
- **THEN** the extracted text SHALL be returned to Open WebUI for embedding

### Requirement: Tika service is removed from active deployment
The system SHALL remove the `tika` service from the active Docker Compose configuration. The Tika service definition SHALL remain in docker-compose.yml as a commented-out block for rollback purposes.

#### Scenario: Stack runs without Tika
- **WHEN** the Docker Compose stack is started after migration
- **THEN** no `openwebui-tika` container SHALL be running
- **THEN** all other services (postgres, redis, litellm, middleware, open-webui, nginx) SHALL remain healthy

### Requirement: Docling resource limits are configured
The system SHALL set resource limits for the Docling container: memory limit of 2GB, CPU limit of 2 cores. UVICORN_WORKERS SHALL be set to 1 to prevent task routing errors.

#### Scenario: Docling operates within resource limits
- **WHEN** multiple documents are being processed concurrently
- **THEN** the container SHALL NOT exceed 2GB memory
- **THEN** document processing SHALL queue rather than crash under load
