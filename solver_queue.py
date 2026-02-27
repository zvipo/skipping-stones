"""
DynamoDB queue for board states that timed out during hint solving.

States are enqueued when the solver times out, then picked up by a
background worker (in-process daemon thread or the solve_queue.py CLI)
and solved without a time limit.
"""

import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class SolverQueue:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.getenv('SOLVER_QUEUE_TABLE_NAME', 'skipping-stones-solver-queue')
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

    def _queue_key(self, board_bits: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False) -> str:
        """Build the DynamoDB hash key, prefixed with shape_id for non-wiegleb shapes.
        When allow_diagonals is True, adds a 'diag:' prefix to differentiate."""
        if allow_diagonals:
            if shape_id == 'wiegleb':
                return f"diag:{board_bits}"
            return f"diag:{shape_id}:{board_bits}"
        if shape_id == 'wiegleb':
            return str(board_bits)
        return f"{shape_id}:{board_bits}"

    def enqueue(self, board_bits: int, stone_count: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Add a board state to the queue. Idempotent — only writes if the
        item doesn't exist or is in pending/failed status."""
        now = datetime.now().isoformat()
        key = self._queue_key(board_bits, shape_id, allow_diagonals)
        try:
            self.table.put_item(
                Item={
                    'board_state': key,
                    'stone_count': stone_count,
                    'shape_id': shape_id,
                    'allow_diagonals': allow_diagonals,
                    'status': 'pending',
                    'created_at': now,
                    'updated_at': now,
                },
                ConditionExpression='attribute_not_exists(board_state) OR #s IN (:pending, :failed)',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':pending': 'pending',
                    ':failed': 'failed',
                },
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                pass  # Already solving or solved — skip
            else:
                print(f"Solver queue enqueue error: {e}")

    def reset_stale_items(self, max_age_seconds=3600):
        """Reset 'solving' items older than max_age_seconds back to 'pending'."""
        try:
            response = self.table.scan(
                FilterExpression='#s = :solving',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':solving': 'solving'},
            )
            items = response.get('Items', [])
            cutoff = datetime.now()
            reset_count = 0
            for item in items:
                updated_at = item.get('updated_at', '')
                try:
                    item_time = datetime.fromisoformat(updated_at)
                except (ValueError, TypeError):
                    item_time = datetime.min  # Treat unparseable as stale
                age = (cutoff - item_time).total_seconds()
                if age > max_age_seconds:
                    item_shape = item.get('shape_id', 'wiegleb')
                    item_diag = item.get('allow_diagonals', False)
                    # Parse board_bits from key (may be "shape:bits" or just "bits")
                    raw_key = item['board_state']
                    item_bits = int(raw_key.split(':')[-1]) if ':' in raw_key else int(raw_key)
                    self.release(item_bits, item_shape, item_diag)
                    reset_count += 1
            if reset_count > 0:
                print(f"Solver queue: reset {reset_count} stale item(s) to pending.")
            return reset_count
        except Exception as e:
            print(f"Solver queue reset_stale_items error: {e}")
            return 0

    def get_all_claimable(self, include_solving=False):
        """Return all pending (and optionally solving) items, sorted by stone_count."""
        self.reset_stale_items()
        try:
            if include_solving:
                response = self.table.scan(
                    FilterExpression='#s IN (:pending, :solving)',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':pending': 'pending',
                        ':solving': 'solving',
                    },
                )
            else:
                response = self.table.scan(
                    FilterExpression='#s = :pending',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':pending': 'pending'},
                )
            items = response.get('Items', [])
            items.sort(key=lambda x: int(x.get('stone_count', 999)))
            # Claim pending items atomically
            for item in items:
                if item.get('status') == 'pending':
                    try:
                        self.table.update_item(
                            Key={'board_state': item['board_state']},
                            UpdateExpression='SET #s = :solving, updated_at = :now',
                            ConditionExpression='#s = :pending',
                            ExpressionAttributeNames={'#s': 'status'},
                            ExpressionAttributeValues={
                                ':solving': 'solving',
                                ':pending': 'pending',
                                ':now': datetime.now().isoformat(),
                            },
                        )
                        item['status'] = 'solving'
                    except ClientError:
                        pass  # Someone else claimed it
            return items
        except Exception as e:
            print(f"Solver queue get_all_claimable error: {e}")
            return []

    def claim_next(self, include_solving=False):
        """Scan for the next item with the lowest stone_count and
        atomically set its status to 'solving'. Returns the item dict or None.

        If include_solving is True, also considers items already being solved
        by another worker (useful for faster local CLI solving)."""
        self.reset_stale_items()
        try:
            if include_solving:
                response = self.table.scan(
                    FilterExpression='#s IN (:pending, :solving)',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':pending': 'pending',
                        ':solving': 'solving',
                    },
                )
            else:
                response = self.table.scan(
                    FilterExpression='#s = :pending',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':pending': 'pending'},
                )
            items = response.get('Items', [])
            if not items:
                return None

            # Sort by stone_count ascending (easier boards first),
            # prefer pending over solving
            items.sort(key=lambda x: (
                0 if x.get('status') == 'pending' else 1,
                int(x.get('stone_count', 999)),
            ))
            chosen = items[0]

            # Atomically claim it (skip condition check for already-solving items)
            if chosen.get('status') == 'solving':
                # Already being solved — just return it without updating
                return chosen

            self.table.update_item(
                Key={'board_state': chosen['board_state']},
                UpdateExpression='SET #s = :solving, updated_at = :now',
                ConditionExpression='#s = :pending',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':solving': 'solving',
                    ':pending': 'pending',
                    ':now': datetime.now().isoformat(),
                },
            )
            chosen['status'] = 'solving'
            return chosen
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return None  # Someone else claimed it
            print(f"Solver queue claim error: {e}")
            return None
        except Exception as e:
            print(f"Solver queue claim error: {e}")
            return None

    def mark_solved(self, board_bits: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Remove a solved item from the queue (result is in the solver cache)."""
        try:
            key = self._queue_key(board_bits, shape_id, allow_diagonals)
            self.table.delete_item(Key={'board_state': key})
        except Exception as e:
            print(f"Solver queue mark_solved error: {e}")

    def mark_failed(self, board_bits: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Remove a failed item from the queue (negative result is in the solver cache)."""
        try:
            key = self._queue_key(board_bits, shape_id, allow_diagonals)
            self.table.delete_item(Key={'board_state': key})
        except Exception as e:
            print(f"Solver queue mark_failed error: {e}")

    def release(self, board_bits: int, shape_id: str = 'wiegleb', allow_diagonals: bool = False):
        """Reset a queue item back to pending (e.g. after a worker crash)."""
        try:
            key = self._queue_key(board_bits, shape_id, allow_diagonals)
            self.table.update_item(
                Key={'board_state': key},
                UpdateExpression='SET #s = :pending, updated_at = :now',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':pending': 'pending',
                    ':now': datetime.now().isoformat(),
                },
            )
        except Exception as e:
            print(f"Solver queue release error: {e}")

    def cleanup_completed(self):
        """Delete all solved and failed items from the queue. Returns count deleted."""
        try:
            response = self.table.scan(
                FilterExpression='#s IN (:solved, :failed)',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':solved': 'solved',
                    ':failed': 'failed',
                },
            )
            items = response.get('Items', [])
            if not items:
                return 0
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={'board_state': item['board_state']})
            return len(items)
        except Exception as e:
            print(f"Solver queue cleanup error: {e}")
            return 0

    def get_queue_stats(self):
        """Return counts by status."""
        try:
            response = self.table.scan()
            items = response.get('Items', [])
            stats = {'pending': 0, 'solving': 0, 'solved': 0, 'failed': 0}
            for item in items:
                status = item.get('status', 'unknown')
                stats[status] = stats.get(status, 0) + 1
            stats['total'] = len(items)
            return stats
        except Exception as e:
            print(f"Solver queue stats error: {e}")
            return {'pending': 0, 'solving': 0, 'solved': 0, 'failed': 0, 'total': 0}


solver_queue = SolverQueue()
