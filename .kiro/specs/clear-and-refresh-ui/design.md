# Design Document

## Overview

This feature adds a simple "Clear All" button to the UI that clears both memories and chat history from the database, then refreshes the interface to show an empty state. The implementation leverages the existing FastAPI backend architecture and React frontend patterns.

## Architecture

The clear functionality follows the existing client-server architecture:

- **Frontend**: React component with a clear button that calls backend API
- **Backend**: New FastAPI endpoint that clears both memories and messages tables
- **Database**: SQLite operations to truncate both tables
- **UI State**: React state updates to reflect empty state immediately

## Components and Interfaces

### Backend API Endpoint

**New Endpoint**: `DELETE /clear`
- Clears all records from `memories` table
- Clears all records from `messages` table  
- Returns success confirmation
- Uses existing database connection patterns from `main.py`

**Response Model**:
```python
class ClearResponse(BaseModel):
    success: bool
    message: str
```

### Frontend Integration

**Clear Button Component**:
- Simple button in the main App.js interface
- Positioned near memory toggle controls
- Uses existing styling patterns from App.css

**API Service Method**:
- New method in existing API service pattern
- Follows same error handling as `chatApi.js` and `memoryApi.js`
- Handles network errors and timeouts

### State Management

**Frontend State Updates**:
- Clear `messages` array immediately after API call
- Clear all memory arrays (`insights`, `anchors`, `routines`, `notes`)
- Reset to initial empty state
- Show success feedback using existing feedback system

## Data Models

### Database Operations

**Clear Memories**:
```sql
DELETE FROM memories;
```

**Clear Messages**:
```sql
DELETE FROM messages;
```

**Transaction Handling**:
- Wrap both operations in a single transaction
- Rollback if either operation fails
- Log operations for debugging

### API Response

```json
{
  "success": true,
  "message": "All data cleared successfully"
}
```

## Error Handling

**Backend Error Scenarios**:
- Database connection failure
- Transaction rollback scenarios
- Partial clear failures

**Frontend Error Handling**:
- Network connectivity issues
- API timeout scenarios
- Display error feedback to user
- Maintain current state if clear fails

**User Feedback**:
- Confirmation dialog before clearing
- Loading state during operation
- Success/error messages using existing feedback system

## Testing Strategy

**Manual Testing Focus** (following absolute rules):
- Test clear button functionality
- Verify confirmation dialog works
- Confirm both memories and chat are cleared
- Test error scenarios (network issues)
- Verify UI state updates correctly