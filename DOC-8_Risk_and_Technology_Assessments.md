# [DOC-8] Risk and Technology Assessments

**Project:** Autonomous Vehicle Job Profiles  
**Group:** Group 3  
**Purpose:** Document testable functional and non-functional requirements, assess relevant technology options, identify delivery skill gaps, and record project risks with mitigation plans.

## 1. Assessment Basis

This assessment is based on the current project requirements, data-model documentation, source investigations, prototype work, repository workflows, meeting records, and GitHub Issues.

Technology options are assessed against the needs of the MVP using the following criteria:

- suitability for a multi-source autonomous-vehicle job-data platform;
- compatibility with the existing Python-based data-processing work;
- support for typed and maintainable frontend/backend integration;
- fit with the relational Silver and Gold data models;
- maintainability when job sources or schemas change;
- testing and CI/CD support;
- implementation effort and learning cost for the team;
- ability to preserve traceability, data quality, and ethical collection practices.

Implementation evidence is used only to show feasibility and current project constraints. It does not by itself determine the technology choice.

---

## 2. Functional Requirements

Each functional requirement is written as a verifiable system behaviour.

### FR-01 — Maintain an approved company and data-source register

**Requirement:** The system shall store a record for each approved autonomous-vehicle company and job-data source, including the company name, source location, collection status, and a documented reason when a source is excluded or cannot be collected.

**Verification:** Compare the stored source register with the agreed project source list and confirm that every approved source has a status and that every excluded source has a recorded reason.

### FR-02 — Collect public job advertisements

**Requirement:** The system shall collect publicly accessible job advertisements from sources that are marked as approved and technically accessible in the source register. Failed collection attempts shall be recorded.

**Verification:** Run collection against a representative set of approved sources and confirm that accessible advertisements are stored and failed attempts produce a collection record rather than being silently ignored.

### FR-03 — Preserve source traceability

**Requirement:** The system shall retain, for every collected job advertisement used in the dataset, the original source URL, collection date, and source platform or source identifier where available.

**Verification:** Select stored advertisements and confirm that each record can be traced back to its original source evidence.

### FR-04 — Extract and store agreed job fields

**Requirement:** The system shall store the agreed analysis fields for each collected advertisement when the information is present in the source. These fields include:

- company;
- job title;
- description;
- location;
- employment type;
- seniority or experience level;
- posting date;
- salary or compensation when available;
- source metadata.

Unavailable values shall remain missing rather than being inferred without evidence.

**Verification:** Compare a manually reviewed sample of source advertisements with their structured records and check that available fields are captured correctly and unavailable fields are not invented.

### FR-05 — Normalise job-market information

**Requirement:** The system shall apply documented normalisation rules to equivalent company names, locations, role categories, skills, and technologies while retaining the original source information needed for traceability.

**Verification:** Test known equivalent source values and confirm that they map to the agreed normalised values without deleting the original evidence.

### FR-06 — Classify jobs using a shared AV taxonomy

**Requirement:** The system shall assign each classifiable job advertisement to one or more categories from the current approved autonomous-vehicle taxonomy. Automated classification shall retain a confidence value or review status and the taxonomy version used.

**Verification:** Run classification on a labelled validation sample and confirm that outputs use only approved taxonomy values, preserve the taxonomy version, and expose uncertainty for review.

### FR-07 — Extract skills and technologies

**Requirement:** The system shall identify and store job-related technical information available in the advertisement, including programming languages, frameworks, tools, platforms, domain concepts, certifications, datasets, and other agreed technology terms.

**Verification:** Compare extracted skill and technology values with a manually reviewed sample of advertisements.

### FR-08 — Provide job search and filtering

**Requirement:** The system shall allow users to search the available job dataset and apply filters for fields supported by the stored data, including category or role, company, location, skill or technology, and experience or employment type.

**Verification:** For each supported filter, execute a query with known matching and non-matching records and confirm that the returned results satisfy the selected criteria.

### FR-09 — Provide company and job detail views

**Requirement:** The system shall allow users to browse companies, view associated jobs, open job details, and follow the original job or career source link when that link is available.

**Verification:** Navigate from company search to company details and from job search to job details, and confirm that displayed relationships and source links match stored data.

### FR-10 — Provide aggregate demand views

