# Data quality sample check (30 postings)

Spot check of the live Supabase data against the original job pages, run on 4 Oct 2026 for the final report (Quality Assurance). It checks the collection and field-accuracy expectations in Deliverable 1 (NFR-01).

## Method

- **Sample:** 30 postings drawn at random (seed 5206) from the 1,229 in the live database, spread round-robin across 12 source platforms. The database was read through a read-only session; nothing was changed.
- **Collection:** a posting counts as collected when its stored source URL opens that posting.
- **Fields:** each stored value was compared with the page: job title, company, location, employment type, salary and category. A field is only scored when the page states it. Skills were not scored, and seniority is empty for every posting (see below).
- **Who checked:** the pages were checked by an AI assistant (Claude) and have not yet been independently re-checked by a team member. Category is a judgement call and the doubtful cases are marked in the notes. *Update this line after a team member re-checks a few postings.*

## Results

| Measure | Correct | Checked | Rate |
|---|---|---|---|
| Source link opens the posting | 20 | 29 | 69% |
| Job title | 19 | 20 | 95% |
| Company | 20 | 20 | 100% |
| Location | 12 | 18 | 67% |
| Employment type | 15 | 15 | 100% |
| Salary | 7 | 9 | 78% |
| Category | 17 | 18 | 94% |

Link failures (9 of 29 checked): 4 postings have no stored source URL, 3 were removed by the employer, and 2 link to a company job list instead of the posting. One further posting (NVIDIA, Workday) did not load during the check and is not counted.

## Findings

1. **Missing source URL.** 293 of 1,229 postings (about 24%) have no `source_url`, mostly Ashby (142), Greenhouse (87) and Lever (31).
2. **Source URL does not point to the posting.** Some links open a company job list (Avride, Wayve) or a raw API response (AutoBrains).
3. **Location.** Postings with several offices store only the first one (Tensor, Waabi); parsing leftovers remain, such as `Gothenburg +1 more` and a `Location:` prefix (AImotive).
4. **Salary.** Two postings state a range on the page (Waabi) but only the currency and period are stored.
5. **Title.** One stored title differs from the page (Einride).
6. **Seniority.** `seniority_level` is empty for all 1,229 postings, although seniority is an extracted field in Deliverable 1 (FR-04).

These are tracked in the open issues listed in the final report.

## Postings checked

Key: ✓ correct, ✗ wrong, missing = stated on the page but not stored, – = not scored. Link = the source URL opens this posting.

