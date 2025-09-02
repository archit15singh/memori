# Design Document

## Overview

This design makes the chat system memory-aware by including all stored memories in the LLM context and automatically extracting new memories from conversations. Simple approach: load all memories, use them in responses, extract new ones automatically.

## Architecture

```
User Message → Load All Memories → Enhanced LLM Prompt → Response → Extract New Memories → Auto-Update Database
                     ↓                      ↓               ↓              ↓
               Memory Store ←────── System Prompt ←─── Analysis ──→ Direct DB Updates
```

## Components and Interfaces

### Simplified Chat Pipeline

**Memory-Aware Chat Endpoint (`POST /chat`)**
1. **Load All Memories**: Get complete memory store from database
2. **Build Context**: Include all memories in system prompt
3. **Generate Response**: Use OpenAI with memory-enhanced prompt
4. **Extract Insights**: Analyze conversation for new memories
5. **Auto-Update**: Directly create/update memories in database
6. **Return Response**: Send chat response back to user

### Memory Context System

**Simple Memory Loading**
```python
def get_all_memories() -> Dict[str, List[MemoryItem]]:
    # Return all memories organized by category
    # No filtering, no relevance scoring - just load everything

def build_memory_context(memories: Dict) -> str:
    # Format all memories into readable context for LLM
    # Simple text formatting by category
```

**Enhanced System Prompt**
```python
MEMORY_AWARE_PROMPT = """
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

### Memory Extraction System

**Simple Insight Detection**
```python
def extract_new_memories(user_message: str, bot_response: str) -> List[Dict]:
    # Use LLM to analyze conversation and extract new memories
    # Return list of memory updates to make
    
def auto_update_memories(memory_updates: List[Dict]):
    # Directly update database with new/updated memories
    # No user approval needed - fully automatic
```

**Memory Extraction Prompt**
```python
EXTRACTION_PROMPT = """
Analyze this conversation and extract any new memories about the AI assistant.

Conversation:
User: {user_message}
Assistant: {bot_response}

Current memories: {current_memories}

Extract new memories in this format:
- category: identity|principles|focus|signals
- key: short_descriptive_key
- value: clear description
- action: create|update

Only extract clear, meaningful insights. Return empty list if no new memories found.
"""
```

## Data Models

### Keep Existing Models Simple
```python
# No changes to existing ChatRequest/ChatResponse
# Just enhance the processing internally

class MemoryExtraction(BaseModel):
    category: str
    key: str  
    value: str
    action: str  # create or update
```

## Implementation Strategy

### Phase 1: Memory-Informed Responses

**Backend Changes**
1. **Modify `get_ai_response()` function**
   - Load all memories at start of function
   - Build enhanced system prompt with all memory context
   - Use enhanced prompt for OpenAI call

2. **Add Simple Memory Functions**
   ```python
   def load_all_memories() -> Dict[str, List[MemoryItem]]
   def format_memories_for_prompt(memories: Dict) -> str
   def build_enhanced_prompt(base_prompt: str, memories: Dict, user_message: str) -> str
   ```

### Phase 2: Automatic Memory Extraction

**Backend Changes**
1. **Add Memory Extraction After Response**
   ```python
   def extract_memories_from_conversation(user_msg: str, bot_response: str, current_memories: Dict) -> List[Dict]
   def apply_memory_updates(updates: List[Dict])
   ```

2. **Integrate into Chat Pipeline**
   - After generating bot response, analyze conversation
   - Extract new memories automatically
   - Update database directly (no user approval needed)

## Error Handling

### Memory Loading Failures
- **Fallback**: Use empty memory context if loading fails
- **Continue**: Chat works normally without memory context
- **Log**: Record errors for debugging

### Memory Extraction Failures  
- **Graceful**: Return chat response even if extraction fails
- **Log**: Track extraction failures
- **Continue**: Don't block chat functionality

### Database Update Failures
- **Log**: Record failed memory updates
- **Continue**: Chat response still works
- **Retry**: Optional retry logic for critical updates

## Performance Considerations

### Simple Optimizations
- **Cache**: Cache all memories for short periods
- **Limit**: Keep total memory context under token limits
- **Async**: Make memory extraction async if needed

### Response Time Targets
- **Memory Loading**: < 50ms (simple SELECT query)
- **Total Chat Response**: < 3 seconds (same as current)
- **Memory Extraction**: Run async after response sent

## Testing Strategy

### Simple Testing Approach
- Test memory loading and formatting
- Test enhanced prompt generation
- Test memory extraction accuracy
- Test database update operations
- Test error handling and fallbacks