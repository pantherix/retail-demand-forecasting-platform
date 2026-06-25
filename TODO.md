# TODO - Docker + Fresh Browser Verification

## Plan
- [ ] Step 1: Ensure docker compose services are running (postgres/api/dashboard).
- [ ] Step 2: Perform fresh browser session verification manually.
  - [ ] 2.1 Clear browser storage.
  - [ ] 2.2 Open http://localhost:3000.
  - [ ] 2.3 Login.
  - [ ] 2.4 Upload a new dataset.
  - [ ] 2.5 Import dataset.
  - [ ] 2.6 Generate forecast.
  - [ ] 2.7 Visit pages:
    - [ ] Dashboard
    - [ ] Forecast Accuracy
    - [ ] Supply Grid
    - [ ] Audit Logs
    - [ ] Crew Management
- [ ] Step 3: Capture evidence from each page
  - [ ] 3.1 Network failures (failed requests)
  - [ ] 3.2 Console errors
  - [ ] 3.3 HTTP status codes (especially non-2xx/3xx)
- [ ] Step 4: If any error appears
  - [ ] 4.1 Identify root cause (frontend console, network response, backend logs)
  - [ ] 4.2 Fix the issue in code/config
  - [ ] 4.3 Rerun verification from scratch
- [ ] Step 5: If no errors
  - [ ] Declare "Release Candidate Stable".

