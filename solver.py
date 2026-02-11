"""
Standalone peg solitaire solver for the Skipping Stones game.

The board is a 9x9 grid with corners cut off (cross/plus shape).
Valid cells exclude the four 3x3 corner squares.

Usage:
    from solver import solve, get_hint
    board = [[False]*9 for _ in range(9)]
    # ... set up stones ...
    hint = get_hint(board)
"""

import time

# Directions: (row_delta, col_delta)
DIRECTIONS = [(-2, 0), (2, 0), (0, -2), (0, 2)]


def is_valid_cell(row, col):
    """Returns whether a cell is in the valid cross-shaped play area."""
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


# Precompute valid cells and their indices for fast bit manipulation
VALID_CELLS = [(r, c) for r in range(9) for c in range(9) if is_valid_cell(r, c)]
_CELL_INDEX = {}
for _i, (_r, _c) in enumerate(VALID_CELLS):
    _CELL_INDEX[(_r, _c)] = _i

# Precompute all possible moves as (from_idx, to_idx, jump_idx) bit masks
_PRECOMPUTED_MOVES = []
for _r, _c in VALID_CELLS:
    for _dr, _dc in DIRECTIONS:
        _to_r, _to_c = _r + _dr, _c + _dc
        _jump_r, _jump_c = _r + _dr // 2, _c + _dc // 2
        if is_valid_cell(_to_r, _to_c):
            _from_bit = 1 << _CELL_INDEX[(_r, _c)]
            _to_bit = 1 << _CELL_INDEX[(_to_r, _to_c)]
            _jump_bit = 1 << _CELL_INDEX[(_jump_r, _jump_c)]
            _PRECOMPUTED_MOVES.append((
                _from_bit, _to_bit, _jump_bit,
                _r, _c, _to_r, _to_c, _jump_r, _jump_c
            ))


def _board_to_bits(board):
    """Convert 9x9 boolean board to a single integer bitmask."""
    bits = 0
    for i, (r, c) in enumerate(VALID_CELLS):
        if board[r][c]:
            bits |= (1 << i)
    return bits


def get_all_valid_moves(board):
    """Returns all legal moves as list of dicts."""
    moves = []
    for r, c in VALID_CELLS:
        if not board[r][c]:
            continue
        for dr, dc in DIRECTIONS:
            to_r, to_c = r + dr, c + dc
            jump_r, jump_c = r + dr // 2, c + dc // 2
            if (is_valid_cell(to_r, to_c)
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


def encode_board(board):
    """Encodes the 45 valid cells as a string for transposition table hashing."""
    chars = []
    for r, c in VALID_CELLS:
        chars.append('1' if board[r][c] else '0')
    return ''.join(chars)


def _count_stones(board):
    count = 0
    for r, c in VALID_CELLS:
        if board[r][c]:
            count += 1
    return count


def solve(board, time_limit=5.0, progress_callback=None):
    """
    DFS backtracking solver with transposition table using bitmask representation.

    Returns list of moves leading to 1 stone remaining, or None.
    Includes a configurable time limit (default 5 seconds).
    Optional progress_callback(current, total) is called after each top-level branch.
    """
    state = _board_to_bits(board)
    stone_count = bin(state).count('1')

    if stone_count <= 1:
        return []

    failed = set()
    solution = []
    deadline = time.monotonic() + time_limit
    moves_list = _PRECOMPUTED_MOVES
    check_interval = 0
    timed_out = False
    top_move_index = 0

    def dfs(state, remaining):
        nonlocal check_interval, timed_out, top_move_index

        if remaining == 1:
            return True

        # Check time every 4096 calls to reduce overhead
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

        if not timed_out:
            failed.add(state)
        return False

    if dfs(state, stone_count):
        return solution
    return None


def get_hint(board):
    """Convenience function: calls solve(), returns the first move or None."""
    solution = solve(board)
    if solution and len(solution) > 0:
        return solution[0]
    return None
