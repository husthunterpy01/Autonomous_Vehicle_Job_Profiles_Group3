# AV company career-page endpoint register

**Status:** implementation reference

**Last verified:** 2026-08-27

**Scope:** 41 companies from the client-supplied list (the ticket's “~42” is approximate)

This document records the preferred job-list target and the job-detail URL or endpoint structure for every company in scope. Prefer an ATS JSON/XML endpoint when one is available. Where no discoverable public API exists, the row explicitly identifies the HTML or third-party-board fallback.

Endpoint availability is not an invitation to bypass authentication, bot controls, rate limits, `robots.txt`, or site terms. Use a descriptive user agent, conservative request rates, retries with backoff, caching, and conditional requests. Never automate application submission endpoints.

## Endpoint recipes

The table below refers to these reusable recipes.

### Greenhouse (`GH`)

- List: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- Detail JSON: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}`
- Public detail page: `https://job-boards.greenhouse.io/{board_token}/jobs/{job_id}`
- Stable key: `job_id`

### Lever (`LEVER`)

- List: `GET https://api.lever.co/v0/postings/{site_id}?mode=json`
- Detail JSON: `GET https://api.lever.co/v0/postings/{site_id}/{posting_id}`
- Public detail page: `https://jobs.lever.co/{site_id}/{posting_id}`
- Stable key: `posting_id` (normally a UUID)

### Ashby (`ASHBY`)

- List/detail payload: `GET https://api.ashbyhq.com/posting-api/job-board/{board_name}`
- Public detail page: `https://jobs.ashbyhq.com/{board_name}/{job_id}`
- Stable key: `job_id` (normally a UUID)
- The public posting response contains each job's detail fields and `jobUrl`; a second public detail JSON request is not required.

### Workday CXS (`WORKDAY`)

- List: `POST https://{host}/wday/cxs/{tenant}/{site}/jobs`
- Typical body: `{"appliedFacets":{},"limit":20,"offset":0,"searchText":""}`
- Detail JSON: `GET https://{host}/wday/cxs/{tenant}/{site}/job/{job_path}`
- Public detail page: `https://{host}/en-US/{site}/job/{job_path}`
- Use the returned `externalPath`/job path verbatim; do not construct it from the title alone.

### SmartRecruiters (`SR`)

- List: `GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings?limit=100&offset=0`
- Detail JSON: `GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings/{posting_id}`
- Public detail page: `https://jobs.smartrecruiters.com/{company_id}/{posting_id}-{slug}`

### Personio (`PERSONIO`)

- List XML: `GET https://{account}.jobs.personio.de/xml`
- Public detail page: `https://{account}.jobs.personio.de/job/{job_id}`
- The XML feed is the preferred machine-readable source; fetch the detail page only for fields absent from the feed.

## API response contracts and database mappings

The examples below are deliberately abridged: they show the response envelope and fields required by the ingestion pipeline, not every applicant-facing field. Store the original response in a raw/bronze layer before normalization so that newly exposed fields can be backfilled without refetching old postings.

### Shared extraction rules

- Convert every source identifier to a string before storage, even when an API currently returns a number.
- Preserve `canonical_job_url` and `apply_url` separately. Never use the application URL as the canonical job URL.
- Retain source HTML in `description_html`; derive `description_text` with an HTML parser rather than regular expressions.
- Treat missing, empty, and `null` optional fields equivalently during normalization, but preserve the raw payload.
- Convert ISO timestamps to UTC. Preserve date-only values as dates; do not invent a time or timezone.
- Do not use a human-relative value such as `Posted Today` as a durable timestamp.
- A successful response with zero records must be validated against the public careers page before marking all existing jobs closed.

### Greenhouse response (`GH`)

Official reference: [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)

Content type is JSON. The list response is an object containing `jobs` and `meta`; the detail response is one job object.

#### List response

```json
{
  "jobs": [
    {
      "id": 123456,
      "internal_job_id": 98765,
      "title": "Software Engineer",
      "updated_at": "2026-08-20T14:30:00-04:00",
      "first_published": "2026-08-01T12:00:00Z",
      "requisition_id": "ENG-101",
      "location": { "name": "Pittsburgh, PA" },
      "absolute_url": "https://job-boards.greenhouse.io/example/jobs/123456",
      "content": "<p>Job description...</p>",
      "departments": [{ "id": 1, "name": "Engineering" }],
      "offices": [{ "id": 2, "name": "Pittsburgh" }],
      "metadata": null
    }
  ],
  "meta": { "total": 1 }
}
```

`content`, `departments`, and `offices` are returned by the list endpoint only when `content=true` is supplied.

#### Detail response

```json
{
  "id": 123456,
  "title": "Software Engineer",
  "company_name": "Example Company",
  "location": { "name": "Pittsburgh, PA" },
  "content": "<p>Job description...</p>",
  "absolute_url": "https://job-boards.greenhouse.io/example/jobs/123456",
  "first_published": "2026-08-01T12:00:00Z",
  "updated_at": "2026-08-20T14:30:00-04:00",
  "requisition_id": "ENG-101",
  "metadata": []
}
```

