---
name: install
description: Install this Lorevell 2.0 checkout and verify its vault-first CLI in an isolated environment.
---

# Install Lorevell

Follow the current source-build instructions in README.md and docs/install.md. Use an isolated Python environment and verify that its `lorevell --version` reports 2.0.0. Registry packages may still describe 1.x until a release is published.

Exercise add, search and show against a disposable Markdown vault; use `--text-only` when verifying without model downloads. Inspect actual failures before continuing. Keep existing personal databases untouched. Install project-local Claude/Codex skills through the explicit `lorevell setup` command only within the requested setup scope. Report the interpreter, executable path, version and checks actually completed.
