## 1. Setup and Library Integration

- [ ] 1.1 Install `xlsx` (SheetJS) library in `tests/` directory
- [ ] 1.2 Create `tests/fixtures/rag_benchmark.xlsx` with a template based on the design

## 2. Implement Excel Data Loader

- [ ] 2.1 Create a utility in `tests/utils/excel-loader.ts` to read the benchmark file
- [ ] 2.2 Add error handling for missing files or invalid schemas

## 3. Refactor Test Runner

- [ ] 3.1 Update `tests/rag.spec.ts` to load data from the Excel loader
- [ ] 3.2 Implement a dynamic test generator or an internal loop for benchmark questions
- [ ] 3.3 Ensure Knowledge Base setup and cleanup happen outside the question loop

## 4. Reporting and Summary

- [ ] 4.1 Create a results accumulator to track status, latency, and citations for each question
- [ ] 4.2 Implement a `summarizeResults` function to print a clean table at the end of the run
- [ ] 4.3 Add a final check: if ANY benchmark question fails, the test suite should fail

## 5. Validation

- [ ] 5.1 Add at least 3-5 real benchmark questions to the Excel file
- [ ] 5.2 Run the full benchmark suite and verify the final summary output
