#!/usr/bin/env python3
"""
Tests for the solver cache module.

Validates bitmask transformations and solution-path decomposition without
requiring a live DynamoDB connection.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solver import _board_to_bits, _CELL_INDEX, VALID_CELLS, solve
from solver_cache import _apply_move_to_bits


def _make_board(marbles):
    """Build a 9x9 boolean board from a list of (row, col) positions."""
    board = [[False] * 9 for _ in range(9)]
    for r, c in marbles:
        board[r][c] = True
    return board


def test_apply_move_to_bits():
    """Verify _apply_move_to_bits matches manual board-level transformation."""
    # Set up a simple board: stones at (4,2), (4,3), (4,4) with (4,4) empty target
    marbles = [(4, 2), (4, 3), (4, 4)]
    board = _make_board(marbles)
    bits_before = _board_to_bits(board)

    # Move: (4,2) jumps over (4,3) to land on (4,4)... wait, (4,4) has a stone.
    # Instead: stone at (4,2) jumps over (4,3) landing at (4,4) — but (4,4) is occupied.
    # Let's use: stones at (4,2), (4,3), empty at (4,4)
    marbles = [(4, 2), (4, 3)]
    board = _make_board(marbles)
    bits_before = _board_to_bits(board)

    move = {
        'from_row': 4, 'from_col': 2,
        'to_row': 4, 'to_col': 4,
        'jump_row': 4, 'jump_col': 3,
    }

    bits_after = _apply_move_to_bits(bits_before, move)

    # After the move: (4,2) gone, (4,3) gone, (4,4) present
    expected_board = _make_board([(4, 4)])
    expected_bits = _board_to_bits(expected_board)

    assert bits_after == expected_bits, (
        f"Bitmask mismatch: got {bits_after}, expected {expected_bits}"
    )
    print("  PASS test_apply_move_to_bits")


def test_apply_move_preserves_other_stones():
    """Verify that _apply_move_to_bits does not disturb unrelated stones."""
    marbles = [(0, 3), (4, 2), (4, 3), (8, 5)]
    board = _make_board(marbles)
    bits_before = _board_to_bits(board)

    move = {
        'from_row': 4, 'from_col': 2,
        'to_row': 4, 'to_col': 4,
        'jump_row': 4, 'jump_col': 3,
    }

    bits_after = _apply_move_to_bits(bits_before, move)

    expected_board = _make_board([(0, 3), (4, 4), (8, 5)])
    expected_bits = _board_to_bits(expected_board)

    assert bits_after == expected_bits, (
        f"Bitmask mismatch: got {bits_after}, expected {expected_bits}"
    )
    print("  PASS test_apply_move_preserves_other_stones")


def test_cache_solution_path_decomposition():
    """Verify all intermediate states are correctly derived from a solution.

    Uses the level-1 solver to get a real solution, then walks through it
    with _apply_move_to_bits and verifies each successive state.
    """
    # Level 1 - Cross
    marbles = [
        (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
        (2, 4), (3, 4), (5, 4), (6, 4),
    ]
    board = _make_board(marbles)
    solution = solve(board, time_limit=10)
    assert solution is not None, "Level 1 should be solvable"

    bits = _board_to_bits(board)
    stone_count = len(marbles)

    # Walk the solution and verify each intermediate state
    for i, move in enumerate(solution):
        # The remaining moves from this state should be solution[i:]
        remaining = solution[i:]
        assert len(remaining) == len(solution) - i

        next_bits = _apply_move_to_bits(bits, move)

        # Verify the stone count decreases by 1
        next_stone_count = bin(next_bits).count('1')
        assert next_stone_count == stone_count - 1, (
            f"Step {i}: expected {stone_count - 1} stones, got {next_stone_count}"
        )

        bits = next_bits
        stone_count = next_stone_count

    # Final state should have exactly 1 stone
    assert stone_count == 1, f"Expected 1 stone at end, got {stone_count}"
    print("  PASS test_cache_solution_path_decomposition")


def test_roundtrip_state_consistency():
    """Verify that applying all moves in sequence produces a 1-stone state."""
    # Level 2 - Small triangle
    marbles = [
        (2, 4),
        (3, 3), (3, 4), (3, 5),
        (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
        (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7),
    ]
    board = _make_board(marbles)
    solution = solve(board, time_limit=10)
    assert solution is not None, "Level 2 should be solvable"

    bits = _board_to_bits(board)
    for move in solution:
        bits = _apply_move_to_bits(bits, move)

    final_stones = bin(bits).count('1')
    assert final_stones == 1, f"Expected 1 stone after full solution, got {final_stones}"
    print("  PASS test_roundtrip_state_consistency")


if __name__ == '__main__':
    print("Running solver cache tests...")
    test_apply_move_to_bits()
    test_apply_move_preserves_other_stones()
    test_cache_solution_path_decomposition()
    test_roundtrip_state_consistency()
    print("\nAll solver cache tests passed!")
