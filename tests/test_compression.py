#!/usr/bin/env python3
"""
Test script to demonstrate the compression benefits of the new board representation.
"""

import json
import sys
import os

# Add the parent directory to the path so we can import from the root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import compress_board, decompress_board, compress_move_history, decompress_move_history, compress_level_states, decompress_level_states

def test_board_compression():
    """Test board compression with the example data"""
    
    # Example board from the user's data
    board = [
        [False, False, False, False, False, False, False, False, False],
        [False, False, False, False, False, False, False, False, False],
        [False, False, False, False, False, False, False, False, False],
        [False, False, False, False, False, False, False, False, False],
        [False, False, False, False, True, False, False, False, False],
        [False, False, False, False, False, False, False, False, False],
        [False, False, False, False, False, False, False, False, False],
        [False, False, False, False, False, False, False, False, False],
        [False, False, False, False, False, False, False, False, False]
    ]
    
    # Original JSON representation
    original_json = json.dumps(board)
    original_size = len(original_json)
    
    # Compressed representation
    compressed = compress_board(board)
    compressed_size = len(compressed)
    
    # Decompress and verify
    decompressed = decompress_board(compressed)
    is_correct = board == decompressed
    
    print("=== Board Compression Test ===")
    print(f"Original JSON: {original_json}")
    print(f"Original size: {original_size} characters")
    print(f"Compressed: {compressed}")
    print(f"Compressed size: {compressed_size} characters")
    print(f"Compression ratio: {compressed_size/original_size:.2%}")
    print(f"Decompression correct: {is_correct}")
    print()

def test_move_history_compression():
    """Test move history compression"""
    
    # Example move history from the user's data
    move_history = [
        {"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 1}},
        {"from": {"col": 4, "row": 5}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 3}},
        {"from": {"col": 2, "row": 4}, "jumped": {"col": 3, "row": 4}, "to": {"col": 4, "row": 4}}
    ]
    
    # Original JSON representation
    original_json = json.dumps(move_history)
    original_size = len(original_json)
    
    # Compressed representation
    compressed = compress_move_history(move_history)
    compressed_size = len(compressed)
    
    # Decompress and verify
    decompressed = decompress_move_history(compressed)
    is_correct = move_history == decompressed
    
    print("=== Move History Compression Test ===")
    print(f"Original JSON: {original_json}")
    print(f"Original size: {original_size} characters")
    print(f"Compressed: {compressed}")
    print(f"Compressed size: {compressed_size} characters")
    print(f"Compression ratio: {compressed_size/original_size:.2%}")
    print(f"Decompression correct: {is_correct}")
    print()

def test_level_states_compression():
    """Test level states compression with the user's example data"""
    
    # Example level states from the user's data
    level_states = {
        "level1": {
            "board": [
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, True, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False]
            ],
            "moveHistory": [
                {"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 1}},
                {"from": {"col": 4, "row": 5}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 3}}
            ],
            "currentConfig": "level1"
        },
        "level2": {
            "board": [
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, True, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False, False]
            ],
            "currentConfig": "level2",
            "moveHistory": [
                {"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 1}},
                {"from": {"col": 4, "row": 5}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 3}},
                {"from": {"col": 2, "row": 4}, "jumped": {"col": 3, "row": 4}, "to": {"col": 4, "row": 4}}
            ]
        }
    }
    
    # Original JSON representation
    original_json = json.dumps(level_states)
    original_size = len(original_json)
    
    # Compressed representation
    compressed = compress_level_states(level_states)
    compressed_size = len(compressed)
    
    # Decompress and verify
    decompressed = decompress_level_states(compressed)
    is_correct = level_states == decompressed
    
    print("=== Level States Compression Test ===")
    print(f"Original size: {original_size} characters")
    print(f"Compressed size: {compressed_size} characters")
    print(f"Compression ratio: {compressed_size/original_size:.2%}")
    print(f"Decompression correct: {is_correct}")
    print()

