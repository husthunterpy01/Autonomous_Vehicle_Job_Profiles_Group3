# Client Meeting Minutes Summary — Frontend Review & LLM Classification

**Project:** Autonomous Vehicle Job Profiles
**Attendees:** Martin, Weishan, Harshil, Lee Le
**Absent:** Adrian Boeing, Nimit, Celine (Lee to brief Adrian)

## Frontend Demo & Feedback (Lee)
- Weishan demoed the frontend (built with Nimit).
- **Find Jobs page:** switch to a table-style layout showing job title, relevant/required skills, key requirements.
- **Skill names:** keep recognised technical names as-is (e.g. C, C++) — don't generalise them.
- **Search:** strengthen skill-based search over broad category search.
- **Categories:** make job categories more specific rather than relying on a broad hierarchy.

## LLM Classification & Cost
- Scalability concern: some companies post 300+ jobs — sending everything to an LLM isn't practical.
- Team to investigate free/low-cost LLM options; description text confirmed as a key input for classification/skill extraction.
- Open question for Adrian: is there a project budget for paid LLM/API usage, or should the team stay within free-tier limits?

## Proposed Filtering Pipeline (before LLM)
1. Scrape all jobs
2. Initial filtering pass
3. Remove clearly non-AV/irrelevant roles
4. Send only AV-relevant jobs to the LLM
5. LLM does detailed classification

Goal: cut unnecessary LLM calls, processing time, tokens, and cost.

## Key Decisions
- Investigate table-style job search results
- Improve visibility of skills/requirements in results
- Preserve technical skill names (C, C++, etc.)
- Strengthen skill-based search
- Make categories/job profiles more specific
- Filter irrelevant jobs before LLM classification
- Investigate free vs. paid LLM options
- Ask Adrian about LLM budget/subscription
- Lee to relay outcomes to Adrian

## Action Items

| Action | Owner | Status |
|---|---|---|
| Table-style layout for Find Jobs | Frontend team | To investigate |
| Improve skills/requirements visibility | Frontend team | To investigate |
| Improve skill-based search/filtering | Frontend team | To investigate |
| Refine job-profile categories | Classification team | Pending |
| Pre-filter non-AV jobs before LLM | Backend/Classification team | Pending |
| Investigate free vs. paid LLM options | Team | Pending |
| Confirm LLM budget with Adrian | Client communication owner | Pending |
| Share outcomes with Adrian | Lee Le | Pending |

## Next Steps
Review Lee's frontend feedback, work out a scalable classification pipeline (filtering before LLM), and confirm with Adrian whether budget exists for a paid LLM service.
