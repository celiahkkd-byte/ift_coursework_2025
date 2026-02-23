### Issue #1: [PM] Draft Investment Goals, Factor Definition & Report Skeleton
**Assignee:** Investment Product Owner (Role 1)
**Labels:** `documentation`, `business-logic`, `report`

**Description:**
As the Product Owner, draft the foundational investment goals and define the core factors to guide the technical implementation. Furthermore, set up the official skeleton for the final 20,000-word Coursework One report to ensure all grading criteria are met from day one.

**Inputs:**
- Investable Universe List (`company_static` table).
- Findings from external API research.

**Outputs:**
- Factor definitions for CW2.
- Master template for the final UCL Turnitin report.

**Acceptance Criteria (Definition of Done):**
- [ ] **CW2 Factor Definition:** Document the economic rationale, formula, and rebalancing frequency for the core factors (Dividend Yield, EBITDA Margin, Debt/Equity, P/B, Sentiment).
- [ ] **Final Report Skeleton:** Create the master template for the final report. It MUST contain these exact 5 sections:
    1. Introduction
    2. Investment goals and needs from a data perspective
    3. Proposed solution & vision: why, what and how this solution is implemented
    4. Architecture and infrastructure design (to be co-authored with Role 3)
    5. Conclusions
- [ ] **Presentation Prep:** Outline the compelling presentation required to demonstrate how the product meets its intended goals.

---
### Issue #2: [Requirements] Define Data Requirements Log & Architecture Diagrams
**Assignee:** Portfolio Product Specialist (Role 2)
**Labels:** `documentation`, `requirements`

**Description:**
Translate the investment factors defined by the PM into strict, technical data specifications. Create high-level visual architecture diagrams to guide the engineering team.

**Inputs:**
- The list of business factors defined by the PO.

**Outputs:**
- Data Requirements Log mapping (`Business Metric` → `Raw Field` → `Origin Source` → `Target Storage` → `Frequency` → `Missing Rules`).
- System architecture diagrams.
- Data Lineage documentation
- Data Dictionary
- Data_catalog

**Acceptance Criteria (Definition of Done):**
- [ ] **Data Requirements Log:** Update `docs/data_requirements_log.md` with explicit missing data tolerance rules and look-ahead bias prevention.
- [ ] **Architecture Diagrams:** Create high-level system architecture diagrams using `draw.io` or `lucidcharts` to visually map the data flow from External APIs / Internal DB → MinIO → PostgreSQL.
- [ ] **Documentation Handoff:** Ensure all requirement logs and diagrams are formatted in standard Markdown (`.md`) and handed over to the developer managing the Sphinx repository (Role 5) for integration.
---

###  Issue #3: [Architecture] Design DB Schema, MinIO Partitioning & Containerization
**Assignee:** Architecture & Storage Designer (Role 3 / Developer)
**Labels:** `database`, `architecture`, `docker`

**Description:**
Design a scalable storage solution utilizing PostgreSQL and MinIO. Ensure that any expanded infrastructure components comply with strict Docker containerization rules.

**Inputs:**
- Data Requirements Log (from the Specialist).

**Outputs:**
- PostgreSQL DDL scripts.
- MinIO Data Lake Pathing schema.
- Extended `docker-compose` configurations if necessary.

**Acceptance Criteria (Definition of Done):**
- [ ] **PostgreSQL DDL:** Provide the SQL script to create `factor_observations` in `systematic_equity`. Must include a composite primary key (`symbol`, `observation_date`, `factor_name`) and proper indexes.
- [ ] **MinIO Data Lake Pathing:** Define the exact folder structure for raw unstructured files. Required format: `raw/{source_name}/{dataset_type}/observation_date={YYYY-MM-DD}/run_date={YYYY-MM-DD}/`.
- [ ] **Robustness:** The database design must be flexible enough to handle the addition or removal of companies from the `company_static` table.
- [ ] **Containerization Compliance:** Ensure any additional components designed for the infrastructure (e.g., Kafka for streaming, Airflow for scheduling) are strictly containerized using Docker, extending the provided `docker-compose.yml`.
- [ ]  Retrieval Optimization:
 - Ensure that the factor_observations table supports efficient retrieval by symbol and by observation year.
 - Implement appropriate indexing strategies to optimize queries filtering by symbol, observation_date, and factor_name.

