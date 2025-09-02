# Design Document

## Overview

This design enhances the existing chat system by loading all stored memories and including them as context in the LLM system prompt. Simple approach: load everything, format it clearly, and let the LLM naturally reference memories in responses.

## Architecture

```
User Message → Load All Memories → Build Enhanced Prompt → LLM Response → User
                     ↓                      ↓
               Memory Database ←──── System Prompt Context
```

## Components and Interfaces

### Memory Loading System

**Simple Memory Loader**
```python
def load_all_memories_for_chat() -> Dict[str, List[MemoryItem]]:
    # Use existing get_all_memories() function
    # Return all memories organized by category
    # Handle database errors gracefully
```

### Enhanced System Prompt

**Memory Context Formatter**
```python
def format_memories_for_prompt(memories: Dict[str, List[MemoryItem]]) -> str:
    # Format memories into readable text for LLM
    # Organize by category with clear headers
    # Keep formatting concise to save tokens
```

**Enhanced Prompt Template**
```python
MEMORY_AWARE_SYSTEM_PROMPT = """
You are a reflective journaling AI bot. Here is what you know about yourself:

IDENTITY (who you are):
{identity_memories}

PRINCIPLES (how you operate):
{principles_memories}

FOCUS (what matters now):
{focus_memories}

SIGNALS (patterns you notice):
{signals_memories}

Reply to user messages in short, reflective responses that naturally reference your memories when relevant. Don't force memory references - only use them when they genuinely add to the conversation.

User: {user_message}
"""
```

## Implementation Strategy

### Modify Existing Chat Function

**Enhanced `get_ai_response()` Function**
```python
async def get_ai_response(message: str) -> str:
    try:
        # Load all memories
        memories = load_all_memories_for_chat()
        
        # Build enhanced prompt
        memory_context = format_memories_for_prompt(memories)
        enhanced_prompt = build_memory_aware_prompt(memory_context, message)
        
        # Call OpenAI with enhanced prompt
        response = await call_openai_with_enhanced_prompt(enhanced_prompt)
        
        return response
        
    except Exception as memory_error:
        # Fallback to normal chat if memory loading fails
        logger.warning(f"Memory loading failed: {memory_error}")
        return await get_ai_response_fallback(message)
```

### Memory Context Functions

**Core Functions to Implement**
```python
def load_all_memories_for_chat() -> Dict[str, List[MemoryItem]]:
    # Wrapper around existing get_all_memories()
    # Add error handling and logging
    
def format_memories_for_prompt(memories: Dict) -> str:
    # Convert memory objects to readable text
    # Format by category with clear structure
    
def build_memory_aware_prompt(memory_context: str, user_message: str) -> str:
    # Combine memory context with user message
    # Use template to build final prompt
    
async def get_ai_response_fallback(message: str) -> str:
    # Original chat functionality without memory context
    # Used when memory loading fails
```

## Data Models

### Keep Existing Models
- No changes to `ChatRequest` or `ChatResponse`
- Use existing `MemoryItem` model
- Enhance internally without changing API

### Memory Context Format
```python
# Internal format for memory context
{
    "identity": [
        {"key": "name", "value": "I'm Alex, a software engineer..."},
        {"key": "role", "value": "Senior Backend Developer..."}
    ],
    "principles": [...],
    "focus": [...],
    "signals": [...]
}
```

## Error Handling

### Memory Loading Failures
- **Fallback**: Use original chat function without memory context
- **Logging**: Log errors for debugging
- **User Experience**: No visible degradation in chat functionality

### Prompt Building Failures
- **Fallback**: Use basic system prompt
- **Logging**: Track prompt building issues
- **Recovery**: Continue with available memory context

### Token Limit Handling
- **Detection**: Monitor prompt length
- **Truncation**: Reduce memory context if needed
- **Prioritization**: Keep most recent or important memories

## Performance Considerations

### Memory Loading Optimization
- **Caching**: Cache memories for short periods (30 seconds)
- **Connection Reuse**: Reuse database connections
- **Query Optimization**: Use existing optimized queries

### Prompt Size Management
- **Token Counting**: Estimate prompt tokens
- **Context Limiting**: Truncate if approaching limits
- **Efficient Formatting**: Minimize formatting overhead

### Response Time Targets
- **Memory Loading**: < 50ms
- **Prompt Building**: < 10ms
- **Total Chat Response**: Maintain current ~2-3 second target

## Testing Strategy

### Unit Testing
- Test memory loading with various database states
- Test prompt formatting with different memory sets
- Test error handling and fallback behavior
- Test token limit handling

### Integration Testing
- Test end-to-end chat with memory context
- Verify memory references in responses
- Test performance with large memory sets
- Validate fallback behavior

### Manual Testing
- Test conversations that should reference memories
- Verify natural memory integration
- Test edge cases (empty memories, database errors)
- Validate response quality with memory context