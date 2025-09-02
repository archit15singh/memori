import React, { useState, useEffect } from 'react';
import './App.css';
import chatApiService from './services/chatApi';
import memoryApiService from './services/memoryApi';

// Reflective phrases for typing indicator
const REFLECTIVE_PHRASES = [
  "Pausing to reflect…",
  "Holding space for your words…",
  "Settling into what this means…",
  "Listening deeply…",
  "Exploring that thought…",
  "Turning it over gently…",
  "In this moment…",
  "Gathering reflections…"
];

// Function to get a random reflective phrase
const getRandomReflectivePhrase = () => {
  const randomIndex = Math.floor(Math.random() * REFLECTIVE_PHRASES.length);
  return REFLECTIVE_PHRASES[randomIndex];
};

// Memory type mapping between frontend and backend
const MEMORY_TYPE_MAP = {
  insights: 'identity',
  anchors: 'principles',
  routines: 'focus',
  notes: 'signals'
};



function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Memory state - loaded from API
  const [insights, setInsights] = useState([]);
  const [anchors, setAnchors] = useState([]);
  const [routines, setRoutines] = useState([]);
  const [notes, setNotes] = useState([]);
  const [memoriesLoaded, setMemoriesLoaded] = useState(false);

  // Edit state
  const [editingMemory, setEditingMemory] = useState(null);
  const [editValue, setEditValue] = useState('');

  // Feedback state
  const [feedback, setFeedback] = useState(null);
  const [memoryLoading, setMemoryLoading] = useState({});

  // Highlight state for memory updates
  const [highlightedMemory, setHighlightedMemory] = useState(null);

  // Refs for auto-scroll and focus
  const messagesEndRef = React.useRef(null);
  const chatInputRef = React.useRef(null);

  // Auto-scroll chat to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-focus input when loading ends (after bot responds)
  useEffect(() => {
    if (!isLoading && chatInputRef.current) {
      chatInputRef.current.focus();
    }
  }, [isLoading]);

  // Auto-hide feedback after 3 seconds
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => {
        setFeedback(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // Auto-hide memory highlight after animation
  useEffect(() => {
    if (highlightedMemory) {
      const timer = setTimeout(() => {
        setHighlightedMemory(null);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [highlightedMemory]);

  // Load memories from backend on app startup
  useEffect(() => {
    const loadMemories = async () => {
      try {
        const memories = await memoryApiService.fetchMemories();

        // Map backend response to frontend state
        setInsights(memories.identity || []);
        setAnchors(memories.principles || []);
        setRoutines(memories.focus || []);
        setNotes(memories.signals || []);
        setMemoriesLoaded(true);
      } catch (error) {
        console.error('Failed to load memories:', error);
        showFeedback(`Failed to load memories: ${error.message}`, 'error');
        setMemoriesLoaded(true); // Still mark as loaded to avoid infinite loading
      }
    };

    loadMemories();
  }, []);

  // Load chat history from backend on app startup
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const response = await chatApiService.fetchMessages();
        
        // Convert backend message format to frontend message format
        const loadedMessages = response.messages.map(message => ({
          id: message.timestamp, // Use timestamp as unique ID for frontend
          text: message.content,  // Map 'content' to 'text'
          sender: message.sender  // Keep sender as-is ('user' or 'bot')
        }));

        // Set loaded messages to existing messages state
        setMessages(loadedMessages);
      } catch (error) {
        console.error('Failed to load chat history:', error);
        // Don't show feedback for chat history loading errors to avoid cluttering UI
        // Chat will just start empty if history fails to load
      }
    };

    loadChatHistory();
  }, []);

  // Helper function to create consistent message objects
  const createMessage = (text, sender, id = null) => {
    // Ensure text is a string and properly formatted
    const formattedText = typeof text === 'string' ? text.trim() : String(text || '').trim();

    return {
      id: id || Date.now(),
      text: formattedText || 'Empty message',
      sender: sender
    };
  };

  const showFeedback = (message, type = 'success') => {
    setFeedback({ message, type });
  };

  // Memory edit operations
  const startEdit = (type, key, value) => {
    setEditingMemory({ type, key });
    setEditValue(value);
  };

  const cancelEdit = () => {
    setEditingMemory(null);
    setEditValue('');
  };

  const saveEdit = async () => {
    if (!editValue.trim() || !editingMemory) return;

    // Validate 240 char limit
    if (editValue.trim().length > 240) {
      showFeedback('Value must be 240 characters or less', 'error');
      return;
    }

    const loadingKey = `${editingMemory.type}-${editingMemory.key}`;
    setMemoryLoading(prev => ({ ...prev, [loadingKey]: true }));

    try {
      // Find the memory item to get its ID
      let memoryItem = null;
      switch (editingMemory.type) {
        case 'insights':
          memoryItem = insights.find(item => item.key === editingMemory.key);
          break;
        case 'anchors':
          memoryItem = anchors.find(item => item.key === editingMemory.key);
          break;
        case 'routines':
          memoryItem = routines.find(item => item.key === editingMemory.key);
          break;
        case 'notes':
          memoryItem = notes.find(item => item.key === editingMemory.key);
          break;
        default:
          console.warn('Unknown memory type:', editingMemory.type);
          return;
      }

      if (!memoryItem || !memoryItem.id) {
        showFeedback('Memory item not found', 'error');
        return;
      }

      // Check if the value has actually changed
      const newValue = editValue.trim();
      const originalValue = memoryItem.value;

      if (newValue === originalValue) {
        // No changes made, just cancel edit without showing success message
        cancelEdit();
        return;
      }

      // Map frontend type to backend type
      const backendType = MEMORY_TYPE_MAP[editingMemory.type];

      // Call API to update memory
      const updatedMemory = await memoryApiService.updateMemory(
        backendType,
        memoryItem.id,
        {
          key: editingMemory.key,
          value: newValue
        }
      );

      // Update local state with the response
      const newItem = {
        id: updatedMemory.id,
        key: updatedMemory.key,
        value: updatedMemory.value
      };

      switch (editingMemory.type) {
        case 'insights':
          setInsights(prev => prev.map(item =>
            item.key === editingMemory.key ? newItem : item
          ));
          break;
        case 'anchors':
          setAnchors(prev => prev.map(item =>
            item.key === editingMemory.key ? newItem : item
          ));
          break;
        case 'routines':
          setRoutines(prev => prev.map(item =>
            item.key === editingMemory.key ? newItem : item
          ));
          break;
        case 'notes':
          setNotes(prev => prev.map(item =>
            item.key === editingMemory.key ? newItem : item
          ));
          break;
        default:
          console.warn('Unknown memory type for update:', editingMemory.type);
          break;
      }

      // Highlight the updated memory
      const memoryId = `${editingMemory.type}-${editingMemory.key}`;
      setHighlightedMemory(memoryId);

      showFeedback('Memory updated successfully');
      cancelEdit();

      // Scroll to updated memory after a brief delay
      setTimeout(() => {
        const element = document.querySelector(`[data-memory-id="${memoryId}"]`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);

    } catch (error) {
      console.error('Failed to update memory:', error);
      showFeedback(`Failed to update memory: ${error.message}`, 'error');
    } finally {
      setMemoryLoading(prev => {
        const newState = { ...prev };
        delete newState[loadingKey];
        return newState;
      });
    }
  };

  const deleteMemory = async (type, key) => {
    const loadingKey = `${type}-${key}`;
    setMemoryLoading(prev => ({ ...prev, [loadingKey]: true }));

    try {
      // Find the memory item to get its ID
      let memoryItem = null;
      switch (type) {
        case 'insights':
          memoryItem = insights.find(item => item.key === key);
          break;
        case 'anchors':
          memoryItem = anchors.find(item => item.key === key);
          break;
        case 'routines':
          memoryItem = routines.find(item => item.key === key);
          break;
        case 'notes':
          memoryItem = notes.find(item => item.key === key);
          break;
        default:
          console.warn('Unknown memory type:', type);
          return;
      }

      if (!memoryItem || !memoryItem.id) {
        showFeedback('Memory item not found', 'error');
        return;
      }

      // Map frontend type to backend type
      const backendType = MEMORY_TYPE_MAP[type];

      // Call API to delete memory
      await memoryApiService.deleteMemory(backendType, memoryItem.id);

      // Update local state
      switch (type) {
        case 'insights':
          setInsights(prev => prev.filter(item => item.key !== key));
          break;
        case 'anchors':
          setAnchors(prev => prev.filter(item => item.key !== key));
          break;
        case 'routines':
          setRoutines(prev => prev.filter(item => item.key !== key));
          break;
        case 'notes':
          setNotes(prev => prev.filter(item => item.key !== key));
          break;
        default:
          console.warn('Unknown memory type for deletion:', type);
          break;
      }

      showFeedback('Memory deleted successfully');

    } catch (error) {
      console.error('Failed to delete memory:', error);
      showFeedback(`Failed to delete memory: ${error.message}`, 'error');
    } finally {
      setMemoryLoading(prev => {
        const newState = { ...prev };
        delete newState[loadingKey];
        return newState;
      });
    }
  };

  const sendMessage = async (userMessage) => {
    // Add user message immediately with consistent formatting
    const newUserMessage = createMessage(userMessage, 'user');
    setMessages(prev => [...prev, newUserMessage]);

    setIsLoading(true);

    try {
      // Call the real API service
      const response = await chatApiService.sendMessage(userMessage);

      // Extract and format the response text from the API response
      // The backend returns: { "response": "message text" }
      // We extract the 'response' field and ensure it's properly formatted
      const responseText = response.response || 'No response received.';

      // Create bot message with consistent formatting
      const botResponse = createMessage(responseText, 'bot', Date.now() + 1);

      // Add bot response to conversation flow seamlessly
      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      // Handle API errors by showing an error message as a bot response
      // Maintain consistent message formatting for errors
      const errorMessage = `Sorry, I encountered an error: ${error.message}`;
      const errorResponse = createMessage(errorMessage, 'bot', Date.now() + 1);
      setMessages(prev => [...prev, errorResponse]);
    } finally {
      // Always reset loading state, whether success or error
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      sendMessage(input.trim());
      setInput('');
    }
  };

  // Helper function to clean key display (remove bucket prefix)
  const getDisplayKey = (key) => {
    // If key contains a dot, take the part after the last dot
    // e.g., "identity.north_star" becomes "north_star"
    const parts = key.split('.');
    return parts.length > 1 ? parts[parts.length - 1] : key;
  };

  // Helper function to render memory items
  const renderMemoryItems = (items, type) => {
    return items.map(item => {
      const loadingKey = `${type}-${item.key}`;
      const isItemLoading = memoryLoading[loadingKey];
      const displayKey = getDisplayKey(item.key);

      const memoryId = `${type}-${item.key}`;
      const isHighlighted = highlightedMemory === memoryId;

      return (
        <div
          key={item.key}
          className={`memory-item ${isItemLoading ? 'loading' : ''} ${isHighlighted ? 'highlighted' : ''}`}
          data-memory-id={memoryId}
        >
          {editingMemory && editingMemory.type === type && editingMemory.key === item.key ? (
            <div className="edit-form">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    saveEdit();
                  } else if (e.key === 'Escape') {
                    e.preventDefault();
                    cancelEdit();
                  }
                }}
                className="edit-input"
                autoFocus
                disabled={isItemLoading}
              />
              <button
                onClick={saveEdit}
                className="save-button"
                disabled={isItemLoading}
                title="Save changes"
              >
                {isItemLoading ? '⏳' : '✓'}
              </button>
              <button
                onClick={cancelEdit}
                className="cancel-button"
                disabled={isItemLoading}
                title="Cancel edit"
              >
                {isItemLoading ? '⏳' : '✕'}
              </button>
            </div>
          ) : (
            <>
              <div className="memory-content">
                <span className="memory-key">{displayKey}</span>
                <span className="memory-text">{item.value}</span>
              </div>
              <div className="memory-actions">
                <button
                  onClick={() => startEdit(type, item.key, item.value)}
                  className="edit-button"
                  disabled={isItemLoading}
                  title="Edit memory"
                >
                  {isItemLoading ? '⏳' : '✏️'}
                </button>
                <button
                  onClick={() => deleteMemory(type, item.key)}
                  className="delete-button"
                  disabled={isItemLoading}
                  title="Delete memory"
                >
                  {isItemLoading ? '⏳' : '🗑️'}
                </button>
              </div>
            </>
          )}
        </div>
      );
    });
  };

  return (
    <div className="app">
      {feedback && (
        <div className={`feedback ${feedback.type}`}>
          {feedback.message}
        </div>
      )}
      <div className="chat-area">
        <h2>Chat</h2>
        <div className="messages-container">
          {messages.map(message => (
            <div key={message.id} className={`message ${message.sender}`}>
              <span className="message-text">{message.text}</span>
            </div>
          ))}
          {isLoading && (
            <div className="message bot loading">
              <span className="message-text">{getRandomReflectivePhrase()}</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <form onSubmit={handleSubmit} className="chat-input-form">
          <input
            ref={chatInputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="chat-input"
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !input.trim()} className="send-button">
            Send
          </button>
        </form>
      </div>
      <div className="memory-area">
        <h2>Memory</h2>

        {!memoriesLoaded ? (
          <div className="memory-loading">
            <div className="loading-spinner"></div>
            <h3>Loading memories...</h3>
            <p>Retrieving your personal knowledge base</p>
          </div>
        ) : (
          <>
            {/* Identity Section */}
            <div className="memory-section identity">
              <h3 className="section-header">
                <span className="section-icon">🧭</span>
                <div className="section-text">
                  <span className="section-title">Identity</span>
                  <span className="section-subtitle">who I am</span>
                </div>
                <span className="section-count">({insights.length})</span>
              </h3>
              <div className="memory-items">
                {renderMemoryItems(insights, 'insights')}
              </div>
            </div>

            {/* Principles Section */}
            <div className="memory-section principles">
              <h3 className="section-header">
                <span className="section-icon">📜</span>
                <div className="section-text">
                  <span className="section-title">Principles</span>
                  <span className="section-subtitle">how I operate</span>
                </div>
                <span className="section-count">({anchors.length})</span>
              </h3>
              <div className="memory-items">
                {renderMemoryItems(anchors, 'anchors')}
              </div>
            </div>

            {/* Focus Section */}
            <div className="memory-section focus">
              <h3 className="section-header">
                <span className="section-icon">🎯</span>
                <div className="section-text">
                  <span className="section-title">Focus</span>
                  <span className="section-subtitle">what matters now</span>
                </div>
                <span className="section-count">({routines.length})</span>
              </h3>
              <div className="memory-items">
                {renderMemoryItems(routines, 'routines')}
              </div>
            </div>

            {/* Signals Section */}
            <div className="memory-section signals">
              <h3 className="section-header">
                <span className="section-icon">🌡️</span>
                <div className="section-text">
                  <span className="section-title">Signals</span>
                  <span className="section-subtitle">patterns I notice</span>
                </div>
                <span className="section-count">({notes.length})</span>
              </h3>
              <div className="memory-items">
                {renderMemoryItems(notes, 'notes')}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;