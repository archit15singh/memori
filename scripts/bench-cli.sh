#!/usr/bin/env bash
# Bounded disposable-vault CLI timing. Requires installed Memori 2 and hyperfine.
set -euo pipefail
command -v hyperfine >/dev/null
command -v memori >/dev/null
BENCH_VAULT=$(mktemp -d "${TMPDIR:-/tmp}/memori-cli-bench.XXXXXX")
export BENCH_VAULT
trap 'rm -rf "$BENCH_VAULT"' EXIT
python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ['BENCH_VAULT'])
for i in range(100):
    (root / f'note-{i}.md').write_text(f'---\nid: note-{i}\ntype: procedure\n---\n# Database procedure {i}\nUse transactions for atomic cache updates.\n')
PY
memori --vault "$BENCH_VAULT" index >/dev/null
hyperfine --warmup 1 --runs 5 \
    "memori --vault '$BENCH_VAULT' search 'cache' --text-only --json" \
    "memori --vault '$BENCH_VAULT' search 'cache' --json" \
    "memori --vault '$BENCH_VAULT' show note-0 --json"
