**Autonomous Vehicle Job Profiles**

*Facilitator Meeting Minutes --- Sprint 2, Week 4*

  ------------------------------------------------------------------------
  **Date**           12th August 2026
  ------------------ -----------------------------------------------------
  **Time**           12:30 -- 12:50

  **Chair**          Martin Dang

  **Minute-taker**   Harshil Prafulbhai Ratanpara, Weishan LI

  **Attendees**      Martin Dang, Weishan Li, Nimit Sureshbhai Gelani,
                     Harshil Prafulbhai Ratanpara, Celine Xu, Sumayyah
                     Ahmad (Facilitator)
  ------------------------------------------------------------------------

# **1. Purpose**

-   Routine Sprint 2 progress meeting with facilitator Sumayyah Ahmad to
    review individual progress, client-communication status, hand over
    the Project Manager role, and plan Sprint 2 tasks.

# 2. **Individual Task Progress**

-   Martin --- Backend setup and data scraping.

    -   Built the backend codebase following a three-layer architecture,
        with CORS configuration and a logging function to flag
        suspicious activity.

    -   Scraped Waymo job data via its public API and used an LLM to
        categorise job descriptions (role profile, skills, functional
        area).

    -   Blocker 1: high LLM cost at scale --- e.g. \~362 jobs for one
        company alone, multiplied across all companies in Adrian\'s
        list.

    -   Blocker 2: category/taxonomy overlap --- a single job can span
        multiple categories (e.g. ML and Computer Vision, or NLP), which
        is not yet resolved.

-   Weishan --- Frontend development.

    -   Designed page styles and built the homepage, job search page,
        and company list page using Next.js, TypeScript, and Tailwind
        CSS, with reusable components (job card, dropdown).

    -   Pages currently run on mock data; next step is connecting to
        real scraped data, pending client feedback on the design.

-   Harshil --- API-based data scraping for 2--3 companies, using
    different recruitment APIs (Lever, Greenhouse, SmartRecruiters).

    -   Retrieves job ID, title, location, and description as JSON;
        scraper reruns before each meeting.

    -   Main challenge: incomplete/null fields in the returned JSON,
        requiring data cleaning and filtering for jobs relevant to the
        AV project.

-   Celine --- Report creation and project documentation/management.

    -   Sprint 1 tasks FE0 (frontend codebase setup) and DOC4 (problem
        statement) completed; also contributed to the Deliverable 1
        draft, consolidating materials and distinguishing implemented
        work, mock data, and pending work.

    -   No major personal blockers; next step is updating report
        contributions pending team/client feedback, then moving to
        Sprint 2 tasks.

-   Nimit --- Frontend development, collaborating with Weishan.

    -   Built the job detail page (title, description, requirements,
        salary, similar jobs, link to original posting) and the company
        profile page (name, location, size, description, open positions,
        link to careers page).

# **3. Client Communication (Adrian)**

-   A meeting request (proposed for Monday) and a follow-up reminder
    were sent to Adrian; no response received yet.

-   A further alternative date was proposed for a demo meeting to show
    the MVP; still awaiting confirmation.

-   Sumayyah advised the team to follow up again, noting two reminders
    have already been sent, and to escalate if there is no response by
    Thursday.

-   The team agreed to keep working on current tasks in the meantime so
    progress is not blocked.

# **4. Project Manager Handover & Sprint 2 Planning**

-   Weishan was proposed and agreed as Project Manager for Sprint 2,
    responsible for scheduling group meetings, assigning a minute-taker,
    and dividing tasks among members.

-   Main focus this week is the Sprint 2 report; Martin has already
    prepared part of the supporting code.

-   The new task set covers both backend and frontend work, as
    previously discussed in the retrospective.

-   Martin has created GitHub issues for the new tasks; members are to
    review the descriptions and indicate their preferences so tasks can
    be assigned and issue statuses updated to "in progress."

# **5. Questions and Discussion**

-   No outstanding questions or concerns were raised by the team.

-   Any remaining issues will be addressed in future meetings.

# **6. Action Items**

  --------------------------------------------------------------------------
  **Owner**   **Action**                                  **Timeline**
  ----------- ------------------------------------------- ------------------
  All members Read GitHub issue descriptions and indicate Before task
              task preferences                            assignment

  Martin      Assign Sprint 2 tasks and update issue      After preferences
              statuses to "in progress"                   are collected

  All members Continue current assigned tasks             Ongoing

  Weishan     Follow up with Adrian on the demo meeting;  Ongoing
              escalate if no response by Thursday         

  All members Work on the Sprint 2 report                 This week

  Weishan     As new PM: schedule next meeting, assign    Ongoing
              minute-taker, divide tasks                  

  Team        Send meeting link and agenda one day before 1 day before next
              the next facilitator meeting                meeting
  --------------------------------------------------------------------------

# **7. Next Meeting**

-   No group meeting next week.

-   Next facilitator meeting scheduled for the following week, same
    time.

-   Meeting link and agenda to be circulated one day in advance.
