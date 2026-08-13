# [DOC-8] Risk and Technology Assessments

**Project:** Autonomous Vehicle Job Profiles  
**Group:** Group 3  
**Purpose:** Document the project's functional and non-functional requirements, justify the selected technologies, identify delivery skill gaps, and record project risks with mitigation plans.

## 1. Assessment Basis

This assessment reflects the latest project implementation and supporting project documentation. The main reference points are:

- the FastAPI backend and PostgreSQL configuration under `backend/`;
- the Next.js/React frontend under `frontend/`;
- the Silver and Gold data models under `document/`;
- source and scraping investigations;
- the Waymo classification prototype in `notebooks/waymo_classification.ipynb`;
- the project problem statement, meeting records, GitHub Issues, and CI workflow.

The requirements below describe the target MVP, while implementation notes are included only where they are relevant to technology choices, skill gaps, or project risk.

---

## 2. Functional Requirements

### FR-01 — Maintain an approved company and data-source register
The system should maintain the agreed list of autonomous-vehicle companies and their job-data sources. Each source should record its career-page or API location and its collection status. Sources that cannot be used should have a documented reason.

### FR-02 — Collect public job advertisements
The system should collect publicly accessible job advertisements from approved and technically accessible sources. Collection failures and excluded sources should be recorded rather than silently ignored.

### FR-03 — Preserve source traceability
Each collected job should retain enough source information to verify where it came from. This includes the original source URL, collection date, and source platform where available.

### FR-04 — Extract and store agreed job fields
The structured dataset should support the main fields required for analysis, including:

- company;
- job title;
- description;
- location;
- employment type;
- seniority or experience level;
- posting date;
- salary or compensation when available;
- source metadata.

### FR-05 — Normalise job-market information
Equivalent company names, locations, categories, skills, and technologies should be represented consistently. Original source information should remain traceable, and unavailable values should remain missing rather than being guessed.

### FR-06 — Classify jobs using a shared AV taxonomy
Job advertisements should be mapped to one or more agreed autonomous-vehicle job categories. The design should support classification confidence, evidence for review, and taxonomy versioning where required.

### FR-07 — Extract skills and technologies
The system should identify and store relevant technical information such as programming languages, frameworks, tools, platforms, domain concepts, certifications, datasets, and other job-related technologies.

### FR-08 — Provide job search and filtering
Users should be able to search job information and apply relevant filters when the required data is available. Expected filters include category or role, company, location, skill or technology, and experience or employment type.

### FR-09 — Provide company and job detail views
Users should be able to browse companies, inspect company information, view associated jobs, open job details, and follow original job or career links where available.

### FR-10 — Provide aggregate demand views
The system should be able to summarise demand across validated data, including distributions or counts by:

- skills and technologies;
- job categories;
- companies;
- locations.

### FR-11 — Provide trend views only when evidence is sufficient
Time-based trends should use valid posting dates or repeated collection snapshots. If there is not enough historical evidence, the interface should report insufficient data rather than presenting an unsupported trend.

### FR-12 — Record collection and processing outcomes
The collection pipeline should record successful and failed processing attempts, including relevant dates, status, number of jobs found, and error information where applicable.

### Implementation position
The backend currently supports company data, a health endpoint, and company list/detail/create operations. The frontend already includes the main landing, job search, company search, job detail, and company detail pages. Job-domain APIs, taxonomy, skills, trends, and full search integration are still part of the remaining implementation work. The Waymo notebook provides an end-to-end prototype for collection, LLM-assisted classification, and salary extraction.

---

## 3. Non-Functional Requirements

### NFR-01 — Data accuracy
For a manually verified sample of at least 20 accessible advertisements, the target should be at least 90% collection success and at least 90% accuracy for the agreed core fields.

### NFR-02 — Data integrity and deduplication
Stored data should conform to the agreed schema. Duplicate advertisements should be removed or clearly identified. `source_url` should remain a traceable identifier where applicable.

### NFR-03 — Traceability and auditability
Source URL, collection date, source platform, raw source information, classification confidence, and collection logs should be retained where relevant so that results can be checked against their source evidence.

### NFR-04 — Ethical and privacy compliance
Collection should be limited to required public job-advertisement information. The project should respect access controls and applicable site restrictions, avoid bypassing authentication or anti-bot protections, and avoid collecting unrelated personal information.

### NFR-05 — Uncertainty handling
Missing information should remain marked as unavailable. Ambiguous classifications should support multi-label assignment, confidence scoring, or manual/client review instead of being presented as certain.

### NFR-06 — Maintainability
Source-specific collection logic should be isolated so one career site can be updated without redesigning the entire pipeline. Configuration should remain environment-based, reusable frontend components should be retained, and schema or taxonomy changes should be documented.

