# Sprint 1 Retrospective — Meeting Minutes

| | |
|---|---|
| **Meeting** | Sprint 1 Retrospective — Autonomous Vehicle Job Profiles |
| **Date** | 10 August 2026 |
| **Time** | 6:28 AM |
| **Duration** | 22 minutes 9 seconds |
| **Attendees** | Martin Dang, Weishan Li, Nimit Sureshbhai Gelani, Celine Xu |
| **Prepared by** | Martin Dang |

## 1. Purpose

Weishan demonstrated the current GUI prototype (landing page, job search, company search, job/company detail pages, and category taxonomy view) so the team could review progress and agree on next steps for Sprint 2.

## 2. GUI Walkthrough

- Landing page: title banner with search bar, 8 job categories, latest jobs (with salary and country), featured jobs, list of AV companies, and a call-to-action section. Nav bar is currently a placeholder pending client feedback on whether login/sign-up is needed.
- Job search page: instant search/filtering (e.g. by "control"), search state reflected in the URL so results can be shared via link, and a clear-filters button.
- Company search page: separate from job search; adjustable results-per-page, category filters (e.g. OEM, tech giants); footer not yet complete.
- Company detail and job detail pages: accessible via hyperlinks from categories/listings; job detail shows salary, country, and requirements.
- Category/taxonomy tab: only a placeholder so far — not functional yet.
- All data shown in the prototype is mock data; the frontend is not yet connected to the scraper/backend.

## 3. Discussion & Decisions

- **Salary display**: source data (from the company list Adrian provided) generally gives a single salary figure rather than a min–max range, so the team will show an average/estimated salary instead of a min–max range.
- **Landing page visuals**: add a mock dashboard/trend chart section to the landing page to make it more visually engaging than a plain job list — agreed as a mock-up only, not live data for now.
- **Skill-trend search tab** (requested by Adrian): not yet built; Weishan will build it next using mock data.
- **Country field**: should become a dropdown menu instead of free text.
- **Company logos**: add real logos in a later development phase to make listings look legitimate and reduce confusion with copycat/scam company names; companies already have unique IDs to distinguish them.
- **Company size**: not all companies publicly disclose size. Team will show it where it can be reliably scraped or AI-estimated, and hide it otherwise.
- **Nav bar**: current center placement doesn't work well. Team leaning toward moving remaining items (Find Jobs, Companies, AV Job Finder) to the top-left/top-right, and either moving login/sign-up to the right or removing it entirely if authentication isn't implemented, relying instead on landing-page links.
- **Category taxonomy**: 8 categories currently in place, but overlapping/ambiguous roles (e.g. Machine Learning, Computer Vision, MLOps) raised concerns about consistent classification. Team will raise this with Adrian, who has previously indicated a preference for an AI-generated taxonomy over a predefined one, since predefining categories risks missing valid ones.
- **Scraping scope**: at an estimated ~452 companies (some, like Waymo, with 200+ listed roles), full-scale scraping may produce too much volume for the requirements matrix. Team will ask Adrian whether scope can be narrowed (e.g. technical roles only) given he has indicated wanting all job types included.

## 4. Action Items

- **Weishan** — message Adrian via Teams (not email) today to request a meeting on the web page and web-extraction/taxonomy strategy.
- **Weishan** — confirm with Adrian whether he received the Terms of Agreement document sent earlier by email; resend via Teams if not.
- **Martin** — post a Teams reminder about updating the sprint report; report writing to be prioritised ahead of the Tuesday deadline.
- **Martin** — create tasks on GitHub and share with the team by Wednesday.
- **All** — review GitHub tasks before Wednesday and come prepared to pick a task at the next meeting (Thursday).
- **Next sprint** — begin UI updates based on Adrian's feedback and start scaling the scraper into a pipeline.
- **Wednesday facilitator/team meeting** — each member to demo progress on their task (screen share, or slides if there's no GUI output yet).

## 5. Next Meeting

Team check-in scheduled for Wednesday (task allocation), with a further meeting Thursday. A meeting with Adrian will be scheduled pending his availability (possibly Friday).
