import boto3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def compress_board(board: List[List[bool]]) -> str:
    """
    Compress a 2D boolean board into a compact binary string representation.
    Each row is converted to a binary string where 1 = true, 0 = false.
    """
    if not board:
        return ""
    
    rows = len(board)
    cols = len(board[0]) if board else 0
    
    # Convert each row to binary string
    binary_rows = []
    for row in board:
        binary_row = ''.join('1' if cell else '0' for cell in row)
        binary_rows.append(binary_row)
    
    # Join rows with a separator and add dimensions
    compressed = f"{rows}x{cols}:{','.join(binary_rows)}"
    return compressed

def decompress_board(compressed: str) -> List[List[bool]]:
    """
    Decompress a binary string representation back to a 2D boolean board.
    """
    if not compressed:
        return []
    
    try:
        # Split dimensions and data
        parts = compressed.split(':', 1)
        if len(parts) != 2:
            return []
        
        dimensions, data = parts
        rows, cols = map(int, dimensions.split('x'))
        
        # Split binary rows
        binary_rows = data.split(',')
        
        # Convert back to 2D boolean array
        board = []
        for binary_row in binary_rows:
            row = [cell == '1' for cell in binary_row]
            board.append(row)
        
        return board
    except Exception as e:
        print(f"Error decompressing board: {e}")
        return []

def compress_move_history(move_history: List[Dict]) -> str:
    """
    Compress move history by using shorter keys and removing redundant data.
    """
    if not move_history:
        return ""
    
    try:
        compressed_moves = []
        for move in move_history:
            # Extract coordinates
            from_pos = move.get('from', {})
            to_pos = move.get('to', {})
            
            # Validate coordinates
            from_col = from_pos.get('col', 0)
            from_row = from_pos.get('row', 0)
            to_col = to_pos.get('col', 0)
            to_row = to_pos.get('row', 0)
            
            # Create compact representation: "from_col,from_row:to_col,to_row"
            # The jumped position can be calculated as the midpoint
            compressed_move = f"{from_col},{from_row}:{to_col},{to_row}"
            compressed_moves.append(compressed_move)
        
        result = '|'.join(compressed_moves)
        print(f"Compressed move history: '{result}'")
        return result
    except Exception as e:
        print(f"Error compressing move history: {e}")
        return ""

def decompress_move_history(compressed: str) -> List[Dict]:
    """
    Decompress move history back to full format.
    """
    if not compressed:
        return []
    
    try:
        print(f"Decompressing move history: '{compressed}'")
        
        # Check if it's the new format (pipe-separated) or old format (JSON)
        # New format can be single move "from_col,from_row:to_col,to_row" or multiple "move1|move2|move3"
        if ':' in compressed and (',' in compressed or '|' in compressed):
            # New format: "from_col,from_row:to_col,to_row" or "move1|move2|move3"
            move_strings = compressed.split('|')
            move_history = []
            
            for move_str in move_strings:
                if not move_str:
                    continue
                    
                parts = move_str.split(':')
                if len(parts) == 2:
                    from_coords = parts[0].split(',')
                    to_coords = parts[1].split(',')
                    
                    if len(from_coords) == 2 and len(to_coords) == 2:
                        try:
                            from_col, from_row = int(from_coords[0]), int(from_coords[1])
                            to_col, to_row = int(to_coords[0]), int(to_coords[1])
                            
                            # Calculate jumped position as the midpoint
                            jumped_col = (from_col + to_col) // 2
                            jumped_row = (from_row + to_row) // 2
                            
                            move = {
                                'from': {'col': from_col, 'row': from_row},
                                'jumped': {'col': jumped_col, 'row': jumped_row},
                                'to': {'col': to_col, 'row': to_row}
                            }
                            move_history.append(move)
                            print(f"Parsed move: {move}")
                        except ValueError:
                            print(f"Invalid coordinates in move string: {move_str}")
                            continue
            
            print(f"Decompressed {len(move_history)} moves")
            return move_history
        else:
            # Old format: JSON with short keys
            # Try to parse as JSON, but handle empty or invalid strings gracefully
            if compressed.strip() == "":
                return []
            
            try:
                compressed_moves = json.loads(compressed)
                move_history = []
                for move in compressed_moves:
                    full_move = {
                        'from': move.get('f', {}),
                        'jumped': move.get('j', {}),
                        'to': move.get('t', {})
                    }
                    move_history.append(full_move)
                return move_history
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in compressed move history: {compressed}")
                print(f"JSON decode error: {e}")
                return []
    except Exception as e:
        print(f"Error decompressing move history: {e}")
        print(f"Compressed string: '{compressed}'")
        return []

