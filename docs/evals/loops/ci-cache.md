# Measured CI dependency-cache loop

Four workflow lines add the same pinned dependency-cache action to the existing Rust and Python CI jobs. No tests, test commands or source gates are skipped. The action is pinned at `d1527c8f67ef9af357290475d4af4b0fab8f12e0`.

The first experimental run exposed a test-launch PATH assumption already corrected in PR #15; that failed run is excluded from performance claims. Its newly created experiment-only cache was removed before the controlled run. The measured run is **43109822635**, exact source head **1b10145c722d5372a5c2fabec710afc6c403163c**, with cold **attempt 1** and warm **attempt 2**. Both jobs passed on both attempts. Logs confirm cache misses in both cold jobs and exact cache hits/restoration in both warm jobs.

| Job | Cold | Warm | Reduction |
| --- | ---: | ---: | ---: |
| Rust fmt/Clippy/tests | 254s | 71s | 72.0% |
| Python build/tests | 220s | 69s | 68.6% |
| Combined job time | 474s | 140s | 70.5% |

Job durations include cache restore/save and test execution but exclude runner queue time. Python native build changed 196→37s; Rust release tests changed 156→14s, Clippy 58→24s. Workspace source still compiles; the cache retains reusable dependencies. [Structured timings and unchanged checks](ci-cache-timings.json).

The operational gate requires successful unchanged checks, verified cache hits, at least 20% lower combined job time and neither job more than 10% slower. This pair passes. It is one cold/warm pair, not statistical evidence or a guaranteed future speedup; toolchain/dependency changes and cache eviction can cause cold runs. Cache contents are disposable and the four-line change is reversible.

Authoritative runs: [cold](https://github.com/archit15singh/lorevell/actions/runs/43109822635/attempts/1), [warm](https://github.com/archit15singh/lorevell/actions/runs/43109822635/attempts/2). Action behavior: [upstream documentation](https://github.com/Swatinem/rust-cache).
