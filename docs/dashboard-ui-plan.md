# Dashboard UI improvement plan

Status: proposed implementation plan; this document does not implement UI changes.

## Context and evidence

The dashboard should help a person find, read, and explore stored memories quickly.
The current dark palette and consistent type colors provide a useful foundation,
but secondary text is hard to read, content previews are short, and the fixed
layout gives analytics permanent space while memory details compete with results.

The initial review inspected the list and expanded detail in Brave using an
isolated database of 24 synthetic memories at commit `82e6b05`. Source inspection
covered the HTML and Python HTTP handler. Mobile behavior, offline behavior,
request races, and injection paths were identified from source, not exercised in
that browser review. The plan was reconciled against `b000664`, which includes
PRs #4 and #5. Search now catches request errors and exposes a minimum semantic
similarity control; those existing improvements must be preserved.

Primary implementation surfaces:

- [Dashboard HTML, styles, and JavaScript](../memori-python/python/memori_cli/data/dashboard.html)
- [Dashboard HTTP handler](../memori-python/python/memori_cli/__init__.py)
- [Python integration tests](../memori-python/tests/)
- [Relevance semantics](relevance.md)

## Scope and constraints

Include safe rendering, resilient loading, keyboard access, readable content,
responsive layout, clearer search behavior, and graceful optional visualizations.
Keep the dashboard read-only and preserve `get_readonly()` access-stat semantics.
Do not change the database schema, ranking algorithm, CLI defaults, or introduce
editing, deletion, accounts, hosted services, or a frontend framework.

Keep the packaged single-file dashboard unless a demonstrated maintenance need
justifies splitting assets. Do not add a runtime build pipeline. A small browser
test dependency is acceptable only if it provides meaningful behavioral coverage
and is documented and runnable in CI. Use synthetic data for screenshots/tests.

Applicable implementation skills: `make-interfaces-feel-better` for interface
review and details, `frontend-design` for layout work, and `testing` for regression
coverage. Use the repository's documented Rust and Python conventions.

## Design direction and alternatives

Recommended desktop layout: search and filters above a compact results list,
with a detail pane alongside it when a record is selected. Analytics should be
collapsible and secondary. On narrow screens, show results or details in one
column with an explicit return action and preserved search/filter state.

Alternatives considered:

| Approach | Tradeoff | Decision |
| --- | --- | --- |
| Keep bottom detail panel and adjust styles | Smallest change, but retains competing vertical scroll areas | Useful fallback, not the preferred desktop layout |
| Results with an adjacent detail pane | Supports comparing and reading memories without losing list position | Recommended; validate at normal and narrow widths |
| Move to a frontend framework | More tooling and packaging complexity for a small read-only surface | Defer |

The layout recommendation is a proposal to validate during implementation, not a
claim that a user-tested design has been approved. Keep existing type colors and
dark mode. Prefer content over identifiers; show full IDs in details with a copy
action. Explain technical search controls in plain language while preserving the
raw cosine range, blank default, and literal-match behavior documented in
[relevance.md](relevance.md). Do not present ranking scores as probabilities.

## Delivery sequence

Deliver small, independently reviewable changes in the order below. Each phase
should normally touch the dashboard and its focused tests; add API or documentation
changes only when required. No phase requires a schema migration.

### 1. Render stored values safely

**Goal:** stored text and metadata cannot become executable markup.

**Changes:** replace unescaped type-legend values, data attributes, and metadata
labels with text-safe DOM construction or context-appropriate escaping. Audit all
remaining HTML insertion sites, including related memories and graph tooltips.

**State:** existing memory and metadata shapes remain unchanged.

**Verification:** review all dynamic HTML sinks; test type names and metadata keys
containing quotes and markup. In a browser, confirm those values display literally,
execute no script, and still support filtering and detail selection.

### 2. Make optional visualizations independent

**Goal:** unavailable chart libraries never break browsing or type filtering.

**Changes:** guard Chart.js, its date adapter, and D3 at their use sites. Render the
text type legend independently of the donut. Keep graph failure local to the graph
and provide an honest unavailable state instead of an empty container.

**State:** track capability availability separately from memory/API state.

**Verification:** block CDN requests before reload and confirm the list, details,
filters, and legend remain usable. Check missing adapter separately from missing
Chart.js and D3. Confirm charts and graph still render when dependencies load.

### 3. Make requests and selection resilient

**Goal:** the latest user intent determines displayed results and details.

**Changes:** add request cancellation or generation guards for list/search/detail
loads; give loading, empty, failure, and retry distinct states. Preserve the search
error handling added by PR #5. Clear stale related/graph content when selection
changes and prevent late requests from reopening closed panels.

**State:** request identity, current query/filter snapshot, selected memory ID,
and per-surface loading/error state; avoid introducing a global state library.

