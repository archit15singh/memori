/**
 * ChatApiService - API service layer for backend communication
 * 
 * Handles HTTP requests to the FastAPI backend's /chat endpoint with proper
 * error handling, environment-based configuration, and response parsing.
 */

class ChatApiService {
  constructor() {
    this.baseURL = this.getBaseURL();
    this.timeout = this.getTimeout();
  }

  /**
   * Get the appropriate base URL based on environment
   * @returns {string} The API base URL
   */
  getBaseURL() {
    const isDevelopment = process.env.NODE_ENV === 'development';
    
    if (isDevelopment) {
      return 'http://localhost:8000';
    }
    
    // In production, use environment variable or fallback to localhost
    return process.env.REACT_APP_API_URL || 'http://localhost:8000';
  }

  /**
   * Get the appropriate timeout based on environment
   * @returns {number} Timeout in milliseconds
   */
  getTimeout() {
    const isDevelopment = process.env.NODE_ENV === 'development';
    return isDevelopment ? 10000 : 15000; // 10s dev, 15s prod
  }

  /**
   * Send a message to the chat endpoint
   * @param {string} message - The user's message to send
   * @returns {Promise<Object>} Promise that resolves to the API response
   * @throws {Error} Throws error for various failure scenarios
   */
  async sendMessage(message) {
    // Validate input
    if (!message || typeof message !== 'string' || !message.trim()) {
      throw new Error('Message cannot be empty');
    }

    // Prepare request configuration
    const requestConfig = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: message.trim() }),
    };

    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      // Make the API request
      const response = await fetch(`${this.baseURL}/chat`, {
        ...requestConfig,
        signal: controller.signal,
      });

      // Clear timeout since request completed
      clearTimeout(timeoutId);

      // Handle different response status codes
      if (!response.ok) {
        await this.handleApiError(response);
      }

      // Parse and validate response
      const data = await response.json();
      return this.parseResponse(data);

    } catch (error) {
      clearTimeout(timeoutId);
      
      // Handle different error types
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.');
      }
      
      if (error.message === 'Failed to fetch' || error.code === 'NETWORK_ERROR') {
        throw new Error('Unable to connect to chat service. Please check your connection and try again.');
      }

      // Re-throw if it's already a handled error
      if (error.message.includes('Request timed out') || 
          error.message.includes('Unable to connect') ||
          error.message.includes('Chat service') ||
          error.message.includes('Message format error')) {
        throw error;
      }

      // Generic error fallback
      throw new Error('An unexpected error occurred. Please try again.');
    }
  }

  /**
   * Handle API error responses
   * @param {Response} response - The fetch response object
   * @throws {Error} Throws appropriate error based on status code
   */
  async handleApiError(response) {
    let errorMessage = 'An error occurred while processing your request.';

    try {
      const errorData = await response.json();
      
      switch (response.status) {
        case 400:
          errorMessage = 'Message format error. Please try again.';
          break;
        case 422:
          errorMessage = 'Message format error. Please try again.';
          break;
        case 500:
          errorMessage = 'Chat service temporarily unavailable. Please try again.';
          break;
        default:
          // Use error detail from response if available
          if (errorData && errorData.detail) {
            errorMessage = `Server error: ${errorData.detail}`;
          } else {
            errorMessage = `Server error (${response.status}). Please try again.`;
          }
      }
    } catch (parseError) {
      // If we can't parse the error response, use status-based message
      switch (response.status) {
        case 400:
        case 422:
          errorMessage = 'Message format error. Please try again.';
          break;
        case 500:
          errorMessage = 'Chat service temporarily unavailable. Please try again.';
          break;
        default:
          errorMessage = `Server error (${response.status}). Please try again.`;
      }
    }

    throw new Error(errorMessage);
  }

  /**
   * Parse and validate the API response
   * @param {Object} data - The response data from the API
   * @returns {Object} Parsed response object with properly formatted message text
   * @throws {Error} Throws error if response format is invalid
   */
  parseResponse(data) {
    // Validate response structure
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid response format from server.');
    }

    // Check for required response field
    if (!data.hasOwnProperty('response')) {
      throw new Error('Invalid response format from server.');
    }

    // Handle different response value types
    let responseText;
    if (typeof data.response === 'string') {
      responseText = data.response.trim();
    } else if (data.response === null || data.response === undefined) {
      responseText = '';
    } else {
      // Convert non-string responses to string
      responseText = String(data.response).trim();
    }

    // Ensure we have a meaningful response
    if (!responseText) {
      responseText = 'No response received.';
    }

    // Return the validated and formatted response
    return {
      response: responseText
    };
  }

  /**
   * Get user-friendly error message for display
   * @param {Error} error - The error object
   * @returns {string} User-friendly error message
   */
  getErrorMessage(error) {
    if (!error || !error.message) {
      return 'An unexpected error occurred. Please try again.';
    }

    // Return the error message as-is since we've already formatted them appropriately
    return error.message;
  }
}

// Export a singleton instance
const chatApiService = new ChatApiService();
export default chatApiService;

// Also export the class for testing purposes
export { ChatApiService };