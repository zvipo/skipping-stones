"""
DynamoDB cache for pre-computed peg solitaire solutions.

Stores solutions keyed by shape_id and the bitmask integer that uniquely
identifies each board state. Supports write-through caching of entire
solution paths so that every intermediate state along a solved path is
also cached.
"""

import boto3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from solver import get_solver_data, _board_to_bits, VALID_CELLS, _CELL_INDEX

load_dotenv()


def _cache_key(board_bits: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False) -> str:
    """Build the DynamoDB hash key, prefixed with shape_id for non-wiegleb shapes.
    When allow_diagonals is True, adds a 'diag:' prefix to differentiate."""
    if allow_diagonals:
        if shape_id == 'wiegleb':
            return f"diag:{board_bits}"
        return f"diag:{shape_id}:{board_bits}"
    if shape_id == 'wiegleb':
        return str(board_bits)
    return f"{shape_id}:{board_bits}"


def _apply_move_to_bits(state: int, move: Dict, shape_id: str = 'wiegleb') -> int:
    """Apply a move dict to a bitmask integer, returning the new state."""
    _, cell_index, _ = get_solver_data(shape_id)
    from_bit = 1 << cell_index[(move['from_row'], move['from_col'])]
    to_bit = 1 << cell_index[(move['to_row'], move['to_col'])]
    jump_bit = 1 << cell_index[(move['jump_row'], move['jump_col'])]
    return (state & ~from_bit & ~jump_bit) | to_bit


class SolverCache:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.getenv('SOLVER_CACHE_TABLE_NAME', 'skipping-stones-solver-cache')
        self.table = self.dynamodb.Table(self.table_name)

    def create_table_if_not_exists(self):
        """Create the DynamoDB table if it doesn't exist."""
        try:
            self.table.load()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.table = self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {
                            'AttributeName': 'board_state',
                            'KeyType': 'HASH'
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'board_state',
                            'AttributeType': 'S'
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                self.table.meta.client.get_waiter('table_exists').wait(
                    TableName=self.table_name
                )
            else:
                raise e

    def get_solution(self, board_bits: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Look up a cached solution by board bitmask.

        Returns:
            None        — cache miss (never seen this state)
            "NO_SOLUTION" — definitively unsolvable
            "QUEUED"      — queued for background solving
            list        — cached solution moves
        """
        try:
            key = _cache_key(board_bits, shape_id, allow_diagonals)
            response = self.table.get_item(Key={'board_state': key})
            if 'Item' in response:
                raw = response['Item']['solution']
                if raw in ('NO_SOLUTION', 'QUEUED'):
                    return raw
                return json.loads(raw)
            return None
        except Exception as e:
            print(f"Solver cache lookup error: {e}")
            return None

    def put_solution(self, board_bits: int, solution: List[Dict], stone_count: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Store a single solution in the cache."""
        try:
            key = _cache_key(board_bits, shape_id, allow_diagonals)
            self.table.put_item(Item={
                'board_state': key,
                'solution': json.dumps(solution),
                'stone_count': stone_count,
                'created_at': datetime.now().isoformat(),
            })
        except Exception as e:
            print(f"Solver cache write error: {e}")

    def put_no_solution(self, board_bits: int, stone_count: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Cache that a board state is definitively unsolvable."""
        try:
            key = _cache_key(board_bits, shape_id, allow_diagonals)
            self.table.put_item(Item={
                'board_state': key,
                'solution': 'NO_SOLUTION',
                'stone_count': stone_count,
                'created_at': datetime.now().isoformat(),
            })
        except Exception as e:
            print(f"Solver cache write error (no_solution): {e}")

    def put_queued(self, board_bits: int, stone_count: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Cache that a board state has been queued for background solving."""
        try:
            key = _cache_key(board_bits, shape_id, allow_diagonals)
            self.table.put_item(Item={
                'board_state': key,
                'solution': 'QUEUED',
                'stone_count': stone_count,
                'created_at': datetime.now().isoformat(),
            })
        except Exception as e:
            print(f"Solver cache write error (queued): {e}")

    def cache_solution_path(self, board_bits: int, solution: List[Dict], stone_count: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Cache every intermediate state along the solution path.

        Walks forward through the move list, computing successive bitmask
        states and writing the remaining suffix of the solution for each.
        Uses Table.batch_writer() which auto-chunks into batches of 25.
        """
        try:
            current_state = board_bits
            remaining_stones = stone_count

            with self.table.batch_writer() as batch:
                for i, move in enumerate(solution):
                    remaining_moves = solution[i:]
                    key = _cache_key(current_state, shape_id, allow_diagonals)
                    batch.put_item(Item={
                        'board_state': key,
                        'solution': json.dumps(remaining_moves),
                        'stone_count': remaining_stones,
                        'created_at': datetime.now().isoformat(),
                    })
                    current_state = _apply_move_to_bits(current_state, move, shape_id)
                    remaining_stones -= 1
        except Exception as e:
            print(f"Solver cache batch write error: {e}")


solver_cache = SolverCache()
