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
            return True
        except Exception as e:
            print(f"Error saving game state for user {user_id}: {e}")
            return False
    
    def save_all_levels_state(self, user_id: str, all_levels_state: Dict[str, Any]) -> bool:
        """Save all levels' state for a user"""
        try:
            item = {
                'user_id': user_id,
                'user_email': all_levels_state.get('user_email', ''),
                'user_name': all_levels_state.get('user_name', ''),
                'all_levels_state': json.dumps(all_levels_state.get('level_states', {})),
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
                return {
                    'current_level': item.get('current_level', 'level1'),
                    'board_state': json.loads(item.get('board_state', '[]')),
                    'move_history': json.loads(item.get('move_history', '[]')),
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
            response = self.table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                item = response['Item']
                result = {
                    'user_email': item.get('user_email', ''),
                    'user_name': item.get('user_name', ''),
                    'level_states': json.loads(item.get('all_levels_state', '{}')),
                    'completed_levels': json.loads(item.get('completed_levels', '[]')),
                    'current_level': item.get('current_level', 'level1')
                }
                return result
            else:
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