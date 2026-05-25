## ADDED Requirements

### Requirement: NLTK data packages SHALL be pre-downloaded in Docker image
The system SHALL include all required NLTK data packages (`averaged_perceptron_tagger_eng`, `punkt_tab`) in the Docker image at build time. The packages SHALL be stored in a directory that is readable by the application user (UID 1000).

#### Scenario: Container starts with NLTK data available
- **WHEN** the Open WebUI container starts
- **THEN** NLTK data packages `averaged_perceptron_tagger_eng` and `punkt_tab` SHALL be present at `/usr/local/nltk_data/`

#### Scenario: File upload triggers document processing without NLTK download
- **WHEN** a user uploads a file (PDF, DOCX, TXT, etc.)
- **THEN** the `unstructured` library SHALL find NLTK data locally and process the file without attempting runtime download
- **THEN** no `PermissionError` SHALL occur

#### Scenario: File content is available for RAG after upload
- **WHEN** a user uploads a document and the processing completes
- **THEN** the document content SHALL be chunked, embedded, and stored in PGVector
- **THEN** the AI SHALL be able to reference the document content in responses
