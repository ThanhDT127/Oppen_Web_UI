## Context

We are moving from a single static test to a comprehensive benchmarking suite. The system must be able to handle dozens of questions across multiple documents, verifying facts and citations for each, and then providing a high-level report.

## Goals / Non-Goals

**Goals:**
- Decouple test data (questions/facts) from test code.
- Support Excel as the primary data management interface for non-technical users.
- Provide a clear performance and accuracy summary at the end of the run.
- Minimize test overhead by reusing Knowledge Bases and login sessions where possible.

**Non-Goals:**
- Implementing a full LLM evaluation backend (this remains an E2E UI test).
- Supporting parallel execution of questions within the same chat (too prone to UI race conditions).

## Decisions

### 1. Data Format: Excel (`.xlsx`)
- **Rationale**: Excel is already used in the project for test documentation. It allows easy editing of multiple fields (Question, Expected Keywords, Document Name).
- **Tool**: `xlsx` (SheetJS) library for reading.

### 2. Test Execution: Sequential Loop
- **Decision**: The test suite will load the Excel file, then iterate through the rows.
- **Rationale**: Sequential execution within a single chat session is more efficient than logging in and uploading for every single question, as long as the questions refer to the same Knowledge Base.

### 3. Reporting: Formatted Terminal Output + Optional JSON
- **Decision**: Collect results in an array and print a summary table at the end of the test run.
- **Rationale**: Immediate visibility for the developer.

### 4. Excel Schema
| Column | Description |
|--------|-------------|
| ID | Unique identifier |
| Category | E.g., Lighting, Safety |
| Question | The prompt to send |
| Expected Facts | Semicolon-separated list of keywords or regex |
| Document | Filename to use for verification/citations |

## Risks / Trade-offs

- **[Risk]** Large Excel files might slow down test initialization.
  - **Mitigation**: Filter by category if needed; usually benchmarks are small (10-50 questions).
- **[Risk]** Sequential execution can be slow.
  - **Mitigation**: Use a very high or zero timeout for the suite and provide progress logging.
- **[Risk]** Context Window limits.
  - **Mitigation**: For very long benchmarks, we may need to reset the chat session periodically.
