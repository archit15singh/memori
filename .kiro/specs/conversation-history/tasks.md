# Implementation Plan

- [x] 1. Create conversation history database table
  - Modify the `init_database()` function to create the `conversation_history` table
  - Add table creation SQL with proper schema (id, message_type, content, timestamp)
  - _Requirements: 2.1_

- [x] 2. Implement message storage function
  - Create `store_message(message_type: str, content: str)` function
  - Handle database connection and INSERT operations
  - Include proper error handling for database failures
  - _Requirements: 1.1, 1.2, 2.2, 2.3_

- [x] 3. Implement conversation history retrieval function
  - Create `get_recent_conversation_history()` function that returns last 10 message pairs
  - Order messages by timestamp (oldest first for proper conversation flow)
  - Limit results to 20 messages total (10 pairs)
  - _Requirements: 1.3, 2.4, 3.1, 3.3_

- [x] 4. Create OpenAI messages builder function
  - Implement `build_messages_for_openai(user_message: str, history: List[dict])` function
  - Combine system message, conversation history, and current user message
  - Convert internal message format to OpenAI API format (role/content structure)
  - _Requirements: 1.4, 3.2_

- [x] 5. Modify chat endpoint to use conversation history
  - Update `chat_endpoint()` function to store incoming user message
  - Retrieve conversation history before calling OpenAI API
  - Pass history to the OpenAI messages builder
  - Store AI response after receiving it from OpenAI
  - Maintain existing error handling and response format
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4_

- [x] 6. Update get_ai_response function to accept conversation history
  - Modify `get_ai_response()` function signature to accept history parameter
  - Use the messages builder function to construct the full messages array
  - Replace hardcoded messages array with dynamic history-aware version
  - _Requirements: 1.4, 3.2_