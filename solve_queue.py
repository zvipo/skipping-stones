#!/usr/bin/env python3
"""
CLI utility for solving queued board states from the solver queue.

Usage:
    python3 solve_queue.py           # solve one pending item
    python3 solve_queue.py --all     # solve all pending items
    python3 solve_queue.py --stats   # show queue statistics
"""

import argparse
import time
from solver import solve, _bits_to_board
from solver_cache import solver_cache
from solver_queue import solver_queue


def show_stats():
    stats = solver_queue.get_queue_stats()
    print("Solver Queue Statistics")
    print("-" * 30)
    for status in ('pending', 'solving', 'solved', 'failed'):
        print(f"  {status:>10}: {stats.get(status, 0)}")
    print(f"  {'total':>10}: {stats.get('total', 0)}")


def solve_one():
    """Claim and solve a single pending item. Returns True if an item was processed."""
    item = solver_queue.claim_next(include_solving=True)
    if item is None:
        print("No items in queue.")
        return False

    bits = int(item['board_state'])
    sc = int(item['stone_count'])
    board = _bits_to_board(bits)

    print(f"Solving state {bits} ({sc} stones)...", flush=True)
    start = time.monotonic()
    solution = solve(board, time_limit=None)
    elapsed = time.monotonic() - start

    if solution is not None and len(solution) > 0:
        solver_cache.cache_solution_path(bits, solution, sc)
        solver_queue.mark_solved(bits)
        print(f"  Solved in {elapsed:.1f}s — {len(solution)} moves cached.")
    else:
        solver_cache.put_no_solution(bits, sc)
        solver_queue.mark_failed(bits)
        print(f"  No solution exists ({elapsed:.1f}s). Negative-cached.")

    return True


def solve_all():
    """Solve all pending items in the queue."""
    count = 0
    while True:
        if not solve_one():
            break
        count += 1
    print(f"\nProcessed {count} item(s).")


def main():
    parser = argparse.ArgumentParser(description="Solve queued board states.")
    parser.add_argument('--all', action='store_true', help='Solve all pending items')
    parser.add_argument('--stats', action='store_true', help='Show queue statistics')
    parser.add_argument('--cleanup', action='store_true', help='Remove solved/failed items from queue')
    args = parser.parse_args()

    # Ensure tables exist
    solver_cache.create_table_if_not_exists()
    solver_queue.create_table_if_not_exists()

    if args.cleanup:
        count = solver_queue.cleanup_completed()
        print(f"Removed {count} solved/failed item(s) from queue.")
    elif args.stats:
        show_stats()
    elif args.all:
        solve_all()
    else:
        solve_one()


if __name__ == '__main__':
    main()
