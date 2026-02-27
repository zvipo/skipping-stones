#!/usr/bin/env python3
"""
CLI utility for solving queued board states from the solver queue.

Usage:
    python3 solve_queue.py                    # solve one pending item
    python3 solve_queue.py --all              # solve all pending items
    python3 solve_queue.py --all --workers 4  # solve all with 4 parallel workers
    python3 solve_queue.py --stats            # show queue statistics
    python3 solve_queue.py --cleanup          # remove solved/failed items from queue
    python3 solve_queue.py --reset-stuck      # reset all 'solving' items to 'pending'
"""

import argparse
import os
import signal
import sys
import time
from multiprocessing import Process, cpu_count

# Force unbuffered stdout so child process output appears immediately
sys.stdout.reconfigure(line_buffering=True)

# Max time (seconds) to spend solving a single board state
MAX_SOLVE_TIME = 1800  # 30 minutes

# Track actively-solving board_bits for signal handler cleanup
_active_items = []


def _signal_handler(signum, frame):
    """Release any claimed items back to pending before exit."""
    sig_name = signal.Signals(signum).name
    print(f"\n[pid {os.getpid()}] Received {sig_name}, releasing {len(_active_items)} active item(s)...", flush=True)
    if _active_items:
        from solver_queue import solver_queue
        for bits, shape_id, allow_diag in list(_active_items):
            try:
                solver_queue.release(bits, shape_id, allow_diag)
                print(f"  Released {bits} (shape={shape_id}, diag={allow_diag})", flush=True)
            except Exception as e:
                print(f"  Failed to release {bits}: {e}", flush=True)
    sys.exit(1)


def _register_signal_handlers():
    """Register signal handlers for the current process."""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)


# Register signal handlers in the main process
_register_signal_handlers()


def solve_item(item):
    """Solve a single queue item. Runs in its own process."""
    # Re-register signal handlers in child process so _active_items
    # (which is a per-process copy after fork) gets cleaned up on signal.
    _register_signal_handlers()

    from solver import solve, _bits_to_board
    from solver_cache import solver_cache
    from solver_queue import solver_queue

    shape_id = item.get('shape_id', 'wiegleb')
    allow_diagonals = item.get('allow_diagonals', False)
    # Parse board_bits from key (may be "shape:bits" or just "bits")
    raw_key = item['board_state']
    bits = int(raw_key.split(':')[-1]) if ':' in raw_key else int(raw_key)
    sc = int(item['stone_count'])
    board = _bits_to_board(bits, shape_id)

    _active_items.append((bits, shape_id, allow_diagonals))

    diag_str = ', diag=True' if allow_diagonals else ''
    print(f"[pid {os.getpid()}] Solving state {bits} ({sc} stones, shape={shape_id}{diag_str})...", flush=True)
    start = time.monotonic()
    solution = solve(board, time_limit=MAX_SOLVE_TIME, shape_id=shape_id, allow_diagonals=allow_diagonals)
    elapsed = time.monotonic() - start

    if solution is not None and len(solution) > 0:
        solver_cache.cache_solution_path(bits, solution, sc, shape_id, allow_diagonals)
        solver_queue.mark_solved(bits, shape_id, allow_diagonals)
        print(f"[pid {os.getpid()}] Solved {bits} in {elapsed:.1f}s — {len(solution)} moves cached.", flush=True)
    else:
        solver_cache.put_no_solution(bits, sc, shape_id, allow_diagonals)
        solver_queue.mark_failed(bits, shape_id, allow_diagonals)
        if elapsed >= MAX_SOLVE_TIME:
            print(f"[pid {os.getpid()}] Timed out on {bits} after {elapsed:.1f}s. Negative-cached.", flush=True)
        else:
            print(f"[pid {os.getpid()}] No solution for {bits} ({elapsed:.1f}s). Negative-cached.", flush=True)

    _active_items.remove((bits, shape_id, allow_diagonals))


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


def reset_stuck():
    """Delete all stuck 'solving' items from the queue."""
    from solver_queue import solver_queue

    response = solver_queue.table.scan(
        FilterExpression='#s = :solving',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':solving': 'solving'},
    )
    items = response.get('Items', [])
    if not items:
        print("No stuck items found.", flush=True)
        return

    for item in items:
        raw_key = item['board_state']
        sc = item.get('stone_count', '?')
        shape_id = item.get('shape_id', 'wiegleb')
        solver_queue.table.delete_item(Key={'board_state': raw_key})
        print(f"  Deleted {raw_key} ({sc} stones, shape={shape_id})", flush=True)

    print(f"\nDeleted {len(items)} stuck item(s).", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Solve queued board states.")
    parser.add_argument('--all', action='store_true', help='Solve all pending items')
    parser.add_argument('--workers', type=int, default=1,
                        help=f'Number of parallel workers (default: 1, max: {cpu_count()})')
    parser.add_argument('--stats', action='store_true', help='Show queue statistics')
    parser.add_argument('--cleanup', action='store_true', help='Remove solved/failed items from queue')
    parser.add_argument('--reset-stuck', action='store_true', help='Reset all solving items to pending')
    args = parser.parse_args()

    # Ensure tables exist (in main process)
    print("Initializing...", flush=True)
    from solver_cache import solver_cache
    from solver_queue import solver_queue
    solver_cache.create_table_if_not_exists()
    solver_queue.create_table_if_not_exists()
    print("Ready.\n", flush=True)

    if args.reset_stuck:
        reset_stuck()
    elif args.cleanup:
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
