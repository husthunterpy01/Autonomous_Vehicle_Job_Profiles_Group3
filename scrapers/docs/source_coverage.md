# Job Scraper — Source Coverage

Status of every company in [`scrapers/data/list_companies.yaml`](../data/list_companies.yaml):
how its jobs are fetched, and — for the three that cannot be scraped — exactly what blocks them.

_Last verified: 2026-09-07 (live checks against each source)._

---

## Summary

| | Count | |
|---|---|---|
| **Enabled & scraping** | **38 / 41** | API 30 · HTML 7 · XML 1 |
| **Blocked (disabled)** | 3 | `apollo_baidu`, `huawei`, `qcraft` |

The pipeline is unchanged for every source: `RawFetch` → raw payload in MinIO
(`source = api | html | xml`) → `BronzeIngest` lands it into `bronze.raw_responses`
(JSONB) → per-source dbt model → `bronze.job_postings` → `silver.cleaned_job_postings`.

`bronze.job_postings` carries two keys: `id` (a `row_number()`, volatile between
runs) and **`job_id`** — the ATS-native posting id (`4012756009` for Greenhouse,
`81ef015f-…` for Lever, `744000147495710` for SmartRecruiters, …). It falls back
to the job URL, then a content hash, only when the ATS supplies no id, so it is
never null and is stable across runs. Use `job_id` for joins and cross-run
comparisons.

---

## Fetch / parse strategies

| Strategy | Where configured | How it works |
|---|---|---|
| **API** | `ats_sources.yaml → ats_sources` | `RawFetch` does an HTTP GET/POST, stores the JSON. One dbt model per ATS parses it. |
| **`css_list`** | `ats_sources.yaml → html_sources` | Fetch the career page HTML, parse job rows with CSS selectors in `HTMLExtractor`. |
| **`css_list` + `render`** | `html_sources` `render: true` | `RawFetch` renders the page in headless Chrome first (`SeleniumClient`), then `css_list` parses the rendered DOM. |
| **`css_list` + `paginate: {param}`** | `html_sources` | `RawFetch` walks `?param=0,25,50…` of a static list endpoint, concatenates the pages; `HTMLExtractor` dedupes by job id. |
| **`css_list` + `paginate: {next_selector}`** | `html_sources` | Headless Chrome clicks a "next page" control up to `max_pages` times; every page snapshot is concatenated and deduped. |
| **`jobylon`** | `html_sources` | Parses the `JBL.embed_v2['jobs']` JS array embedded in a Jobylon widget page. |
| **`+ detail`** | `html_sources` `detail:` | When the list page has no description, `RawFetch` also fetches each job's detail page — `detail.url` (with `{id}` = the native job id) or the row's own `job_url` for `css_list`; the JobPosting JSON-LD (`detail.json_ld: true`) for `jobylon` — and embeds the results in a `<script type="application/x-bronze-detail">` map that `HTMLExtractor` reads into `job_description`. |
| **`headless` (stub)** | `html_sources` | Placeholder for the blocked sources — logs a warning and yields nothing. |

Extractor field selectors support `"selector@attr"` to read an attribute (e.g. `time@datetime`)
instead of the element text.

---

## Coverage by company

### API (30)

| ATS | Companies |
|---|---|
| `greenhouse` (14) | av_ride, bot_auto, gatik, kodiak, latitude_ford, may_mobility, motional, nuro, stack_av, torc, vay, waymo, wayve, xpeng |
| `lever` (6) | horizon, mobileye, plus_ai, waabi, weride, zoox |
| `ashby` (3) | applied_intuition, aurora, fortytwo_dot |
| `workable` (3) | deeproute, inceptio, pony_ai |
| `workday` (2) | gm, nvidia |
| `smartrecruiters` (1) | bosch |
| `comeet` (1) | autobrains |

### HTML (7)

| Company | Strategy | Source | Verified | Descriptions |
|---|---|---|---|---|
| `tensor` | `css_list` + `detail` | tensor.auto/careers (Webflow) | 100 jobs | per-job page (`.w-richtext`) |
| `tier_iv` | `css_list` | herp.careers/v1/tier4 | 60 jobs | on the list |
| `aimotive` | `css_list` + `detail` | aimotive.com/career (Liferay) | 6 jobs | per-job page (`.single-post`) |
| `adastec` | `css_list` + `paginate {param: start}` + `detail` | LinkedIn public guest job feed (`f_C=13011997`) | 3 jobs | guest `jobPosting/{id}` fragment |
| `woven` | `css_list` + `render` + `detail` | woven.toyota/en/careers (Next.js) | 88 jobs | per-job page (server-rendered) |
| `didi` | `css_list` + `render` + `paginate {next_selector}` + `detail` | careers.didiglobal.com/job (Nuxt) | ~270 jobs (50 across a 5-page test) | per-job page — **~260 extra fetches/run** |
| `einride` | `jobylon` + `detail` | Jobylon widget embed (company 3143) | 30 jobs | per-job page JobPosting JSON-LD |

