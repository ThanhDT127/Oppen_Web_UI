## Why

The current RAG functional tests are limited to a single hardcoded question and verification logic. To properly evaluate the system's performance across different domains and document types, we need a scalable benchmarking system. This change introduces data-driven testing, allowing users to define a set of benchmark questions and expected facts in an Excel file, which the test suite will then execute and summarize.

## What Changes

- **Excel Integration**: Add the capability to read benchmark data (questions, expected facts, categories) from an Excel file.
- **Dynamic Test Loop**: Refactor the RAG test to loop through multiple questions within a single session or across scoped sessions.
- **Summary Reporting**: Implement a post-test summary that aggregates:
    - Pass/Fail status per question.
    - Latency statistics (min, max, average).
    - Citation coverage and accuracy.
- **Improved Fixture Management**: Standardize the organization of benchmark documents and their corresponding questions.

## Capabilities

### New Capabilities
- `rag-data-driven-benchmarking`: System to ingest test cases from external files (Excel) and execute them sequentially with automated validation and summary reporting.

### Modified Capabilities
- `rag-functional-testing`: (Delta) Extend the existing functional test to support iteration and result aggregation.

## Impact

- **New Dependencies**: Introduction of `exceljs` or `xlsx` library to the `tests/` directory.
- **Test File Refactoring**: `tests/rag.spec.ts` will become a dynamic test runner.
- **New Assets**: Addition of `tests/fixtures/rag_benchmark.xlsx` as the source of truth for test cases.
