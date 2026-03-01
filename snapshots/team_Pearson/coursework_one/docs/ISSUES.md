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
- [ ] **Data Requirements Log:** Update `docs/data_requirement.md` with explicit missing data tolerance rules and look-ahead bias prevention.
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
- [ ] **PostgreSQL DDL:** Provide the SQL script to create `factor_observations` in `systematic_equity`. Must enforce uniqueness on (`symbol`, `observation_date`, `factor_name`) and include proper indexes.
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
- [ ] **Strict Folder Structure:** All developments MUST be placed under `team_<insert your team id>/coursework_one/` and include `config/`, `modules/` (with `db/`, `input/`, `output/` sub-directories), and a test directory (`tests/` or `test/`). You MUST also initialize a `README.md` and a `CHANGELOG.md` at the team root as shown in the coursework specifications.
- [ ] **Database Isolation:** Do NOT copy databases into other folders. Ensure any changes outside the group folder (e.g., `000.Database`) are un-staged before committing to Git.
- [ ] **CLI & Scheduling:** `Main.py` must support `--run-date` and `--frequency`. Implement or mock a scheduling library (like `APScheduler` or `Airflow`) to satisfy the "Application Flexibility" requirement.
- [ ] **Security Vulnerability Fixes:** Configure bandit (or safety) for security scans. You must implement a process to not just scan, but promptly address and fix any identified vulnerabilities before code is merged.
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
- [ ] **Auto-Documentation:** Ensure sphinx.ext.autodoc is correctly configured in conf.py to automatically pull docstrings from all modules (Input, Transform, DB) into the final HTML API Reference.
---

### Issue #6: [Extraction] Ingest Structured Pricing and Fundamental Data to MinIO
**Assignee:** Extractor A (Role 6 / Developer)
**Labels:** `data-ingestion`, `api`, `alpha-vantage`

**Description:**
Develop the data ingestion pipeline to pull historical structured pricing and deep fundamental financial data (Income Statement, Balance Sheet, Dividends) from external APIs (e.g., Alpha Vantage) and store the raw payloads securely in the Data Lake (MinIO).

**Inputs:**
- Company list from `get_company_universe()`.

**Outputs:**
- `modules/input/extract_source_a.py` (or equivalent source-specific extractor module).

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

### Issue #7: [Extraction & Aggregation] Ingest Unstructured News & Compute Rolling Sentiment
**Assignee:** Extractor B (Role 7 / Developer)
**Labels:** `data-ingestion`, `alternative-data`, `pandas-aggregation`

**Description:**
Enhance the dataset by ingesting unstructured alternative data (news headlines) from external APIs to compute the Sentiment risk factor. Crucially, this module must handle both the immutable storage of raw JSONs in the Data Lake AND the in-memory time-series aggregation to deliver a clean factor table to downstream ETL.

**Inputs:**
- Company list from `get_company_universe()`.

**Outputs:**
- `modules/input/extract_source_b.py` (**Must `return` a clean Pandas DataFrame for Role 8**).

**Acceptance Criteria (Definition of Done):**

- [ ] **Extraction Logic & Raw Storage:** Call an external news API (e.g., Alpha Vantage News Sentiment) to scrape raw news. Persistently store the raw JSON payloads into MinIO strictly adhering to the `raw/{source}/...` pathing. **DO NOT filter or drop any data here.**
- [ ] **Pandas Time-Series Aggregation (CRITICAL):** After fetching the data, use Pandas to compress the high-frequency data in memory:
  1. *Daily Compression:* Group by company and date to get a daily average.
  2. *Rolling Window:* Apply `.rolling(window=30, min_periods=1).mean()` to compute the 30-day moving average of the sentiment score (-1.0 to 1.0).
- [ ] **Module Handoff (Return Format):** The module must NOT attempt to write to PostgreSQL. It must simply `return` a clean DataFrame containing exactly these columns: `[symbol, observation_date, sentiment_score_30d, article_count_30d]` to hand off to Role 8.
- [ ] **Fallback Logic:** If no news exists for a 30-day window, handle the empty state gracefully and output a score of `0.0`.

---

### Issue #8: [ETL & QA] Merge Factors, Enforce Quality Rules & Achieve 80% pytest Coverage
**Assignee:** Transform, Quality & Tests Anchor (Role 8 / Developer)
**Labels:** `testing`, `data-processing`, `quality-assurance`

**Description:**
Act as the central integration point. Call the extraction modules (Roles 6 & 7) to retrieve pre-aggregated data, perform cross-frequency merging, enforce strict financial data quality rules, and load the final hybrid factors into the curated PostgreSQL table.

**Inputs:**
- Raw pricing & fundamental data from MinIO (via Role 6's module).
- Pre-aggregated Sentiment DataFrame (returned directly from Role 7's module).
- Investable universe mapping from PostgreSQL `company_static`.

**Outputs:**
- `modules/output/normalize.py`
- `modules/output/quality.py`
- Comprehensive `pytest` test suite.

**Acceptance Criteria (Definition of Done):**

- [ ] **Cross-Frequency Normalization Logic:** Call the functions written by Role 6 and Role 7. You will receive DataFrames of varying frequencies (Daily Sentiment, Monthly Price, Quarterly/Annual Fundamentals). You must successfully merge these using Pandas `merge_asof` or forward-filling mechanisms to align them perfectly on the `observation_date`.

- [ ] **Quality Rules Engine:** Programmatically enforce the strict business rules:
  * **Look-ahead Bias Prevention:** Enforce the strictly backward-looking `[-3 to 0 days]` lag for all Price data.
  * **Staleness Drops:** Enforce the max 12-month forward-fill limit for fundamentals (and the 9-month limit for Debt/Equity).
  * **Distress Exclusions:** Explicitly `DROP` rows with Negative Revenue or Negative Equity.

- [ ] **Coverage Red Line:** Execute tests using `poetry run pytest ./tests/` and achieve a minimum of 80% code coverage. You must mock the upstream DataFrames to test edge cases (e.g., forcing negative equity to ensure the row drops).

- [ ] **Git Submission Compliance:** Ensure the final code is pushed to branch `feature/coursework_one_<YOUR_TEAM_ID>` before creating the PR for @uceslc0.rsework_one_<YOUR_TEAM_ID>` before creating the PR for `@uceslc0`.
