# Memori 2.0: UI, UX and customer experience research

Date: 2026-11-12. Status: design proposal, not an approved implementation plan.

## Recommendation

Use the agent and CLI as the everyday interface, Obsidian or another editor for authoring, and a small local web companion for search, inspection and consolidation review. Default to search, not analytics or a global graph. Do not rebuild an editor or chat engine.

## First-party evidence

- [Duolingo home redesign](https://blog.duolingo.com/new-duolingo-home-screen-design/): guided next steps, smaller units and integrated practice. Transfer: a clear first-use sequence and bounded maintenance tasks. A fixed learning path is not appropriate for arbitrary knowledge retrieval.
- [Duolingo quality metric](https://blog.duolingo.com/time-spent-learning-well/): raw session counts and XP can reward activity poorly aligned with learning. Transfer: measure successful recall and retained meaning, not note volume or app visits.
- [Obsidian storage](https://obsidian.md/help/data-storage): Markdown files remain editable in other applications; metadata is cached. Transfer: make ownership visible and distinguish file state from search-index state.
- [Quick switcher](https://obsidian.md/help/plugins/quick-switcher): keyboard navigation by name or alias. Transfer: fast title lookup alongside semantic recall.
- [Backlinks](https://obsidian.md/help/plugins/backlinks), [local graph](https://obsidian.md/help/plugins/graph), [page preview](https://obsidian.md/help/plugins/page-preview): navigation with local context. Transfer: linked-note lists and previews before a visual graph.
- [File recovery](https://obsidian.md/help/plugins/file-recovery): snapshots are useful but not a complete backup. Transfer: visible Git history and tested, narrowly scoped recovery; do not advertise Git alone as backup.

Research followed primary product pages into specific interaction and recovery documentation. These are documented product mechanisms, not evidence that they will improve Memori outcomes; validate the transfer with users.

## Proposed surfaces

1. Recall: one search field, compact results, note detail, links/backlinks and file path. Label explicit links separately from semantic similarity. Preserve query and list position when navigating. Provide empty, unavailable and indexing states; no confidence percentages derived from ranking scores.
2. Care: a bounded dream run with selected scope and limits, actual execution state, changed-file diff, unresolved contradictions and a Git commit reference. Archives retain source meaning. Reverting must preserve later unrelated edits. No new scheduler or workflow engine.
3. Setup: choose folder, connect supported agent skill, index, save a real note, then retrieve it in a new session. Explain that headless execution uses the selected provider and may send note content outside the machine.

## Visual direction

Quiet, readable Markdown typography, restrained accent color, clear focus indicators, keyboard-accessible linked context, reduced-motion support and responsive list/detail navigation. A small optional dream illustration can add warmth without occupying search space.

## Minimum validation

Test finding a known procedure, recovering from a missed result, following a backlink, indexing an external edit, inspecting a contradictory consolidation and recovering from an unwanted merge. Suggested targets, not measured results: first useful recall within five minutes; known-note discovery within thirty seconds. Use a small held-out query set for before/after dream comparisons and inspect preserved meaning separately. No automatic session recording or telemetry is required.

## Repository implications

The current dashboard contains search, charts, timeline and graph surfaces. The existing docs/dashboard-ui-plan.md already recommends adjacent result/detail panes and secondary analytics. Memori 2.0 should retain those usability improvements while moving analytics out of the default path. This proposal changes no product code.
