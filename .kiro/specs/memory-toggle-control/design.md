# Design Document

## Overview

This feature adds a memory toggle control to the chat application, allowing users to enable/disable memory functionality. When disabled, the system will not extract memories from conversations or use existing memories to inform AI responses.

## Architecture

The memory toggle will be implemented as a frontend state that controls both UI behavior and API requests. The backend will receive a new parameter to indicate whether memory functionality should be active for each chat request.

### Current Memory Flow
1. User sends message → Chat endpoint
2. AI generates response using memories as context
3. System extracts new memories from conversation
4. Memories are stored in database

### New Memory Flow with Toggle
1. User sends message + memory enabled flag → Chat endpoint
2. If memory enabled: AI uses memories, extracts new memories
3. If memory disabled: AI ignores memories, no extraction

## Components and Interfaces

### Frontend Changes

#### Memory Toggle Component
- Location: Memory area header
- Type: Toggle switch with ON/OFF states
- Persistence: localStorage
- Default: ON (enabled)

#### Visual States
- **Memory ON**: Normal appearance, toggle shows enabled state
- **Memory OFF**: Dimmed memory sections, "Memory disabled" text, toggle shows disabled state

#### State Management
```javascript
const [memoryEnabled, setMemoryEnabled] = useState(true);

// Load from localStorage on mount
useEffect(() => {
  const saved = localStorage.getItem('memoryEnabled');
  if (saved !== null) {
    setMemoryEnabled(JSON.parse(saved));
  }
}, []);

// Save to localStorage on change
const toggleMemory = (enabled) => {
  setMemoryEnabled(enabled);
  localStorage.setItem('memoryEnabled', JSON.stringify(enabled));
};
```

### Backend Changes

#### Chat Request Model
Add optional memory flag to ChatRequest:
```python
class ChatRequest(BaseModel):
    message: str = Field(...)
    memory_enabled: bool = Field(default=True, description="Whether to use memory functionality")
```

#### Modified Functions

**get_ai_response(message: str, memory_enabled: bool = True)**
- When memory_enabled=False: Skip memory loading and context rendering
- Return clean response without memory context

**chat_endpoint(request: ChatRequest)**
- When memory_enabled=False: Skip memory extraction after response
- Pass memory_enabled flag to get_ai_response

## Data Models

### Frontend State
```javascript
{
  memoryEnabled: boolean,  // Current toggle state
  // ... existing state
}
```

### Backend Request
```python
{
  "message": "Hello",
  "memory_enabled": true  // Optional, defaults to true
}
```

## Error Handling

- localStorage errors: Fall back to default enabled state
- Backend compatibility: memory_enabled parameter is optional for backward compatibility
- Invalid toggle states: Reset to default enabled

## Testing Strategy

### Frontend Tests
- Toggle state persistence across page refreshes
- Visual state changes when toggling
- API requests include correct memory_enabled flag

### Backend Tests  
- Chat responses without memory context when disabled
- No memory extraction when disabled
- Backward compatibility with requests missing memory_enabled flag

### Integration Tests
- End-to-end memory disable/enable flow
- Memory sections show correct disabled state
- Chat responses differ based on memory state