**Requirement:** The system shall calculate and present aggregate counts or distributions from validated stored data by skills and technologies, job categories, companies, and locations where sufficient data is available.

**Verification:** Compare displayed aggregate values with independently calculated counts from the same validated dataset.

### FR-11 — Control time-based trend presentation

**Requirement:** The system shall present a time-based trend only when the underlying records contain valid dates or repeated collection snapshots that satisfy the project’s agreed evidence threshold. When the threshold is not met, the system shall display an insufficient-data state.

**Verification:** Test one dataset that meets the agreed threshold and one that does not, and confirm that a trend is shown only for the qualifying dataset.

### FR-12 — Record collection and processing outcomes

**Requirement:** The system shall record each collection or processing run with its date, source, status, number of jobs found or processed where available, and error information when a run fails.

**Verification:** Execute both successful and intentionally failing runs and confirm that the corresponding log records contain the required fields.

### Current implementation note

The current repository provides partial implementation evidence for company data, frontend routes, source investigation, and a single-source collection/classification prototype. Job-domain APIs, full taxonomy/skill integration, real-data frontend integration, and trend evidence remain incomplete. These implementation notes do not change the requirements above.

---

## 3. Non-Functional Requirements

Each accepted NFR below includes a measurable or inspectable verification condition.

### NFR-01 — Data accuracy

**Requirement:** For a manually verified sample of at least 20 accessible advertisements, the system shall achieve at least 90% successful collection and at least 90% accuracy for the agreed core fields.

**Verification:** Compare the collected sample against the original advertisements and calculate collection success and field accuracy.

### NFR-02 — Data integrity and deduplication

**Requirement:** Stored records shall conform to the agreed schema, and advertisements identified as duplicates by the documented deduplication rule shall not appear as separate active job records.

**Verification:** Validate stored records against the schema and insert or process known duplicate advertisements to confirm that the deduplication rule is applied.

### NFR-03 — Traceability and auditability

**Requirement:** Every job record used in user-facing analysis shall retain sufficient source evidence to identify its origin and collection time. Where automated classification is used, the relevant confidence or review information shall also be retained.

**Verification:** Audit a sample of records used in search or analytics and confirm that each one can be traced to its source evidence and processing information.

### NFR-04 — Ethical and privacy compliance

**Requirement:** The collection process shall be limited to required public job-advertisement information, shall not bypass authentication or access controls, and shall not intentionally collect unrelated personal information.

**Verification:** Review source adapters, collection configuration, and a sample of stored records for compliance with the approved collection rules and documented exclusions.

### NFR-05 — Uncertainty handling

**Requirement:** Missing source values shall remain null or explicitly unavailable. Ambiguous automated classifications shall retain a confidence value, multi-label result, or review status rather than being represented as certain.

**Verification:** Test records with missing fields and ambiguous classification examples and confirm that uncertainty is preserved in stored and displayed results.

### NFR-06 — Maintainability

**Requirement:** Source-specific collection logic shall be isolated by source or source type so that changing one source adapter does not require redesigning unrelated adapters or the core data model. Shared configuration shall remain environment-based and reusable frontend components shall be retained.

**Verification:** Review the collection and application structure and confirm that a source-specific change can be implemented without modifying unrelated source adapters.

### NFR-07 — Development quality and CI coverage

**Requirement:** Pull requests to the main branch shall run automated quality checks for both backend and frontend code. Backend checks shall include linting and automated tests as they are added; frontend checks shall include linting and build validation, with integration checks added when the corresponding interfaces are available.

**Verification:** Open or update a pull request and confirm that the configured backend and frontend GitHub Actions checks execute and report pass/fail status.

### NFR-08 — Usability and responsive presentation

**Requirement:** Core search, filtering, navigation, company, and job-detail functions shall remain usable at the project’s supported responsive breakpoints, with primary controls visible and usable and without layout failure that prevents task completion.

**Verification:** Execute the main user flows at each supported breakpoint and confirm that users can complete the required search and detail-view tasks.

### Pending NFR decision — Performance target

A formal response-time threshold is not yet supported by current project evidence because the real dataset size and integrated backend workload have not been validated. Before performance is accepted as an NFR, the team should define:

- the endpoint or user action being measured;
- the dataset size;
- the test environment and expected concurrent load;
- the response-time threshold and percentile;
- the pass/fail test method.