def compress_level_states(level_states: Dict[str, Any]) -> str:
    """
    Compress level states by compressing board and move history for each level.
    """
    if not level_states:
        return ""
    
    compressed_levels = {}
    for level_name, level_data in level_states.items():
        compressed_level = {}
        
        # Compress board if present
        if 'board' in level_data:
            compressed_level['b'] = compress_board(level_data['board'])
        
        # Compress move history if present
        if 'moveHistory' in level_data:
            compressed_level['m'] = compress_move_history(level_data['moveHistory'])
        
        # Keep other fields as is
        for key, value in level_data.items():
            if key not in ['board', 'moveHistory']:
                compressed_level[key] = value
        
        compressed_levels[level_name] = compressed_level
    
    return json.dumps(compressed_levels)

def decompress_level_states(compressed: str) -> Dict[str, Any]:
    """
    Decompress level states back to full format.
    """
    if not compressed:
        print("No compressed data to decompress")
        return {}
    
    try:
        print(f"Decompressing level states, compressed string length: {len(compressed)}")
        compressed_levels = json.loads(compressed)
        print(f"Parsed compressed levels: {compressed_levels}")
        
        level_states = {}
        
        for level_name, level_data in compressed_levels.items():
            print(f"Processing level: {level_name}")
            decompressed_level = {}
            
            # Decompress board if present
            if 'b' in level_data:
                print(f"Decompressing board for {level_name}")
                decompressed_level['board'] = decompress_board(level_data['b'])
            
            # Decompress move history if present
            if 'm' in level_data:
                print(f"Decompressing move history for {level_name}, raw: '{level_data['m']}'")
                decompressed_level['moveHistory'] = decompress_move_history(level_data['m'])
                print(f"Decompressed move history for {level_name}: {decompressed_level['moveHistory']}")
            
            # Keep other fields as is
            for key, value in level_data.items():
                if key not in ['b', 'm']:
                    decompressed_level[key] = value
            
            level_states[level_name] = decompressed_level
            print(f"Final decompressed level {level_name}: {decompressed_level}")
        
        print(f"Final decompressed level states: {level_states}")
        return level_states
    except Exception as e:
        print(f"Error decompressing level states: {e}")
        print(f"Compressed string: '{compressed}'")
        return {}

