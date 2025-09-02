# Design Document

## Overview

The persistent chat history feature adds database storage for chat messages and automatic loading on page refresh. This design leverages the existing SQLite database and follows the current API patterns used by the memory system.

## Architecture

### Database Layer
- Add a new `messages` table to the existing SQLite database (`chat_app.db`)
- Store messages with id, content, sender type, and timestamp
- Use the existing database connection patterns from the memory system

### Backend API Layer
- Add new endpoints to the existing FastAPI application
- Follow the same patterns as memory endpoints for consistency
- Integrate with the existing `/chat` endpoint to save messages automatically

### Frontend Layer
- Extend the existing React state management to load messages on startup
- Use the same API service patterns as the memory system
- Minimal changes to existing chat UI components

## Components and Interfaces

### Database Schema

```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    sender TEXT NOT NULL,  -- 'user' or 'bot'
    timestamp INTEGER NOT NULL
);
```

### Backend Models

```python
class MessageItem(BaseModel):
    id: str
    content: str
    sender: str  # 'user' or 'bot'
    timestamp: int

class MessagesResponse(BaseModel):
    messages: List[MessageItem]
```

### API Endpoints

**GET /messages**
- Returns all stored messages in chronological order
- Response: `MessagesResponse`

**Modified POST /chat**
- Existing functionality unchanged
- Adds automatic message storage after successful chat completion
- Stores both user message and bot response

### Frontend Integration

**New API Service Method**
```javascript
// In chatApi.js
async fetchMessages() {
  // GET /messages
  // Returns array of message objects
}
```

**React Component Changes**
```javascript
// In App.js
useEffect(() => {
  // Load messages on component mount
  loadChatHistory();
}, []);
```

## Data Models

### Message Storage Format
```javascript
{
  id: "uuid-string",
  content: "message text",
  sender: "user" | "bot",
  timestamp: 1640995200000  // Unix timestamp
}
```

### Frontend Message Format (existing)
```javascript
{
  id: number,
  text: string,
  sender: "user" | "bot"
}
```

## Error Handling

- Database connection errors: Log and continue without persistence
- Message loading errors: Display empty chat, allow new messages
- Message saving errors: Log but don't interrupt chat flow

## Testing Strategy

- Test database table creation and message storage
- Test message retrieval and ordering
- Test frontend loading and display
- Test integration with existing chat flow