def test_user_example():
    """Test with the exact user's example data"""
    
    user_data = {
        "level1": {
            "board": [[False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, True, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False]],
            "moveHistory": [{"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 1}}, {"from": {"col": 4, "row": 5}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 3}}, {"from": {"col": 2, "row": 4}, "jumped": {"col": 3, "row": 4}, "to": {"col": 4, "row": 4}}, {"from": {"col": 4, "row": 4}, "jumped": {"col": 4, "row": 3}, "to": {"col": 4, "row": 2}}, {"from": {"col": 6, "row": 4}, "jumped": {"col": 5, "row": 4}, "to": {"col": 4, "row": 4}}, {"from": {"col": 4, "row": 1}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 3}}, {"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 5}}, {"from": {"col": 4, "row": 6}, "jumped": {"col": 4, "row": 5}, "to": {"col": 4, "row": 4}}],
            "currentConfig": "level1"
        },
        "level2": {
            "board": [[False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, True, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False]],
            "currentConfig": "level2",
            "moveHistory": [{"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 1}}, {"from": {"col": 4, "row": 5}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 3}}, {"from": {"col": 2, "row": 4}, "jumped": {"col": 3, "row": 4}, "to": {"col": 4, "row": 4}}, {"from": {"col": 4, "row": 4}, "jumped": {"col": 4, "row": 3}, "to": {"col": 4, "row": 2}}, {"from": {"col": 6, "row": 4}, "jumped": {"col": 5, "row": 4}, "to": {"col": 4, "row": 4}}, {"from": {"col": 4, "row": 1}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 3}}, {"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 5}}, {"from": {"col": 4, "row": 6}, "jumped": {"col": 4, "row": 5}, "to": {"col": 4, "row": 4}}, {"from": {"col": 3, "row": 4}, "jumped": {"col": 3, "row": 5}, "to": {"col": 3, "row": 6}}, {"from": {"col": 5, "row": 4}, "jumped": {"col": 5, "row": 5}, "to": {"col": 5, "row": 6}}, {"from": {"col": 1, "row": 5}, "jumped": {"col": 2, "row": 5}, "to": {"col": 3, "row": 5}}, {"from": {"col": 7, "row": 5}, "jumped": {"col": 6, "row": 5}, "to": {"col": 5, "row": 5}}, {"from": {"col": 5, "row": 6}, "jumped": {"col": 5, "row": 5}, "to": {"col": 5, "row": 4}}, {"from": {"col": 3, "row": 6}, "jumped": {"col": 3, "row": 5}, "to": {"col": 3, "row": 4}}, {"from": {"col": 3, "row": 3}, "jumped": {"col": 3, "row": 4}, "to": {"col": 3, "row": 5}}, {"from": {"col": 4, "row": 5}, "jumped": {"col": 3, "row": 5}, "to": {"col": 2, "row": 5}}, {"from": {"col": 2, "row": 5}, "jumped": {"col": 2, "row": 4}, "to": {"col": 2, "row": 3}}, {"from": {"col": 5, "row": 3}, "jumped": {"col": 4, "row": 3}, "to": {"col": 3, "row": 3}}, {"from": {"col": 2, "row": 3}, "jumped": {"col": 3, "row": 3}, "to": {"col": 4, "row": 3}}, {"from": {"col": 5, "row": 4}, "jumped": {"col": 4, "row": 4}, "to": {"col": 3, "row": 4}}, {"from": {"col": 4, "row": 2}, "jumped": {"col": 4, "row": 3}, "to": {"col": 4, "row": 4}}, {"from": {"col": 3, "row": 4}, "jumped": {"col": 4, "row": 4}, "to": {"col": 5, "row": 4}}, {"from": {"col": 6, "row": 4}, "jumped": {"col": 5, "row": 4}, "to": {"col": 4, "row": 4}}]
        },
        "level3": {
            "board": [[False, False, False, False, False, False, False, False, False], [False, False, False, False, True, False, False, False, False], [False, False, False, True, True, True, False, False, False], [False, False, True, True, True, True, True, False, False], [False, False, False, False, True, False, False, False, False], [False, False, False, False, True, False, False, False, False], [False, False, False, True, True, True, False, False, False], [False, False, False, True, True, True, False, False, False], [False, False, False, False, False, False, False, False, False]],
            "currentConfig": "level3",
            "moveHistory": [{"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 1}}, {"from": {"col": 4, "row": 5}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 3}}, {"from": {"col": 2, "row": 4}, "jumped": {"col": 3, "row": 4}, "to": {"col": 4, "row": 4}}, {"from": {"col": 4, "row": 4}, "jumped": {"col": 4, "row": 3}, "to": {"col": 4, "row": 2}}, {"from": {"col": 6, "row": 4}, "jumped": {"col": 5, "row": 4}, "to": {"col": 4, "row": 4}}, {"from": {"col": 4, "row": 1}, "jumped": {"col": 4, "row": 2}, "to": {"col": 4, "row": 3}}, {"from": {"col": 4, "row": 3}, "jumped": {"col": 4, "row": 4}, "to": {"col": 4, "row": 5}}, {"from": {"col": 4, "row": 6}, "jumped": {"col": 4, "row": 5}, "to": {"col": 4, "row": 4}}]
        }
    }
    
    # Original JSON representation
    original_json = json.dumps(user_data)
    original_size = len(original_json)
    
    # Compressed representation
    compressed = compress_level_states(user_data)
    compressed_size = len(compressed)
    
    # Decompress and verify
    decompressed = decompress_level_states(compressed)
    is_correct = user_data == decompressed
    
    print("=== User Example Compression Test ===")
    print(f"Original size: {original_size} characters")
    print(f"Compressed size: {compressed_size} characters")
    print(f"Compression ratio: {compressed_size/original_size:.2%}")
    print(f"Decompression correct: {is_correct}")
    print()

if __name__ == "__main__":
    test_board_compression()
    test_move_history_compression()
    test_level_states_compression()
    test_user_example() 