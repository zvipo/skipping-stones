import boto3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
            print(f"Table {self.table_name} already exists")
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
                print(f"Created table {self.table_name}")
            else:
                raise e
    
    def save_game_state(self, user_id: str, game_state: Dict[str, Any]) -> bool:
        """Save the current game state for a user"""
        try:
            item = {
                'user_id': user_id,
                'current_level': game_state.get('current_level', 'level1'),
                'board_state': json.dumps(game_state.get('board_state', [])),
                'move_history': json.dumps(game_state.get('move_history', [])),
                'marbles_left': game_state.get('marbles_left', 0),
                'moves_count': game_state.get('moves_count', 0),
                'game_status': game_state.get('game_status', 'Playing'),
                'last_updated': datetime.now().isoformat(),
                'completed_levels': json.dumps(game_state.get('completed_levels', []))
            }
            
            self.table.put_item(Item=item)
            print(f"Saved game state for user {user_id}")
            return True
        except Exception as e:
            print(f"Error saving game state for user {user_id}: {e}")
            return False
    
    def save_all_levels_state(self, user_id: str, all_levels_state: Dict[str, Any]) -> bool:
        """Save all levels' state for a user"""
        try:
            print(f"Saving all levels state for user {user_id}: {all_levels_state}")
            
            item = {
                'user_id': user_id,
                'all_levels_state': json.dumps(all_levels_state.get('level_states', {})),
                'completed_levels': json.dumps(all_levels_state.get('completed_levels', [])),
                'current_level': all_levels_state.get('current_level', 'level1'),
                'last_updated': datetime.now().isoformat()
            }
            
            print(f"Saving item to database: {item}")
            self.table.put_item(Item=item)
            print(f"Saved all levels state for user {user_id}")
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
                return {
                    'current_level': item.get('current_level', 'level1'),
                    'board_state': json.loads(item.get('board_state', '[]')),
                    'move_history': json.loads(item.get('move_history', '[]')),
                    'marbles_left': item.get('marbles_left', 0),
                    'moves_count': item.get('moves_count', 0),
                    'game_status': item.get('game_status', 'Playing'),
                    'last_updated': item.get('last_updated'),
                    'completed_levels': json.loads(item.get('completed_levels', '[]'))
                }
            else:
                print(f"No game state found for user {user_id}")
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
                print(f"Found item in database: {item}")
                
                all_levels_state = json.loads(item.get('all_levels_state', '{}'))
                completed_levels = json.loads(item.get('completed_levels', '[]'))
                current_level = item.get('current_level', 'level1')
                
                result = {
                    'level_states': all_levels_state,
                    'completed_levels': completed_levels,
                    'current_level': current_level,
                    'last_updated': item.get('last_updated')
                }
                
                print(f"Returning all levels state: {result}")
                return result
            else:
                print(f"No all levels state found for user {user_id}")
                return None
        except Exception as e:
            print(f"Error loading all levels state for user {user_id}: {e}")
            return None
    
    def mark_level_completed(self, user_id: str, level: str) -> bool:
        """Mark a level as completed for a user"""
        try:
            # First, get the current state
            current_state = self.load_game_state(user_id)
            if not current_state:
                current_state = {
                    'current_level': level,
                    'board_state': [],
                    'move_history': [],
                    'marbles_left': 0,
                    'moves_count': 0,
                    'game_status': 'Playing',
                    'completed_levels': []
                }
            
            # Add the level to completed levels if not already there
            completed_levels = current_state.get('completed_levels', [])
            if level not in completed_levels:
                completed_levels.append(level)
            
            # Save the updated state
            current_state['completed_levels'] = completed_levels
            return self.save_game_state(user_id, current_state)
        except Exception as e:
            print(f"Error marking level {level} as completed for user {user_id}: {e}")
            return False
    
    def delete_game_state(self, user_id: str) -> bool:
        """Delete the game state for a user (used on logout)"""
        try:
            self.table.delete_item(Key={'user_id': user_id})
            print(f"Deleted game state for user {user_id}")
            return True
        except Exception as e:
            print(f"Error deleting game state for user {user_id}: {e}")
            return False
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            state = self.load_game_state(user_id)
            if state:
                return {
                    'completed_levels': state.get('completed_levels', []),
                    'total_levels_completed': len(state.get('completed_levels', [])),
                    'current_level': state.get('current_level', 'level1'),
                    'last_updated': state.get('last_updated')
                }
            else:
                return {
                    'completed_levels': [],
                    'total_levels_completed': 0,
                    'current_level': 'level1',
                    'last_updated': None
                }
        except Exception as e:
            print(f"Error getting stats for user {user_id}: {e}")
            return {
                'completed_levels': [],
                'total_levels_completed': 0,
                'current_level': 'level1',
                'last_updated': None
            }

# Global database instance
db = GameStateDB() 