# Board Representation Compression

This document describes the compression improvements made to reduce the size of board data stored in DynamoDB.

## Problem

The original board representation was very verbose, storing 2D boolean arrays as JSON. For example:

```json
{
  "board": [
    [false, false, false, false, false, false, false, false, false],
    [false, false, false, false, false, false, false, false, false],
    [false, false, false, false, false, false, false, false, false],
    [false, false, false, false, false, false, false, false, false],
    [false, false, false, false, true, false, false, false, false],
    [false, false, false, false, false, false, false, false, false],
    [false, false, false, false, false, false, false, false, false],
    [false, false, false, false, false, false, false, false, false],
    [false, false, false, false, false, false, false, false, false]
  ]
}
```

This resulted in large storage requirements and increased DynamoDB costs.

## Solution

### 1. Board Compression

**Original**: 584 characters for a 9x9 board
**Compressed**: 93 characters (84% reduction)

The board is now stored as a binary string with dimensions:
```
9x9:000000000,000000000,000000000,000000000,000010000,000000000,000000000,000000000,000000000
```

Format: `{rows}x{cols}:{binary_rows_separated_by_commas}`

### 2. Move History Compression

**Original**: 276 characters for 3 moves
**Compressed**: 23 characters (92% reduction)

Moves are now stored in a compact format:
```
4,3:4,1|4,5:4,3|2,4:4,4
```

Format: `{from_col},{from_row}:{to_col},{to_row}|{next_move}`

The jumped position is calculated as the midpoint between from and to positions, eliminating redundancy.

### 3. Level States Compression

**Original**: 5,525 characters for 3 levels
**Compressed**: 915 characters (83% reduction)

Level states use shortened field names:
- `board` → `b`
- `moveHistory` → `m`

## Implementation

### Compression Functions

```python
def compress_board(board: List[List[bool]]) -> str:
    """Convert 2D boolean array to binary string representation"""
    
def decompress_board(compressed: str) -> List[List[bool]]:
    """Convert binary string back to 2D boolean array"""
    
def compress_move_history(move_history: List[Dict]) -> str:
    """Convert move history to compact string format"""
    
def decompress_move_history(compressed: str) -> List[Dict]:
    """Convert compact string back to move history"""
    
def compress_level_states(level_states: Dict[str, Any]) -> str:
    """Compress all level states including boards and move histories"""
    
def decompress_level_states(compressed: str) -> Dict[str, Any]:
    """Decompress all level states back to full format"""
```

### Backward Compatibility

The system maintains backward compatibility:
- Old uncompressed data is automatically detected and handled
- New data is compressed automatically
- No data migration required

### Database Integration

The compression is transparent to the application:
- `save_game_state()` automatically compresses data
- `load_game_state()` automatically decompresses data
- `save_all_levels_state()` compresses level states
- `load_all_levels_state()` decompresses level states

## Benefits

1. **Storage Reduction**: 80-90% reduction in storage size
2. **Cost Savings**: Reduced DynamoDB storage and transfer costs
3. **Performance**: Faster network transfers due to smaller payloads
4. **Backward Compatibility**: Existing data continues to work
5. **Transparency**: No changes required in application code

## Example Results

| Data Type | Original Size | Compressed Size | Reduction |
|-----------|---------------|-----------------|-----------|
| 9x9 Board | 584 chars | 93 chars | 84% |
| 3 Moves | 276 chars | 23 chars | 92% |
| 3 Levels | 5,525 chars | 759 chars | 86% |

## Testing

Run the test script to see compression results:
```bash
python3 test_compression.py
```

This will show detailed compression ratios and verify that decompression produces identical data. 