Do not request `questions=true`; applicant questions and compliance data are outside the ingestion scope. Compensation is optional and requires `pay_transparency=true` on the detail request.

| Normalized field | Greenhouse source | Notes |
|---|---|---|
| `source_job_id` | `jobs[].id` / detail `id` | Job-post ID; stringify it. Do not substitute `internal_job_id`. |
| `requisition_id` | `requisition_id` | Optional; may be `null`. |
| `title` | `title` | Required for a usable record. |
| `locations` | `location.name`; optionally `offices[].location` | `location.name` can contain multiple locations in one string. |
| `department` | `departments[].name` | Zero, one, or multiple departments; store all values if the database supports an array. |
| `description_html` | `content` | HTML may contain entities; decode once, parse, and sanitize. |
| `canonical_job_url` | `absolute_url` | Prefer the API value over a constructed URL. |
| `published_at` | `first_published` | May be absent from some list entries; the detail response is more complete. |
| `updated_at` | `updated_at` | ISO timestamp with offset. |

Pagination: the public job-board list returns the complete published set and exposes `meta.total`; there are no documented `offset`/`limit` parameters. Validate `jobs.length === meta.total`.

### Lever response (`LEVER`)

Official reference: [Lever Postings API](https://github.com/lever/postings-api)

Content type is JSON when `mode=json` is supplied. Unlike Greenhouse, the list response is a top-level array. The detail endpoint returns one object with the same field family.

#### List and detail item

```json
[
  {
    "id": "0f4d2f32-0000-4000-8000-123456789abc",
    "text": "Software Engineer",
    "categories": {
      "location": "Toronto, Ontario, Canada",
      "allLocations": ["Toronto, Ontario, Canada"],
      "commitment": "Full-time",
      "department": "Engineering",
      "team": "Autonomy"
    },
    "country": "CA",
    "workplaceType": "hybrid",
    "createdAt": 1787203200000,
    "description": "<div>Combined description...</div>",
    "descriptionPlain": "Combined description...",
    "lists": [
      { "text": "Responsibilities", "content": "<li>Build systems</li>" }
    ],
    "hostedUrl": "https://jobs.lever.co/example/0f4d2f32-0000-4000-8000-123456789abc",
    "applyUrl": "https://jobs.lever.co/example/0f4d2f32-0000-4000-8000-123456789abc/apply"
  }
]
```

The detail endpoint returns the object inside the example array, not an array.

| Normalized field | Lever source | Notes |
|---|---|---|
| `source_job_id` | `id` | UUID string. |
| `title` | `text` | Lever uses `text`, not `title`. |
| `locations` | `categories.allLocations`; fallback `categories.location` | `allLocations` may be absent on older postings. |
| `country_code` | `country` | Optional ISO 3166-1 alpha-2 value. |
| `department` | `categories.department` | Optional or empty. |
| `team` | `categories.team` | Optional or empty. |
| `employment_type` | `categories.commitment` | Free-text company value; normalize through a lookup table. |
| `workplace_type` | `workplaceType` | `unspecified`, `on-site`, `remote`, or `hybrid`. |
| `description_html` | `description` | Already combines opening and body. Do not concatenate `lists` again unless the company payload omits them from `description`. |
| `description_text` | `descriptionPlain` | Prefer this over stripping HTML when present. |
| `canonical_job_url` | `hostedUrl` | Required for deduplication. |
| `apply_url` | `applyUrl` | Store but do not request during ingestion. |
| `published_at` | `createdAt` | Epoch milliseconds; convert using milliseconds, not seconds. |
| `updated_at` | Not exposed | Leave `null`; do not copy `retrieved_at`. |

Optional compensation fields are `salaryRange` (`currency`, `interval`, `min`, `max`) and `salaryDescription`; many companies omit them.

Pagination: use `skip` and `limit`. Continue until the returned array contains fewer than `limit` items. Do not use Lever's `group` parameter because it changes the response shape.

### Ashby response (`ASHBY`)

Official reference: [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api)

Ashby returns all published jobs in one JSON response. There is no separate public detail JSON endpoint: each item already contains the description and job URLs.

#### List/detail response

```json
{
  "apiVersion": "1",
  "jobs": [
    {
      "id": "9534b49a-9feb-4063-ac33-a9c4d94a1352",
      "title": "Software Engineer",
      "location": "Sunnyvale, CA",
      "secondaryLocations": [
        { "location": "Washington, DC", "address": { "addressCountry": "USA" } }
      ],
      "department": "Engineering",
      "team": "Autonomy",
      "isListed": true,
      "isRemote": false,
      "workplaceType": "OnSite",
      "employmentType": "FullTime",
      "publishedAt": "2026-08-20T16:21:55.393+00:00",
      "descriptionHtml": "<p>Job description...</p>",
      "descriptionPlain": "Job description...",
      "jobUrl": "https://jobs.ashbyhq.com/example/9534b49a-9feb-4063-ac33-a9c4d94a1352",
      "applyUrl": "https://jobs.ashbyhq.com/example/9534b49a-9feb-4063-ac33-a9c4d94a1352/application"
    }
  ]
}
```

| Normalized field | Ashby source | Notes |
|---|---|---|
| `source_job_id` | `jobs[].id` | Present in the current Aurora and Applied responses. If absent in a future version, extract the final UUID from `jobUrl` and record the fallback. |
| `title` | `title` | Required. |
| `locations` | `location` plus `secondaryLocations[].location` | Deduplicate while retaining source order. |
| `country_code` | `address.postalAddress.addressCountry` | Often a country name rather than a two-letter code; normalize separately. |
| `department` | `department` | Optional. |
| `team` | `team` | Optional. |
| `employment_type` | `employmentType` | Enum such as `FullTime`, `PartTime`, `Intern`, `Contract`, or `Temporary`. |
| `workplace_type` | `workplaceType` | `OnSite`, `Remote`, or `Hybrid`; `isRemote` is a useful consistency check. |
| `description_html` | `descriptionHtml` | Full detail is already present in the list response. |
| `description_text` | `descriptionPlain` | May be missing if the source field is missing in Ashby. |
| `canonical_job_url` | `jobUrl` | Store the returned URL. |
| `apply_url` | `applyUrl` | Store only. |
| `published_at` | `publishedAt` | ISO timestamp for the most recent publication. |
| `updated_at` | Not exposed | Leave `null`. |

Compensation is included only with `includeCompensation=true`; map salary components using `compensation.summaryComponents[]` and retain the full compensation object because a job may contain multiple geographic tiers.

Pagination: none documented. Filter out `isListed=false` unless the product explicitly wants unlisted direct-link roles.

### Workday CXS response (`WORKDAY`)

Workday CXS is a public endpoint used by the tenant's careers site, but it is not a stable, generally documented public API. Treat the following as an observed contract and retain fixtures for both GM and NVIDIA.

#### List response

```json
{
  "total": 125,
  "jobPostings": [
    {
      "title": "Software Engineer",
      "externalPath": "/job/City-Country/Software-Engineer_JR-12345",
      "locationsText": "City, Country",
      "postedOn": "Posted Today",
      "remoteType": "Hybrid",
      "bulletFields": ["JR-12345", "Full time"]
    }
  ],
  "facets": [],
  "userAuthenticated": false
}
```

#### Detail response

```json
{
  "jobPostingInfo": {
    "id": "opaque-id",
    "title": "Software Engineer",
    "jobDescription": "<p>Job description...</p>",
    "location": "City, Country",
    "postedOn": "Posted Today",
    "startDate": "2026-08-27",
    "timeType": "Full time",
    "jobReqId": "JR-12345",
    "jobPostingId": "opaque-posting-id",
    "country": { "descriptor": "Country", "id": "opaque-country-id" },
    "remoteType": "Hybrid",
    "externalUrl": "https://tenant.myworkdayjobs.com/Site/job/..."
  },
  "hiringOrganization": { "name": "Example Company", "url": "https://example.com" },
  "similarJobs": [],
  "userAuthenticated": false
}
```

| Normalized field | Workday source | Notes |
|---|---|---|
| `source_job_id` | Detail `jobPostingInfo.jobReqId`; fallback list `bulletFields` only after validation | Retain `jobPostingId` and `externalPath` as additional source identifiers. |
| `title` | Detail `jobPostingInfo.title`; list `title` | Prefer detail. |
| `locations` | Detail `jobPostingInfo.location`; list `locationsText` | Strings may contain multiple locations. |
| `country_code` | `jobPostingInfo.country.descriptor` | Descriptor is normally a name, not a code. |
| `employment_type` | `jobPostingInfo.timeType` | Optional; do not depend on a fixed `bulletFields` position. |
| `workplace_type` | `jobPostingInfo.remoteType`; list `remoteType` | Values and capitalization vary by tenant. |
| `description_html` | `jobPostingInfo.jobDescription` | Detail request required. |
| `canonical_job_url` | `jobPostingInfo.externalUrl` | Prefer this URL over constructing one. |
| `published_at` | `jobPostingInfo.startDate` | Date only. `postedOn` is localized/human-relative and should be stored only as raw display text. |
| `updated_at` | Not exposed | Leave `null`. |

Pagination: increment request-body `offset` by the number of returned `jobPostings`, keep `limit` at a conservative value, and stop when `offset + returned_count >= total`.

Tenant differences:

- GM and NVIDIA use the same envelope, but facet names, `bulletFields`, localized text, optional fields, and `remoteType` values can differ.
- Always build the detail API request by appending the returned `externalPath` to the tenant CXS base. Do not reconstruct it from the title or requisition ID.

### SmartRecruiters response (`SR`)

Official references: [list postings](https://developers.smartrecruiters.com/reference/v1listpostings) and [retrieve a posting](https://developers.smartrecruiters.com/reference/v1getposting)

The list response is a paginated JSON object. Full descriptions are available only from the detail endpoint.

#### List response

```json
{
  "offset": 0,
  "limit": 100,
  "totalFound": 1,
  "content": [
    {
      "id": "743000123456789",
      "uuid": "opaque-uuid",
      "name": "Software Engineer",
      "refNumber": "REF12345",
      "releasedDate": "2026-08-20T12:00:00.000Z",
      "location": {
        "city": "Stuttgart",
        "region": "BW",
        "country": "de",
        "remote": false,
        "hybrid": true,
        "fullLocation": "Stuttgart, Germany"
      },
      "department": { "id": "eng", "label": "Engineering" },
      "typeOfEmployment": { "id": "full-time", "label": "Full-time" }
    }
  ]
}
```

#### Detail response

```json
{
  "id": "743000123456789",
  "uuid": "opaque-uuid",
  "name": "Software Engineer",
  "refNumber": "REF12345",
  "releasedDate": "2026-08-20T12:00:00.000Z",
  "postingUrl": "https://jobs.smartrecruiters.com/Example/...",
  "applyUrl": "https://jobs.smartrecruiters.com/Example/.../apply",
  "location": { "fullLocation": "Stuttgart, Germany", "hybrid": true },
  "jobAd": {
    "sections": {
      "companyDescription": { "title": "Company", "text": "<p>...</p>" },
      "jobDescription": { "title": "Role", "text": "<p>...</p>" },
      "qualifications": { "title": "Qualifications", "text": "<ul>...</ul>" },
      "additionalInformation": { "title": "Additional information", "text": "<p>...</p>" }
    }
  }
}
```

| Normalized field | SmartRecruiters source | Notes |
|---|---|---|
| `source_job_id` | `id` | Stringify; also retain `uuid`. |
| `requisition_id` | `refNumber` | Optional. |
| `title` | `name` | SmartRecruiters uses `name`. |
| `locations` | `location.fullLocation`; fallback join city/region/country | Do not include empty separators. |
| `country_code` | `location.country` | Usually a two-letter lowercase code; normalize case. |
| `department` | `department.label` | May be absent from detail; retain the list value. |
| `employment_type` | `typeOfEmployment.label` | May be absent from detail; retain the list value. |
| `workplace_type` | derive from `location.remote` and `location.hybrid` | If both are false, treat as onsite only when the source confirms it. |
| `description_html` | concatenate labelled `jobAd.sections.*.text` blocks in source order | Sections are independently optional. Keep headings to prevent meaning loss. |
| `canonical_job_url` | `postingUrl` | Detail response. |
| `apply_url` | `applyUrl` | Store only. |
| `published_at` | `releasedDate` | ISO timestamp. |
| `updated_at` | Not exposed publicly | Leave `null`. |

Pagination: request up to `limit=100`, increase `offset` by the number of records received, and stop when `offset + returned_count >= totalFound`.

### Personio response (`PERSONIO`)

Official reference: [Personio open-position XML feed](https://developer.personio.de/docs/retrieving-open-job-positions)

The response is XML, not JSON. The feed contains full description blocks, so a separate detail request is normally unnecessary.

```xml
<workzag-jobs>
  <position>
    <id>4103</id>
    <subcompany>Momenta Europe GmbH</subcompany>
    <office>Böblingen</office>
    <department>R&amp;D</department>
    <name>Software Engineer</name>
    <jobDescriptions>
      <jobDescription>
        <name>Responsibilities</name>
        <value><![CDATA[<ul><li>Build software</li></ul>]]></value>
      </jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType>
    <seniority>experienced</seniority>
    <schedule>full-time</schedule>
    <createdAt>2026-08-20T12:14:07+0200</createdAt>
  </position>
</workzag-jobs>
```

| Normalized field | Personio source | Notes |
|---|---|---|
| `source_job_id` | `position.id` | Integer in XML; stringify it. |
| `title` | `position.name` | Required. |
| `locations` | `position.office` | Office name may not be a full geographic location. |
| `department` | `position.department` | Optional. |
| `employment_type` | combine/normalize `employmentType` and `schedule` | Example: `permanent` plus `full-time`. Keep both raw values. |
| `description_html` | ordered `jobDescriptions.jobDescription[]` values | Preserve each block's `name` as a heading and concatenate in source order. Content is CDATA containing HTML. |
| `canonical_job_url` | construct `https://{account}.jobs.personio.de/job/{id}` | The feed does not provide the public URL directly. |
| `published_at` | `createdAt` | Optional ISO-like timestamp with numeric timezone. |
| `updated_at` | Not exposed | Leave `null`. |

Pagination: none; each request returns the full set of open positions.

### Per-company response differences

| Response profile | Companies | Company-specific handling |
|---|---|---|
| `GH` | Avride, Bot Auto, Gatik, Kodiak, Latitude AI, May Mobility, Motional, Nuro, Stack AV, Torc Robotics, Vay, Wayve, XPENG | Use one parser. Treat `metadata`, `requisition_id`, `application_deadline`, departments, offices, and compensation as optional. May Mobility's separate `maymobilityjobs` board is excluded unless explicitly added to scope. |
| `LEVER` | Horizon Robotics, Plus AI, Waabi, WeRide, Zoox | Use one parser. `country`, department, team, `allLocations`, workplace type, and salary fields vary by posting. The response has no public update timestamp. |
| `ASHBY` | Applied Intuition, Aurora | Use one parser with different board names. Both current responses expose `id`; compensation remains optional and can contain multiple geographic tiers. |
| `WORKDAY` | General Motors, NVIDIA | Use one structural parser with tenant configuration. Do not assign meaning by `bulletFields` array position; prefer named fields from the detail response. |
| `SR` | Bosch | Combine the independently optional `jobAd.sections` blocks. Retain the list record while fetching detail because list-only classification fields may be absent from detail. |
| `PERSONIO` | Momenta Europe | Coverage is Europe only. Other Momenta regions must remain separately labelled HTML/board sources rather than being assumed absent. |
| HTML / hosted board | Remaining 17 companies | There is no response contract. Each adapter must emit the normalized schema below and keep an HTML fixture plus selector/version notes. |

## Company register

“No public API” means that no stable, unauthenticated machine-readable endpoint was discoverable during this review. It does not mean that the browser never calls an internal service.

| # | Company | Career page / board | Preferred list target | Detail endpoint or URL structure | Ingestion decision |
|---:|---|---|---|---|---|
| 1 | 42dot | [Open roles](https://42dot.ai/en/careers/open-roles) | `https://api.ashbyhq.com/posting-api/job-board/42dot` | `https://42dot.ai/en/careers/open-roles/{role_uuid}` | Direct HTML/framework-data fallback. Preserve the UUID from each role link. |
| 2 | ADASTEC | [Company site](https://www.adastec.com/) | **No dedicated careers feed or public API discovered.** | No stable company-hosted job-detail pattern discovered. | Monitor the company site for a careers link; use its official LinkedIn/third-party vacancies as a separately labelled fallback (They have Consider API but required further contact for the API keys). |
| 3 | Aurora | [Careers](https://aurora.tech/careers/) | `ASHBY(aurora-operations-inc)` | `https://api.ashbyhq.com/posting-api/job-board/aurora-operations-inc`; details are also present in the Ashby list payload. | Preferred: Ashby JSON. The retired Greenhouse `aurora` endpoint returns 404 and must not be used. |
| 4 | Autobrains | [Open positions](https://www.comeet.com/jobs/autobrains/57.004) | **No supported keyless public API discovered** — scrape the Comeet/Spark Hire Recruit board. | Follow and store the opaque position `href` emitted by the board; do not guess a position ID format. | Third-party-board HTML fallback. Board/company identifiers may change. |
| 5 | Apollo / Baidu | [Baidu jobs](https://talent.baidu.com/jobs/list) | **No public API discovered** — render/scrape the list and, if necessary, capture the site's read-only XHR after review. | `https://talent.baidu.com/jobs/detail/{recruit_type}/{job_uuid}` where `recruit_type` includes `SOCIAL`, `GRADUATE`, or `INTERN`. | Custom SPA fallback. Preserve both path parameters from the list link. |
| 6 | Applied Intuition | [Careers](https://www.appliedintuition.com/careers) | `ASHBY(applied)` | `https://api.ashbyhq.com/posting-api/job-board/applied`; details are also present in the Ashby list payload. | Preferred: Ashby JSON. The former Greenhouse board is inactive. |
| 7 | aiMotive | [Careers](https://aimotive.com/career) | **No public API discovered** — scrape server-rendered role cards. | `https://aimotive.com/w/{role_slug}` | Direct HTML fallback; index pages link to stable, company-hosted detail pages. |
| 8 | Avride | [Greenhouse board](https://job-boards.greenhouse.io/avride) | `GH(avride) - https://boards-api.greenhouse.io/v1/boards/avride/jobs` | GH detail with board token `avride` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 9 | Bot Auto | [Careers](https://bot.auto/career) | `GH(botauto) - https://boards-api.greenhouse.io/v1/boards/botauto/jobs?content=true ` | GH detail with board token `botauto` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 10 | Bosch | [Bosch jobs](https://jobs.smartrecruiters.com/BoschGroup) | `SR(BoschGroup) - https://api.smartrecruiters.com/v1/companies/BoschGroup/postings?limit=100&offset=0&utm` | SR detail with company ID `BoschGroup` and `{posting_id}`. | Preferred: SmartRecruiters JSON. This matches the existing Bosch scraper. |
| 11 | DeepRoute.ai | [Company site](https://www.deeproute.ai/) | **No dedicated careers page or public API discovered on the international site.** | No stable company-hosted detail pattern discovered. | Monitor the official site; use official LinkedIn/other explicitly linked recruiting channels as a labelled fallback. |
| 12 | DiDi | [Careers](https://careers.didiglobal.com/job) | **No public API discovered** — scrape the rendered list or a reviewed read-only XHR. | `https://careers.didiglobal.com/jobDetail%3A{job_id}` (the route contains an encoded colon). | Custom SPA fallback. Treat `{job_id}` as an opaque string. |
| 13 | May Mobility | [Careers](https://maymobility.com/careers/) | `GH(maymobility) - https://boards-api.greenhouse.io/v1/boards/maymobility/jobs?content=true` | GH detail with board token `maymobility` and `{job_id}`. | Preferred: Greenhouse JSON. Do not mix the separate `maymobilityjobs` board into the main feed without a product decision. |
| 14 | Gatik | [Careers](https://www.gatik.ai/careers) | `GH(gatikaiinc) - https://boards-api.greenhouse.io/v1/boards/gatikaiinc/jobs?content=true` | GH detail with board token `gatikaiinc` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 15 | Inceptio.ai | [Company site](https://en.inceptio.ai/) | **No job-list API or vacancy index discovered.** The site publishes `career@inceptioglobal.ai`. | No job-detail URL structure exists on the current site. | Contact/manual-monitoring fallback; do not fabricate jobs from the contact address. |
| 16 | Horizon Robotics | [Lever board](https://jobs.lever.co/horizon) | `LEVER(horizon)- https://api.lever.co/v0/postings/horizon?mode=json` | Lever detail with site ID `horizon` and `{posting_id}`. | Preferred: Lever JSON. |
| 17 | Huawei | [Huawei Careers](https://career.huawei.com/) | **No stable public API discovered** — the regional/social/campus portals are custom SPAs. | Detail routes and identifiers are portal/locale specific; retain the literal detail URL returned by the selected portal. | Rendered HTML/read-only XHR fallback, scoped by portal and locale. Expect authentication and anti-bot controls. |
| 18 | Kodiak | [Greenhouse board](https://job-boards.greenhouse.io/kodiak) | `GH(kodiak) - https://boards-api.greenhouse.io/v1/boards/kodiak/jobs?content=true` | GH detail with board token `kodiak` and `{job_id}`. | Preferred: Greenhouse JSON. Ignore older/stale Lever links. |
| 19 | Einride | [Careers](https://careers.einride.tech/) | **No supported public API discovered** — the page is a Jobylon-powered board. | Retain the opaque job/detail URL emitted by the Jobylon widget; application URLs commonly use `https://emp.jobylon.com/applications/jobs/{job_id}/create/`. | Third-party-board HTML/widget fallback. Do not scrape the application form for job content. |
| 20 | Latitude AI | [Greenhouse board](https://job-boards.greenhouse.io/latitude) | `GH(latitude) - https://boards-api.greenhouse.io/v1/boards/latitude/jobs?content=true` | GH detail with board token `latitude` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 21 | General Motors (GM) | [GM careers](https://generalmotors.wd5.myworkdayjobs.com/Careers_GM) | `WORKDAY(host=generalmotors.wd5.myworkdayjobs.com, tenant=generalmotors, site=Careers_GM) - https://generalmotors.wd5.myworkdayjobs.com/wday/cxs/generalmotors/Careers_GM/jobs` | CXS detail `/wday/cxs/generalmotors/Careers_GM/job/{job_path}`; public page `/en-US/Careers_GM/job/{job_path}`. | Preferred: Workday CXS JSON with pagination. |
| 22 | Mobileye | [Careers](https://careers.mobileye.com/jobs) | **No public API discovered** — scrape the server-rendered/custom job index. | `https://careers.mobileye.com/jobs/{role_slug}/{job_uuid}` | Direct HTML fallback. Preserve both slug and UUID from the source link. |
| 23 | Motional | [Greenhouse board](https://job-boards.greenhouse.io/motional) | `GH(motional) - https://boards-api.greenhouse.io/v1/boards/motional/jobs?content=true` | GH detail with board token `motional` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 24 | Momenta | [Momenta careers](https://www.momenta.cn/en/join.html) / [Europe board](https://momenta-europe-gmbh.jobs.personio.de/) | `PERSONIO(account=momenta-europe-gmbh) -https://momenta-europe-gmbh.jobs.personio.de/xml?language=en (XML instead of external API or pure HTML` for Europe. The China/global page itself exposes no public job API. | `https://momenta-europe-gmbh.jobs.personio.de/job/{job_id}` | Preferred for Europe: Personio XML. For other regions, scrape only the official region board linked by Momenta and label region coverage. |
| 25 | Nuro | [Careers](https://www.nuro.ai/careers) | `GH(nuro) - https://boards-api.greenhouse.io/v1/boards/nuro/jobs?content=true` | GH detail with board token `nuro` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 26 | NVIDIA | [NVIDIA careers](https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite) | `https://nvidia.eightfold.ai/api/pcsx/search?domain=nvidia.com&start=0&num=10&query=&location=` | CXS detail `/wday/cxs/nvidia/NVIDIAExternalCareerSite/job/{job_path}`; public page `/en-US/NVIDIAExternalCareerSite/job/{job_path}`. | Preferred: Workday CXS JSON with pagination. |
| 27 | Pony.ai | [Pony.ai careers](https://www.pony.ai/careers?lang=en) / [US board](https://apply.workable.com/pony-dot-ai/) | **No supported unauthenticated public API selected.** US roles are on Workable; China roles are on Feishu. | US: `https://apply.workable.com/pony-dot-ai/j/{short_code}/   - https://www.workable.com/api/accounts/pony-dot-ai?details=true`; China: retain the Feishu URL, commonly `https://ponyai.jobs.feishu.cn/ponyai/m/position/{position_id}/detail`. | Third-party-board HTML fallback. Ingest US and China as separate sources and deduplicate by canonical URL. |
| 28 | Plus AI | [Lever board](https://jobs.lever.co/plus-2) | `LEVER(plus-2) - https://api.lever.co/v0/postings/plus-2?mode=json` | Lever detail with site ID `plus-2` and `{posting_id}`. | Preferred: Lever JSON. |
| 29 | QCraft | [Careers](https://www.qcraft.ai/en/careers) / [Feishu board](https://qcraft.jobs.feishu.cn/631429) | **No supported public API discovered** — use the linked Feishu board. | Retain the opaque detail URL emitted by Feishu; position routes commonly contain `/position/{position_id}/detail`. | Third-party-board rendered HTML fallback. |
| 30 | Stack AV | [Greenhouse board](https://job-boards.greenhouse.io/stackav) | `GH(stackav) - https://boards-api.greenhouse.io/v1/boards/stackav/jobs?content=true` | GH detail with board token `stackav` and `{job_id}`. | Preferred: Greenhouse JSON. This matches the existing Stack AV scraper. |
| 31 | Tensor (formerly AutoX) | [Careers](https://www.tensor.auto/careers) | **No public API discovered** — scrape the company-hosted career index. | `https://www.tensor.auto/careers/jd{numeric_id}` | Direct HTML fallback. Treat the `jd` identifier as opaque, not necessarily sequential. |
| 32 | Torc Robotics | [Careers](https://torc.ai/careers/) | `GH(torcrobotics) - https://boards-api.greenhouse.io/v1/boards/torcrobotics/jobs?content=true` | GH detail with board token `torcrobotics` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 33 | TIER IV | [Careers](https://tier4.co.jp/en/careers) / [HERP board](https://herp.careers/v1/tier4) | **No supported public API discovered** — scrape the public HERP board. | `https://herp.careers/v1/tier4/{opaque_requisition_id}` | Third-party-board HTML fallback. Preserve the case-sensitive opaque ID. |
| 34 | Waabi | [Lever board](https://jobs.lever.co/waabi) | `LEVER(waabi) - https://api.lever.co/v0/postings/waabi?mode=json` | Lever detail with site ID `waabi` and `{posting_id}`. | Preferred: Lever JSON. This matches the existing Waabi scraper. |
| 35 | Waymo | [Careers](https://careers.withwaymo.com/) / [job search](https://careers.withwaymo.com/jobs/search/) | `https://boards-api.greenhouse.io/v1/boards/waymo/jobs?content=true`. | `https://careers.withwaymo.com/jobs/{role-slug}` | Direct HTML/custom-career-platform fallback. Extract the displayed requisition number as a secondary key because slugs can change. |
| 36 | Wayve | [Greenhouse board](https://job-boards.greenhouse.io/wayve) | `GH(wayve) - https://boards-api.greenhouse.io/v1/boards/wayve/jobs?content=true` | GH detail with board token `wayve` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 37 | WeRide | [Lever board](https://jobs.lever.co/weride) | `LEVER(weride) - https://api.lever.co/v0/postings/weride?mode=json` | Lever detail with site ID `weride` and `{posting_id}`. | Preferred: Lever JSON. |
| 38 | Woven by Toyota | [Careers](https://woven.toyota/en/careers) | **No public API discovered** — scrape company-hosted list/framework data. | `https://www.woven.toyota/en/careers/detail/{job_uuid}` | Direct HTML/framework-data fallback. Preserve the UUID. |
| 39 | Vay | [Greenhouse board](https://job-boards.greenhouse.io/vay) | `GH(vay) - https://boards-api.greenhouse.io/v1/boards/vay/jobs?content=true` | GH detail with board token `vay` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 40 | XPENG | [Global openings](https://www.xpeng.com/no/join-us) | `GH(xpengmotors) - https://boards-api.greenhouse.io/v1/boards/xpengmotors/jobs?content=true` | GH detail with board token `xpengmotors` and `{job_id}`. | Preferred: Greenhouse JSON. The country path is only a presentation page; ingest the GH board once to avoid duplicates. |
| 41 | Zoox | [Careers](https://zoox.com/careers) / [Lever board](https://jobs.lever.co/zoox) | `LEVER(zoox) - https://api.lever.co/v0/postings/zoox?mode=json` | Lever detail with site ID `zoox` and `{posting_id}`. | Preferred: Lever JSON. |

## Coverage summary

| Source type | Companies | Count |
|---|---|---:|
| Greenhouse JSON | Avride, Bot Auto, Gatik, Kodiak, Latitude AI, May Mobility, Motional, Nuro, Stack AV, Torc Robotics, Vay, Wayve, XPENG | 13 |
| Lever JSON | Horizon Robotics, Plus AI, Waabi, WeRide, Zoox | 5 |
| Ashby JSON | Applied Intuition, Aurora | 2 |
| Workday CXS JSON | General Motors, NVIDIA | 2 |
| SmartRecruiters JSON | Bosch | 1 |
| Personio XML (regional coverage) | Momenta | 1 |
| No discoverable public API / HTML or hosted-board fallback | 42dot, ADASTEC, Autobrains, Apollo/Baidu, aiMotive, DeepRoute.ai, DiDi, Inceptio.ai, Huawei, Einride, Mobileye, Pony.ai, QCraft, Tensor, TIER IV, Waymo, Woven by Toyota | 17 |
| **Total** |  | **41** |

## Normalized output expectations

Every source adapter should emit the same minimum fields:

```json
{
  "source_company": "Waabi",
  "source_system": "lever",
  "source_job_id": "opaque-source-id",
  "requisition_id": null,
  "canonical_job_url": "https://jobs.lever.co/waabi/opaque-source-id",
  "apply_url": "https://jobs.lever.co/waabi/opaque-source-id/apply",
  "title": "Software Engineer",
  "locations": ["Toronto, Ontario, Canada"],
  "country_code": "CA",
  "workplace_type": "hybrid",
  "description_html": "<p>...</p>",
  "description_text": "...",
  "employment_type": "Full-time",
  "department": "Engineering",
  "team": "Autonomy",
  "compensation": {
    "currency": null,
    "interval": null,
    "minimum": null,
    "maximum": null,
    "raw_text": null
  },
  "published_at": "2026-08-20T00:00:00Z",
  "updated_at": null,
  "retrieved_at": "2026-08-27T00:00:00Z",
  "raw_payload": {}
}
```

Use `(source_company, source_system, source_job_id)` as the primary natural key. When an HTML-only source exposes no durable ID, hash the canonical detail URL and retain the original URL so changes can be audited. `raw_payload` represents storage in the bronze/raw layer; it may be stored outside the normalized table as long as the normalized row keeps a reference to it.

### Required validation before database upsert

Reject or quarantine a record when any of these conditions apply:

- `source_job_id`, `title`, or `canonical_job_url` is empty;
- the canonical URL is an application-form URL rather than a job-detail URL;
- a date or epoch value cannot be parsed without guessing its unit or timezone;
- the source company does not match the configured adapter;
- the detail response returns a different job identifier from the list response; or
- HTML sanitization removes all meaningful description text from a posting that previously had content.

Optional fields should remain `null` or empty arrays; their absence must not fail the whole company run.

## Maintenance checklist

1. Before each production run, fetch the list target and record HTTP status, redirect chain, content type, and item count.
2. Treat a sudden zero-job response as a possible integration failure, not immediately as “no vacancies.” Retry and compare the career page.
3. Detect ATS migrations by comparing official career-page outbound links with the configured host/token.
4. Keep list and detail parsers separate; a list request should not trigger application-form requests.
5. Add a fixture and contract test for every source adapter. Redact cookies, tokens, applicant data, and analytics identifiers from fixtures.
6. Review HTML-only targets more frequently because selectors and framework payloads change more often than public ATS schemas.

## Verification notes

- All 13 Greenhouse, 5 Lever, 2 Ashby, 2 Workday, 1 SmartRecruiters, and 1 Personio configurations returned their documented response envelope during the 2026-08-27 contract check.
- Response examples are abridged schemas, not frozen payloads. Optional fields and live job counts will change without a documentation update.
- The Horizon, Plus AI, Waabi, WeRide, and Zoox identifiers refer to current Lever boards; older aliases should not be merged without verification.
- Aurora and Applied Intuition have migrated away from their older Greenhouse targets to Ashby; the current Ashby posting endpoints are the configured sources.
- The supplied client list contains 41 rows. No company was invented to force the count to 42.
