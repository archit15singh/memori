/**
 * MemoryApiService - API service layer for memory backend communication
 * 
 * Handles HTTP requests to the FastAPI backend's memory endpoints with proper
 * error handling, environment-based configuration, and response parsing.
 */

class MemoryApiService {
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
    return isDevelopment ? 300000 : 300000; // 5 minutes for both dev and prod
  }

  /**
   * Fetch all memories from the backend
   * @returns {Promise<Object>} Promise that resolves to memories organized by type
   * @throws {Error} Throws error for various failure scenarios
   */
  async fetchMemories() {
    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      // Make the API request
      const response = await fetch(`${this.baseURL}/memories`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      // Clear timeout since request completed
      clearTimeout(timeoutId);

      // Handle different response status codes
      if (!response.ok) {
        await this.handleApiError(response, 'fetch memories');
      }

      // Parse and validate response
      const data = await response.json();
      return this.parseMemoriesResponse(data);

    } catch (error) {
      clearTimeout(timeoutId);
      return this.handleRequestError(error, 'fetch memories');
    }
  }

  /**
   * Update a memory item on the backend
   * @param {string} type - The memory type (identity, principles, focus, signals)
   * @param {string} id - The memory item ID
   * @param {Object} memoryData - The updated memory data with key and value
   * @returns {Promise<Object>} Promise that resolves to the updated memory item
   * @throws {Error} Throws error for various failure scenarios
   */
  async updateMemory(type, id, memoryData) {
    // Validate input
    if (!type || typeof type !== 'string' || !type.trim()) {
      throw new Error('Memory type cannot be empty');
    }
    if (!id || typeof id !== 'string' || !id.trim()) {
      throw new Error('Memory ID cannot be empty');
    }
    if (!memoryData || !memoryData.key || !memoryData.value) {
      throw new Error('Memory data must include key and value');
    }

    // Prepare request configuration
    const requestConfig = {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: id,
        key: memoryData.key,
        value: memoryData.value
      }),
    };

    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      // Make the API request
      const response = await fetch(`${this.baseURL}/memories/${type}/${id}`, {
        ...requestConfig,
        signal: controller.signal,
      });

      // Clear timeout since request completed
      clearTimeout(timeoutId);

      // Handle different response status codes
      if (!response.ok) {
        await this.handleApiError(response, 'update memory');
      }

      // Parse and validate response
      const data = await response.json();
      return this.parseMemoryItemResponse(data);

    } catch (error) {
      clearTimeout(timeoutId);
      return this.handleRequestError(error, 'update memory');
    }
  }

  /**
   * Delete a memory item from the backend
   * @param {string} type - The memory type (identity, principles, focus, signals)
   * @param {string} id - The memory item ID
   * @returns {Promise<void>} Promise that resolves when deletion is complete
   * @throws {Error} Throws error for various failure scenarios
   */
  async deleteMemory(type, id) {
    // Validate input
    if (!type || typeof type !== 'string' || !type.trim()) {
      throw new Error('Memory type cannot be empty');
    }
    if (!id || typeof id !== 'string' || !id.trim()) {
      throw new Error('Memory ID cannot be empty');
    }

    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      // Make the API request
      const response = await fetch(`${this.baseURL}/memories/${type}/${id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      // Clear timeout since request completed
      clearTimeout(timeoutId);

      // Handle different response status codes
      if (!response.ok) {
        await this.handleApiError(response, 'delete memory');
      }

      // For 204 No Content, there's no response body to parse
      return;

    } catch (error) {
      clearTimeout(timeoutId);
      return this.handleRequestError(error, 'delete memory');
    }
  }

  /**
   * Handle API error responses
   * @param {Response} response - The fetch response object
   * @param {string} operation - The operation being performed (for error context)
   * @throws {Error} Throws appropriate error based on status code
   */
  async handleApiError(response, operation) {
    let errorMessage = `An error occurred while trying to ${operation}.`;

    try {
      const errorData = await response.json();
      
      switch (response.status) {
        case 400:
          errorMessage = `Invalid request to ${operation}. Please check your data.`;
          break;
        case 404:
          errorMessage = `Memory item not found. It may have been deleted.`;
          break;
        case 422:
          errorMessage = `Invalid data format for ${operation}. Please check your input.`;
          break;
        case 500:
          errorMessage = `Memory service temporarily unavailable. Please try again.`;
          break;
        default:
          // Use error detail from response if available
          if (errorData && errorData.detail) {
            errorMessage = `Server error: ${errorData.detail}`;
          } else {
            errorMessage = `Server error (${response.status}) while trying to ${operation}.`;
          }
      }
    } catch (parseError) {
      // If we can't parse the error response, use status-based message
      switch (response.status) {
        case 400:
        case 422:
          errorMessage = `Invalid request to ${operation}. Please check your data.`;
          break;
        case 404:
          errorMessage = `Memory item not found. It may have been deleted.`;
          break;
        case 500:
          errorMessage = `Memory service temporarily unavailable. Please try again.`;
          break;
        default:
          errorMessage = `Server error (${response.status}) while trying to ${operation}.`;
      }
    }

    throw new Error(errorMessage);
  }

  /**
   * Handle request errors (network, timeout, etc.)
   * @param {Error} error - The error object
   * @param {string} operation - The operation being performed (for error context)
   * @throws {Error} Throws appropriate error based on error type
   */
  handleRequestError(error, operation) {
    // Handle different error types
    if (error.name === 'AbortError') {
      throw new Error(`Request to ${operation} timed out. Please try again.`);
    }
    
    if (error.message === 'Failed to fetch' || error.code === 'NETWORK_ERROR') {
      throw new Error(`Unable to connect to memory service. Please check your connection and try again.`);
    }

    // Re-throw if it's already a handled error
    if (error.message.includes('timed out') || 
        error.message.includes('Unable to connect') ||
        error.message.includes('Memory service') ||
        error.message.includes('cannot be empty') ||
        error.message.includes('must include')) {
      throw error;
    }

    // Generic error fallback
    throw new Error(`An unexpected error occurred while trying to ${operation}. Please try again.`);
  }

  /**
   * Parse and validate the memories response
   * @param {Object} data - The response data from the API
   * @returns {Object} Parsed response object with memories organized by type
   * @throws {Error} Throws error if response format is invalid
   */
  parseMemoriesResponse(data) {
    // Validate response structure
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid response format from memory service.');
    }

    // Check for required memory types
    const requiredTypes = ['identity', 'principles', 'focus', 'signals'];
    for (const type of requiredTypes) {
      if (!data.hasOwnProperty(type)) {
        throw new Error(`Invalid response format: missing ${type} memories.`);
      }
      if (!Array.isArray(data[type])) {
        throw new Error(`Invalid response format: ${type} must be an array.`);
      }
    }

    // Return the validated response
    return {
      identity: data.identity || [],
      principles: data.principles || [],
      focus: data.focus || [],
      signals: data.signals || []
    };
  }

  /**
   * Parse and validate a memory item response
   * @param {Object} data - The response data from the API
   * @returns {Object} Parsed memory item object
   * @throws {Error} Throws error if response format is invalid
   */
  parseMemoryItemResponse(data) {
    // Validate response structure
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid memory item response format.');
    }

    // Check for required fields
    if (!data.hasOwnProperty('id') || !data.hasOwnProperty('key') || !data.hasOwnProperty('value')) {
      throw new Error('Invalid memory item format: missing required fields.');
    }

    // Return the validated memory item
    return {
      id: data.id,
      key: data.key,
      value: data.value
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
const memoryApiService = new MemoryApiService();
export default memoryApiService;

// Also export the class for testing purposes
export { MemoryApiService };