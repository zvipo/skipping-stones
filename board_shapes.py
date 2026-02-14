"""
Board shape definitions for peg solitaire variants.

Each shape defines the grid dimensions, valid cell positions, and center cell.
This module is the single source of truth for all board geometries.
"""


def _compute_valid_cells(rows, cols, is_valid):
    """Compute sorted list of valid (row, col) tuples for a shape."""
    return [(r, c) for r in range(rows) for c in range(cols) if is_valid(r, c)]


def _english_valid(r, c):
    """English board: 7x7 with 2x2 corners cut."""
    if r < 0 or r > 6 or c < 0 or c > 6:
        return False
    if r < 2 and c < 2:
        return False
    if r < 2 and c > 4:
        return False
    if r > 4 and c < 2:
        return False
    if r > 4 and c > 4:
        return False
    return True


def _european_valid(r, c):
    """European board: English + 4 inner corner cells."""
    if _english_valid(r, c):
        return True
    if (r, c) in {(1, 1), (1, 5), (5, 1), (5, 5)}:
        return True
    return False


def _wiegleb_valid(r, c):
    """Wiegleb board: 9x9 with 3x3 corners cut."""
    if r < 0 or r > 8 or c < 0 or c > 8:
        return False
    if r < 3 and c < 3:
        return False
    if r < 3 and c > 5:
        return False
    if r > 5 and c < 3:
        return False
    if r > 5 and c > 5:
        return False
    return True


def _asymmetrical_valid(r, c):
    """Asymmetrical board: 8x8 cross shape.

    Horizontal band: rows 3-5 (3 rows), all 8 columns.
    Vertical arm: columns 2-4 (3 cols), rows 0-2 (top, 3 rows) and rows 6-7 (bottom, 2 rows).
    Top arm is 3 deep, bottom arm is 2 deep. Left arm is 2 wide, right arm is 3 wide.
    """
    if r < 0 or r > 7 or c < 0 or c > 7:
        return False
    if 3 <= r <= 5:
        return True
    if 2 <= c <= 4:
        return True
    return False


def _diamond_valid(r, c):
    """Diamond board: 9x9 with Manhattan distance <= 4 from center."""
    if r < 0 or r > 8 or c < 0 or c > 8:
        return False
    return abs(r - 4) + abs(c - 4) <= 4


# Shape definitions
BOARD_SHAPES = {
    'wiegleb': {
        'id': 'wiegleb',
        'name': 'Wiegleb',
        'rows': 9,
        'cols': 9,
        'center': (4, 4),
        'valid_cells': _compute_valid_cells(9, 9, _wiegleb_valid),
    },
    'english': {
        'id': 'english',
        'name': 'English',
        'rows': 7,
        'cols': 7,
        'center': (3, 3),
        'valid_cells': _compute_valid_cells(7, 7, _english_valid),
    },
    'european': {
        'id': 'european',
        'name': 'European',
        'rows': 7,
        'cols': 7,
        'center': (2, 3),
        'valid_cells': _compute_valid_cells(7, 7, _european_valid),
    },
    'asymmetrical': {
        'id': 'asymmetrical',
        'name': 'Asymmetrical',
        'rows': 8,
        'cols': 8,
        'center': (4, 3),
        'valid_cells': _compute_valid_cells(8, 8, _asymmetrical_valid),
    },
    'diamond': {
        'id': 'diamond',
        'name': 'Diamond',
        'rows': 9,
        'cols': 9,
        'center': (4, 4),
        'valid_cells': _compute_valid_cells(9, 9, _diamond_valid),
    },
}

# Display order for the shape selector
SHAPE_ORDER = ['wiegleb', 'english', 'european', 'asymmetrical', 'diamond']
