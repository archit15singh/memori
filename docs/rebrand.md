# Memori → Lorevell

**Local knowledge for humans and agents. Plain Markdown. Yours to keep.**

The rebrand separates this project from MemoriLabs/Memori. Lorevell leads with readable, portable knowledge that people control; coding agents provide reasoning and consolidation. It welcomes personal knowledge users, coding-agent users and developers without adding new product capabilities.

| Interface | Previous | Current |
| --- | --- | --- |
| GitHub | archit15singh/memori | archit15singh/lorevell |
| Command | `memori` | `lorevell` |
| Python distribution | `py-memori` | `lorevell` |
| Python import | `memori`, `memori_cli` | `lorevell`, `lorevell_cli` |
| Low-level binding | `PyMemori` | `PyLorevell` |
| Rust package/import | `memori-ai-core` / `memori_core` | `lorevell-core` / `lorevell_core` |
| Source directories | `memori-core`, `memori-python` | `lorevell-core`, `lorevell-python` |
| Vault environment | `MEMORI_VAULT` | `LOREVELL_VAULT` |
| Local cache | `.memori/` | `.lorevell/` |
| Installed skills | `memori`, `memori-dream` | `lorevell`, `lorevell-dream` |

## Existing vaults

Markdown format and stable IDs are unchanged. Point `lorevell --vault <directory> index` at an existing vault to rebuild its cache. `lorevell init` adds the new cache ignore rule. Keep the old `.memori/` ignored; there is no need to delete it. If preserving incremental dream progress, copy `.memori/dream-state.json` to `.lorevell/dream-state.json` before the first dream run; otherwise the first run considers the active notes again.

Run `lorevell setup --agent codex` or `lorevell setup --agent claude` to install the renamed skills. Remove old project-local Memori skills after reviewing any customizations; setup does not delete them. No compatibility command/import aliases, automatic vault migration or package publication is included. Existing GitHub clones may use redirects; update the remote URL explicitly to `https://github.com/archit15singh/lorevell.git` when convenient.

## Naming research

The user selected Lorevell after an interview about audience, ownership, inspectability, naming style and rename scope. Preliminary public checks found no exact Lorevell package on PyPI/crates.io and no matching GitHub repository names at selection time. This is discovery screening, not a trademark or domain-ownership claim. No domain was purchased.

Sources: [existing Memori product](https://github.com/MemoriLabs/Memori), [nearby Markdown memory positioning](https://agentcairn.dev/). Historical evaluation fixtures, observed runs and earlier plans retain the original Memori identity rather than relabeling past evidence.

## Rebrand verification

Under the Lorevell identity: Rust release suite 94 passed; no-embedding vault/relevance/freshness suite 24 passed; Python suite 87 passed; formatting, Clippy and shared-skill equality/validation passed. A clean wheel-only installation verified `lorevell 2.0.0`, native imports, `LOREVELL_VAULT`, indexing/search of byte-unchanged pre-rebrand Markdown fixtures, add, both agent skill installations, dream dry-run and `.lorevell/` cache creation. The real authenticated agent evidence remains in the historical 2.0 verification report; this rename does not claim a new live agent experiment.

The renamed low-level binding also opened a disposable SQLite database created by the original Memori binding and retrieved its original record, confirming that product renaming did not rename internal SQL tables.
