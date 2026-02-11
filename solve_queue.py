#!/usr/bin/env python3
"""
CLI utility for solving queued board states from the solver queue.

Usage:
    python3 solve_queue.py                    # solve one pending item
    python3 solve_queue.py --all              # solve all pending items
    python3 solve_queue.py --all --workers 4  # solve all with 4 parallel workers
    python3 solve_queue.py --stats            # show queue statistics
    python3 solve_queue.py --cleanup          # remove solved/failed items from queue
"""

import argparse
import os
import sys
import time
from multiprocessing import Process, cpu_count

# Force unbuffered stdout so child process output appears immediately
sys.stdout.reconfigure(line_buffering=True)


def solve_item(item):
    """Solve a single queue item. Runs in its own process."""
    from solver import solve, _bits_to_board
    from solver_cache import solver_cache
    from solver_queue import solver_queue

    bits = int(item['board_state'])
    sc = int(item['stone_count'])
    board = _bits_to_board(bits)

    print(f"[pid {os.getpid()}] Solving state {bits} ({sc} stones)...", flush=True)
    start = time.monotonic()
    solution = solve(board, time_limit=None)
    elapsed = time.monotonic() - start

    if solution is not None and len(solution) > 0:
        solver_cache.cache_solution_path(bits, solution, sc)
        solver_queue.mark_solved(bits)
        print(f"[pid {os.getpid()}] Solved {bits} in {elapsed:.1f}s — {len(solution)} moves cached.", flush=True)
    else:
        solver_cache.put_no_solution(bits, sc)
        solver_queue.mark_failed(bits)
        print(f"[pid {os.getpid()}] No solution for {bits} ({elapsed:.1f}s). Negative-cached.", flush=True)


def solve_one():
    """Claim and solve a single pending item. Returns True if an item was processed."""
    from solver_queue import solver_queue

    item = solver_queue.claim_next(include_solving=True)
    if item is None:
        print("No items in queue.", flush=True)
        return False

    solve_item(item)
    return True


def solve_all(num_workers):
    """Solve all pending items using multiple worker processes."""
    from solver_queue import solver_queue

    # Grab all pending/solving items in one scan
    items = solver_queue.get_all_claimable(include_solving=True)

    if not items:
        print("No items in queue.", flush=True)
        return

    print(f"Found {len(items)} item(s). Solving with {num_workers} worker(s)...\n", flush=True)

    if num_workers == 1:
        for item in items:
            solve_item(item)
    else:
        # Process items in batches of num_workers
        for i in range(0, len(items), num_workers):
            batch = items[i:i + num_workers]
            batch_num = i // num_workers + 1
            total_batches = (len(items) + num_workers - 1) // num_workers
            print(f"Batch {batch_num}/{total_batches}: launching {len(batch)} worker(s)...", flush=True)
            procs = []
            for item in batch:
                p = Process(target=solve_item, args=(item,))
                p.start()
                procs.append(p)
            for p in procs:
                p.join()
                if p.exitcode != 0:
                    print(f"[pid {p.pid}] Worker exited with code {p.exitcode}", flush=True)

    print(f"\nProcessed {len(items)} item(s).", flush=True)


def show_stats():
    from solver_queue import solver_queue

    stats = solver_queue.get_queue_stats()
    print("Solver Queue Statistics")
    print("-" * 30)
    for status in ('pending', 'solving', 'solved', 'failed'):
        print(f"  {status:>10}: {stats.get(status, 0)}")
    print(f"  {'total':>10}: {stats.get('total', 0)}")


def main():
    parser = argparse.ArgumentParser(description="Solve queued board states.")
    parser.add_argument('--all', action='store_true', help='Solve all pending items')
    parser.add_argument('--workers', type=int, default=1,
                        help=f'Number of parallel workers (default: 1, max: {cpu_count()})')
    parser.add_argument('--stats', action='store_true', help='Show queue statistics')
    parser.add_argument('--cleanup', action='store_true', help='Remove solved/failed items from queue')
    args = parser.parse_args()

    # Ensure tables exist (in main process)
    print("Initializing...", flush=True)
    from solver_cache import solver_cache
    from solver_queue import solver_queue
    solver_cache.create_table_if_not_exists()
    solver_queue.create_table_if_not_exists()
    print("Ready.\n", flush=True)

    if args.cleanup:
        count = solver_queue.cleanup_completed()
        print(f"Removed {count} solved/failed item(s) from queue.", flush=True)
    elif args.stats:
        show_stats()
    elif args.all:
        num_workers = max(1, min(args.workers, cpu_count()))
        solve_all(num_workers)
    else:
        solve_one()


if __name__ == '__main__':
    main()