---

### Issue #4: [Integrator] Establish Pipeline Skeleton, Toolchain & Strict Folder Structure
**Assignee:** Pipeline Integrator (Role 4 / Developer)
**Labels:** `infrastructure`, `toolchain`

**Description:**
Set up the fundamental project architecture using Poetry. Enforce the strict folder structure required by the coursework guidelines and configure the scheduling logic.

**Inputs:**
- Architectural design specifications.

**Outputs:**
- `Main.py` with CLI.
- `pyproject.toml` (Poetry).
- Initialized folder structure.

**Acceptance Criteria (Definition of Done):**
- [ ] **Toolchain Configuration:** Initialize with `poetry init`. Configure `flake8`, `black`, `isort`, and `bandit` (or `safety`) for security scans.
- [ ] **Strict Folder Structure:** All developments MUST be placed under `team_<insert your team id>/coursework_one/` containing EXACTLY the following subfolders: `config/`, `modules/` (with `db/`, `input/`, `output/` sub-directories), `static/`, and `test/`.
- [ ] **Database Isolation:** Do NOT copy databases into other folders. Ensure any changes outside the group folder (e.g., `000.Database`) are un-staged before committing to Git.
- [ ] **CLI & Scheduling:** `Main.py` must support `--run-date` and `--frequency`. Implement or mock a scheduling library (like `APScheduler` or `Airflow`) to satisfy the "Application Flexibility" requirement.

---

### Issue #5: [DB Connectivity] Implement Universe Extraction Layer & Sphinx Docs
**Assignee:** Universe & DB Connectivity Engineer (Role 5 / Developer)
**Labels:** `database`, `core-module`, `documentation`

**Description:**
Develop a secure and reusable database connection module that reads the dynamic investable universe from the predefined PostgreSQL database. Additionally, initialize and configure the Sphinx documentation framework for the project.

**Inputs:**
- PostgreSQL configuration details exposed via Docker.

**Outputs:**
- `modules/db/db_connection.*`
- Initialized Sphinx `/docs` directory.

**Acceptance Criteria (Definition of Done):**
- [ ] **Connection Manager:** Implement a robust connection manager reading credentials securely from environment variables.
- [ ] **Universe Retrieval:** Implement a function `get_company_universe()` that dynamically fetches symbols (or `symbols`) from `systematic_equity.company_static`.
- [ ] **Limit Parameter:** The function MUST support a `--company-limit` parameter to allow developers to pull a small subset of companies for fast local debugging.
- [ ] **Sphinx Setup:** Run `sphinx-quickstart` to initialize the `/docs` directory. Configure `conf.py` (e.g., adding `myst_parser` for markdown support and `sphinx.ext.autodoc` to automatically extract Python docstrings).
- [ ] **Documentation Build:** Ensure the command `make html` successfully builds the documentation site locally.
- [ ]  Documentation Content Requirements:
 - The Sphinx documentation must include:
   * Installation Guide (environment setup, docker instructions).
   * Usage Instructions (CLI examples with --run-date and --frequency).
   * API Reference generated automatically via autodoc.
   * Architecture Overview describing the data flow and storage design.
 - Ensure the HTML documentation builds successfully using `make html`.

---

### Issue #6: [Extraction] Ingest Structured Pricing and Fundamental Data to MinIO
**Assignee:** Extractor A (Role 6 / Developer)
**Labels:** `data-ingestion`, `api`, `alpha-vantage`

**Description:**
Develop the data ingestion pipeline to pull historical structured pricing and deep fundamental financial data (Income Statement, Balance Sheet, Dividends) from external APIs (e.g., Alpha Vantage) and store the raw payloads securely in the Data Lake (MinIO).

**Inputs:**
- Company list from `get_company_universe()`.

**Outputs:**
- `modules/input/extract_alphavantage.py` (or equivalent source-specific extractor module).

**Acceptance Criteria (Definition of Done):**

