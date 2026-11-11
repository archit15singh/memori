# Memori 2.0 UX prototype

Throwaway, offline design study on `prototype/memori-2-ux`. No production dashboard changes, network requests, real vault access, or agent launches. All six notes are synthetic. Reload resets state. Clipboard access occurs only after clicking Copy Markdown.

Open directly:

```sh
open -a 'Brave Browser' "$PWD/artifacts/memori-2-prototype/index.html"
```

Compare `?variant=Library`, `?variant=Focus`, and `?variant=Garden` using the floating arrows. Library places results beside the note; Focus stacks a narrow recall workspace; Garden offers a connection-oriented card collection. Arrow keys switch layouts outside controls; Cmd/Ctrl+K focuses recall. The chosen layout survives reload through the URL; other state does not.

## Review question

Which arrangement makes it easiest to find a previous lesson, understand its context, and return to work? No layout winner has been validated yet. Duolingo informs clear next actions and bounded feedback; Obsidian informs file ownership, backlinks and local navigation. The source research is in [the UX research note](../../docs/memori-2-ux-research.md).

## Try it

1. Search `git`: one result. Follow “Make the failing test tell the story”; the query stays in place and the selected note changes.
2. Filter by Decisions or search an absent word. Clear the empty state.
3. Switch among all three layouts; the query and selection remain.
4. Open Dream → Preview a dream → inspect the diff and unresolved contradiction → Apply simulated merge → Undo demo changes. This is a review-state simulation; it does not mutate the sample note collection or Git.
5. Open Setup → Simulate external edit → Reindex demo → Try a recall.
6. Reload to reset. Open a variant URL directly to restore that layout.

## Verification recorded 2026-11-12

- Inline JavaScript passes Node syntax compilation.
- In Brave, verified `git` filters six notes to one, linked navigation changes note content while preserving query, and layout switches update the URL to Focus and Garden.
- Visually inspected Focus at desktop size.
- In Brave, verified dream preview, diff, conflict preservation, simulated apply and undo; setup stale-index and reindex states; and return to recall.
- Responsive CSS collapses columns below 720px. Narrow-screen visual inspection, screen-reader testing and clipboard behavior remain unverified.
- Search is local AND text matching, explicitly labeled; hybrid retrieval is not implemented in this UI study.
- No Rust/Python runtime changes, so native suites were not run for this artifact.