### XML (1)

| Company | Source | Verified |
|---|---|---|
| `momenta` | Personio `workzag-jobs` XML feed | 3 jobs |

### Blocked — disabled (3)

`apollo_baidu`, `huawei`, `qcraft` — see next section.

---

## Blocked sources — specific reasons

All three were tested with (a) a plain HTTP fetch, (b) headless Chrome with scroll +
network capture, and (c) their underlying JSON API where one exists.

### `apollo_baidu` — https://talent.baidu.com/jobs/list

| | |
|---|---|
| **Plain fetch** | Returns the SPA shell only — no job data, no JSON-LD, no server-rendered cards. |
| **Headless Chrome** | Navigation terminates at `about:blank`; `document` is 39 bytes. The page never renders — Baidu refuses to serve content to a non-interactive / datacenter client. |
| **Guest API** | `POST talent.baidu.com/httpservice/getPostListNew` → `{"status":"need-login","message":"need login!"}`. Job data is gated behind an authenticated Baidu account. |
| **What it would take** | A logged-in Baidu session **and** defeating their client-fingerprint check. Not viable without credentials, and brittle even then. |

### `huawei` — https://career.huawei.com/

| | |
|---|---|
| **Redirect** | `/` geo-redirects to `/cn` (Chinese portal, title 华为招聘官网首页). No locale exposes server-rendered listings. |
| **Bot gateway** | On load the page runs a device-verification handshake — XHRs to `corp.hwp.huawei.com/hwp-internet/rts-gateway/services/hwp_ocs_verify` and `…/hwp_ocs_collect_batch`. The HTML carries `verify` / `403` markers. |
| **Jobs API** | `apigw-dgg-b0.huawei.com/api/apig/channelhw/recommend/pub/getRecommendLicense` issues a **per-request signed `licenseCode`** produced by obfuscated client JS *after* the verify step completes. |
| **What it would take** | A fully instrumented browser session that completes the verification handshake and replays the signed token on every API call. High effort, breaks whenever Huawei changes the handshake. |

### `qcraft` — https://qcraft.jobs.feishu.cn/631429

| | |
|---|---|
| **Platform** | Feishu / ByteDance "headhunting platform" board (title 字节跳动猎头平台). |
| **Direct API** | `GET /api/v1/search/job/posts?…` returns the SPA **HTML shell**, not JSON. |
| **Anti-bot** | JSON is only returned when the request carries a `_signature` query param minted per-call by ByteDance's `acrawler.js` / `webmssdk`, plus a `csrf/token` cookie. Observed calls in headless: `/api/v1/csrf/token`, `/api/v1/config/job/filters/6?_signature=…`, `/api/v1/search/job/posts?…`. |
| **Headless DOM** | The `#mainBox` React app renders **0 job cards / 0 job links** to Selenium — Feishu serves a degraded tree to headless browsers. |
| **What it would take** | Reverse-engineering or executing ByteDance's `_signature` algorithm. It is deliberate anti-crawling and a standing maintenance burden. |

---

## Known limitations of the working sources

| Source | Limitation |
|---|---|
| `didi` | `paginate.max_pages: 30` cap (~270 jobs). Plus `detail:` adds one static fetch **per job** (~260/run, several minutes) — drop the `detail` block if runs get too slow. |
| `einride` | The Jobylon embed inlines only its **first 30** jobs; the rest load via a "show more" AJAX call that is not implemented. `detail:` adds a fetch per job for the description. |
| `adastec` | Uses LinkedIn's public **guest** feed (no auth), but scraping LinkedIn is against their ToS — keep the request volume low. The company id `f_C=13011997` is hard-coded in `html_sources.adastec.url`. |
| `autobrains` (`comeet`) | The API token is copied from the Comeet careers-page HTML into `params.token`. If Comeet rotates it the fetch will 401 — re-copy from the page source. |
| `workday` | `job_id` / `job_uploaded_at` / `job_description` / `employment_type` come from `job->'jobPostingDetail'->'jobPostingInfo'`; if RawFetch's per-job detail GET failed for a posting, those fall back to the sparse list fields (id from `bulletFields`, no description). |
| `inceptio` | Workable account is valid but currently lists **0 jobs**. |
