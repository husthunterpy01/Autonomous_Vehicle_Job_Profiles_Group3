# Meeting Summary — Group 3 IT Capstone Project
**Project:** Autonomous Vehicle Job Profiles
**Client:** Adrian Boeing
**Date:** 27 July 2026

## Overview

The core idea: Adrian wants a tool similar to an AI-jobs search website, but focused on autonomous vehicle (AV) companies. He gave the group a list of roughly 42 self-driving-tech companies to pull job data from.

## Why he wants it

- As an educator, he wants to know what technical skills and tools companies are actually hiring for, so he can shape his course content around real industry demand rather than guessing.
- As a secondary use case, it doubles as a public-facing job search tool — e.g. Lee (the AV PhD "end-user") could search "how many sensor fusion jobs exist right now."

## Proposed workflow

1. Scrape each company's careers page (use whatever scraping tool does 90%+ of the work — don't hand-roll one).
2. Feed job titles/descriptions to an LLM to extract skills and cluster them into job profiles (e.g. hardware engineer → sensing / compute / networking sub-types).
3. Build a data structure (he suggested sketching an ER diagram first) before dumping data into an LLM — unstructured input won't classify cleanly.
4. Map job profiles back onto a typical AV org structure (perception/sensing, fusion, prediction, motion planning/control, V&V, vehicle platform/hardware, cloud/software platform, etc.) — he shared his own former employer's org chart as a reference.
5. Build a searchable front end on top of the resulting dataset.

## Suggested prep reading

- Open-source AV stacks (e.g. **Autoware**) and their architecture diagrams
- Open datasets (e.g. **Waymo**, and others mentioned)
- Visual datasets give a more intuitive feel for the tech than architecture diagrams alone

## Front-end / UI requirements he flagged

- Search by region / country / city
- Search by role
- Search by experience level (must include an "internship" option)
- Salary info — cross-reference **levels.fyi** rather than building a scraper for salary specifically

## Practical / process points

- A small, locally-run LLM is probably sufficient for the text analysis/clustering work — he's open to discussing infra further if the team thinks otherwise.
- Ambiguous job classifications will be resolved through discussion between the team and Adrian — this process will effectively define a "standard" AV org taxonomy.
- Smaller companies will have blended roles; larger companies will be more specialized — worth accounting for in the data model.
- Project should run Agile/Scrum, with 2-week sprints.
- Scope and requirements (with acceptance criteria) should be nailed down early — e.g. "salary" isn't a useful requirement unless you define acceptable granularity, like $50k bands vs. exact figures.
- Adrian is less available day-to-day — Sumayyah is the first point of contact. A Teams channel will be set up for the group.
- Adrian will send: the full company list, the AI-jobs website link, architecture diagram links, dataset links, and the levels.fyi link.
- A parallel group has the same brief but scrapes **off-road** (vs. this group's **on-road**) self-driving company data — worth comparing notes on scraping tools with them.

## Sprint 1 deliverables expected

- Scope of work
- Requirements (with acceptance criteria)
- Project plan
- GUI design mockups