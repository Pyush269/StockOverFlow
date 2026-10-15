"""Bounded traffic against StockFlow read endpoints; never changes inventory."""
import argparse
import concurrent.futures
import json
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--duration', type=int, default=120)
    parser.add_argument('--concurrency', type=int, default=8)
    parser.add_argument('--rps', type=int, default=60)
    parser.add_argument('--output', default='.logs/load-test.json')
    args = parser.parse_args()
    url = urllib.parse.urlsplit(args.base_url)
    if url.scheme not in ['http', 'https'] or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ['', '/']:
        parser.error('Use an HTTP(S) origin without credentials, a path, query, or fragment')
    if not (5 <= args.duration <= 300 and 1 <= args.concurrency <= 32 and 1 <= args.rps <= 200):
        parser.error('Bounds: duration 5..300 seconds, concurrency 1..32, total RPS 1..200')
    start = time.monotonic()
    deadline = start + args.duration
    next_slot = start
    lock = threading.Lock()
    durations, statuses = [], Counter()
    endpoints = ['/api/products?limit=20', '/api/dashboard']

    def worker():
        nonlocal next_slot
        index = 0
        while True:
            with lock:
                slot = max(next_slot, time.monotonic())
                if slot >= deadline:
                    return
                next_slot = slot + 1 / args.rps
            time.sleep(max(0, slot - time.monotonic()))
            before = time.monotonic()
            try:
                with urllib.request.urlopen(args.base_url.rstrip('/') + endpoints[index % 2], timeout=5) as response:
                    response.read()
                    status = str(response.status)
            except urllib.error.HTTPError as exc:
                status = str(exc.code)
                exc.close()
            except (urllib.error.URLError, TimeoutError, OSError):
                status = 'transport_error'
            elapsed = (time.monotonic() - before) * 1000
            with lock:
                durations.append(elapsed)
                statuses[status] += 1
            index += 1

    print(f'Read-only load: {args.duration}s, {args.concurrency} workers, at most {args.rps} requests/s', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        list(executor.map(lambda _: worker(), range(args.concurrency)))
    ordered = sorted(durations)
    total = sum(statuses.values())
    failed = sum(count for status, count in statuses.items() if status != '200')
    result = {'base_url': args.base_url, 'duration_seconds': round(time.monotonic() - start, 2), 'concurrency': args.concurrency, 'target_max_rps': args.rps, 'requests': total, 'statuses': dict(statuses), 'failed': failed, 'achieved_rps': round(total / (time.monotonic() - start), 2), 'latency_ms': {'median': round(statistics.median(ordered), 2) if ordered else None, 'p95': round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))], 2) if ordered else None}, 'endpoints': endpoints}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if failed or not total:
        raise SystemExit('Load failed: inspect status counts and service health')


if __name__ == '__main__':
    main()