This item should be converted into a numbered NFR only after those values are agreed, so that the final requirement is testable.

---

## 4. Technology Assessment and Justification

This section compares technology options against the MVP requirements and current project constraints.

### 4.1 Frontend technology options

| Option | Strengths for this project | Limitations / Cost |
|---|---|---|
| **React + Next.js + TypeScript** | Reusable components, structured routing, typed API models, suitable for search/detail pages, and compatible with the current frontend work. | Requires the team to maintain the Next.js conventions and TypeScript types. |
| **React + Vite + TypeScript** | Lightweight React setup and good development speed. | Would require restructuring the current frontend with little clear benefit to the MVP. |
| **Vue + Nuxt** | Strong component model and routing support. | Would introduce a framework rewrite and additional team learning cost. |

**Decision:** Continue with **React + Next.js + TypeScript** because it supports the required multi-page interface and avoids unnecessary migration work.

### 4.2 Backend API technology options

| Option | Strengths for this project | Limitations / Cost |
|---|---|---|
| **FastAPI** | Python ecosystem compatibility, typed request/response validation, OpenAPI documentation, and a lightweight API structure. | Requires disciplined service/schema organisation as the API grows. |
| **Flask** | Simple Python web framework with low initial overhead. | More validation, API documentation, and structure would need to be assembled manually. |
| **Django / Django REST Framework** | Mature framework with a broad built-in feature set. | Heavier than the current MVP requires and would add migration cost. |
| **Node.js / Express** | Uses the same language family as the frontend. | Would create a separate backend ecosystem from the Python scraping and analysis pipeline. |

**Decision:** Continue with **FastAPI** because it provides the required API layer while remaining aligned with the project’s Python data-processing work.

### 4.3 Database technology options

| Option | Strengths for this project | Limitations / Cost |
|---|---|---|
| **PostgreSQL + SQLAlchemy** | Strong relational support, many-to-many relationships, shared-service use, and a consistent Python ORM. | Requires database service configuration and migrations. |
| **SQLite** | Very simple for local prototyping. | Less suitable for a shared and growing multi-source application. |
| **MongoDB / document database** | Flexible document storage. | Less aligned with the project’s explicit relational company/job/category/skill model. |

**Decision:** Continue with **PostgreSQL + SQLAlchemy** because the Silver and Gold models are primarily relational and depend on structured relationships.

### 4.4 Data-collection technology options

The project must collect job advertisements from multiple kinds of career systems rather than depending on one company or one dataset.

| Option | Strengths for this project | Limitations / Risk |
|---|---|---|
| **Public ATS/API endpoints** | Structured data, easier parsing, easier validation, and lower maintenance when a supported endpoint is available. | Not every company exposes a usable public endpoint. |
| **Direct HTML extraction** | Can support accessible static career pages without browser automation. | Page-structure changes can break selectors and some sites render data dynamically. |
| **Browser automation such as Selenium** | Can handle some JavaScript-rendered workflows that direct HTTP collection cannot. | Higher maintenance and execution cost, and it must not be used to bypass access restrictions. |
| **Exclude/document inaccessible sources** | Preserves ethical and technical boundaries and makes coverage limitations explicit. | Reduces source coverage. |

**Decision:** Use an **ATS/API-first, source-specific collection strategy**. Use HTML extraction where appropriate, retain browser automation as a controlled fallback, and document inaccessible sources rather than forcing collection.

### 4.5 Classification and analysis technology options

Classification must work across job advertisements from multiple companies and source formats.

| Option | Strengths for this project | Limitations / Risk |
|---|---|---|
| **Rule/keyword-based classification** | Deterministic, inexpensive, and easy to explain. | Difficult to maintain for overlapping AV roles and varied terminology. |
| **LLM-only classification** | Flexible with unstructured job text and varied terminology. | Output can be inconsistent and requires validation, confidence handling, and controlled prompts. |
| **Hybrid Python/Pandas + rules + LLM-assisted classification** | Keeps deterministic preprocessing and validation while using an LLM where semantic interpretation is useful. | Requires benchmark data and clear rules for low-confidence or ambiguous cases. |

Current prototype work shows that Python/Pandas-based preprocessing and LLM-assisted extraction are feasible for a source sample, but that evidence does not establish accuracy across all companies.

