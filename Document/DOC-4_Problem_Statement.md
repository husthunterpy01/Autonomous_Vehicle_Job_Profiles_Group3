# [DOC-4] Problem Statement

## 1. Problem statement

Information about employment in the autonomous-vehicle industry is spread across many company career pages and job platforms. These sources use inconsistent job titles, role categories, skill names, technology terms, qualification descriptions, experience levels, and location formats. As a result, there is no reliable and consolidated view of what employers currently require across the autonomous-vehicle job market.

This creates two connected problems:

1. **Course-design problem:** Adrian needs evidence showing which technical skills, tools, technologies, and wider competencies are most frequently requested by autonomous-vehicle employers. Without structured and current market data, it is difficult to decide which topics should be prioritised in the new course or to check whether the planned curriculum reflects current employer demand.
2. **Job-market exploration problem:** A representative end user, referred to as Lee in the current project notes, must search many separate company websites and read advertisements individually. This makes it difficult to find relevant roles, compare requirements, or identify patterns across companies, locations, role families, and technologies.

The core problem is therefore the lack of a single, structured, searchable, and traceable source of autonomous-vehicle job and skill-demand information.

## 2. Why the client wants this project

The client wants a data-driven view of the autonomous-vehicle labour market for two main purposes:

- **Curriculum planning:** identify the technical domains, tools, technologies, and competencies that employers currently request so that course content can be aligned with real industry demand.
- **Job-market exploration:** allow users to find and compare autonomous-vehicle vacancies through one interface instead of manually checking many company websites.

During the client meeting, the client emphasised that the most valuable part of the proposed system is the data behind a specialised job-search website. The client wants to understand the technical skills and other requirements requested by employers. The meeting also identified company career pages as the expected source of job advertisements and referred to a list of approximately 42 autonomous-vehicle companies.

## 3. Why existing information is insufficient

Current information is insufficient because:

- job advertisements are distributed across many independent websites;
- employers use different terminology for similar roles and skills;
- company career pages usually support searching within one employer only;
- job advertisements can be edited or removed, making later comparison difficult;
- manually reviewing individual advertisements is slow and difficult to repeat;
- unstructured advertisements do not directly show aggregate skill demand or market trends;
- existing general job platforms do not provide a focused, normalised view of the autonomous-vehicle domain.

A useful solution must therefore collect data from agreed sources, preserve traceability to the original advertisement, normalise key fields, and present the information in a form that supports both individual job searches and aggregate analysis.

## 4. Proposed MVP deliverables

The minimum viable product will include the following components.

### 4.1 Job-data collection pipeline

- Collect publicly available job advertisements from the agreed autonomous-vehicle companies or other approved sources.
- Retain the original source URL and collection date for traceability.
- Extract the fields confirmed in the project requirements.
- Record unavailable or uncertain values clearly rather than inventing data.

### 4.2 Normalised job dataset

- Store collected advertisements in a structured format.
- Standardise company names, job titles, locations, role categories, seniority levels, and skill or technology terms where practical.
- Preserve the original advertisement text or a source reference where permitted.
- Document normalisation rules and known data-quality limitations.

### 4.3 Searchable and filterable dashboard

- Provide keyword search across job titles, descriptions, skills, and technologies.
- Provide filters based on the confirmed requirements, expected to include company, location, role or category, technical skill or technology, and experience level where the data is available.
- Display relevant job details and a link to the original posting.

### 4.4 Aggregate demand and trend views

- Show the frequency of requested technical skills and technologies.
- Show the distribution of jobs by role or category, company, and location.
- Provide time-based trend views when sufficient dated data is available.

### 4.5 Project documentation

- Data-source register.
- Data dictionary and field definitions.
- Collection and extraction method.
- Normalisation rules.
- Assumptions, limitations, ethical considerations, and known data-quality issues.

## 5. Scope boundary

### In scope

- Publicly available autonomous-vehicle job advertisements from agreed companies or approved job sources.
- Extraction of job attributes and employer-requested skills.
- Search, filtering, comparison, aggregation, and visualisation of collected advertisements.
- Evidence that supports curriculum review and individual job-market exploration.
- Traceable links between dashboard records and source pages where possible.

### Out of scope for the MVP

- Predicting whether an applicant will obtain a job.
- Automatically applying for jobs or ranking candidates.
- Guaranteeing complete coverage of every autonomous-vehicle vacancy worldwide.
- Treating advertisement frequency as proof of actual hiring volume, labour supply, or a verified skill shortage.
- Collecting from sources whose terms, access controls, or technical restrictions prohibit collection.
- Making curriculum decisions automatically. The system will provide evidence for human decision-making.

## 6. Validation criteria and dependencies

The problem statement can be treated as confirmed when the team and client agree that:

- the central problem is the lack of an aggregate and structured view of autonomous-vehicle job and skill demand;
- curriculum planning and end-user job exploration are the intended uses;
- the proposed dataset, dashboard, and aggregate views match the intended MVP;
- the company or source list and required data fields are agreed;
- the stated scope limitations are acceptable.
