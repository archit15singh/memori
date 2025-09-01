# Implementation Plan

- [x] 1. Add CORS support to backend
  - Import CORSMiddleware from fastapi.middleware.cors
  - Configure CORS middleware with localhost:3000 and localhost:3001 origins
  - Allow all necessary HTTP methods (GET, POST, PUT, DELETE, OPTIONS)
  - Allow all headers for development
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Fix data model field names for consistency
  - Update InsightCreate model to use 'value' field instead of 'text'
  - Update InsightUpdate model to use 'value' field instead of 'text'
  - Update Insight response model to use 'value' field instead of 'text'
  - Update all endpoint logic to use 'value' field consistently
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Add key-based lookup functionality
  - Create find_insight_by_key helper function
  - Add GET /insights/by-key/{key} endpoint
  - Add PUT /insights/by-key/{key} endpoint
  - Add DELETE /insights/by-key/{key} endpoint
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 4. Add storage for missing memory types
  - Create anchors_db dictionary for anchors storage
  - Create routines_db dictionary for routines storage
  - Create notes_db dictionary for notes storage
  - Create get_memory_db helper function to route to correct storage
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. Create generic memory models and operations
  - Create MemoryCreate model for all memory types
  - Create MemoryUpdate model for all memory types
  - Create Memory response model for all memory types
  - Create create_memory_item generic function
  - Create find_memory_by_key generic function
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 6. Implement anchors CRUD endpoints
  - Add POST /anchors endpoint for creating anchors
  - Add GET /anchors endpoint for listing all anchors
  - Add GET /anchors/by-key/{key} endpoint for getting anchor by key
  - Add PUT /anchors/by-key/{key} endpoint for updating anchor by key
  - Add DELETE /anchors/by-key/{key} endpoint for deleting anchor by key
  - _Requirements: 5.2, 5.6, 5.7_

- [x] 7. Implement routines CRUD endpoints
  - Add POST /routines endpoint for creating routines
  - Add GET /routines endpoint for listing all routines
  - Add GET /routines/by-key/{key} endpoint for getting routine by key
  - Add PUT /routines/by-key/{key} endpoint for updating routine by key
  - Add DELETE /routines/by-key/{key} endpoint for deleting routine by key
  - _Requirements: 5.3, 5.6, 5.7_

- [x] 8. Implement notes CRUD endpoints
  - Add POST /notes endpoint for creating notes
  - Add GET /notes endpoint for listing all notes
  - Add GET /notes/by-key/{key} endpoint for getting note by key
  - Add PUT /notes/by-key/{key} endpoint for updating note by key
  - Add DELETE /notes/by-key/{key} endpoint for deleting note by key
  - _Requirements: 5.4, 5.6, 5.7_

- [ ] 9. Add comprehensive error handling
  - Ensure 404 errors for non-existent memories with proper messages
  - Add validation for memory type parameters
  - Return structured JSON error responses
  - Handle duplicate key scenarios appropriately
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 10. Add data validation
  - Add validator for non-empty key fields in MemoryCreate
  - Add validator for non-empty value fields in MemoryCreate
  - Add memory type validation with allowed types list
  - Add proper error messages for validation failures
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 11. Update frontend API calls to use key-based endpoints
  - Modify saveEdit function to use new key-based PUT endpoints
  - Modify deleteMemory function to use new key-based DELETE endpoints
  - Update error handling to work with new backend responses
  - Test all memory operations work correctly
  - _Requirements: 4.1, 4.2, 6.4_

- [x] 12. Add development testing support
  - Create seed data endpoint with sample data for all memory types
  - Add health check endpoint returning system status and memory counts
  - Add request/response logging for debugging
  - Create test data covering all memory types and operations
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 13. Refactor backend with generic endpoints
  - Create generic POST /{memory_type} endpoint
  - Create generic GET /{memory_type} endpoint
  - Create generic GET /{memory_type}/by-key/{key} endpoint
  - Create generic PUT /{memory_type}/by-key/{key} endpoint
  - Create generic DELETE /{memory_type}/by-key/{key} endpoint
  - Remove duplicate endpoint implementations
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [ ] 14. Add production readiness features
  - Add structured logging with request/response details
  - Add environment configuration for CORS origins
  - Add comprehensive health check with detailed status
  - Add input sanitization and security headers
  - _Requirements: 8.4_

- [ ] 15. Perform integration testing
  - Test frontend loads without CORS errors
  - Test all 4 memory types load correctly
  - Test create, update, delete operations for each memory type
  - Test error scenarios and user feedback
  - Verify loading states and UI responsiveness
  - _Requirements: 1.1, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 6.1, 6.4_