- [ ]  **Extraction Logic (CRITICAL):**
  Successfully call the external API (e.g., Alpha Vantage) and extract the following required fields:
  * **Pricing & Dividends (Daily/Monthly):**
    * Adjusted Close Price
    * Dividend Per Share (DPS)
  * **Income Statement (Quarterly & Annual):**
    * EBITDA
    * Revenue
    * Report `end_date` (mandatory)
  * **Balance Sheet (Quarterly & Annual):**
    * Book Value / Total Equity
    * Outstanding Shares
    * Total Debt
  * **Fallback Requirement (Mandatory):**
    * Short-term Debt
    * Long-term Debt
    *(These must be extracted even if Total Debt exists, so downstream ETL can compute it when missing).*

- [ ] **Historical Depth:**
  * Must successfully retrieve at least **5 years** of historical data across all required endpoints for the full company universe.

- [ ]  **Raw Storage (Immutable):**
  * Persistently serialize and store the entire raw API response (JSON/CSV) into MinIO.
  * Must strictly follow the `raw/{source}/...` pathing convention.
  * **Do NOT drop missing values.**
  * **Do NOT filter negative values.**
  * Raw data must remain fully intact for downstream QA.

- [ ]  **Strict Error Handling & Rate Limits:**
  * Implement robust retry logic.
  * Use exponential backoff.
  * Implement `time.sleep()` safeguards.
  * Prevent HTTP 429 bans.
  * Ensure the pipeline can run continuously without crashing under API rate limits.
---

### Issue #7: [Extraction] Ingest Unstructured News & Calculate Sentiment
**Assignee:** Extractor B (Role 7 / Developer)
**Labels:** `data-ingestion`, `alternative-data`

**Description:**
Enhance the dataset by ingesting unstructured alternative data (news headlines) to compute the Sentiment risk factor.

**Inputs:**
- Company list from `get_company_universe()`.

**Outputs:**
- `modules/input/extract_source_b.py`.

**Acceptance Criteria (Definition of Done):**
- [ ] **Extraction Logic:** Call an external news API (e.g., Alpha Vantage News Sentiment) to scrape raw news text related to the target companies.
- [ ] **Raw Storage:** Persistently store the raw JSON news payloads into MinIO.
- [ ] **Sentiment Computation:** Implement NLP scoring logic to calculate a normalized daily `sentiment_score` (-1.0 to 1.0) over a rolling 30-day window.
- [ ] **Fallback Logic:** If no news exists for a 30-day window, the function must handle the empty state gracefully and return `0.0`.

---

###  Issue #8: [ETL & QA] Normalize Data, Enforce Quality & Achieve 80% pytest Coverage
**Assignee:** Transform, Quality & Tests Anchor (Role 8 / Developer)
**Labels:** `testing`, `data-processing`

**Description:**
Transform the raw MinIO data and internal database fields into the curated PostgreSQL table. Enforce strict data quality standards and ensure the entire codebase meets the academic 80% test coverage requirement.

**Inputs:**
- Raw data stored in MinIO.
- Internal fundamentals from PostgreSQL.

**Outputs:**
- `modules/transform/normalize.py`.
- `modules/quality/checks.py`.
- Comprehensive `pytest` test suite.

**Acceptance Criteria (Definition of Done):**
- [ ] **Normalization Logic:** Implement the computation for hybrid factors (EBITDA Margin, P/B Ratio, Debt/Equity) merging internal SQL data with external API data.
- [ ] **Quality Rules Engine:** Programmatically enforce the rules defined in Issue #2 (e.g., look-ahead bias prevention, maximum 12-month staleness drops).
- [ ] **Coverage Red Line:** Execute tests using `poetry run pytest ./tests/` and achieve a minimum of **80% code coverage**.
- [ ] **E2E Integration Test:** Automate the execution of the Architect's two required queries to assert that row counts, time ranges, and unique keys are valid and non-duplicated.
- [ ] **Git Submission Compliance:** Ensure the final code is pushed to branch `feature/coursework_one_<YOUR_TEAM_ID>` before creating the PR for `@uceslc0`.
