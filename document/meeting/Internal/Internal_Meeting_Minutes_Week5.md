# Internal Team Meeting Minutes

**Project:** Autonomous Vehicle Job Profiles (Project 3)
**Date:** Thursday, 20 August 2026
**Duration:** ~10 minutes
**Attendees:** Martin Dang, Weishan Li, Nimit Sureshbhai Gelani, Harshil Prafulbhai Ratanpara
**Absent:** Celine Xu
**Minutes taken from:** Meeting recording/transcript

---

## 1. Recap: Meeting with Lee (End User)

Martin summarised the previous day's discussion with end-user Lee for Nimit, who had missed the recording.

**Requested changes from Lee:**
- Ability to search by job category.
- Add a table-format view for job listings, alongside the existing card format, since some users prefer tables.

**Scraping volume/cost:**
- Lee said the team should estimate the scraping price/volume first so Martin can report it to Adrian, who may sponsor the cost.

**Taxonomy scope:**
- Lee confirmed the taxonomy should focus on autonomous-vehicle roles only; non-AV job categories (e.g. accountants, economists) should be removed from the list.

**MVP sign-off:**
- Lee wants to sign off on the MVP but doesn't have the authority; he will ask Adrian to approve, expected by Friday.
- Team asked to stay alert on Friday (particularly around 3pm) and flag immediately if Adrian's response comes through.

## 2. Sprint Tasks (Screen Walkthrough)

- The pass involving the MVP/"hash-user" part has been sent to Martin; he will review it and aim to finish the report by Saturday. Once posted, the team should review it and flag any issues.
- **Main focus this sprint:** fix the frontend first (per Lee's request), alongside continued work on the scripting/scraping part.
- Plan to start loading actual scraped data into the **bronze layer** this sprint; moving data from bronze → silver → frontend will take longer, so that integration may extend beyond this week.

**New tasks (links shared in chat):**
1. Document/summarise the API endpoints for all ~42 companies — each has a different API and response format, so this needs to be consolidated before backend work on the bronze layer.
2. Implement the bronze layer (stores raw/unsanitised scraped data before it's cleaned into the silver layer).
3. Update the job listings table view, per Lee's request.
4. Build a "top scale" view showing which AV job categories are currently most in demand.

Team asked to comment on the task board with which task they'd like to take by end of day today, so Martin can assign tasks tomorrow (Friday).

## 3. Sprint 2 Report Update (Weishan)

Martin asked Weishan to update the Sprint 2 section of the report with:
- **Achievements:** based on assigned targets — e.g. implementing the silver layer, improving categorisation performance.
- **Risks and decisions:** note the client communication delay (Adrian/Lee) as a risk, and record the backup plan — preparing a prototype that doesn't require client approval first.
- Not urgent — to be done when Weishan has time.

## 4. Reminder: LLM-Generated Code Standards

Martin reminded the team that while using LLMs for coding is fine, members must carefully review generated code/data before submitting, since LLMs can produce invalid or "dummy" output that could break the system. Pull requests with code that doesn't follow the team's patterns/conventions will not be approved.

## 5. Open Floor

No further questions raised. Meeting closed; Martin wished the team good luck with any tests they had that day.

---

## Action Items

| # | Action | Owner | Due |
|---|--------|-------|-----|
| 1 | Comment on the task board with preferred task pick | All members | Today (20 Aug 2026) |
| 2 | Assign tasks based on team replies | Martin | Tomorrow (21 Aug 2026) |
| 3 | Finish MVP/report section | Martin | Saturday (22 Aug 2026) |
| 4 | Review finished report once posted | All members | After Martin posts |
| 5 | Document/summarise API endpoints across all ~42 companies | TBC (assigned from task board) | This sprint |
| 6 | Implement bronze layer for raw scraped data | TBC (assigned from task board) | This sprint |
| 7 | Update job listings table view (per Lee's request) | TBC (assigned from task board) | This sprint |
| 8 | Build "top scale" / in-demand AV job categories view | TBC (assigned from task board) | This sprint |
| 9 | Update Sprint 2 report — achievements + risks/decisions (client comms risk, backup prototype plan) | Weishan | When time permits (not urgent) |
| 10 | Monitor for Adrian's MVP approval response (esp. ~3pm Friday) and flag immediately if received | All members | Friday, 21 Aug 2026 |

---

*Next meeting: Not scheduled at time of this meeting.*
