# Project Plan — Autonomous Vehicle Job Profiles (Group 3)

**Project:** Autonomous Vehicle Job Profiles
**Client:** Dr Adrian Boeing, Lee Le
**Facilitator:** Sumayyah Ahmad
**Team:** Martin Dang, Nimit Sureshbhai Gelani, Harshil Prafulbhai Ratanpara, Celine Xu, Weishan Li

This document sets out how the team plans and manages its work: the way tasks are organised into two-week sprints, the tools used to track progress, the schedule for the seven sprints that make up the project, and who is responsible for what at each stage. It is the GitHub-hosted companion to Section 5 (Project Plan and Team Management) of the D1 report.

---

## 1. Development Methodology

This project is conducted using the Agile-Scrum method, following a two-week sprint schedule. Each sprint normally starts on Monday and ends on the Sunday of the following week. Work not completed in a sprint is rolled into the next sprint or reallocated to another member, rather than being treated as tech debt.

This cadence was adopted over a longer sprint cycle for several reasons:

- With a team of five, heavy process overhead is unnecessary; however, regular checkpoints remain important to ensure individual contributions stay aligned with the team's shared direction and do not diverge unnoticed.
- The client demonstration is scheduled for mid-project. A two-week sprint provides natural checkpoints to demonstrate progress and adjust course beforehand, keeping the team's output aligned with client needs rather than drifting toward internally driven priorities.
- The work splits naturally into a few tracks — researching, prototyping, and production — and a sprint board is an easy way to keep those tracks visible to everyone without needing constant status-update messages.
- The team's experience in Sprint 1 supports this cadence: most members are comfortably managing approximately three story points per sprint, indicating a two-week cycle is a suitable unit of work for the team's current task breakdown.

**Tools used to track the plan:**

- **GitHub Issues** — task declarations
- **GitHub Project** — task tracking (Kanban board)
- **Shared Excel Sprint Tracker (Teams)** — visualised progress, tracking members and effort per sprint
- **Milestones** — aligned with project deliverables after each sprint
- **Pull Requests** — peer-reviewed to ensure code quality
- **CITS5206 – Information Technology Capstone Project Group 3 channel** — main communication channel for the team

---

## 2. Sprint Plan

This sprint structure was formally agreed by the whole team and the client at the first client meeting. Standard Scrum ceremonies — Sprint Planning, Weekly Standup, Sprint Review, and Retrospective — are held each sprint to maintain alignment and allow early client feedback.

Sprints are grouped into three broad tracks reflecting the project's overall progression — research, prototyping, and production — with each sprint's purpose building on the work completed before it. Each sprint comprises a development phase followed by a review & update phase, checked against the Sprint Tracker.

| Sprint | Start Date | End Date | Duration | What We'll Do |
|---|---|---|---|---|
| **Sprint 1: Kickoff & Requirements** | 27 Jul 2026 | 09 Aug 2026 | 14 days | Hold the project kickoff and first client discussion; investigate requirements and start initial scraping; build a simple feedback UI and prepare a frontend demo; hold the sprint review to update requirements and the backlog. |
| **Sprint 2: Core Build** | 10 Aug 2026 | 18 Aug 2026 | 9 days | Build the landing page, search/filter UI, and API to requirements; hold the sprint review and finalise/submit Deliverable 1. |
| **Sprint 3: Scraper Expansion & Data Modeling** | 19 Aug 2026 | 08 Sep 2026 | 21 days | Expand the scraper beyond the Sprint 1 prototype to more companies and refine the data model for classification; hold the sprint review to update the scraper and data model. |
| **Sprint 4: Data Pipeline** | 09 Sep 2026 | 22 Sep 2026 | 14 days | Scale the scraper to all companies and build the classification pipeline and trend charts; hold the sprint review to update the pipeline and data model. |
| **Sprint 5: Feature Finalization** | 23 Sep 2026 | 29 Sep 2026 | 7 days | Finalise software features; hold the sprint review and submit Deliverable 2. |
| **Sprint 6: Demo Prep** | 30 Sep 2026 | 06 Oct 2026 | 7 days | Record and edit the product demo; hold the sprint review and submit the Deliverable 3 demo video. |
| **Sprint 7: Final Delivery** | 07 Oct 2026 | 13 Oct 2026 | 7 days | Complete production deployment and draft the final report; hold the sprint review, submit the Final Report, and present the showcase. |
| **Wrap-up** | 14 Oct 2026 | 16 Oct 2026 | 3 days | Apply post-showcase fixes and finalise documentation; hold the retrospective and submit peer feedback. |

The client demo falls within the early-to-mid stage of this schedule, giving the team at least one full sprint review cycle to incorporate feedback before the milestone.

*(See Figure 6, Sprint Schedule Gantt Chart, in the D1 report for the visualised timeline.)*

---

## 3. Project Management Tools

The team's workflow and task allocation are tracked using:

- **GitHub Projects board** — columns Backlog, Ready, In progress, In review, and Done, showing how individual tasks move through the sprint lifecycle and how work is currently distributed across the team.
- **Sprint Task Tracker spreadsheet** — records who each task is assigned to, its estimated effort, status, and due date, with a link back to the corresponding GitHub issue for traceability.