**Verification:** use controlled response delays to race two searches and two
selections; close a detail while it loads; simulate API failures and retry. Verify
that stale responses do not overwrite newer content or remain stuck loading.

### 4. Establish keyboard and screen-reader access

**Goal:** all essential browsing actions work without a pointer.

**Changes:** give cards and type filters semantic keyboard-operable controls,
visible focus, and selected-state semantics. Label search, sort, and date fields;
announce result/loading/error changes without excessive chatter. Provide Escape
and focus return for details; keep graph exploration available through the
accessible related-memory list. Aim for at least 40px control hit areas.

**State:** focused/selected item identity and the detail return target.

**Verification:** complete search, filtering, pagination, selection, related-memory
navigation, and closing with keyboard alone. Inspect accessible names and focus
order; verify status announcements with a screen reader. Confirm no focus traps.

### 5. Improve readability and result scanning

**Goal:** memory content is easier to evaluate before opening a record.

**Changes:** lead cards with content, permit two or three preview lines, reduce
UUID emphasis, and raise secondary-text contrast. Use readable metadata sizes,
tabular numbers for changing counts, and clear focus/hover/selected differences.
Avoid broad transitions and respect reduced-motion preferences.

**State:** existing memory data; no new backend fields.

**Verification:** measure normal-text contrast against a 4.5:1 target; capture
screenshots with long prose, code, long tokens, missing metadata, and many types.
At 200% zoom, essential content and controls must remain readable and reachable.

### 6. Introduce responsive results and details

**Goal:** provide a useful reading layout across desktop and narrow screens.

**Changes:** implement the recommended desktop detail pane, collapsible analytics,
and wrapping/collapsible filters. Replace the hard-coded viewport subtraction with
layout sizing that accounts for actual toolbar height. On narrow screens, provide
one-column navigation and preserve list position when returning from details.

**State:** analytics visibility and list/detail presentation; keep query, filters,
selection, and scroll position consistent across layout changes.

**Verification:** capture list, selected detail, and filter states at 1440px, 1024px,
768px, and 390px widths. Check 200% zoom, long IDs, and long metadata. Require no
clipped essential controls or unintended horizontal page scroll. Confirm that
opening details and graphs cannot collapse the results area into unusable space.

### 7. Clarify search, filters, and pagination

**Goal:** controls accurately communicate what retrieval is doing.

**Changes:** label search as relevance ordered, disable the browse sort during
search, and label capped results as “Top 10 results” when the cap is reached.
Keep the existing top-10 behavior for this iteration; defer exhaustive search
pagination. Add clear/reset filters, visible date labels, invalid-range feedback,
and an explanation of minimum semantic similarity. Document whether dates use UTC
or local days and make inputs, request bounds, and displayed explanation agree.

**State:** explicit browse/search mode and active filter values, derived from the
current input rather than the completion of an earlier request.

**Verification:** cover blank search, zero results, more than 10 matches, threshold
validation/recovery, literal matches below a semantic floor, and filter resets.
Check date boundaries and reversed ranges. Verify browse pagination at 0, 20,
and 21 records; avoid an enabled Next action leading to a known empty page.

### 8. Explain analytics and finish integrated verification

**Goal:** analytics add context without implying complete coverage or hiding errors.

**Changes:** label global statistics separately from filtered results. Disclose
that the timeline covers at most the newest 500 memories and label its axes.
Show graph loading, empty, and failure states; explain node selection and provide
a textual alternative. Update README and CLAUDE.md to describe delivered behavior,
with before/after screenshots attached to implementation PRs.

**State:** existing counts and chart data; add total/filter scope labels only as
needed. Any new API count field must have endpoint coverage.

**Verification:** exercise empty, populated, and over-500-record databases and
unavailable related-memory data. Confirm graph resize/close behavior and no new
access-count changes from browsing. Run the complete verification gate below.

## Verification and completion gate

For each implementation phase, inspect the diff, run focused behavioral regression
tests, and visually verify affected states. Do not substitute tests of HTML string
contents for actual interaction, layout, race, or accessibility checks. If browser
automation is introduced, document its setup and include it in CI; otherwise retain
a reproducible manual browser checklist with screenshots and recorded results.

For the completed implementation, build the native extension from that checkout
and ensure its CLI is first on PATH, following [install.md](install.md). Run:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test -p memori-ai-core --release
# In the activated source-build virtual environment:
(cd memori-python && maturin develop --release)
pytest memori-python/tests -v
```

Run any added browser checks as documented by the implementing PR. Verify online
and blocked-CDN operation, keyboard access, narrow layouts, failure/retry, stale
responses, literal rendering of stored markup, and unchanged read-only semantics.
The plan is complete when it is merged; UI work is complete only when these
acceptance checks pass and the implementation documentation reflects shipped
behavior. This docs-only PR requires link/diff checks, not a claim of passing
runtime verification for future changes.