### NFR-07 — Development quality
Pull requests should pass automated code-quality checks. The current CI already performs backend Ruff checks; backend tests, frontend checks, and integration tests should be added as the project develops.

### NFR-08 — Usability and responsive presentation
Search, filtering, navigation, company information, job details, and source links should remain clear and usable across supported screen sizes.

### NFR-09 — Performance
A formal response-time target has not yet been validated against the real dataset. A measurable performance threshold should be agreed after backend integration and realistic data-volume testing.

---

## 4. Technology Assessment and Justification

### 4.1 Frontend — React + Next.js + TypeScript

The frontend uses **React, Next.js, TypeScript, Tailwind CSS, ESLint, and Prettier**. This stack suits a multi-page web application with reusable components and several related search/detail routes.

**Why it fits the project**

- Next.js provides a clear routing and project structure for the landing page, search pages, and detail pages.
- React supports reusable UI elements such as job cards, company cards, search controls, pagination, and status components.
- TypeScript helps keep frontend data structures and future API responses consistent.
- The team can continue building on the existing interface without spending time on a framework migration.

**Alternatives considered**

- **React + Vite:** suitable for a simpler client-side application, but it would provide little benefit over the existing Next.js structure.
- **Vue/Nuxt:** capable of implementing the same features, but changing frameworks would create unnecessary rewrite and learning cost.

**Decision:** Continue with **React + Next.js + TypeScript**.

### 4.2 Backend API — FastAPI

The backend uses **FastAPI** with Uvicorn, Pydantic, SQLAlchemy, psycopg2, CORS middleware, logging, and generated Swagger/ReDoc documentation.

The API already includes `/health`, company list/create routes, and company detail retrieval. This confirms FastAPI as the working backend framework for the project.

**Why it fits the project**

- The project needs a clear API layer between the frontend and structured job-market data.
- Scraping, data processing, and classification work are already Python-based, so FastAPI keeps the backend in the same ecosystem.
- Pydantic provides typed validation for request and response data.
- OpenAPI documentation makes the frontend/backend contract easier to inspect and test.
- FastAPI is lightweight enough for the MVP while still supporting a router/service/schema architecture.

**Alternatives considered**

- **Flask:** can provide a REST API, but FastAPI offers stronger built-in typing, validation, and API documentation.
- **Django / Django REST Framework:** provides a larger full-stack feature set than the MVP currently requires.
- **Node.js / Express:** would align with the frontend language, but would introduce a separate server-side stack alongside the Python data pipeline.

**Decision:** Continue with **FastAPI**.

### 4.3 Database and ORM — PostgreSQL + SQLAlchemy

The project uses **PostgreSQL** with **SQLAlchemy**. The data model is strongly relational: jobs belong to companies, jobs can have multiple categories and skills, collection logs relate to companies, and trend snapshots are derived from these records.

The current ORM implementation covers `Company` and `CompanyLocation`, while the wider Silver design also defines `JobPosting`, `Category`, `JobCategory`, `Skill`, `JobSkill`, and `ScrapeLog`. The Gold design adds `CategoryTrendSnapshot` for trend analysis.

**Why it fits the project**

- PostgreSQL handles relational and many-to-many structures cleanly.
- It supports a shared backend service better than a local-only database.
- SQLAlchemy provides a consistent Python ORM layer for database access.
- The technology aligns directly with the current Silver and Gold data models.

**Alternatives considered**

- **SQLite:** useful for small local prototypes, but less suitable for a shared and growing multi-source application.
- **MongoDB or another document database:** flexible for raw documents, but less aligned with the project's explicit relational taxonomy and skill model.

**Decision:** Continue with **PostgreSQL + SQLAlchemy**.

### 4.4 Data Collection — ATS/API-first with source-specific fallbacks

The target company list uses several career-site technologies, including Greenhouse, Lever, SmartRecruiters, Ashby, custom first-party sites, proprietary portals, and sources that still need confirmation. The current seeded source register contains **41 companies: 24 confirmed, 3 provisional, and 14 unconfirmed**.

An ATS/API-first strategy is appropriate because structured public endpoints are usually easier to parse, validate, and maintain than browser-driven extraction. The Waymo prototype already demonstrates Greenhouse API collection through Python `requests` and Pandas.

For sources without a stable endpoint, source-specific HTML or browser-based extraction may be considered where technically and ethically appropriate.

**Decision:** Use an **ATS/API-first, source-specific collection strategy**. Browser automation such as Selenium remains a fallback option rather than a core committed dependency.

### 4.5 Classification and Analysis — Python + Pandas + LLM prototype