Together, these two artefacts provide evidence that the team's workflow and deadlines are actively documented and maintained, rather than planned only at a high level.

*(See Figures 4 and 5 in the D1 report for screenshots of the board and tracker.)*

---

## 4. Team Roles and Responsibilities by Sprint

Roles are assigned per sprint and rotated as the project progresses, allowing members to build experience across functional areas while ensuring coverage across research, prototyping, and production tracks.

Sprint 1 entries below are the completed tasks recorded in the team's Sprint Tracker. Project Manager rotation is confirmed through Sprint 6. Tasks for Sprint 2 onward reflect each member's planned focus for that sprint's goal and will be finalised at each Sprint Planning session; a Project Manager for Sprint 7 and Wrap-up has not yet been assigned. From Sprint 5 onward, Celine moves into a dedicated testing role, verifying the platform ahead of each milestone rather than continuing feature development.

| Sprint | Martin | Nimit | Harshil | Celine | Weishan |
|---|---|---|---|---|---|
| **Sprint 1: Kickoff & Requirements**<br>(27 Jul – 09 Aug) | PM. Requirement verification & domain research; task splitting & planning; identified user & non-functional requirements; codebase setup; scraped job sources with Harshil | Requirement verification & domain research; built the landing page with Weishan | Requirement verification & domain research; scraped job profile sources with Martin | Codebase setup; drafted the problem statement | Created the ERD for job categorisation; built the landing page with Nimit |
| **Sprint 2: Core Build**<br>(10 – 18 Aug) | Built the job search and filter API and updated the scraper codebase | Updated landing page and search/filter UI build-out | Supported search/filter API build-out; updated the API document to support Martin | Created trend chart for AV jobs | PM. Coordinated the sprint toward Deliverable 1; page layout/UX for the search & filter UI |
| **Sprint 3: Scraper Expansion & Data Modeling**<br>(19 Aug – 08 Sep) | Refined the data model for classification | Verified additional company sources; supported updates for expanded data | PM. Coordinated scraper expansion to more companies | Updated UI to reflect the refined data model | Supported data-model refinement and category definitions |
| **Sprint 4: Data Pipeline**<br>(09 – 22 Sep) | PM. Coordinated scaling the scraper to all companies; built the classification pipeline | Supported classification-pipeline requirements; integration of trend charts | Scaled the scraper across the full company list | Updated page UI navbar components | Supported trend-chart design and data visualisation |
| **Sprint 5: Feature Finalization**<br>(23 – 29 Sep) | Finalised API and data features for Deliverable 2 | Finalised requirements coverage; supported feature testing | Finalised scraper/classification features | Tested the finalised features for Deliverable 2 and logged any issues found | PM. Coordinated the sprint toward Deliverable 2 submission |
| **Sprint 6: Demo Prep**<br>(30 Sep – 06 Oct) | Supported the demo script with technical accuracy checks | Supported demo content and requirements walkthrough | PM. Coordinated recording and editing the product demo video | Tested the platform ahead of the demo recording and flagged issues for fixing | Supported demo visuals and presentation design |
| **Sprint 7: Final Delivery**<br>(07 – 13 Oct) | PM. Completes production deployment | Supports final report drafting and requirements sign-off | Supports production deployment and final testing | Tested the final build ahead of showcase and confirmed outstanding issues were resolved | Supports final report drafting and showcase presentation |
| **Wrap-up**<br>(14 – 16 Oct) | Team-wide: apply post-showcase fixes, finalise documentation, attend the retrospective, and submit individual peer feedback | *(same, team-wide)* | *(same, team-wide)* | *(same, team-wide)* | *(same, team-wide)* |

---

## 5. Meeting Schedule

In addition to ad-hoc client meetings, the team follows a fixed weekly meeting rhythm to keep track of each member's progress and stay responsive to the client's needs as they arise. This gives every stakeholder — teammates, the facilitator, and the client — a predictable point of contact throughout the sprint, so blockers surface early and progress updates don't wait until the next formal review meeting.

| Day | Meeting | Details |
|---|---|---|
| Monday | Retrospective session | The team reviews the previous week's progress, blockers, and any process improvements. |
| Monday–Wednesday (as needed) | Client progress report | An update is sent to Adrian Boeing and Lee Le on whichever day that week's progress is ready to report. |
| Wednesday | Facilitator meeting | The team meets with the facilitator to report on the project's progress and get suggestions on organisation practice. |
| Thursday | Internal team meeting | A stand-up covering sprint task progress and blockers among all members. |

**Note:** Client meetings with Adrian Boeing and Lee Le beyond the weekly progress report are scheduled as needed rather than on a fixed day. The team reports progress to the client weekly, typically on Monday, so they can track what has been developed and what still needs improvement.

---

*This plan is maintained alongside the GitHub Projects board and Sprint Tracker referenced above. For the full project specification — including the problem statement, requirements, client communication record, and risk/technology assessment — see the D1 report (Deliverable 1).*
