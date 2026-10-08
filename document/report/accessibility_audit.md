# Accessibility audit of the frontend (issue #162)

Date: 8 October 2026. Target: WCAG 2.1 level AA. Scope: the public pages of the frontend.

## Method

- Ran axe-core 4.10.2 (rule sets WCAG 2.0 A/AA and 2.1 A/AA) in a browser against the
  frontend running locally on the live API data.
- Pages: home, Find Jobs, Companies, a job detail page, Market Trends, Log in, Sign up and About.
- Checked keyboard use by hand: the first Tab stop, the skip link, and the focus outline.
- Checked reflow (WCAG 1.4.10) by loading each page in a 320 px, 375 px and 640 px wide frame and looking for
  horizontal page scroll. 640 px is a 1280 px window at 200% zoom; 320 px is the WCAG reflow width.
- Checked colour contrast by hand where axe disagreed with the computed styles (see "False positive").

## Findings and what was done

| # | Finding | WCAG | Status |
|---|---|---|---|
| 1 | Muted text (`--color-ink-muted`, #94a3b8) has a contrast of 2.4 to 2.6:1 on the page, white and card backgrounds, on every page. 4.5:1 is required. | 1.4.3 | Fixed: token changed to #5f6f86 (4.6 to 5.1:1). |
| 2 | Secondary text (`--color-ink-secondary`, #64748b) is 4.4:1 on the grey tag background, just under 4.5:1 (skill and category tags on the job page). | 1.4.3 | Fixed: token changed to #475569. |
| 3 | The green "open" status text (#10b981) is 2.2:1 on its light green background. | 1.4.3 | Fixed: text colour changed to emerald-700. |
| 4 | The page-size box on Companies has no label. | 1.3.1, 4.1.2 | Fixed: `aria-label="Companies per page"`. |
| 5 | Nine pages share one title ("Autonomous Vehicle Job Finder"), so tabs and history entries look the same. | 2.4.2 | Fixed: each page now has its own title (for example "Find Jobs \| AV Job Finder"). The home page keeps the site title. |
| 6 | No way to skip the navigation bar with the keyboard. | 2.4.1 | Fixed: a "Skip to main content" link appears on the first Tab and moves focus to the page content. |
| 7 | There is no shared focus style. Controls rely on the browser default, and some inputs remove the outline. | 2.4.7 | Partly fixed: a global focus ring (2 px, indigo) for links, buttons, selects and other controls. Text inputs keep the highlighted border of their wrapper; not changed. |
| 8 | At 320 px wide the job detail page scrolled sideways: the title (30 px) and the logo sat in one row, and the longest word did not fit. | 1.4.10 | Fixed: the logo stacks above the title on phones, the title is 24 px below the `sm` breakpoint, and the text box can shrink and break long words. |

After the fixes, axe reports no violations on any audited page, apart from the false positive below, and none of
the eight pages scrolls sideways at 320, 375 or 640 px.
The 82 frontend tests, lint, type check and build still pass.

## False positive

axe reports a contrast of 1.05:1 for the footer links. It reads the link colour as opaque white and the
background as the page background. The footer is dark (#1e293b) and the links are white at 60% opacity, which
is 6.2:1 by calculation; the copyright line (50% white) is 4.8:1. Both pass. The cause is that axe cannot
resolve the semi-transparent colours used by Tailwind 4.

## Not done and limits

- **Not audited:** Favorites and My Account (they need a signed-in user), hover and error states, and the
  dropdown menus.
- **Phone layout** was checked only in a desktop browser at phone widths, not on a real phone. The menu button
  has a label and `aria-expanded`, and is 40 by 40 px. The Find Jobs table scrolls sideways inside its own box
  on a phone, which WCAG allows for data tables; the box itself cannot take keyboard focus, but the links in
  the rows can.
- **No screen reader test.** The Market Trends chart (SVG) has labelled controls but was not tested with
  NVDA or VoiceOver.
- Most pages have no `<main>` landmark (only Account, Sign up and Market Trends do). Adding one needs the
  pages restructured, so it is left for later.
- Text inputs inside a bordered wrapper (search boxes) show focus only through the wrapper border; whether the
  change is large enough was not measured.
- axe finds roughly a third of accessibility problems automatically. This audit is a first pass, not a
  certificate of WCAG conformance.
