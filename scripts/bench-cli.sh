#!/usr/bin/env bash
# Bounded disposable-vault CLI timing. Requires installed Lorevell 2 and hyperfine.
set -euo pipefail
command -v hyperfine >/dev/null
command -v lorevell >/dev/null
BENCH_VAULT=$(mktemp -d "${TMPDIR:-/tmp}/lorevell-cli-bench.XXXXXX")
export BENCH_VAULT
trap 'rm -rf "$BENCH_VAULT"' EXIT
python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ['BENCH_VAULT'])
for i in range(100):
    (root / f'note-{i}.md').write_text(f'---\nid: note-{i}\ntype: procedure\n---\n# Database procedure {i}\nUse transactions for atomic cache updates.\n')
PY
lorevell --vault "$BENCH_VAULT" index >/dev/null
hyperfine --warmup 1 --runs 5 \
    "lorevell --vault '$BENCH_VAULT' search 'cache' --text-only --json" \
    "lorevell --vault '$BENCH_VAULT' search 'cache' --json" \
    "lorevell --vault '$BENCH_VAULT' show note-0 --json"
