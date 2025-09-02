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
```

### Enhanced System Prompt

**Memory Context Formatter**
```python
def format_memories_for_prompt(memories: Dict[str, List[MemoryItem]]) -> str:
    # Format memories into readable text for LLM
    # Organize by category with clear headers
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

Reply to user messages in short, reflective responses that naturally reference your memories when relevant.

User: {user_message}
"""
```

## Implementation Strategy

### Modify Existing Chat Function

**Enhanced `get_ai_response()` Function**
```python
async def get_ai_response(message: str) -> str:
    # Load all memories
    memories = load_all_memories_for_chat()
    
    # Build enhanced prompt
    memory_context = format_memories_for_prompt(memories)
    enhanced_prompt = build_memory_aware_prompt(memory_context, message)
    
    # Call OpenAI with enhanced prompt
    response = await call_openai_with_enhanced_prompt(enhanced_prompt)
    
    return response
```

### Memory Context Functions

**Core Functions to Implement**
```python
def load_all_memories_for_chat() -> Dict[str, List[MemoryItem]]:
    # Wrapper around existing get_all_memories()
    
def format_memories_for_prompt(memories: Dict) -> str:
    # Convert memory objects to readable text
    # Format by category with clear structure
    
def build_memory_aware_prompt(memory_context: str, user_message: str) -> str:
    # Combine memory context with user message
    # Use template to build final prompt
```

## Data Models

### Keep Existing Models
- No changes to `ChatRequest` or `ChatResponse`
- Use existing `MemoryItem` model
- Enhance internally without changing API