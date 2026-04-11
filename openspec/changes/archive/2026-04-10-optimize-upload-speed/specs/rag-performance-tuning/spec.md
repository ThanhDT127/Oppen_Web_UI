## ADDED Requirements

### Requirement: Embedding batch size SHALL be configurable for optimal throughput
The system SHALL process document chunks in configurable batches during embedding generation, defaulting to batch size 100 for CPU-optimized throughput.

#### Scenario: Batch embedding processes multiple chunks simultaneously
- **WHEN** a file with 100 chunks is uploaded
- **THEN** the system SHALL embed all 100 chunks in a single batch call
- **THEN** embedding generation SHALL complete in under 2 seconds on CPU

#### Scenario: Large files with more than batch_size chunks
- **WHEN** a file generates more than 100 chunks
- **THEN** the system SHALL process chunks in batches of 100
- **THEN** total processing time SHALL be significantly less than processing 1-at-a-time

### Requirement: Chunk configuration SHALL balance performance and quality
The system SHALL use chunk size 1500 with overlap 100 to reduce total chunk count while maintaining sufficient context for RAG retrieval.

#### Scenario: Document chunking produces fewer, larger chunks
- **WHEN** a 50KB markdown file is processed
- **THEN** the system SHALL produce approximately 33% fewer chunks compared to chunk_size=1000
- **THEN** each chunk SHALL contain sufficient context for meaningful semantic search

### Requirement: File upload count limit SHALL support batch workflows
The system SHALL allow uploading up to 20 files per request.

#### Scenario: User uploads many files at once
- **WHEN** a user uploads 15 files simultaneously
- **THEN** the system SHALL accept and process all 15 files
- **THEN** processing SHALL NOT be rejected due to file count limits