| # | Company | Job title | Platform | Link | Title | Co. | Location | Empl. | Salary | Cat. | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ADASTEC | Autonomous Driving Software Engineer (Machine... | adastec | ✓ | ✓ | ✓ | ✓ | – | – | ✓ | LinkedIn page; employment and salary not shown. |
| 2 | AImotive | Embedded SW Engineer (QNX & Linux) | aimotive | ✓ | ✓ | ✓ | ✗ | – | – | ✓ | Location stored with the label prefix: "Location: Budapest, Hungary". |
| 3 | Applied Intuition | Robotic Software Engineer, Perception | ashby | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| 4 | AutoBrains | Embedded Software Engineer | comeet | ✗ | – | – | – | – | – | – | Source URL is an API endpoint (careers-api) that now returns 404, not a readable posting page. |
| 5 | Einride | Senior Calibration Engineer | einride | ✓ | ✓ | ✓ | ✗ | ✓ | – | ✓ | Location stored as "Gothenburg +1 more"; page says Gothenburg or Stockholm. |
| 6 | Avride | Senior C++ Software Engineer – Simulation Inf... | greenhouse | ✗ | – | – | – | – | – | – | Source URL is the company job list, not this posting. Salary period stored without any amount. |
| 7 | Zoox | Senior Systems Engineer, Fail Operational Cap... | lever | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| 8 | Momenta | Autonomous Driving Decision & Planning R&D In... | personio | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ |  |
| 9 | Tensor / AutoX | System Engineer - Motion Control | tensor | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | Page lists San Jose, Singapore, Dubai, Barcelona; only San Jose stored. Salary is the company-wide range. |
| 10 | Tier IV | 1406_Test Platform Engineer, System Verificat... | tier_iv | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ |  |
| 11 | Pony.ai | Software Engineer, Behavior | workable | ✓ | ✓ | ✓ | – | – | ✓ | ✓ | Location and employment type not visible in the page text. |
| 12 | GM | Senior Software, AV Platform Core Test | workday | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ | Salary not visible in the part of the page checked. |
| 13 | ADASTEC | Sr. Autonomous Driving Software Engineer (Loc... | adastec | ✓ | ✓ | ✓ | ✓ | – | – | ✓ | LinkedIn page. |
| 14 | AImotive | AI Research Engineer - aiDrive | aimotive | ✗ | – | – | – | – | – | – | Page returns 404 (posting removed). Stored location has the "Location:" prefix. |
| 15 | Applied Intuition | Software Engineer (SDS Hardware-in-the-Loop) | ashby | ✗ | – | – | – | – | – | – | No source URL stored. |
| 16 | AutoBrains | Planner Stack Engineer | comeet | ✓ | ✓ | ✓ | ✓ | – | – | ✓ | Source URL is a JSON API response, not a readable page. |
| 17 | Einride | Compute Integration Engineer | einride | ✗ | – | – | – | – | – | – | No source URL stored. |
| 18 | Torc Robotics | Senior, Machine Learning Engineer - 3D Percep... | greenhouse | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| 19 | Waabi | Research Engineer, World Models | lever | ✓ | ✓ | ✓ | ✗ | ✓ | missing | ✗ | Page lists Toronto, San Francisco, Pittsburgh and remote; only Toronto stored. Page states $155,000-$269,000 but no amount stored. Category System and Safety looks wrong for a world-models research role (my judgement). |
| 20 | Tensor / AutoX | Perception Engineer: Recognition of Road Weat... | tensor | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | Four locations on the page; only San Jose stored. |
| 21 | Tier IV | 1320_Systems Engineer (Safety & ODD), Autonom... | tier_iv | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ |  |
| 22 | Pony.ai | Research Intern - Deep Learning | workable | ✓ | ✓ | ✓ | – | ✓ | – | – | Category Planning is arguable for a deep-learning research internship; not scored. |
| 23 | NVIDIA | Senior Software Engineer, Context Fusion and ... | workday | – | – | – | – | – | – | – | Workday page did not load in the check; not verified. |
| 24 | AImotive | Compiler Engineer Intern | aimotive | ✗ | – | – | – | – | – | – | No source URL stored. |
| 25 | 42dot | Machine Learning & Data Engineer, Vehicle Mod... | ashby | ✗ | – | – | – | – | – | – | Ashby shows "Job not found" (posting removed). |
| 26 | AutoBrains | Senior DevOps Engineer - Solo Role (Site Only) | comeet | ✗ | – | – | – | – | – | – | No source URL stored. |
| 27 | Einride | Perception Engineer — Autonomy with dual-use ... | einride | ✓ | ✗ | ✓ | ✓ | ✓ | – | – | Page title is "Machine Learning Engineer - Autonomy with dual-use application"; stored title is "Perception Engineer - ...". |
| 28 | Wayve | Staff / Senior Machine Learning Engineer, Rei... | greenhouse | ✗ | – | – | – | – | – | – | Source URL opens the Wayve job list ("0 jobs open"), not this posting. |
| 29 | Waabi | Physical Infrastructure Engineer (On-premise) | lever | ✓ | ✓ | ✓ | ✓ | ✓ | missing | ✓ | Page states $125,000-$190,000 but no amount stored. |
| 30 | Tensor / AutoX | Vehicle Integration Engineer: C++ Software De... | tensor | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | Four locations on the page; only San Jose stored. Salary is the company-wide range. |

## Limits

- 30 postings is a small sample, and the round-robin draw gives small platforms more weight than their share of the data.
- The sample includes postings that employers have since removed. That reflects the state of the data but is not always a collection error.
- Salary, employment type and location are only scored where the page shows them, so the denominators differ.
