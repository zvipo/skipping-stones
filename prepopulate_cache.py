#!/usr/bin/env python3
"""
Pre-populate the solver cache by solving each level configuration and
caching every intermediate state along the solution path.

Usage:
    python3 prepopulate_cache.py                  # solve all levels
    python3 prepopulate_cache.py --levels 1,2,3   # specific levels only
    python3 prepopulate_cache.py --time-limit 300  # generous timeout
    python3 prepopulate_cache.py --dry-run         # solve but don't write
"""

import argparse
import time

from solver import solve, _board_to_bits
from solver_cache import solver_cache, _apply_move_to_bits

# Level configurations (mirrored from app.py)
LEVEL_CONFIGS = {
    1: {
        'name': 'Level 1 - Cross',
        'marbles': [
            (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
            (2, 4), (3, 4), (5, 4), (6, 4),
        ],
    },
    2: {
        'name': 'Level 2 - Small triangle',
        'marbles': [
            (2, 4),
            (3, 3), (3, 4), (3, 5),
            (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
            (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7),
        ],
    },
    3: {
        'name': 'Level 3 - Arrow',
        'marbles': [
            (1, 4),
            (2, 3), (2, 4), (2, 5),
            (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
            (4, 4),
            (5, 4),
            (6, 3), (6, 4), (6, 5),
            (7, 3), (7, 4), (7, 5),
        ],
    },
    4: {
        'name': 'Level 4 - Diamond',
        'marbles': [
            (1, 4),
            (2, 3), (2, 4), (2, 5),
            (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
            (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7),
            (5, 2), (5, 3), (5, 4), (5, 5), (5, 6),
            (6, 3), (6, 4), (6, 5),
            (7, 4),
        ],
    },
    5: {
        'name': 'Level 5 - Big triangle',
        'marbles': [
            (1, 4),
            (2, 3), (2, 4), (2, 5),
            (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
            (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7),
            (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8),
        ],
    },
    6: {
        'name': 'Level 6 - Small square',
        'marbles': [
            (1, 3), (1, 4), (1, 5),
            (2, 3), (2, 4), (2, 5),
            (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7),
            (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7),
            (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7),
            (6, 3), (6, 4), (6, 5),
            (7, 3), (7, 4), (7, 5),
        ],
    },
    7: {
        'name': 'Level 7 - Full board',
        'marbles': [
            (0, 3), (0, 4), (0, 5),
            (1, 3), (1, 4), (1, 5),
            (2, 3), (2, 4), (2, 5),
            (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7), (3, 8),
            (4, 0), (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7), (4, 8),
            (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8),
            (6, 3), (6, 4), (6, 5),
            (7, 3), (7, 4), (7, 5),
            (8, 3), (8, 4), (8, 5),
        ],
    },
}


def build_board(marbles):
    """Build a 9x9 boolean board from a list of (row, col) marble positions."""
    board = [[False] * 9 for _ in range(9)]
    for r, c in marbles:
        board[r][c] = True
    return board


def main():
    parser = argparse.ArgumentParser(description='Pre-populate solver cache')
    parser.add_argument('--levels', type=str, default=None,
                        help='Comma-separated level numbers (default: all)')
    parser.add_argument('--time-limit', type=int, default=300,
                        help='Seconds per level (default: 300)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Solve but do not write to DynamoDB')
    args = parser.parse_args()

    if args.levels:
        levels = [int(x) for x in args.levels.split(',')]
    else:
        levels = list(LEVEL_CONFIGS.keys())

    if not args.dry_run:
        print("Initializing solver cache table...")
        solver_cache.create_table_if_not_exists()

    for level_num in levels:
        config = LEVEL_CONFIGS[level_num]
        name = config['name']
        marbles = config['marbles']
        stone_count = len(marbles)

        print(f"\n{'='*50}")
        print(f"{name}  ({stone_count} stones)")
        print(f"{'='*50}")

        board = build_board(marbles)
        bits = _board_to_bits(board)

        # Skip if already cached
        if not args.dry_run:
            cached = solver_cache.get_solution(bits)
            if cached:
                print(f"  Already cached ({len(cached)} moves) — skipping")
                continue

        start = time.monotonic()
        solution = solve(board, time_limit=args.time_limit)
        elapsed = time.monotonic() - start

        if solution is None:
            print(f"  FAILED - no solution found in {elapsed:.1f}s")
            continue

        states_count = len(solution)
        print(f"  Solved in {elapsed:.1f}s  ({states_count} moves, {states_count} intermediate states)")

        if args.dry_run:
            print("  (dry-run) Skipping cache write")
        else:
            solver_cache.cache_solution_path(bits, solution, stone_count)
            print(f"  Cached {states_count} states")

    print(f"\n{'='*50}")
    print("Done.")


if __name__ == '__main__':
    main()
