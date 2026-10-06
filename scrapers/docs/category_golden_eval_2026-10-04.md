# Category golden-set evaluation — 2026-10-04

Run for DOC-15 QA section (accuracy). The repo does
not otherwise store a result for this script, so this is a one-off capture.

## Run

```
python -m scrapers.utils.eval_category_golden --repeats 1
```

- Model: `openai/gpt-oss-20b` (from `scrapers/.env`'s `GROQ_MODEL`).
- Prompt/taxonomy version: commit `df50400`, PR #129 "Feature/martin/fix
  false categorizing pipeline" (last change to `job_enrichment.txt` and
  `categories_definition.txt`)
- `--repeats 1` only, due to sustained Groq TPM rate limiting during this
  session; the consistency metric (`--repeats 3`+) was not obtained.

## Result

```
accuracy 87/106 = 82.07%; consistent across 1 run(s): 106/106
```

(The consistency figure is trivial at `--repeats 1` — it only compares the
run against itself. A real consistency measurement needs `--repeats 3`+.)

## Misclassified jobs (19/106)

```
WRONG  42dot | System Framework Engineer: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  Applied Intuition | Senior Software Engineer - Operating Systems: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  Applied Intuition | Software Engineer - Middleware: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  General Motors | Software Engineer, AV Frameworks – Early Career: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  General Motors | Software Manager, AV Platform OS and Drivers: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  Mobileye | Embedded Linux OS Architect: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  NVIDIA | Engineering Manager, DRIVE OS Communication Infrastructure: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  Plus AI | Software Engineer, Runtime & C++ Middleware: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  Torc Robotics | Software Engineer, II - Operating System: expected Vehicle Interface, got [('Infrastructure',)]
WRONG  Mobileye | Experienced Formal Verification Engineer: expected Infrastructure, got [()]
WRONG  Mobileye | Experienced Physical Design Engineer: expected Infrastructure, got [()]
WRONG  TIER IV | 1022_Senior Machine Learning Engineer, (自動運転End to Endモデル): expected Planning, got [('Infrastructure',)]
WRONG  May Mobility | Lead Machine Learning Engineer: expected Planning, got [()]
WRONG  Applied Intuition | Research Engineer - 3D Vision and Generation, Self-Driving: expected Perception, got [()]
WRONG  Tensor (AutoX) | Routing Service Software Engineer: expected Mapping, got [('Planning',)]
WRONG  General Motors | Staff Research Scientist - VLM / VLA: expected Prediction, got [('Perception',)]
WRONG  Zoox | Senior/Staff Software Engineer - Ride and Fleet Services: expected NONE, got [('Infrastructure',)]
WRONG  Tensor (AutoX) | Vehicle Passive Safety Certification Engineer: expected NONE, got [('System and Safety',)]
WRONG  Wayve | Operational Safety Manager: expected NONE, got [('System and Safety',)]
```

## Known systematic error

9 of the 19 misses are on-vehicle OS/middleware/driver roles (42dot,
Applied Intuition ×2, General Motors ×2, Mobileye, NVIDIA, Plus AI, Torc)
classified as Infrastructure instead of Vehicle Interface. Checked against
the full job descriptions in `category_golden.json`: all nine describe
vehicle OS, IPC/middleware, BSP, kernel, or embedded driver work, matching
`categories_definition.txt`'s own placement rule ("Vehicle OS, middleware,
IPC/messaging, BSP, kernel, bootchain, device drivers, firmware... are
Vehicle Interface, not Infrastructure") almost verbatim — the golden-set
labels are correct; the model is following title-level lexical cues (e.g.
NVIDIA's title literally contains the word "Infrastructure") over that
rule. Not yet fixed in the prompt.
