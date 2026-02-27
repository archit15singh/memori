#!/usr/bin/env python3
"""Parse criterion JSON output into a README-ready markdown table.

Usage:
    python3 scripts/bench-table.py [target/criterion]

Reads target/criterion/<group>/<bench>/new/estimates.json and formats
mean latencies into markdown tables with auto-unit selection.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def format_duration(ns: float) -> str:
    """Format nanoseconds with auto-unit selection."""
    if ns < 1_000:
        return f"{ns:.0f} ns"
    elif ns < 1_000_000:
        return f"{ns / 1_000:.1f} us"
    elif ns < 1_000_000_000:
        return f"{ns / 1_000_000:.2f} ms"
    else:
        return f"{ns / 1_000_000_000:.2f} s"


def find_estimates(base_dir: Path) -> dict[str, dict[str, float]]:
    """Walk criterion output and extract mean point estimates.

    Returns: {group_name: {bench_name: mean_ns}}
    """
    results = defaultdict(dict)

    for estimates_file in base_dir.rglob("new/estimates.json"):
        parts = estimates_file.relative_to(base_dir).parts
        # Typical path: group/bench_name/new/estimates.json
        # or: bench_name/new/estimates.json
        if len(parts) >= 3:
            group = parts[0]
            bench = parts[1]
        else:
            continue

        try:
            data = json.loads(estimates_file.read_text())
            mean_ns = data["mean"]["point_estimate"]
            results[group][bench] = mean_ns
        except (KeyError, json.JSONDecodeError):
            continue

    return dict(results)


def render_table(results: dict[str, dict[str, float]]) -> str:
    """Render results as markdown tables grouped by benchmark group."""
    lines = []

    # Separate scale-based benchmarks from single benchmarks
    scale_groups = {}
    single_groups = {}

    for group, benches in sorted(results.items()):
        # Check if benches have numeric names (scale parameters)
        has_scale = any(name.replace("_", "").isdigit() or name.isdigit() for name in benches)
        if has_scale:
            scale_groups[group] = benches
        else:
            single_groups[group] = benches

    # Scale-based table: operation x scale
    if scale_groups:
        # Collect all scales
        all_scales = sorted(
            {name for benches in scale_groups.values() for name in benches},
            key=lambda x: int(x.replace("_", "")) if x.replace("_", "").isdigit() else 0,
        )

        scale_headers = [f"{int(s.replace('_', '')):,}" if s.replace("_", "").isdigit() else s for s in all_scales]

        lines.append("| Operation | " + " | ".join(scale_headers) + " |")
        lines.append("|" + "---|" * (len(all_scales) + 1))

        for group in sorted(scale_groups):
            benches = scale_groups[group]
            cells = []
            for scale in all_scales:
                if scale in benches:
                    cells.append(format_duration(benches[scale]))
                else:
                    cells.append("-")
            lines.append(f"| {group} | " + " | ".join(cells) + " |")

        lines.append("")

    # Single benchmarks table
    if single_groups:
        lines.append("| Operation | Latency |")
        lines.append("|---|---|")

        for group in sorted(single_groups):
            for bench, ns in sorted(single_groups[group].items()):
                label = f"{group}/{bench}" if len(single_groups[group]) > 1 else group
                lines.append(f"| {label} | {format_duration(ns)} |")

        lines.append("")

    return "\n".join(lines)


def main():
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("target/criterion")

    if not base.exists():
        print(f"Error: {base} not found. Run `cargo bench` first.", file=sys.stderr)
        sys.exit(1)

    results = find_estimates(base)
    if not results:
        print(f"Error: no estimates.json found under {base}", file=sys.stderr)
        sys.exit(1)

    print(render_table(results))


if __name__ == "__main__":
    main()
