#!/usr/bin/env bash
# CLI-level benchmark timing using hyperfine.
# Measures full Python startup + PyO3 FFI + Rust core round-trip.
#
# Prerequisites:
#   brew install hyperfine
#   cd memori-python && maturin develop --release
#
# Usage:
#   bash scripts/bench-cli.sh

set -euo pipefail

DB="/tmp/memori-bench-cli.db"
SEED_COUNT=10000

command -v hyperfine >/dev/null 2>&1 || { echo "Error: hyperfine not found. Install with: brew install hyperfine"; exit 1; }
command -v memori >/dev/null 2>&1 || { echo "Error: memori CLI not found. Install with: cd memori-python && uv tool install --from . memori"; exit 1; }

echo "=== Memori CLI Benchmarks ==="
echo "Seeding $SEED_COUNT memories into $DB..."

# Seed by generating JSONL and importing
SEED_FILE="/tmp/memori-bench-seed.jsonl"
python3 -c "
import json, uuid, random, time
random.seed(42)
words = ['algorithm', 'binary', 'cache', 'database', 'embedding', 'function',
         'graph', 'hashmap', 'index', 'json', 'kernel', 'lambda', 'memory',
         'network', 'optimizer', 'parser', 'query', 'runtime', 'schema', 'thread',
         'vector', 'webhook', 'async', 'batch', 'cluster', 'pipeline', 'kafka',
         'sqlite', 'postgres', 'redis', 'kubernetes', 'docker', 'rust', 'python']
types = ['debugging', 'decision', 'architecture', 'preference', 'fact', 'pattern']
base_ts = 1700000000.0
for i in range($SEED_COUNT):
    content = ' '.join(random.choices(words, k=random.randint(50, 150)))
    meta = {'type': random.choice(types), 'topic': random.choice(words)}
    ts = base_ts + i
    record = {
        'id': str(uuid.uuid4()),
        'content': content,
        'metadata': meta,
        'created_at': ts,
        'updated_at': ts,
        'last_accessed': 0.0,
        'access_count': 0,
    }
    print(json.dumps(record))
" > "$SEED_FILE"

rm -f "$DB"
memori --db "$DB" import < "$SEED_FILE"
echo "Seeded $(memori --db "$DB" count) memories."
echo ""

echo "--- Running hyperfine benchmarks ---"
echo ""

hyperfine \
    --warmup 3 \
    --min-runs 10 \
    --export-markdown /tmp/memori-bench-cli-results.md \
    "memori --db $DB count" \
    "memori --db $DB search --text 'database query optimization' --text-only --limit 10 --raw" \
    "memori --db $DB search --text 'database query optimization' --limit 10 --raw" \
    "memori --db $DB list --limit 20 --raw" \
    "memori --db $DB stats --raw"

echo ""
echo "Results saved to /tmp/memori-bench-cli-results.md"
echo ""
cat /tmp/memori-bench-cli-results.md

# Cleanup
rm -f "$DB" "$SEED_FILE"
