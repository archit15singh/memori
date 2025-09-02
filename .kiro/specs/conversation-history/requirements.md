# Requirements Document

## Introduction

This feature adds conversation history functionality to the existing chat backend. The system will store user messages and AI responses in the SQLite database and feed the last 10 message pairs back to the AI to maintain conversation context within a single chat session.

## Requirements

### Requirement 1

**User Story:** As a user, I want the AI to remember what we discussed earlier in our conversation, so that I can have a coherent dialogue without repeating context.

#### Acceptance Criteria

1. WHEN a user sends a message THEN the system SHALL store the user message in the database
2. WHEN the AI generates a response THEN the system SHALL store the AI response in the database  
3. WHEN processing a new message THEN the system SHALL retrieve the last 10 message pairs from the database
4. WHEN calling the OpenAI API THEN the system SHALL include the conversation history in the messages array

### Requirement 2

**User Story:** As a user, I want my conversation history to be persisted in the database, so that the context is maintained even if there are temporary connection issues.

#### Acceptance Criteria

1. WHEN the system starts up THEN it SHALL create a conversation_history table if it doesn't exist
2. WHEN storing messages THEN the system SHALL include timestamps for each message
3. WHEN storing messages THEN the system SHALL distinguish between user messages and AI responses
4. WHEN retrieving history THEN the system SHALL order messages by timestamp

### Requirement 3

**User Story:** As a user, I want the conversation history to be limited to recent messages, so that the AI responses remain focused and don't exceed token limits.

#### Acceptance Criteria

1. WHEN retrieving conversation history THEN the system SHALL limit results to the last 10 message pairs (20 total messages)
2. WHEN building the OpenAI messages array THEN the system SHALL include the system message, conversation history, and current user message
3. WHEN there are more than 10 message pairs THEN the system SHALL only use the most recent ones

### Requirement 4

**User Story:** As a developer, I want the conversation history feature to integrate seamlessly with the existing chat endpoint, so that no breaking changes are introduced.

#### Acceptance Criteria

1. WHEN the chat endpoint receives a request THEN it SHALL maintain the same request/response format
2. WHEN storing conversation history THEN it SHALL not affect the response time significantly
3. WHEN the database operations fail THEN the system SHALL still return an AI response without history
4. WHEN retrieving conversation history THEN it SHALL handle empty history gracefully