The Waymo prototype combines Python and Pandas with an LLM-based extraction step. It currently demonstrates:

- retrieval of Waymo jobs;
- conversion into structured Pandas data;
- extraction of role profile, technical skills/technologies, and functional area;
- salary extraction from job text;
- structured JSON parsing.

The prototype is useful evidence that the classification workflow is feasible, but sample success is not enough to establish production accuracy across all companies. The Silver data model already includes `extraction_confidence`, `taxonomy_version`, and per-job/category `confidence_score`, which provide a basis for controlled validation.

**Decision:** Keep the LLM workflow as a **prototype that must be benchmarked before large-scale use**.

### 4.6 CI and Repository Workflow — GitHub Actions

GitHub Actions is integrated with the pull-request workflow. The backend CI starts a PostgreSQL service, installs backend dependencies, and runs `ruff check .`.

This provides a useful baseline for code-quality checking, but the workflow should expand to include automated backend tests, frontend lint/build checks, data-validation tests, and later integration testing.

**Decision:** Retain **GitHub Actions** and extend CI coverage as implementation matures.

---

## 5. Skills Gap Assessment

The skills gaps below represent delivery capabilities that still need strengthening. They do not assign personal skill ratings to individual team members.

### 5.1 Production multi-source scraping

**Impact:** The company list spans several ATS platforms and custom career sites. Seventeen of the 41 seeded sources remain provisional or unconfirmed, while the strongest executable collection example is currently the Waymo prototype.

**How the team is addressing it:** Prioritise confirmed structured ATS/API sources, build adapters incrementally, log collection failures, and document excluded sources instead of trying to solve every portal at once.

### 5.2 LLM classification validation

**Impact:** The classification prototype works on selected examples, but its accuracy and stability at larger scale have not yet been demonstrated.

**How the team is addressing it:** Build a labelled validation sample, measure classification accuracy, retain evidence and confidence scores, support multi-label categories, and manually review low-confidence outputs.

### 5.3 Stable AV taxonomy design

**Impact:** AV roles can overlap across areas such as Machine Learning, Computer Vision, MLOps, Perception, Prediction, and Planning. Inconsistent definitions would affect classification and analytics.

**How the team is addressing it:** Agree and version one taxonomy, test it against real postings, preserve matched terms, and keep database, classifier, and frontend definitions aligned.

### 5.4 Backend job-domain implementation

**Impact:** Company data is implemented, while JobPosting, Skill, Category, ScrapeLog, trend, search, and filter APIs still need to be completed.

**How the team is addressing it:** Extend the SQLAlchemy models and Pydantic schemas from the Silver design, add endpoints incrementally, and keep the API contract visible through OpenAPI documentation.

### 5.5 Frontend-backend integration

**Impact:** The frontend currently relies on mock job data, so the user interface is not yet driven by the real backend dataset.

**How the team is addressing it:** Define typed API service functions and replace mock data route-by-route once the corresponding backend endpoints are stable.

### 5.6 Database and schema consistency

**Impact:** The target Silver model is broader than the currently implemented ORM, which creates a risk of inconsistent assumptions between the scraper, backend, and analytics layer.

**How the team is addressing it:** Use the agreed ERD and data dictionary as the common reference, reconcile field names and statuses, and review schema changes before dependent components are merged.

### 5.7 Automated testing and CI

**Impact:** The current CI checks backend Ruff conventions but does not yet provide broad automated regression coverage.

**How the team is addressing it:** Add API/database tests, classification and data-validation tests, frontend lint/build checks, and end-to-end integration checks progressively.

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

### R-04 — LLM classification is inaccurate or unstable at scale
**Likelihood:** Medium–High  
**Impact:** High  
**Mitigation:** Build a labelled benchmark, measure classification accuracy, retain evidence and confidence scores, support multi-label classification, review low-confidence outputs, and version the taxonomy and prompt.

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
**Mitigation:** Add backend unit/API/database tests, frontend lint/build checks, data-validation tests, and integration tests to GitHub Actions.

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
3. Turn the Waymo prototype into a repeatable and testable collection/classification pipeline, then add confirmed ATS sources incrementally.
4. Define the frontend/backend API contract and replace mock data progressively.
5. Expand GitHub Actions to include automated tests and frontend checks.
6. Remove or clearly label mock salary and trend claims before client-facing or assessed demonstrations.

---

## 8. Acceptance Criteria Check

- [x] Functional and non-functional requirements are documented.
- [x] Skills gap assessment is included, with how the team is addressing each identified gap.
- [x] Technology choices are justified, including why FastAPI and React/Next.js are used over relevant alternatives.
- [x] Each identified project risk has a corresponding mitigation plan.
