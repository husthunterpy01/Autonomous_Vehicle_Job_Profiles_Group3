# End-to-end tests

Browser tests for the core flows, written with [Playwright](https://playwright.dev) and run in Chromium. They cover:

| Spec                 | Flows                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `find-jobs.spec.ts`  | First page of jobs, keyword search, country filter (Apply and Clear), salary range, paging, empty and error states |
| `job-detail.spec.ts` | The posting, opening a result and going back, job not found                                                        |
| `trends.spec.ts`     | Skill chart and legend, selecting a skill, zooming the chart and resetting it, empty and error states              |

## Run them

From `frontend/`:

```bash
npx playwright install chromium   # once, downloads the test browser
npm run test:e2e
```

The tests start their own dev server on port `3100` (see `playwright.config.ts`) and reuse one that is already running outside CI. In CI, the frontend workflow installs Chromium and runs the same command on every pull request.

Use `npx playwright test e2e/trends.spec.ts` for one file, `--ui` to step through a test, and `--debug` to pause on a failure.

## The API is mocked

Every test answers the page's `/api/v1/...` calls from `mock-api.ts`; no backend or database runs. That makes the tests fast and repeatable, but it limits what they prove.

**What they check:** that each page renders, reacts to filters, paging and clicks, sends the right query to the API (the specs read the recorded requests), and handles an empty or failing response.

**What they do not check:** that the real backend matches the mock. The mocked responses are written by hand. If the backend renames a field, changes a type, drops a value or changes how a filter works, the tests keep passing and the page can break.

Ways to reduce that risk:

- When an endpoint changes, update `mock-api.ts` in the same pull request, using the backend's response schemas (`backend/app/schemas/`) as the source.
- When a change touches both the frontend and the backend, also try the page against the real API: run the backend and the frontend, set `NEXT_PUBLIC_API_URL` to the backend, and use the page by hand.
- The mock only returns what a test needs. A field the page does not read is not checked at all.

There is no automated test against the real backend yet. A contract check (comparing the mock with the backend's OpenAPI schema) or a run against a seeded test backend would close this gap.

## How the mock works

`mockApi(page, options)` registers one handler for `**/api/v1/**` and returns `{ listRequests }`, the query string of each job search.

- Jobs: 23 generated jobs. Odd numbers are "Perception Engineer N", even numbers are "Planning Engineer N"; jobs 1 to 15 are in the United States and the rest in Germany. The handler filters by `q` and `country` and pages by `page` and `page_size`, so a test sees realistic results.
- Options: `jobsStatus` makes the job list fail, `detail: null` makes the job detail a 404, `trends` and `trendsStatus` replace the trends response.
- Anything not mocked returns a 404, so a page that calls a new endpoint fails loudly instead of quietly passing.

## Writing a test

1. Call `mockApi(page)` before `page.goto(...)`.
2. Wait for the data to show before you click or type. The pages fetch in the browser, so once the list is visible the page has hydrated; acting earlier can be silently dropped.
3. Prefer roles and accessible names (`getByRole`, `getByLabel`) over CSS selectors. Match buttons with `exact: true` where a short name could also match another control (for example "Next" and the Next.js dev tools button).
4. Assert on the request when the behaviour is "sends X to the API", for example `expect(listRequests.at(-1)?.get("country")).toBe("Germany")`.

## Things to know

- The dev server only accepts `localhost` as the browser's host. `127.0.0.1` makes Next block its own scripts and the page never hydrates, so `baseURL` uses `localhost`.
- A failing run leaves `test-results/` and `playwright-report/` in `frontend/`. Both are ignored by git.
