# Design Document

## Overview

The LLM Memory Extractor integrates into the existing FastAPI chat endpoint to automatically extract memories from conversations. It uses the OpenAI API to analyze conversation turns and extract key-value memories, storing them in the existing SQLite database using the current 4-bucket system.

## Architecture

### Integration Point
- **Location**: Added to the existing `/chat` endpoint in `main.py`
- **Timing**: Called asynchronously after the chat response is generated
- **Dependencies**: Uses existing OpenAI client, database connection, and memory functions

### Flow
1. User sends message to `/chat` endpoint
2. System generates AI response (existing flow)
3. System calls memory extractor with user message + AI response
4. Memory extractor analyzes conversation and returns memory actions
5. System applies memory actions to database
6. Chat response is returned to user

## Components and Interfaces

### Memory Extractor Function
```python
async def extract_memories(user_message: str, assistant_response: str, existing_memories: dict) -> List[dict]:
    """
    Extract memories from a conversation turn.
    
    Args:
        user_message: The user's input message
        assistant_response: The AI's response
        existing_memories: Current memory keys organized by bucket
        
    Returns:
        List of memory actions: [{"action": "create|update", "bucket": "identity", "key": "name", "value": "Alex"}]
    """
```

### Memory Action Processor
```python
def apply_memory_actions(memory_actions: List[dict]) -> None:
    """
    Apply extracted memory actions to the database.
    
    Args:
        memory_actions: List of memory actions from extractor
    """
```

### LLM Prompt Structure
- **System prompt**: Defines extraction rules and output format
- **User prompt**: Contains conversation context and existing memory keys
- **Output format**: JSON array of memory actions

## Data Models

### Memory Action
```python
{
    "action": "create" | "update",
    "bucket": "identity" | "principles" | "focus" | "signals", 
    "key": "memory_key",
    "value": "memory_value"
}
```

### Existing Memory Keys Structure
```python
{
    "identity": ["name", "role", "background"],
    "principles": ["code_quality", "collaboration"],
    "focus": ["current_project", "learning_goal"],
    "signals": ["energy_pattern", "stress_indicator"]
}
```

## Error Handling

### LLM API Failures
- Log error and continue without memory extraction
- Don't block chat response

### Invalid JSON Response
- Attempt to parse partial JSON
- Fall back to empty memory actions list

### Database Errors
- Log error and continue
- Don't affect chat functionality

## Testing Strategy

### Unit Tests
- Test memory extraction with sample conversations
- Test memory action processing
- Test error handling scenarios

### Integration Tests
- Test full chat flow with memory extraction
- Verify database updates after chat
- Test with existing memory keys

### Manual Testing
- Chat conversations that should generate memories
- Verify memories appear in database
- Test edge cases and error scenarios