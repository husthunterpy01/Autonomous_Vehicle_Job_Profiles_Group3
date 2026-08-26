# AV company career-page endpoint register

**Status:** implementation reference

**Last verified:** 2026-08-26

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

## Company register

“No public API” means that no stable, unauthenticated machine-readable endpoint was discoverable during this review. It does not mean that the browser never calls an internal service.

| # | Company | Career page / board | Preferred list target | Detail endpoint or URL structure | Ingestion decision |
|---:|---|---|---|---|---|
| 1 | 42dot | [Open roles](https://42dot.ai/en/careers/open-roles) | **No public API** — scrape the rendered role index or page-embedded application data. | `https://42dot.ai/en/careers/open-roles/{role_uuid}` | Direct HTML/framework-data fallback. Preserve the UUID from each role link. |
| 2 | ADASTEC | [Company site](https://www.adastec.com/) | **No dedicated careers feed or public API discovered.** | No stable company-hosted job-detail pattern discovered. | Monitor the company site for a careers link; use its official LinkedIn/third-party vacancies as a separately labelled fallback. |
| 3 | Aurora | [Careers](https://aurora.tech/careers/) | `ASHBY(aurora-operations-inc)` | `https://jobs.ashbyhq.com/aurora-operations-inc/{job_uuid}`; details are also present in the Ashby list payload. | Preferred: Ashby JSON. The retired Greenhouse `aurora` endpoint returns 404 and must not be used. |
| 4 | Autobrains | [Open positions](https://www.comeet.com/jobs/autobrains/57.004) | **No supported keyless public API discovered** — scrape the Comeet/Spark Hire Recruit board. | Follow and store the opaque position `href` emitted by the board; do not guess a position ID format. | Third-party-board HTML fallback. Board/company identifiers may change. |
| 5 | Apollo / Baidu | [Baidu jobs](https://talent.baidu.com/jobs/list) | **No public API discovered** — render/scrape the list and, if necessary, capture the site's read-only XHR after review. | `https://talent.baidu.com/jobs/detail/{recruit_type}/{job_uuid}` where `recruit_type` includes `SOCIAL`, `GRADUATE`, or `INTERN`. | Custom SPA fallback. Preserve both path parameters from the list link. |
| 6 | Applied Intuition | [Careers](https://www.appliedintuition.com/careers) | `ASHBY(applied)` | `https://jobs.ashbyhq.com/applied/{job_uuid}`; details are also present in the Ashby list payload. | Preferred: Ashby JSON. The former Greenhouse board is inactive. |
| 7 | aiMotive | [Careers](https://aimotive.com/career) | **No public API discovered** — scrape server-rendered role cards. | `https://aimotive.com/w/{role_slug}` | Direct HTML fallback; index pages link to stable, company-hosted detail pages. |
| 8 | Avride | [Greenhouse board](https://job-boards.greenhouse.io/avride) | `GH(avride)` | GH detail with board token `avride` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 9 | Bot Auto | [Careers](https://bot.auto/career) | `GH(botauto)` | GH detail with board token `botauto` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 10 | Bosch | [Bosch jobs](https://jobs.smartrecruiters.com/BoschGroup) | `SR(BoschGroup)` | SR detail with company ID `BoschGroup` and `{posting_id}`. | Preferred: SmartRecruiters JSON. This matches the existing Bosch scraper. |
| 11 | DeepRoute.ai | [Company site](https://www.deeproute.ai/) | **No dedicated careers page or public API discovered on the international site.** | No stable company-hosted detail pattern discovered. | Monitor the official site; use official LinkedIn/other explicitly linked recruiting channels as a labelled fallback. |
| 12 | DiDi | [Careers](https://careers.didiglobal.com/job) | **No public API discovered** — scrape the rendered list or a reviewed read-only XHR. | `https://careers.didiglobal.com/jobDetail%3A{job_id}` (the route contains an encoded colon). | Custom SPA fallback. Treat `{job_id}` as an opaque string. |
| 13 | May Mobility | [Careers](https://maymobility.com/careers/) | `GH(maymobility)` | GH detail with board token `maymobility` and `{job_id}`. | Preferred: Greenhouse JSON. Do not mix the separate `maymobilityjobs` board into the main feed without a product decision. |
| 14 | Gatik | [Careers](https://www.gatik.ai/careers) | `GH(gatikaiinc)` | GH detail with board token `gatikaiinc` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 15 | Inceptio.ai | [Company site](https://en.inceptio.ai/) | **No job-list API or vacancy index discovered.** The site publishes `career@inceptioglobal.ai`. | No job-detail URL structure exists on the current site. | Contact/manual-monitoring fallback; do not fabricate jobs from the contact address. |
| 16 | Horizon Robotics | [Lever board](https://jobs.lever.co/horizon) | `LEVER(horizon)` | Lever detail with site ID `horizon` and `{posting_id}`. | Preferred: Lever JSON. |
| 17 | Huawei | [Huawei Careers](https://career.huawei.com/) | **No stable public API discovered** — the regional/social/campus portals are custom SPAs. | Detail routes and identifiers are portal/locale specific; retain the literal detail URL returned by the selected portal. | Rendered HTML/read-only XHR fallback, scoped by portal and locale. Expect authentication and anti-bot controls. |
| 18 | Kodiak | [Greenhouse board](https://job-boards.greenhouse.io/kodiak) | `GH(kodiak)` | GH detail with board token `kodiak` and `{job_id}`. | Preferred: Greenhouse JSON. Ignore older/stale Lever links. |
| 19 | Einride | [Careers](https://careers.einride.tech/) | **No supported public API discovered** — the page is a Jobylon-powered board. | Retain the opaque job/detail URL emitted by the Jobylon widget; application URLs commonly use `https://emp.jobylon.com/applications/jobs/{job_id}/create/`. | Third-party-board HTML/widget fallback. Do not scrape the application form for job content. |
| 20 | Latitude AI | [Greenhouse board](https://job-boards.greenhouse.io/latitude) | `GH(latitude)` | GH detail with board token `latitude` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 21 | General Motors (GM) | [GM careers](https://generalmotors.wd5.myworkdayjobs.com/Careers_GM) | `WORKDAY(host=generalmotors.wd5.myworkdayjobs.com, tenant=generalmotors, site=Careers_GM)` | CXS detail `/wday/cxs/generalmotors/Careers_GM/job/{job_path}`; public page `/en-US/Careers_GM/job/{job_path}`. | Preferred: Workday CXS JSON with pagination. |
| 22 | Mobileye | [Careers](https://careers.mobileye.com/jobs) | **No public API discovered** — scrape the server-rendered/custom job index. | `https://careers.mobileye.com/jobs/{role_slug}/{job_uuid}` | Direct HTML fallback. Preserve both slug and UUID from the source link. |
| 23 | Motional | [Greenhouse board](https://job-boards.greenhouse.io/motional) | `GH(motional)` | GH detail with board token `motional` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 24 | Momenta | [Momenta careers](https://www.momenta.cn/en/join.html) / [Europe board](https://momenta-europe-gmbh.jobs.personio.de/) | `PERSONIO(account=momenta-europe-gmbh)` for Europe. The China/global page itself exposes no public job API. | `https://momenta-europe-gmbh.jobs.personio.de/job/{job_id}` | Preferred for Europe: Personio XML. For other regions, scrape only the official region board linked by Momenta and label region coverage. |
| 25 | Nuro | [Careers](https://www.nuro.ai/careers) | `GH(nuro)` | GH detail with board token `nuro` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 26 | NVIDIA | [NVIDIA careers](https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite) | `WORKDAY(host=nvidia.wd5.myworkdayjobs.com, tenant=nvidia, site=NVIDIAExternalCareerSite)` | CXS detail `/wday/cxs/nvidia/NVIDIAExternalCareerSite/job/{job_path}`; public page `/en-US/NVIDIAExternalCareerSite/job/{job_path}`. | Preferred: Workday CXS JSON with pagination. |
| 27 | Pony.ai | [Pony.ai careers](https://www.pony.ai/careers?lang=en) / [US board](https://apply.workable.com/pony-dot-ai/) | **No supported unauthenticated public API selected.** US roles are on Workable; China roles are on Feishu. | US: `https://apply.workable.com/pony-dot-ai/j/{short_code}/`; China: retain the Feishu URL, commonly `https://ponyai.jobs.feishu.cn/ponyai/m/position/{position_id}/detail`. | Third-party-board HTML fallback. Ingest US and China as separate sources and deduplicate by canonical URL. |
| 28 | Plus AI | [Lever board](https://jobs.lever.co/plus-2) | `LEVER(plus-2)` | Lever detail with site ID `plus-2` and `{posting_id}`. | Preferred: Lever JSON. |
| 29 | QCraft | [Careers](https://www.qcraft.ai/en/careers) / [Feishu board](https://qcraft.jobs.feishu.cn/631429) | **No supported public API discovered** — use the linked Feishu board. | Retain the opaque detail URL emitted by Feishu; position routes commonly contain `/position/{position_id}/detail`. | Third-party-board rendered HTML fallback. |
| 30 | Stack AV | [Greenhouse board](https://job-boards.greenhouse.io/stackav) | `GH(stackav)` | GH detail with board token `stackav` and `{job_id}`. | Preferred: Greenhouse JSON. This matches the existing Stack AV scraper. |
| 31 | Tensor (formerly AutoX) | [Careers](https://www.tensor.auto/careers) | **No public API discovered** — scrape the company-hosted career index. | `https://www.tensor.auto/careers/jd{numeric_id}` | Direct HTML fallback. Treat the `jd` identifier as opaque, not necessarily sequential. |
| 32 | Torc Robotics | [Careers](https://torc.ai/careers/) | `GH(torcrobotics)` | GH detail with board token `torcrobotics` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 33 | TIER IV | [Careers](https://tier4.co.jp/en/careers) / [HERP board](https://herp.careers/v1/tier4) | **No supported public API discovered** — scrape the public HERP board. | `https://herp.careers/v1/tier4/{opaque_requisition_id}` | Third-party-board HTML fallback. Preserve the case-sensitive opaque ID. |
| 34 | Waabi | [Lever board](https://jobs.lever.co/waabi) | `LEVER(waabi)` | Lever detail with site ID `waabi` and `{posting_id}`. | Preferred: Lever JSON. This matches the existing Waabi scraper. |
| 35 | Waymo | [Careers](https://careers.withwaymo.com/) / [job search](https://careers.withwaymo.com/jobs/search/) | **No public API discovered** — scrape the public search pages with pagination. | `https://careers.withwaymo.com/jobs/{role-slug}` | Direct HTML/custom-career-platform fallback. Extract the displayed requisition number as a secondary key because slugs can change. |
| 36 | Wayve | [Greenhouse board](https://job-boards.greenhouse.io/wayve) | `GH(wayve)` | GH detail with board token `wayve` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 37 | WeRide | [Lever board](https://jobs.lever.co/weride) | `LEVER(weride)` | Lever detail with site ID `weride` and `{posting_id}`. | Preferred: Lever JSON. |
| 38 | Woven by Toyota | [Careers](https://woven.toyota/en/careers) | **No public API discovered** — scrape company-hosted list/framework data. | `https://www.woven.toyota/en/careers/detail/{job_uuid}` | Direct HTML/framework-data fallback. Preserve the UUID. |
| 39 | Vay | [Greenhouse board](https://job-boards.greenhouse.io/vay) | `GH(vay)` | GH detail with board token `vay` and `{job_id}`. | Preferred: Greenhouse JSON. |
| 40 | XPENG | [Global openings](https://www.xpeng.com/no/join-us) | `GH(xpengmotors)` | GH detail with board token `xpengmotors` and `{job_id}`. | Preferred: Greenhouse JSON. The country path is only a presentation page; ingest the GH board once to avoid duplicates. |
| 41 | Zoox | [Careers](https://zoox.com/careers) / [Lever board](https://jobs.lever.co/zoox) | `LEVER(zoox)` | Lever detail with site ID `zoox` and `{posting_id}`. | Preferred: Lever JSON. |

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
  "canonical_job_url": "https://jobs.lever.co/waabi/opaque-source-id",
  "title": "Software Engineer",
  "locations": ["Toronto, Ontario, Canada"],
  "description_html": "<p>...</p>",
  "employment_type": "Full-time",
  "department": "Engineering",
  "published_at": "2026-08-20T00:00:00Z",
  "retrieved_at": "2026-08-26T00:00:00Z"
}
```

Use `(source_company, source_system, source_job_id)` as the primary natural key. When an HTML-only source exposes no durable ID, hash the canonical detail URL and retain the original URL so changes can be audited.

## Maintenance checklist

1. Before each production run, fetch the list target and record HTTP status, redirect chain, content type, and item count.
2. Treat a sudden zero-job response as a possible integration failure, not immediately as “no vacancies.” Retry and compare the career page.
3. Detect ATS migrations by comparing official career-page outbound links with the configured host/token.
4. Keep list and detail parsers separate; a list request should not trigger application-form requests.
5. Add a fixture and contract test for every source adapter. Redact cookies, tokens, applicant data, and analytics identifiers from fixtures.
6. Review HTML-only targets more frequently because selectors and framework payloads change more often than public ATS schemas.

## Verification notes

- Greenhouse tokens in the table returned a successful public jobs endpoint during this review.
- The Horizon, Plus AI, Waabi, WeRide, and Zoox identifiers refer to current Lever boards; older aliases should not be merged without verification.
- Aurora and Applied Intuition have migrated away from their older Greenhouse targets to Ashby; the current Ashby posting endpoints are the configured sources.
- The supplied client list contains 41 rows. No company was invented to force the count to 42.
