# Design Document

## Overview

The frontend-backend integration will replace the current mock chat responses in the React frontend with real HTTP API calls to the FastAPI backend's `/chat` endpoint. The design focuses on maintaining the existing user experience while adding proper error handling, loading states, and API communication.

## Architecture

The integration will follow a clean separation of concerns:

```
┌─────────────────┐    HTTP POST     ┌─────────────────┐
│   React App     │ ───────────────> │  FastAPI Backend│
│   (Frontend)    │                  │   /chat endpoint│
│                 │ <─────────────── │                 │
│ - Chat UI       │    JSON Response │ - Chat Logic    │
│ - API Service   │                  │ - CORS Enabled  │
│ - Error Handling│                  │ - Error Handling│
└─────────────────┘                  └─────────────────┘
```

## Components and Interfaces

### API Service Layer
- **Purpose**: Centralized HTTP communication with backend
- **Location**: `frontend/src/services/chatApi.js`
- **Responsibilities**:
  - Make HTTP requests to backend `/chat` endpoint
  - Handle request/response formatting
  - Manage API configuration (base URL)
  - Provide error handling utilities

### Enhanced Chat Component
- **Purpose**: Updated App.js to use real API instead of mocks
- **Location**: `frontend/src/App.js`
- **Responsibilities**:
  - Replace mock `sendMessage` function with API calls
  - Handle loading states during API requests
  - Maintain existing UI/UX patterns
  - Display API responses seamlessly

## Data Models

### API Request Format
```javascript
{
  message: "User's chat message"
}
```

### API Response Format (Success)
```javascript
{
  response: "Backend's response message"
}
```

### API Response Format (Error)
```javascript
{
  detail: "Error description"
}
```

### Frontend Message Object
```javascript
{
  id: timestamp,
  text: "message content",
  sender: "user" | "bot"
}
```

## API Communication

The system will handle API communication simply and directly:

### Successful Responses
- **Scenario**: Backend returns successful response
- **Response**: Display the response message as a bot message
- **Action**: Continue conversation flow

### Simple Integration
- **Approach**: Direct API calls without complex error handling
- **Focus**: Seamless user experience with minimal complexity
- **Assumption**: Backend is available and functioning correctly

## API Configuration

### Environment-based Configuration
```javascript
const API_CONFIG = {
  development: {
    baseURL: 'http://localhost:8000',
    timeout: 10000
  },
  production: {
    baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
    timeout: 15000
  }
};
```

### Request Configuration
- **Method**: POST
- **Endpoint**: `/chat`
- **Headers**: 
  - `Content-Type: application/json`
- **Timeout**: 10 seconds (development), 15 seconds (production)

## Implementation Details

### API Service Structure
```javascript
// chatApi.js
class ChatApiService {
  constructor() {
    this.baseURL = this.getBaseURL();
    this.timeout = this.getTimeout();
  }
  
  async sendMessage(message) {
    // Implementation details
  }
  
  handleApiError(error) {
    // Error handling logic
  }
}
```

### Updated sendMessage Function
```javascript
const sendMessage = async (userMessage) => {
  // Add user message immediately
  const newUserMessage = { id: Date.now(), text: userMessage, sender: 'user' };
  setMessages(prev => [...prev, newUserMessage]);
  
  setIsLoading(true);
  
  // Call API and display response
  const response = await chatApi.sendMessage(userMessage);
  const botResponse = { 
    id: Date.now() + 1, 
    text: response.response, 
    sender: 'bot' 
  };
  setMessages(prev => [...prev, botResponse]);
  setIsLoading(false);
};
```

### Loading State Management
- Maintain existing loading indicator ("Bot is typing...")
- Disable input field during API calls
- Re-enable input after response or error
- Auto-focus input after completion

### Response Display
- Show API responses as bot messages
- Maintain conversation flow with backend responses
- Keep consistent message styling and formatting
- Integrate responses seamlessly into chat interface

## Manual Verification

### Integration Points
- Verify CORS configuration works correctly
- Confirm request/response format compatibility
- Check error response handling matches backend error formats
- Validate loading states work as expected

### Verification Scenarios
- Verify with backend running (successful communication)
- Confirm message sending and response display
- Validate conversation flow with real API responses
- Check loading states during API calls
- Ensure input field behavior works correctly

## Backward Compatibility

- Maintain all existing UI components and styling
- Keep the same message flow and user experience
- Preserve existing state management patterns
- Ensure no breaking changes to component interfaces