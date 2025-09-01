# Design Document

## Overview

Replace in-memory `MEMORY_STORE` with SQLite database. Use built-in SQLite3, keep existing API interface unchanged.

## Architecture

### Core Components
- **SQLite Database**: `chat_app.db` file in backend directory
- **Simple Database Functions**: Direct SQLite operations, no complex ORM
- **Single Table**: `memories` table stores all memory data

### Integration
- Replace `MEMORY_STORE` dictionary with database calls
- Initialize database on app startup
- Maintain exact same API responses

## Data Models

### Database Schema
```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);
```

### Memory Types
- `identity`, `principles`, `focus`, `signals`

## Error Handling

- Use SQLite's built-in error handling
- Let FastAPI handle HTTP error responses
- Simple approach: if database fails, let the exception bubble up