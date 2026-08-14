# [DOC-7] Project Management: Methodology, Plan & Responsibilities

## 1. Methodology

We're running this project as Agile/Scrum with 2-week sprints. Each sprint starts Monday and ends the
following-following Sunday (14 days), and covers a fixed batch of tasks pulled from the Guideline document
(the DOC-x / FE-x / BE-x numbering). If something doesn't get finished in a sprint, it rolls into the next
one instead of just getting forgotten.

We picked this over a longer/looser cycle for a few reasons:

- We're only 5 people, so we don't need heavy process — but we do need regular checkpoints so nobody's work
  drifts off in a direction the rest of the team didn't agree on.
- There's a client demo (with Adrian) coming up mid-project, and 2-week sprints give us a couple of natural
  points to show progress and course-correct before that meeting, instead of finding out too late that we
  built the wrong thing.
- The work splits naturally into a few tracks — survey/research, ERD/data modelling, frontend, backend/
  scraping — and a sprint board is an easy way to keep those tracks visible to everyone without needing
  constant status-update messages.
- Sprint 1 is basically done (currently at 91%), which is a decent sign that 2 weeks is a reasonable chunk
  size for how we're splitting tasks — most people are handling ~3 story points per sprint comfortably.

## 2. Plan for the Next Stage
Sprint 1 (28 Jul – 10 Aug) is nearly wrapped — DOC-1 through DOC-6, plus FE-0, BE-0, FE-1 and BE-1 are all
done. The one thing still stuck is the Adrian demo meeting, which is blocked until we get a date confirmed.

Sprint 2 (11 – 24 Aug) is the next stage and is already scoped out:

| Task | Assigned To | Effort | Status | Due |
|---|---|---|---|---|
| [BE-2] Create job search and filter API | — | 1 | Not Started | 7-Aug |
| [DOC-7] Define project management and plans | Nimit, Martin | 1.5 | In Progress | 14-Aug |
| [DOC-8] Risk and technology statements | Celine | 1.5 | In Progress | 14-Aug |
| [DOC-9] Client communication and MVP agreement | Harshil | 1.5 | In Progress | 14-Aug |
| [DOC-10] Problem statement (revision) | Weishan | 1.5 | In Progress | 14-Aug |
| [FE-4] Update platform navbar position | — | 1 | Not Started | 18-Aug |
| [FE-5] Update job trend chart on main page | — | 1 | Not Started | 19-Aug |
| [BE-3] Refactor scraper structure | — | 1 | Not Started | 20-Aug |

After that, the Gantt chart blocks out Sprints 3–7 (25 Aug – 2 Nov) at 14 days each for the rest of the MVP
build — frontend pages, backend/pipeline work, review passes. We haven't broken those down task-by-task yet;
we're planning to scope each one properly at the start of that sprint rather than guess too far ahead now.

## 3. Team Members and Responsibilities

| Member | Sprint 1 Role(s) | Sprint 2 Role(s) |
|---|---|---|
| Martin | Project Manager, Backend Developer | *TBC* |
| Nimit | Business Analyst, Frontend Developer | *TBC* |
| Harshil | Business Analyst, Frontend Developer | *TBC* |
| Celine | Business Analyst, Frontend Developer | *TBC* |
| Weishan | UI/UX Designer, Frontend Developer | Project Manager |

Roles rotate each sprint — Weishan's taken over as PM for Sprint 2. We still need to fill in the other four
members' Sprint 2 roles in the tracker.

## 4. Ownership

Every task has one clear owner (or two, when it's shared), a due date and a status, tracked in the shared
sprint sheet and linked to its GitHub issue — not just something agreed verbally in a call. Here's Sprint 1
as an example of how that's tracked:

| Task | Assigned To | Status | Due Date | Issue |
|---|---|---|---|---|
| [DOC-1] Requirement Verification & Domain Research | Martin, Nimit, Harshil | Done | 3-Aug | [#5](https://github.com/husthunterpy01/Autonomous_Vehicle_Job_Profiles_Group3/issues/5) |
| [DOC-2] Task Splitting & Planning | Martin | Done | 2-Aug | [#6](https://github.com/husthunterpy01/Autonomous_Vehicle_Job_Profiles_Group3/issues/6) |
| [DOC-3] Create ERD for Job Categorizing | Weishan | Done | 31-Jul | [#7](https://github.com/husthunterpy01/Autonomous_Vehicle_Job_Profiles_Group3/issues/7) |
| [FE-0] Frontend Codebase Setup | Celine | Done | 3-Aug | — |
| [DOC-4] Problem statement | Celine | Done | 3-Aug | — |
| [DOC-5] Identify user requirements | Martin | Done | 2-Aug | — |
| [DOC-6] Identify non-functional requirements | Martin | Done | 2-Aug | — |
| [BE-0] Backend Codebase Setup | Martin | Done | 7-Aug | — |
| [FE-1] Create landing page for the system | Nimit, Weishan | Done | 8-Aug | — |
| [BE-1] Scrape job profiles sources | Martin, Harshil | Done | 8-Aug | — |
| Host meeting with Adrian for MVP demo | Nimit, Weishan, Martin | Blocked | 11-Aug | — |

The Adrian meeting is the one open risk right now — it's blocked on getting a date confirmed, so we're
tracking it rather than letting it quietly slip.

## 5. Planning and Tracking Tools

We use two tools together:

1. **GitHub Issues** — one issue per task (DOC-x / FE-x / BE-x), used for discussion, acceptance criteria,
   and linking to the PR that closes it. Every row in the sprint sheet links to its issue.
2. **Sprint Task Tracker** — a shared spreadsheet
   ([AV_Job_Profiles_Sprint_Overview_Gantt.xlsx](https://uniwa.sharepoint.com/:x:/r/teams/CITS5206-InformationTechnologyCapstoneProjectSEM-22026-Group3/_layouts/15/doc2.aspx?action=edit&sourcedoc=%7Bd29fd1a1-0b96-4863-aa68-0d047071dcf3%7D&wdExp=TEAMS-TREATMENT&web=1),
   also checked into the repo at `document/plan/AV_Job_Profiles_Sprint_Overview_Gantt.xlsx`)
   with three tabs:
   - *Sprint Task Tracker*: task, assignee, effort (story points), status, due date, issue link, plus charts
     of effort by sprint and by member.
   - *Member Roles by Sprint*: who's playing what role each sprint.
   - *Sprint Gantt Chart*: sprint start/end dates, 14-day durations, and % complete (pulled automatically
     from task status).

*(TODO — Martin: attach screenshots of the three tabs above as evidence, either embedded here or attached
directly to issue #36.)*


