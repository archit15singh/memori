# Frontend-Backend Integration Design

## Overview

This design addresses the integration gaps between the React frontend and FastAPI backend by implementing missing API endpoints, fixing data model inconsistencies, and adding proper CORS support. The solution maintains backward compatibility while extending functionality to support all four memory types expected by the frontend.

## Architecture

### Current State
- **Frontend**: Expects 4 memory types (insights, anchors, routines, notes) with key-based operations
- **Backend**: Only supports insights with ID-based operations
- **Issues**: CORS blocking, missing endpoints, data model mismatch

### Target State
- **Unified API**: All 4 memory types supported with consistent CRUD operations
- **Key-based Operations**: Frontend can use user-defined keys for updates/deletes
- **CORS Enabled**: Cross-origin requests work seamlessly
- **Data Consistency**: Unified field naming between frontend and backend

## Components and Interfaces

### Backend API Structure

#### Memory Storage
```python
# Separate storage for each memory type
insights_db: Dict[str, dict] = {}
anchors_db: Dict[str, dict] = {}
routines_db: Dict[str, dict] = {}
notes_db: Dict[str, dict] = {}
```

#### Data Models
```python
class MemoryCreate(BaseModel):
    key: str
    value: str  # Matches frontend expectation

class MemoryUpdate(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None

class Memory(BaseModel):
    id: str      # Backend-generated UUID
    key: str     # User-defined identifier
    value: str   # Content
```

#### API Endpoints
```
GET    /{memory_type}                 # List all memories of type
POST   /{memory_type}                 # Create new memory
GET    /{memory_type}/by-key/{key}    # Get memory by key
PUT    /{memory_type}/by-key/{key}    # Update memory by key
DELETE /{memory_type}/by-key/{key}    # Delete memory by key
GET    /health                        # Health check
POST   /dev/seed-data                 # Development test data
```

### Frontend Integration Points

#### API Communication
```javascript
// Consistent API calls for all memory types
const API_BASE = 'http://localhost:8000';

// Load memories
fetch(`${API_BASE}/${type}`)

// Update memory
fetch(`${API_BASE}/${type}/by-key/${key}`, {
  method: 'PUT',
  body: JSON.stringify({ value: newValue })
})

// Delete memory
fetch(`${API_BASE}/${type}/by-key/${key}`, {
  method: 'DELETE'
})
```

## Data Models

### Memory Entity
```
Memory {
  id: string (UUID)           # Backend identifier
  key: string                 # User-defined key
  value: string              # Content
}
```

### Memory Types
- **insights**: Personal learnings and realizations
- **anchors**: Grounding techniques and coping mechanisms
- **routines**: Daily habits and practices
- **notes**: General observations and thoughts

## Error Handling

### HTTP Status Codes
- **200 OK**: Successful GET, PUT operations
- **201 Created**: Successful POST operations
- **400 Bad Request**: Invalid memory type or validation errors
- **404 Not Found**: Memory not found by key
- **422 Unprocessable Entity**: Pydantic validation errors

### Error Response Format
```json
{
  "detail": "Error message description"
}
```

## Testing Strategy

### Unit Tests
- Memory CRUD operations for each type
- Key-based lookup functionality
- Data validation rules
- Error handling scenarios

### Integration Tests
- Frontend-backend communication
- CORS functionality
- End-to-end memory operations
- Error propagation

### Development Testing
- Seed data endpoint for quick testing
- Health check endpoint for monitoring
- Logging for debugging integration issues

## Implementation Phases

### Phase 1: Critical Fixes
1. Add CORS middleware
2. Fix data model field names (text → value)
3. Add key-based lookup support

### Phase 2: Memory Type Support
1. Add storage for missing memory types
2. Create generic memory operations
3. Implement all missing endpoints

### Phase 3: Frontend Adaptation
1. Update API calls to use key-based endpoints
2. Ensure consistent error handling
3. Test all memory operations

### Phase 4: Optimization
1. Refactor to generic endpoints
2. Add comprehensive validation
3. Improve error messages

### Phase 5: Production Readiness
1. Add logging and monitoring
2. Add health checks
3. Environment configuration
4. Performance optimization

## Security Considerations

### CORS Configuration
- Restrict origins to known frontend URLs
- Limit allowed methods to necessary operations
- Validate all cross-origin requests

### Input Validation
- Sanitize all user inputs
- Validate memory type parameters
- Prevent injection attacks through key/value fields

### Data Protection
- No sensitive data in memory keys
- Proper error messages without data leakage
- Rate limiting for API endpoints (future enhancement)

## Performance Considerations

### Memory Usage
- In-memory storage suitable for development
- Consider database migration for production
- Monitor memory growth with usage

### Response Times
- O(1) operations for key-based lookups
- Efficient data structures for storage
- Minimal processing overhead

### Scalability
- Current design supports single instance
- Database migration needed for multi-instance
- Consider caching strategies for high load

## Monitoring and Observability

### Logging
- Request/response logging
- Error tracking and alerting
- Performance metrics collection

### Health Checks
- API availability monitoring
- Memory usage tracking
- Database connectivity (future)

### Metrics
- Request counts by endpoint
- Error rates by operation type
- Response time distributions