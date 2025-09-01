# Design Document

## Overview

Simple integration that replaces frontend mock data with backend API calls. Core focus: make the existing memory UI work with real backend endpoints for loading, editing, and deleting memories.

## Architecture

```
Frontend Memory UI ──> Backend API Endpoints ──> In-Memory Storage
```

## Components and Interfaces

### Backend API (3 endpoints)
- `GET /memories` - Return all memories
- `PUT /memories/{type}/{id}` - Update a memory  
- `DELETE /memories/{type}/{id}` - Delete a memory

### Frontend API Service
- `memoryApi.js` - Simple service with 3 methods matching the endpoints

### Frontend Integration
- Replace mock data with API calls in existing App.js functions

## Data Models

### Simple Memory Item
```javascript
{
  id: "unique-id",
  key: "Label", 
  value: "Description"
}
```

### API Response
```javascript
{
  identity: [items...],
  principles: [items...], 
  focus: [items...],
  signals: [items...]
}
```

## Implementation Details

### Backend: Add 3 endpoints to main.py
```python
MEMORY_STORE = { "identity": [], "principles": [], "focus": [], "signals": [] }

@app.get("/memories")
@app.put("/memories/{type}/{id}")  
@app.delete("/memories/{type}/{id}")
```

### Frontend: Create memoryApi.js service
```javascript
class MemoryApiService {
  fetchMemories()
  updateMemory(type, id, data)
  deleteMemory(type, id)
}
```

### Frontend: Update App.js
- Load memories on mount
- Update saveEdit to use API
- Update deleteMemory to use API