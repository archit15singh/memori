# Design Document

## Overview

The conversation history feature extends the existing chat backend to store and retrieve conversation context. The system will maintain a conversation history table in the existing SQLite database and modify the chat endpoint to include recent message history when calling the OpenAI API.

## Architecture

The feature integrates into the existing FastAPI application architecture:

- **Database Layer**: New `conversation_history` table in existing SQLite database
- **Service Layer**: New functions for storing and retrieving conversation history
- **API Layer**: Modified `/chat` endpoint to use conversation history
- **Models**: No new Pydantic models needed (reuse existing ChatRequest/ChatResponse)

## Components and Interfaces

### Database Schema

New table `conversation_history`:
```sql
CREATE TABLE conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_type TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### Core Functions

#### `init_conversation_history_table()`
- Creates the conversation_history table during database initialization
- Integrates with existing `init_database()` function

#### `store_message(message_type: str, content: str)`
- Stores a single message (user or assistant) in the database
- Parameters:
  - `message_type`: Either "user" or "assistant"
  - `content`: The message content

#### `get_recent_conversation_history() -> List[dict]`
- Retrieves the last 10 message pairs (20 messages total)
- Returns messages ordered by timestamp (oldest first)
- Returns list of dictionaries with keys: message_type, content, timestamp

#### `build_messages_for_openai(user_message: str, history: List[dict]) -> List[dict]`
- Constructs the messages array for OpenAI API
- Combines system message, conversation history, and current user message
- Returns properly formatted messages array

### Modified Chat Endpoint Flow

1. Receive user message via existing ChatRequest
2. Store user message in conversation_history table
3. Retrieve recent conversation history (last 10 pairs)
4. Build OpenAI messages array with system message + history + current message
5. Call OpenAI API with enhanced context
6. Store AI response in conversation_history table
7. Return response via existing ChatResponse

## Data Models

### Existing Models (No Changes)
- `ChatRequest`: Continues to handle incoming user messages
- `ChatResponse`: Continues to handle outgoing AI responses

### Internal Data Structures

#### Conversation History Item
```python
{
    "message_type": str,  # "user" or "assistant"
    "content": str,       # message content
    "timestamp": str      # ISO timestamp
}
```

#### OpenAI Messages Format
```python
[
    {"role": "system", "content": "You are a reflective journaling AI bot..."},
    {"role": "user", "content": "Previous user message"},
    {"role": "assistant", "content": "Previous AI response"},
    # ... more history pairs ...
    {"role": "user", "content": "Current user message"}
]
```

## Error Handling

### Database Operation Failures
- If storing message fails: Log error but continue processing
- If retrieving history fails: Continue with empty history
- Graceful degradation ensures chat functionality remains available

### Empty History Scenarios
- New conversations with no history work normally
- System message + current user message sent to OpenAI

### Token Limit Considerations
- Limit to 10 message pairs prevents excessive token usage
- If individual messages are very long, they're still included (OpenAI handles truncation)



## Implementation Notes

### Database Integration
- Extends existing `init_database()` function
- Uses same SQLite connection pattern as existing memory functions
- Maintains existing error handling patterns

### Performance Considerations
- Database operations are lightweight (simple INSERT/SELECT)
- History retrieval limited to 20 messages maximum
- No significant impact on response time expected

### Backward Compatibility
- No changes to existing API contracts
- Existing chat functionality preserved
- New feature is additive only