**Decision:** Use a **hybrid classification approach as the working option**, with Python/Pandas for structured processing and validation and LLM-assisted classification only where it is benchmarked against labelled data. Low-confidence outputs shall remain reviewable.

### 4.6 CI/CD and repository workflow options

| Option | Strengths for this project | Limitations / Cost |
|---|---|---|
| **GitHub Actions** | Integrates directly with the existing GitHub pull-request workflow and can run backend, frontend, and integration checks. | Workflow files must be maintained as project components evolve. |
| **External CI server** | Can support highly customised pipelines. | Adds infrastructure and administration that the current project does not require. |

**Decision:** Retain **GitHub Actions** as the project CI/CD platform.

The CI scope should cover the whole application:

- **Backend:** dependency installation, linting, automated API/database tests, and required service setup such as PostgreSQL.
- **Frontend:** dependency installation, linting, type/build validation, and frontend tests as they are added.
- **Integration:** add cross-component checks when stable frontend/backend interfaces are available.

---

## 5. Skills Gap Assessment

The skills gaps below represent delivery capabilities that still need strengthening. They do not assign personal skill ratings to individual team members.

### 5.1 Production multi-source scraping

**Impact:** The company list spans several ATS platforms, custom career sites, and sources that remain provisional or unconfirmed. Current executable collection evidence is still limited compared with the intended multi-source scope.

**How the team is addressing it:** Prioritise confirmed structured ATS/API sources, build source adapters incrementally, log collection failures, and document excluded sources instead of trying to solve every portal at once.

### 5.2 LLM classification validation

**Impact:** Current prototype work shows that automated classification is feasible on selected examples, but accuracy and stability across companies and source formats have not yet been demonstrated.

**How the team is addressing it:** Build a labelled validation sample, measure classification accuracy, retain evidence and confidence scores, support multi-label categories, and manually review low-confidence outputs.

### 5.3 Stable AV taxonomy design

**Impact:** AV roles can overlap across areas such as Machine Learning, Computer Vision, MLOps, Perception, Prediction, and Planning. Inconsistent definitions would affect classification and analytics.

**How the team is addressing it:** Agree and version one taxonomy, test it against real postings from multiple sources, preserve matched terms, and keep database, classifier, and frontend definitions aligned.

### 5.4 Backend job-domain implementation

**Impact:** Company data is implemented, while JobPosting, Skill, Category, ScrapeLog, trend, search, and filter APIs still need to be completed.

**How the team is addressing it:** Extend the SQLAlchemy models and Pydantic schemas from the Silver design, add endpoints incrementally, and keep the API contract visible through OpenAPI documentation.

### 5.5 Frontend-backend integration

**Impact:** The frontend currently relies on mock job data, so the user interface is not yet driven by the real backend dataset.

**How the team is addressing it:** Define typed API service functions and replace mock data route-by-route once the corresponding backend endpoints are stable.

### 5.6 Database and schema consistency

**Impact:** The target Silver model is broader than the currently implemented ORM, which creates a risk of inconsistent assumptions between collection, backend, and analytics components.

**How the team is addressing it:** Use the agreed ERD and data dictionary as the common reference, reconcile field names and statuses, and review schema changes before dependent components are merged.

### 5.7 Automated testing and CI

**Impact:** Current CI coverage is incomplete and does not yet provide broad regression protection across both application layers.

**How the team is addressing it:** Add backend API/database tests, classification and data-validation tests, frontend lint/build/test checks, and end-to-end integration checks progressively.

### 5.8 Real-data validation of UI and analytics

**Impact:** Some current job records, salaries, counts, and trend values are mock data. These cannot be treated as market evidence.

**How the team is addressing it:** Keep mock content clearly separated during development, replace it with validated backend data, and enforce agreed salary and trend evidence rules before client-facing presentation.

---

## 6. Risk Assessment and Mitigation Plan

### R-01 — Career sites cannot be collected reliably
**Likelihood:** High  
**Impact:** High  
**Mitigation:** Prioritise confirmed ATS/API sources, use source-specific adapters, respect access restrictions, record source status and failure reasons, and exclude inaccessible sources transparently.

### R-02 — Source coverage remains incomplete
**Likelihood:** High  
**Impact:** Medium–High  
**Mitigation:** Define an explicit MVP source subset, validate provisional sources early, track coverage, and avoid claiming complete market coverage.

