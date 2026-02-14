"""
Standalone peg solitaire solver for the Skipping Stones game.

Supports multiple board shapes (Wiegleb, English, European, Asymmetrical, Diamond).
Each shape's valid cells and precomputed moves are lazily cached on first use.

Usage:
    from solver import solve, get_hint
    board = [[False]*9 for _ in range(9)]
    # ... set up stones ...
    hint = get_hint(board)  # defaults to wiegleb
    hint = get_hint(board, shape_id='english')
"""

import time
from board_shapes import BOARD_SHAPES

# Directions: (row_delta, col_delta)
DIRECTIONS = [(-2, 0), (2, 0), (0, -2), (0, 2)]

# Per-shape solver data cache: shape_id -> (valid_cells, cell_index, precomputed_moves)
_SOLVER_DATA_CACHE = {}


def _build_solver_data(shape_id):
    """Build valid_cells list, cell_index dict, and precomputed_moves for a shape."""
    shape = BOARD_SHAPES[shape_id]
    valid_cells = shape['valid_cells']
    valid_set = set(valid_cells)

    cell_index = {}
    for i, (r, c) in enumerate(valid_cells):
        cell_index[(r, c)] = i

    precomputed_moves = []
    for r, c in valid_cells:
        for dr, dc in DIRECTIONS:
            to_r, to_c = r + dr, c + dc
            jump_r, jump_c = r + dr // 2, c + dc // 2
            if (to_r, to_c) in valid_set:
                from_bit = 1 << cell_index[(r, c)]
                to_bit = 1 << cell_index[(to_r, to_c)]
                jump_bit = 1 << cell_index[(jump_r, jump_c)]
                precomputed_moves.append((
                    from_bit, to_bit, jump_bit,
                    r, c, to_r, to_c, jump_r, jump_c
                ))

    return valid_cells, cell_index, precomputed_moves


def get_solver_data(shape_id='wiegleb'):
    """Get (valid_cells, cell_index, precomputed_moves) for a shape, with lazy caching."""
    if shape_id not in _SOLVER_DATA_CACHE:
        _SOLVER_DATA_CACHE[shape_id] = _build_solver_data(shape_id)
    return _SOLVER_DATA_CACHE[shape_id]


# Legacy Wiegleb aliases for backward compatibility (used by solver_cache.py etc.)
def is_valid_cell(row, col):
    """Returns whether a cell is in the valid Wiegleb play area."""
    if row < 0 or row > 8 or col < 0 or col > 8:
        return False
    if row < 3 and col < 3:
        return False
    if row < 3 and col > 5:
        return False
    if row > 5 and col < 3:
        return False
    if row > 5 and col > 5:
        return False
    return True


# Module-level Wiegleb data for backward compatibility
VALID_CELLS, _CELL_INDEX, _PRECOMPUTED_MOVES = get_solver_data('wiegleb')


def _board_to_bits(board, shape_id='wiegleb'):
    """Convert boolean board to a single integer bitmask."""
    valid_cells, cell_index, _ = get_solver_data(shape_id)
    bits = 0
    for i, (r, c) in enumerate(valid_cells):
        if board[r][c]:
            bits |= (1 << i)
    return bits


def _bits_to_board(bits, shape_id='wiegleb'):
    """Convert a bitmask integer back to a boolean board."""
    shape = BOARD_SHAPES[shape_id]
    rows, cols = shape['rows'], shape['cols']
    valid_cells = shape['valid_cells']
    board = [[False] * cols for _ in range(rows)]
    for i, (r, c) in enumerate(valid_cells):
        if bits & (1 << i):
            board[r][c] = True
    return board


def get_all_valid_moves(board, shape_id='wiegleb'):
    """Returns all legal moves as list of dicts."""
    valid_cells, _, _ = get_solver_data(shape_id)
    valid_set = set(valid_cells)
    moves = []
    for r, c in valid_cells:
        if not board[r][c]:
            continue
        for dr, dc in DIRECTIONS:
            to_r, to_c = r + dr, c + dc
            jump_r, jump_c = r + dr // 2, c + dc // 2
            if ((to_r, to_c) in valid_set
                    and not board[to_r][to_c]
                    and board[jump_r][jump_c]):
                moves.append({
                    'from_row': r,
                    'from_col': c,
                    'to_row': to_r,
                    'to_col': to_c,
                    'jump_row': jump_r,
                    'jump_col': jump_c,
                })
    return moves


def solve(board, time_limit=5.0, progress_callback=None, shape_id='wiegleb'):
    """
    DFS backtracking solver with transposition table using bitmask representation.

    Returns list of moves leading to 1 stone remaining, or None.
    Includes a configurable time limit (default 5 seconds).
    Optional progress_callback(current, total) is called after each top-level branch.
    """
    valid_cells, cell_index, precomputed_moves = get_solver_data(shape_id)
    state = _board_to_bits(board, shape_id)
    stone_count = bin(state).count('1')

    if stone_count <= 1:
        return []

    failed = set()
    solution = []
    has_time_limit = time_limit is not None
    deadline = time.monotonic() + time_limit if has_time_limit else 0
    moves_list = precomputed_moves
    check_interval = 0
    timed_out = False
    top_move_index = 0

    def dfs(state, remaining):
        nonlocal check_interval, timed_out, top_move_index

        if remaining == 1:
            return True

        # Check time every 4096 calls to reduce overhead
        if has_time_limit:
            check_interval += 1
            if check_interval & 4095 == 0:
                if time.monotonic() > deadline:
                    timed_out = True
                    return False

            if timed_out:
                return False

        if state in failed:
            return False

        is_top_level = remaining == stone_count

        # Count valid top-level moves for progress reporting
        if is_top_level and progress_callback:
            total_top_moves = 0
            for from_bit, to_bit, jump_bit, fr, fc, tr, tc, jr, jc in moves_list:
                if (state & from_bit) and not (state & to_bit) and (state & jump_bit):
                    total_top_moves += 1
            top_move_index = 0

        found_move = False
        for from_bit, to_bit, jump_bit, fr, fc, tr, tc, jr, jc in moves_list:
            if not (state & from_bit):
                continue
            if state & to_bit:
                continue
            if not (state & jump_bit):
                continue

            found_move = True
            new_state = (state & ~from_bit & ~jump_bit) | to_bit

            solution.append({
                'from_row': fr, 'from_col': fc,
                'to_row': tr, 'to_col': tc,
                'jump_row': jr, 'jump_col': jc,
            })

            if dfs(new_state, remaining - 1):
                return True

            solution.pop()

            if timed_out:
                return False

            # Report progress after each top-level branch
            if is_top_level and progress_callback:
                top_move_index += 1
                progress_callback(top_move_index, total_top_moves)

        if not timed_out and len(failed) < 1_000_000:
            failed.add(state)
        return False

    if dfs(state, stone_count):
        return solution
    return None


def get_hint(board, shape_id='wiegleb'):
    """Convenience function: calls solve(), returns the first move or None."""
    solution = solve(board, shape_id=shape_id)
    if solution and len(solution) > 0:
        return solution[0]
    return None
