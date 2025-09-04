/**
 * ClearApiService - API service layer for clear functionality
 * 
 * Handles HTTP requests to the FastAPI backend's /clear endpoint with proper
 * error handling, environment-based configuration, and response parsing.
 */

class ClearApiService {
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
   * Clear all memories and chat history from the backend
   * @returns {Promise<Object>} Promise that resolves to the clear response
   * @throws {Error} Throws error for various failure scenarios
   */
  async clearAll() {
    // Validate environment before making request
    if (!this.baseURL) {
      throw new Error('Clear service configuration error. Please refresh the page and try again.');
    }

    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      // Make the API request with enhanced error context
      const response = await fetch(`${this.baseURL}/clear`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      // Clear timeout since request completed
      clearTimeout(timeoutId);

      // Validate response object
      if (!response) {
        throw new Error('No response received from clear service. Please try again.');
      }

      // Handle different response status codes
      if (!response.ok) {
        await this.handleApiError(response);
      }

      // Parse and validate response with additional error handling
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('Failed to parse clear response JSON:', parseError);
        throw new Error('Invalid response format from clear service. Please try again.');
      }

      // Validate and return response
      return this.parseClearResponse(data);

    } catch (error) {
      clearTimeout(timeoutId);
      
      // Add context to the error for better debugging
      if (error.message && !error.message.includes('Clear service') && !error.message.includes('timed out')) {
        console.error('Clear API error context:', {
          baseURL: this.baseURL,
          timeout: this.timeout,
          errorType: error.name,
          errorMessage: error.message
        });
      }
      
      return this.handleRequestError(error);
    }
  }

  /**
   * Handle API error responses
   * @param {Response} response - The fetch response object
   * @throws {Error} Throws appropriate error based on status code
   */
  async handleApiError(response) {
    let errorMessage = 'An error occurred while clearing data.';

    try {
      const errorData = await response.json();
      
      switch (response.status) {
        case 400:
          errorMessage = 'Invalid clear request. Please try again.';
          break;
        case 500:
          errorMessage = 'Clear service temporarily unavailable. Please try again.';
          break;
        default:
          // Use error detail from response if available
          if (errorData && errorData.detail) {
            errorMessage = `Server error: ${errorData.detail}`;
          } else {
            errorMessage = `Server error (${response.status}) while clearing data.`;
          }
      }
    } catch (parseError) {
      // If we can't parse the error response, use status-based message
      switch (response.status) {
        case 400:
          errorMessage = 'Invalid clear request. Please try again.';
          break;
        case 500:
          errorMessage = 'Clear service temporarily unavailable. Please try again.';
          break;
        default:
          errorMessage = `Server error (${response.status}) while clearing data.`;
      }
    }

    throw new Error(errorMessage);
  }

  /**
   * Handle request errors (network, timeout, etc.)
   * @param {Error} error - The error object
   * @throws {Error} Throws appropriate error based on error type
   */
  handleRequestError(error) {
    // Handle different error types with enhanced specificity
    if (error.name === 'AbortError') {
      throw new Error('Request to clear data timed out. Please try again.');
    }
    
    if (error.message === 'Failed to fetch') {
      throw new Error('Unable to connect to clear service. Please check your connection and try again.');
    }
    
    if (error.code === 'NETWORK_ERROR' || error.message.includes('NetworkError')) {
      throw new Error('Network error occurred. Please check your connection and try again.');
    }
    
    if (error.message.includes('ECONNREFUSED') || error.message.includes('Connection refused')) {
      throw new Error('Clear service is not available. Please try again later.');
    }
    
    if (error.message.includes('ENOTFOUND') || error.message.includes('getaddrinfo')) {
      throw new Error('Unable to reach clear service. Please check your connection.');
    }

    // Re-throw if it's already a handled error
    if (error.message.includes('timed out') || 
        error.message.includes('Unable to connect') ||
        error.message.includes('Clear service') ||
        error.message.includes('Invalid clear request') ||
        error.message.includes('Network error') ||
        error.message.includes('not available')) {
      throw error;
    }

    // Generic error fallback with more context
    console.error('Unhandled clear API error:', error);
    throw new Error('An unexpected error occurred while clearing data. Please try again.');
  }

  /**
   * Parse and validate the clear response
   * @param {Object} data - The response data from the API
   * @returns {Object} Parsed response object with success status and message
   * @throws {Error} Throws error if response format is invalid
   */
  parseClearResponse(data) {
    // Validate response structure
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid response format from clear service.');
    }

    // Check for required response fields
    if (!data.hasOwnProperty('success') || !data.hasOwnProperty('message')) {
      throw new Error('Invalid response format: missing success or message field.');
    }

    // Validate success field is boolean
    if (typeof data.success !== 'boolean') {
      throw new Error('Invalid response format: success must be boolean.');
    }

    // Validate message field is string
    if (typeof data.message !== 'string') {
      throw new Error('Invalid response format: message must be string.');
    }

    // Return the validated response
    return {
      success: data.success,
      message: data.message
    };
  }

  /**
   * Get user-friendly error message for display
   * @param {Error} error - The error object
   * @returns {string} User-friendly error message
   */
  getErrorMessage(error) {
    if (!error || !error.message) {
      return 'An unexpected error occurred while clearing data. Please try again.';
    }

    // Return the error message as-is since we've already formatted them appropriately
    return error.message;
  }
}

// Export a singleton instance
const clearApiService = new ClearApiService();
export default clearApiService;

// Also export the class for testing purposes
export { ClearApiService };