# Local recall workspace

The first job is specific: find a past lesson quickly, inspect its source, and reuse it. This direction was confirmed by the project owner. Product-market fit still needs observation with real users; a working interface alone does not establish it.

```text
Question or keyword → ranked notes → source Markdown → copy and reuse
                                      ↕
                              links and backlinks

New note → ordinary Markdown file → the same rebuildable search index
```

Run `lorevell --vault <directory> ui`. The printed address is local to your computer. `--port 0` selects a free port, and `--no-open` prints the address without opening a browser. The default port is 8765. An occupied port produces an error; choose another port. A new vault can start empty: use New note to save its first lesson.

## Daily use

1. Enter a keyword or question and submit. Keyword search works without model inference. Hybrid combines keywords and semantic similarity, using the existing local embedding model. The first hybrid request can take longer while model files download.
2. Choose a result. The reader shows its source filename, note type, tags and content. Linked notes and derived backlinks are separate from search matches. Connected search context is bounded to three additional notes; the reader shows up to fifty neighbors in each direction.
3. Copy Markdown, copy the absolute source path for your editor, or copy a fenced command block. On a narrow screen, choose a result to enter the reader, then use Notes to return.
4. Save a useful new lesson with a title, body and type. Include its source and verification in the body. Saving writes a Markdown file; it does not create an AI-generated summary. If another malformed file prevents indexing, the response preserves the saved note and reports that indexing needs attention.

Cmd/Ctrl K focuses search. Up/down moves focus between result buttons; Enter opens one. The selected note and query are reflected in the URL, so browser back/forward and reload can recover the view while this server is running. The index refreshes before reads/searches; Refresh also notices file edits and removals.

## Boundaries

- The server uses Python's standard HTTP library, the native `PyVault` API and packaged HTML/CSS/JavaScript. No frontend build, account, hosted service or telemetry is required.
- It listens only on IPv4 loopback, checks Host and Origin, and requires a random per-process token for API requests. Pages have no-store headers and a restrictive content security policy. This protects the browser boundary; it is not authentication against other programs running as your local user. Do not expose it through a public proxy or tunnel.
- Keyword mode makes no model request. Hybrid may download model files; inference is local. External source links open only when selected. Note text and queries are not written to HTTP request logs.
- The reader supports headings, paragraphs, bullets, fenced code, inline code, bold text, HTTP(S) links and resolved wiki links. Raw HTML is displayed as text. It is deliberately a small Markdown reader: tables, embedded images and the complete CommonMark grammar are not rendered. Copy Markdown preserves the note body.
- Browse shows the first 500 notes in source-path order. Search covers the full vault and returns up to 40 ranked matches. There are no confidence percentages. A ranking score is not evidence that a lesson is correct.
- Editing, archiving, consolidation and Git history remain in the CLI or your editor. The UI adds capture alongside recall; it does not become an agent dashboard.

## Verification

`lorevell-python/tests/test_ui.py` exercises a real loopback server and native SQLite retrieval: keyword recall, outgoing/backlinks, type filters, external edits, capture across independent vault instances, save/index failure recovery, malformed-source recovery, request boundaries, packaged static assets and launching the actual CLI on an ephemeral port.

Desktop reading layout was inspected in Brave with a disposable vault of 25 public project notes. Browser automation was unavailable, and a concurrent session was controlling the native browser; interactive copy/search/capture and narrow-screen behavior were not verified in a browser. Those checks remain distinct from the passing HTTP integration coverage.

A separate DOM harness against the live server exercised search, reading, linked navigation, capture, copy actions, no-hit states and literal rendering of raw HTML. Clipboard and dialog APIs were simulated, so this does not establish actual browser clipboard or layout behavior. A live hybrid request for “undo a consolidation” returned the rollback procedure first.
