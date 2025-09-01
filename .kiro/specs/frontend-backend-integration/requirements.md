# Frontend-Backend Integration Requirements

## Introduction

This specification addresses the critical integration issues between the React frontend and FastAPI backend in the reflective journaling application. The frontend expects 4 memory types (insights, anchors, routines, notes) with key-based operations, while the backend currently only supports insights with ID-based operations. This integration work will ensure seamless communication between both systems.

## Requirements

### Requirement 1: CORS Configuration

**User Story:** As a frontend application, I want to communicate with the backend API without CORS errors, so that I can load and manage memory data.

#### Acceptance Criteria

1. WHEN the frontend makes a request to the backend THEN the backend SHALL include proper CORS headers
2. WHEN the frontend runs on localhost:3000 THEN the backend SHALL allow cross-origin requests from this origin
3. WHEN the frontend makes OPTIONS preflight requests THEN the backend SHALL respond with appropriate CORS headers

### Requirement 2: Data Model Consistency

**User Story:** As a frontend application, I want to send and receive data with consistent field names, so that memory operations work correctly.

#### Acceptance Criteria

1. WHEN the frontend sends memory data THEN it SHALL use the field name "value" for content
2. WHEN the backend receives memory data THEN it SHALL accept the field name "value" for content
3. WHEN the backend returns memory data THEN it SHALL include the field name "value" for content
4. WHEN memory updates are performed THEN both systems SHALL use consistent field naming

### Requirement 3: Memory Type Support

**User Story:** As a user, I want to manage four different types of memories (insights, anchors, routines, notes), so that I can organize my reflective content effectively.

#### Acceptance Criteria

1. WHEN the frontend requests insights THEN the backend SHALL provide insights CRUD operations
2. WHEN the frontend requests anchors THEN the backend SHALL provide anchors CRUD operations
3. WHEN the frontend requests routines THEN the backend SHALL provide routines CRUD operations
4. WHEN the frontend requests notes THEN the backend SHALL provide notes CRUD operations
5. WHEN any memory type is accessed THEN the backend SHALL maintain separate storage for each type

### Requirement 4: Key-Based Operations

**User Story:** As a frontend application, I want to perform memory operations using user-defined keys, so that I can update and delete specific memories without managing backend IDs.

#### Acceptance Criteria

1. WHEN the frontend updates a memory THEN it SHALL use the memory's key in the URL path
2. WHEN the frontend deletes a memory THEN it SHALL use the memory's key in the URL path
3. WHEN the backend receives key-based requests THEN it SHALL locate memories by their key field
4. WHEN a key is not found THEN the backend SHALL return a 404 error with appropriate message

### Requirement 5: API Endpoint Completeness

**User Story:** As a frontend application, I want all expected API endpoints to exist, so that all memory management features work without errors.

#### Acceptance Criteria

1. WHEN the frontend requests GET /insights THEN the backend SHALL return all insights
2. WHEN the frontend requests GET /anchors THEN the backend SHALL return all anchors
3. WHEN the frontend requests GET /routines THEN the backend SHALL return all routines
4. WHEN the frontend requests GET /notes THEN the backend SHALL return all notes
5. WHEN the frontend makes PUT requests to /{type}/by-key/{key} THEN the backend SHALL update the specified memory
6. WHEN the frontend makes DELETE requests to /{type}/by-key/{key} THEN the backend SHALL delete the specified memory

### Requirement 6: Error Handling Consistency

**User Story:** As a frontend application, I want consistent error responses from the backend, so that I can provide appropriate user feedback.

#### Acceptance Criteria

1. WHEN a memory is not found THEN the backend SHALL return HTTP 404 with error details
2. WHEN invalid data is submitted THEN the backend SHALL return HTTP 422 with validation errors
3. WHEN an invalid memory type is requested THEN the backend SHALL return HTTP 400 with error message
4. WHEN any error occurs THEN the backend SHALL return structured error responses in JSON format

### Requirement 7: Data Validation

**User Story:** As a system, I want to validate memory data to ensure data quality and prevent errors.

#### Acceptance Criteria

1. WHEN memory data is created THEN the key field SHALL not be empty
2. WHEN memory data is created THEN the value field SHALL not be empty
3. WHEN invalid memory types are used THEN the system SHALL reject the request
4. WHEN duplicate keys are created within the same memory type THEN the system SHALL handle appropriately

### Requirement 8: Development Testing Support

**User Story:** As a developer, I want test data and health check endpoints, so that I can verify the integration works correctly.

#### Acceptance Criteria

1. WHEN the system is in development mode THEN it SHALL provide a seed data endpoint
2. WHEN the health check endpoint is called THEN it SHALL return system status and memory counts
3. WHEN test data is seeded THEN all memory types SHALL have sample data for testing
4. WHEN the system starts THEN it SHALL log important operations for debugging