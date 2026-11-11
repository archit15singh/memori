"""Bounded real-vault benchmark. Run identical commands with baseline/candidate Python.

Each size runs in a fresh process and temporary vault. Prefetch model files before
comparing --hybrid runs: an absent cache adds network download time.
No timing threshold is a correctness test; compare raw distributions on one host.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import threading
import time


def rss():
    return int(subprocess.check_output(['ps', '-o', 'rss=', '-p', str(os.getpid())])) * 1024


def peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024


def cpu():
    own = resource.getrusage(resource.RUSAGE_SELF)
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + child.ru_utime + child.ru_stime


def worker(args):
    from lorevell import PyVault
    from lorevell_cli.ui import CompanionServer
    with tempfile.TemporaryDirectory(prefix='lorevell-benchmark-') as directory:
        root = Path(directory)
        for i in range(args.size):
            kind = 'decision' if i % 3 == 0 else 'procedure'
            links = ' '.join(f'[[note-{(i + step) % args.size:05}]]' for step in (1, 7, 19))
            body = f'# Database lesson {i}\n' + ('Use transactions for atomic cache updates and preserve original evidence.\n' * 12)
            if i % 20 == 0:
                body += 'Diagnose quasar failures with a repeatable canary.\n'
            (root / f'note-{i:05}.md').write_text(f'---\nid: note-{i:05}\ntype: {kind}\ntags: [database, testing]\n---\n{body}\n{links}\n')
        result = {'size': args.size, 'samples': args.samples, 'metrics': {}, 'memory': {'import_rss_bytes': rss()}}
        def measure(name, call, count=None):
            values, cpu_values = [], []
            returned = None
            for _ in range(count or args.samples):
                start_cpu, start = cpu(), time.perf_counter()
                returned = call()
                values.append((time.perf_counter() - start) * 1000)
                cpu_values.append((cpu() - start_cpu) * 1000)
            ordered = sorted(values)
            result['metrics'][name] = {'n': len(values), 'wall_ms': values,
                'p50_ms': statistics.median(values), 'p95_ms': ordered[math.ceil(.95 * len(values))-1],
                'cpu_ms': cpu_values, 'ops_per_second': 1000 / statistics.mean(values)}
            print(f"{args.label} n={args.size} {name}: {statistics.median(values):.2f} ms", file=sys.stderr, flush=True)
            return returned
        vault = measure('open_first', lambda: PyVault(str(root)), 1)
        measure('index_initial_keyword', lambda: vault.index(embeddings=False), 1)
        measure('index_unchanged_keyword', lambda: vault.index(embeddings=False))
        measure('list_sources', vault.notes)
        view = measure('show_linked', lambda: vault.show('note-00000', neighbor_limit=5))
        assert len(view['outgoing']) == 3 and len(view['backlinks']) == 3
        plain = measure('search_keyword_no_graph', lambda: vault.search('quasar', limit=5, graph_limit=0, text_only=True))
        graph = measure('search_keyword_graph', lambda: vault.search('quasar', limit=5, graph_limit=3, text_only=True))
        assert [h['note']['id'] for h in plain['matches']] == [h['note']['id'] for h in graph['matches']]
        assert len(graph['context']) <= 3
        result['keyword_ids'] = [h['note']['id'] for h in graph['matches']]
        measure('search_keyword_broad_40', lambda: vault.search('transactions', limit=40, graph_limit=3, text_only=True))
        edited = root / 'note-00000.md'
        edited.write_text(edited.read_text().replace('Diagnose quasar', 'Diagnose supernovaneedle'))
        measure('index_one_edit', lambda: vault.index(embeddings=False), 1)
        assert vault.search('supernovaneedle', limit=1, text_only=True)['matches'][0]['note']['id'] == 'note-00000'
        result['memory']['keyword_rss_bytes'] = rss()
        result['memory']['keyword_peak_bytes'] = peak()
        cli = str(Path(sys.executable).parent / 'lorevell')
        def command(*arguments):
            return subprocess.run([cli, '--vault', str(root), *arguments], capture_output=True, check=True).stdout
        measure('cli_keyword_fresh_process', lambda: command('search', 'quasar', '--limit', '5', '--text-only', '--json'))
        measure('cli_show_fresh_process', lambda: command('show', 'note-00000', '--json'))
        server = CompanionServer(root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(path):
            connection = HTTPConnection('127.0.0.1', server.server_port, timeout=300)
            connection.request('GET', path, headers={'X-Lorevell-Token': server.token})
            response = connection.getresponse()
            data = response.read()
            connection.close()
            assert response.status == 200, data
            return data
        try:
            catalog = measure('http_catalog', lambda: request('/api/catalog'))
            hit = measure('http_search_keyword', lambda: request('/api/search?q=quasar'))
            note = measure('http_note', lambda: request('/api/note?id=note-00000'))
            result['payload_bytes'] = {'catalog': len(catalog), 'search': len(hit), 'note': len(note)}
            def concurrent():
                with ThreadPoolExecutor(max_workers=4) as pool:
                    return list(pool.map(lambda _: request('/api/search?q=quasar'), range(4)))
            measure('http_four_concurrent', concurrent, 1)
            result['http_concurrent_requests_per_second'] = 4000 / result['metrics']['http_four_concurrent']['p50_ms']
            if args.hybrid:
                measure('index_first_hybrid_cached_model', lambda: vault.index(embeddings=True), 1)
                measure('search_hybrid_first_inference', lambda: vault.search('quasar', limit=5, graph_limit=3), 1)
                measure('search_hybrid_warm', lambda: vault.search('quasar', limit=5, graph_limit=3))
                measure('http_search_hybrid_warm', lambda: request('/api/search?q=quasar&mode=hybrid'))
                measure('cli_hybrid_fresh_process', lambda: command('search', 'quasar', '--limit', '5', '--json'))
                result['memory']['hybrid_rss_bytes'] = rss()
                result['memory']['hybrid_peak_bytes'] = peak()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        result['disk_bytes'] = {'markdown': sum(p.stat().st_size for p in root.glob('*.md')),
            'index_and_journal': sum(p.stat().st_size for p in (root / '.lorevell').glob('index.sqlite*'))}
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', default='25,250,1000')
    parser.add_argument('--samples', type=int, default=5)
    parser.add_argument('--hybrid', action='store_true')
    parser.add_argument('--label', required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--size', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('samples must be positive')
    if args.size is not None:
        print(json.dumps(worker(args)))
        return
    sizes = [int(s) for s in args.sizes.split(',')]
    if any(size < 25 for size in sizes):
        parser.error('sizes must be at least 25 for the linked fixture')
    report = {'label': args.label, 'environment': {'platform': platform.platform(), 'python': sys.version,
        'processor': platform.processor(), 'timer': 'perf_counter', 'percentile': 'nearest rank',
        'notes': 'Sequential runs; OS file cache not evicted. First use is process/model cold, not disk cold. Prefetch model files before comparison; no downloads occurred in the recorded runs. RSS includes Python/native runtime; CPU includes child processes. n=1 measurements are observations, not distributions.'}, 'workloads': []}
    for size in sizes:
        command = [sys.executable, str(Path(__file__).resolve()), '--size', str(size), '--samples', str(args.samples), '--label', args.label]
        if args.hybrid:
            command.append('--hybrid')
        process = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE)
        report['workloads'].append(json.loads(process.stdout))
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, indent=2) + '\n')
    if not args.out:
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