class GameStateDB:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.getenv('DYNAMODB_TABLE_NAME', 'skipping-stones-game-state')
        self.table = self.dynamodb.Table(self.table_name)
        
    def create_table_if_not_exists(self):
        """Create the DynamoDB table if it doesn't exist"""
        try:
            # Check if table exists
            self.table.load()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                self.table = self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'user_id',
                            'AttributeType': 'S'
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                
                # Wait for table to be created
                self.table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
            else:
                raise e
    
    def save_game_state(self, user_id: str, game_state: Dict[str, Any]) -> bool:
        """Save the current game state for a user"""
        try:
            # Compress board and move history
            board_state = game_state.get('board_state', [])
            move_history = game_state.get('move_history', [])
            
            compressed_board = compress_board(board_state)
            compressed_moves = compress_move_history(move_history)
            
            item = {
                'user_id': user_id,
                'current_level': game_state.get('current_level', 'level1'),
                'board_state': compressed_board,
                'move_history': compressed_moves,
                'marbles_left': game_state.get('marbles_left', 0),
                'moves_count': game_state.get('moves_count', 0),
                'game_status': game_state.get('game_status', 'Playing'),
                'last_updated': datetime.now().isoformat(),
                'completed_levels': json.dumps(game_state.get('completed_levels', []))
            }
            
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error saving game state for user {user_id}: {e}")
            return False
    
    def save_all_levels_state(self, user_id: str, all_levels_state: Dict[str, Any]) -> bool:
        """Save all levels' state for a user"""
        try:
            # Compress level states
            level_states = all_levels_state.get('level_states', {})
            compressed_level_states = compress_level_states(level_states)
            
            item = {
                'user_id': user_id,
                'user_email': all_levels_state.get('user_email', ''),
                'user_name': all_levels_state.get('user_name', ''),
                'all_levels_state': compressed_level_states,
                'completed_levels': json.dumps(all_levels_state.get('completed_levels', [])),
                'current_level': all_levels_state.get('current_level', 'level1'),
                'last_updated': datetime.now().isoformat()
            }
            
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error saving all levels state for user {user_id}: {e}")
            return False
    
    def load_game_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load the game state for a user"""
        try:
            response = self.table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                item = response['Item']
                
                # Decompress board and move history
                board_state_str = item.get('board_state', '')
                move_history_str = item.get('move_history', '')
                
                # Check if data is compressed (new format) or uncompressed (old format)
                board_state = decompress_board(board_state_str) if board_state_str and ':' in board_state_str else json.loads(board_state_str or '[]')
                move_history = decompress_move_history(move_history_str) if move_history_str else json.loads(move_history_str or '[]')
                
                return {
                    'current_level': item.get('current_level', 'level1'),
                    'board_state': board_state,
                    'move_history': move_history,
                    'marbles_left': item.get('marbles_left', 0),
                    'moves_count': item.get('moves_count', 0),
                    'game_status': item.get('game_status', 'Playing'),
                    'completed_levels': json.loads(item.get('completed_levels', '[]'))
                }
            else:
                return None
        except Exception as e:
            print(f"Error loading game state for user {user_id}: {e}")
            return None
    
    def load_all_levels_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load all levels' state for a user"""
        try:
            print(f"Loading all levels state for user {user_id}")
            response = self.table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                item = response['Item']
                print(f"Found item for user {user_id}")
                
                # Decompress level states
                all_levels_state_str = item.get('all_levels_state', '')
                print(f"Raw all_levels_state string length: {len(all_levels_state_str)}")
                
                level_states = decompress_level_states(all_levels_state_str) if all_levels_state_str else {}
                print(f"Decompressed level states: {level_states}")
                
                result = {
                    'user_email': item.get('user_email', ''),
                    'user_name': item.get('user_name', ''),
                    'level_states': level_states,
                    'completed_levels': json.loads(item.get('completed_levels', '[]')),
                    'current_level': item.get('current_level', 'level1')
                }
                print(f"Returning result for user {user_id}: {result}")
                return result
            else:
                print(f"No item found for user {user_id}")
                return None
        except Exception as e:
            print(f"Error loading all levels state for user {user_id}: {e}")
            return None
    
    def mark_level_completed(self, user_id: str, level: str) -> bool:
        """Mark a level as completed for a user"""
        try:
            # Get current completed levels
            response = self.table.get_item(Key={'user_id': user_id})
            completed_levels = []
            
            if 'Item' in response:
                item = response['Item']
                completed_levels = json.loads(item.get('completed_levels', '[]'))
            
            # Add the new level if not already completed
            if level not in completed_levels:
                completed_levels.append(level)
                
                # Update the item
                self.table.update_item(
                    Key={'user_id': user_id},
                    UpdateExpression='SET completed_levels = :completed_levels',
                    ExpressionAttributeValues={
                        ':completed_levels': json.dumps(completed_levels)
                    }
                )
            
            return True
        except Exception as e:
            print(f"Error marking level {level} as completed for user {user_id}: {e}")
            return False
    
    def delete_game_state(self, user_id: str) -> bool:
        """Delete the game state for a user"""
        try:
            self.table.delete_item(Key={'user_id': user_id})
            return True
        except Exception as e:
            print(f"Error deleting game state for user {user_id}: {e}")
            return False
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user"""
        try:
            response = self.table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                item = response['Item']
                completed_levels = json.loads(item.get('completed_levels', '[]'))
                
                return {
                    'total_levels_completed': len(completed_levels),
                    'completed_levels': completed_levels,
                    'current_level': item.get('current_level', 'level1'),
                    'last_updated': item.get('last_updated', '')
                }
            else:
                return {
                    'total_levels_completed': 0,
                    'completed_levels': [],
                    'current_level': 'level1',
                    'last_updated': ''
                }
        except Exception as e:
            print(f"Error getting stats for user {user_id}: {e}")
            return {
                'total_levels_completed': 0,
                'completed_levels': [],
                'current_level': 'level1',
                'last_updated': ''
            }

# Create a global instance
db = GameStateDB() 