### R-03 — Job fields are inconsistent or missing
**Likelihood:** High  
**Impact:** High  
**Mitigation:** Keep optional fields nullable, preserve raw source evidence, normalise only through documented rules, and manually validate a sample of at least 20 records.

### R-04 — Automated classification is inaccurate or unstable at scale
**Likelihood:** Medium–High  
**Impact:** High  
**Mitigation:** Build a labelled benchmark, measure classification accuracy, retain evidence and confidence scores, support multi-label classification, review low-confidence outputs, and version the taxonomy and classification prompt/rules.

### R-05 — Taxonomy definitions diverge across components
**Likelihood:** Medium  
**Impact:** High  
**Mitigation:** Maintain one versioned taxonomy and shared definitions. Review taxonomy changes across the database, API, classifier, and frontend together.

### R-06 — Frontend/backend integration is delayed
**Likelihood:** High  
**Impact:** High  
**Mitigation:** Agree the next API contract early, implement endpoints incrementally, create typed frontend service functions, and replace mock data route-by-route.

### R-07 — Mock values are mistaken for real evidence
**Likelihood:** Medium  
**Impact:** High  
**Mitigation:** Clearly label or remove mock analytics in assessed demonstrations, replace them with validated data, and apply the agreed evidence threshold before showing salary or trend claims.

### R-08 — Database implementation diverges from the target data models
**Likelihood:** Medium  
**Impact:** High  
**Mitigation:** Reconcile ORM models with the agreed Silver/Gold data design, standardise field/status names, and review schema changes before dependent code is merged.

### R-09 — CI does not catch regressions
**Likelihood:** Medium  
**Impact:** High  
**Mitigation:** Add backend unit/API/database tests, frontend lint/build/test checks, data-validation tests, and integration tests to GitHub Actions.

### R-10 — Development seeding damages persistent data
**Likelihood:** Medium  
**Impact:** High  
**Mitigation:** Keep automatic seeding disabled outside local/testing environments, protect persistent environments, document the behaviour of `SEED_ON_STARTUP`, and use explicit migration or seed commands for persistent deployments.

### R-11 — Historical data is insufficient for trend analysis
**Likelihood:** High  
**Impact:** Medium  
**Mitigation:** Retain collection dates and snapshots. Only show time-based views when enough valid periods meet the agreed evidence threshold; otherwise display an insufficient-data state.

### R-12 — Scraping creates ethical, privacy, or site-policy issues
**Likelihood:** Medium  
**Impact:** High  
**Mitigation:** Collect only required public job information, avoid unrelated personal data, do not bypass authentication or access controls, respect applicable restrictions and rate limits, and document exclusions.

### R-13 — Salary data is incomplete or misleading
**Likelihood:** High  
**Impact:** Medium  
**Mitigation:** Store salary only when supported by an approved source or extraction method, keep missing salary unavailable, retain currency/source information, and remove unsupported estimated values from evidence-based outputs.

### R-14 — Secrets or environment configuration are mishandled
**Likelihood:** Low–Medium  
**Impact:** High  
**Mitigation:** Keep API keys and database credentials in uncommitted environment files, provide only example environment files, separate local and CI values, and review the repository for secrets before release.

---

## 7. Immediate Technology and Delivery Priorities

1. Finalise one shared taxonomy and data dictionary before more classification or UI logic is built around fixed categories.
2. Extend the backend from company-only endpoints to the job-domain entities required by the MVP.
3. Convert the current collection/classification prototype into a repeatable and testable multi-source pipeline, then add confirmed sources incrementally.
4. Define the frontend/backend API contract and replace mock data progressively.
5. Expand GitHub Actions to cover both backend and frontend quality checks and automated tests.
6. Remove or clearly label mock salary and trend claims before client-facing or assessed demonstrations.

---

## 8. Acceptance Criteria Check

- [x] Functional requirements are written as verifiable system behaviours.
- [x] Accepted non-functional requirements include measurable or inspectable verification conditions.
- [x] Technology options are compared and justified rather than described only as architecture.
- [x] The collection and classification approach is written for multiple companies and source types rather than one dataset.
- [x] CI/CD scope includes both backend and frontend work.
- [x] Skills gap assessment is included, with how the team is addressing each identified gap.
- [x] Each identified project risk has a corresponding mitigation plan.
