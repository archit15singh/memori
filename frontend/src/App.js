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

  // Memory toggle state
  const [memoryEnabled, setMemoryEnabled] = useState(true);

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
  const [highlightType, setHighlightType] = useState(null);

  // Refs for auto-scroll and focus
  const messagesEndRef = React.useRef(null);
  const chatInputRef = React.useRef(null);

  // Load memory toggle state from localStorage on component mount
  useEffect(() => {
    const savedMemoryEnabled = localStorage.getItem('memoryEnabled');
    if (savedMemoryEnabled !== null) {
      setMemoryEnabled(JSON.parse(savedMemoryEnabled));
    }
  }, []);

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
      // Different timing based on highlight type
      const duration = highlightType === 'created' ? 800 : 
                      highlightType === 'updated' ? 700 : 
                      highlightType === 'deleted' ? 600 : 700;
      
      const timer = setTimeout(() => {
        setHighlightedMemory(null);
        setHighlightType(null);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [highlightedMemory, highlightType]);

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

  // Apply memory changes from chat response with enhanced error handling
  const applyMemoryChanges = (changes) => {
    // Enhanced input validation
    if (!changes) {
      console.warn('Memory changes is null or undefined, skipping processing');
      return;
    }

    if (!Array.isArray(changes)) {
      console.error('Invalid memory changes received - expected array, got:', typeof changes, changes);
      showFeedback('Invalid memory changes format received', 'error');
      return;
    }

    if (changes.length === 0) {
      console.log('No memory changes to process');
      return;
    }

    console.log(`Processing ${changes.length} memory changes`);

    let successCount = 0;
    let errorCount = 0;
    const errors = [];

    changes.forEach((change, index) => {
      try {
        // Enhanced validation with detailed error messages
        if (!change || typeof change !== 'object') {
          const error = `Invalid memory change at index ${index}: expected object, got ${typeof change}`;
          console.warn(error);
          errors.push(error);
          errorCount++;
          return;
        }

        // Validate required fields with specific error messages
        const requiredFields = ['action', 'type', 'id', 'key'];
        const missingFields = requiredFields.filter(field => !change[field]);
        
        if (missingFields.length > 0) {
          const error = `Memory change at index ${index} missing required fields: ${missingFields.join(', ')}`;
          console.warn(error, change);
          errors.push(error);
          errorCount++;
          return;
        }

        // Validate action type
        const validActions = ['created', 'updated', 'deleted'];
        if (!validActions.includes(change.action)) {
          const error = `Invalid action '${change.action}' at index ${index}, expected one of: ${validActions.join(', ')}`;
          console.warn(error);
          errors.push(error);
          errorCount++;
          return;
        }

        // Map backend memory type to frontend state with validation
        let frontendType;
        switch (change.type) {
          case 'identity':
            frontendType = 'insights';
            break;
          case 'principles':
            frontendType = 'anchors';
            break;
          case 'focus':
            frontendType = 'routines';
            break;
          case 'signals':
            frontendType = 'notes';
            break;
          default:
            const error = `Unknown memory type '${change.type}' at index ${index}`;
            console.warn(error);
            errors.push(error);
            errorCount++;
            return;
        }

        // Validate value field for created/updated actions
        if ((change.action === 'created' || change.action === 'updated') && !change.value) {
          const error = `Missing value for ${change.action} action at index ${index}`;
          console.warn(error);
          errors.push(error);
          errorCount++;
          return;
        }

        // Create memory item object (for created/updated actions)
        const memoryItem = {
          id: change.id,
          key: change.key,
          value: change.value
        };

        // Apply the change based on action type with enhanced error handling
        try {
          switch (change.action) {
            case 'created':
              console.log(`Creating new ${frontendType} memory:`, change.key);
              // Add new memory to appropriate array with error handling
              switch (frontendType) {
                case 'insights':
                  setInsights(prev => {
                    // Check for duplicates
                    if (prev.some(item => item.id === change.id)) {
                      console.warn(`Duplicate memory ID ${change.id} for insights, skipping creation`);
                      return prev;
                    }
                    return [...prev, memoryItem];
                  });
                  break;
                case 'anchors':
                  setAnchors(prev => {
                    if (prev.some(item => item.id === change.id)) {
                      console.warn(`Duplicate memory ID ${change.id} for anchors, skipping creation`);
                      return prev;
                    }
                    return [...prev, memoryItem];
                  });
                  break;
                case 'routines':
                  setRoutines(prev => {
                    if (prev.some(item => item.id === change.id)) {
                      console.warn(`Duplicate memory ID ${change.id} for routines, skipping creation`);
                      return prev;
                    }
                    return [...prev, memoryItem];
                  });
                  break;
                case 'notes':
                  setNotes(prev => {
                    if (prev.some(item => item.id === change.id)) {
                      console.warn(`Duplicate memory ID ${change.id} for notes, skipping creation`);
                      return prev;
                    }
                    return [...prev, memoryItem];
                  });
                  break;
                default:
                  console.warn(`Unknown frontend memory type: ${frontendType}`);
                  break;
              }
              break;

            case 'updated':
              console.log(`Updating ${frontendType} memory:`, change.key);
              // Update existing memory in appropriate array with existence check
              let updateFound = false;
              switch (frontendType) {
                case 'insights':
                  setInsights(prev => {
                    const updated = prev.map(item => {
                      if (item.id === change.id) {
                        updateFound = true;
                        return memoryItem;
                      }
                      return item;
                    });
                    if (!updateFound) {
                      console.warn(`Memory ID ${change.id} not found in insights for update, adding as new`);
                      return [...prev, memoryItem];
                    }
                    return updated;
                  });
                  break;
                case 'anchors':
                  setAnchors(prev => {
                    const updated = prev.map(item => {
                      if (item.id === change.id) {
                        updateFound = true;
                        return memoryItem;
                      }
                      return item;
                    });
                    if (!updateFound) {
                      console.warn(`Memory ID ${change.id} not found in anchors for update, adding as new`);
                      return [...prev, memoryItem];
                    }
                    return updated;
                  });
                  break;
                case 'routines':
                  setRoutines(prev => {
                    const updated = prev.map(item => {
                      if (item.id === change.id) {
                        updateFound = true;
                        return memoryItem;
                      }
                      return item;
                    });
                    if (!updateFound) {
                      console.warn(`Memory ID ${change.id} not found in routines for update, adding as new`);
                      return [...prev, memoryItem];
                    }
                    return updated;
                  });
                  break;
                case 'notes':
                  setNotes(prev => {
                    const updated = prev.map(item => {
                      if (item.id === change.id) {
                        updateFound = true;
                        return memoryItem;
                      }
                      return item;
                    });
                    if (!updateFound) {
                      console.warn(`Memory ID ${change.id} not found in notes for update, adding as new`);
                      return [...prev, memoryItem];
                    }
                    return updated;
                  });
                  break;
                default:
                  console.warn(`Unknown frontend memory type: ${frontendType}`);
                  break;
              }
              break;

            case 'deleted':
              console.log(`Deleting ${frontendType} memory:`, change.key);
              // First highlight the memory for deletion animation
              const deleteMemoryId = `${frontendType}-${change.key}`;
              setHighlightedMemory(deleteMemoryId);
              setHighlightType('deleted');
              
              // Remove memory from appropriate array after animation delay with existence check
              setTimeout(() => {
                switch (frontendType) {
                  case 'insights':
                    setInsights(prev => {
                      const filtered = prev.filter(item => item.id !== change.id);
                      if (filtered.length === prev.length) {
                        console.warn(`Memory ID ${change.id} not found in insights for deletion`);
                      }
                      return filtered;
                    });
                    break;
                  case 'anchors':
                    setAnchors(prev => {
                      const filtered = prev.filter(item => item.id !== change.id);
                      if (filtered.length === prev.length) {
                        console.warn(`Memory ID ${change.id} not found in anchors for deletion`);
                      }
                      return filtered;
                    });
                    break;
                  case 'routines':
                    setRoutines(prev => {
                      const filtered = prev.filter(item => item.id !== change.id);
                      if (filtered.length === prev.length) {
                        console.warn(`Memory ID ${change.id} not found in routines for deletion`);
                      }
                      return filtered;
                    });
                    break;
                  case 'notes':
                    setNotes(prev => {
                      const filtered = prev.filter(item => item.id !== change.id);
                      if (filtered.length === prev.length) {
                        console.warn(`Memory ID ${change.id} not found in notes for deletion`);
                      }
                      return filtered;
                    });
                    break;
                  default:
                    console.warn(`Unknown frontend memory type: ${frontendType}`);
                    break;
                }
              }, 600); // Match the animation duration
              break;

            default:
              // This should not happen due to earlier validation, but keeping for safety
              const error = `Unknown memory change action: ${change.action}`;
              console.warn(error);
              errors.push(error);
              errorCount++;
              return;
          }

          // Highlight the changed memory for visual feedback with appropriate animation
          // Only for created/updated actions (deleted already handled above)
          if (change.action !== 'deleted') {
            const memoryId = `${frontendType}-${change.key}`;
            setHighlightedMemory(memoryId);
            setHighlightType(change.action);
          }

          successCount++;

        } catch (stateError) {
          const error = `Failed to update UI state for memory change at index ${index}: ${stateError.message}`;
          console.error(error, stateError);
          errors.push(error);
          errorCount++;
        }

      } catch (error) {
        const errorMsg = `Error processing memory change at index ${index}: ${error.message}`;
        console.error(errorMsg, error, change);
        errors.push(errorMsg);
        errorCount++;
      }
    });

    // Enhanced logging and user feedback
    console.log(`Memory changes processing completed: ${successCount} successful, ${errorCount} failed`);
    
    if (errorCount > 0) {
      console.warn('Memory change processing errors:', errors);
      console.warn('Failed changes details:', changes.filter((_, index) => 
        errors.some(error => error.includes(`index ${index}`))
      ));
      
      // Show user feedback for errors, but don't break the chat experience
      if (successCount === 0) {
        // All changes failed
        console.error('All memory changes failed - this may indicate a serious issue');
        showFeedback('Failed to update memories - please refresh to see latest state', 'error');
      } else if (errorCount < changes.length) {
        // Partial success
        console.warn(`Partial memory update success: ${successCount}/${changes.length}`);
        showFeedback(`Some memory updates failed (${successCount}/${changes.length} successful)`, 'error');
      }
    } else if (successCount > 0) {
      // All successful - no need to show feedback as the visual highlights will indicate success
      console.log('All memory changes applied successfully');
    } else {
      // No changes processed (shouldn't happen if we got here, but safety check)
      console.warn('No memory changes were processed - this may indicate an issue');
    }

    // Additional debugging information
    if (process.env.NODE_ENV === 'development') {
      console.log('Memory processing debug info:', {
        totalChanges: changes.length,
        successCount,
        errorCount,
        errors: errors.slice(0, 5), // Limit to first 5 errors to avoid console spam
        currentMemoryState: {
          insights: insights.length,
          anchors: anchors.length,
          routines: routines.length,
          notes: notes.length
        }
      });
    }
  };

  // Toggle memory functionality and persist to localStorage
  const toggleMemory = (enabled) => {
    setMemoryEnabled(enabled);
    localStorage.setItem('memoryEnabled', JSON.stringify(enabled));
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
      setHighlightType('updated');

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

      // Animate deletion before removing from state
      const deleteMemoryId = `${type}-${key}`;
      setHighlightedMemory(deleteMemoryId);
      setHighlightType('deleted');

      // Update local state after animation delay
      setTimeout(() => {
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
      }, 600); // Match the animation duration

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
      // Call the real API service with memory toggle state
      const response = await chatApiService.sendMessage(userMessage, memoryEnabled);

      // Extract and format the response text from the API response
      // The backend returns: { "response": "message text", "memory_changes": [...] }
      // We extract the 'response' field and ensure it's properly formatted
      const responseText = response.response || 'No response received.';

      // Create bot message with consistent formatting
      const botResponse = createMessage(responseText, 'bot', Date.now() + 1);

      // Add bot response to conversation flow seamlessly
      setMessages(prev => [...prev, botResponse]);

      // Apply memory changes immediately after updating chat UI with enhanced error handling
      // This ensures real-time memory updates as per requirements 1.1 and 1.4
      try {
        if (response.memory_changes) {
          if (Array.isArray(response.memory_changes)) {
            if (response.memory_changes.length > 0) {
              console.log('Applying memory changes:', response.memory_changes);
              applyMemoryChanges(response.memory_changes);
            } else {
              console.log('No memory changes to apply (empty array)');
            }
          } else {
            console.warn('Invalid memory_changes format - expected array, got:', typeof response.memory_changes);
            showFeedback('Invalid memory changes format received', 'error');
          }
        } else {
          console.log('No memory changes in response');
        }
      } catch (memoryError) {
        console.error('Error processing memory changes:', memoryError);
        showFeedback('Failed to process memory updates - please refresh to see latest state', 'error');
        // Chat functionality continues normally despite memory processing error
      }
    } catch (error) {
      // Handle API errors by showing an error message as a bot response
      // Maintain consistent message formatting for errors
      console.error('Chat API error:', error);
      
      // Determine if this is a memory-related error or a general chat error
      const isMemoryError = error.message && (
        error.message.includes('memory') || 
        error.message.includes('Memory') ||
        error.message.includes('Invalid memory changes')
      );
      
      let errorMessage;
      if (isMemoryError) {
        errorMessage = `Sorry, I encountered an issue with memory processing: ${error.message}. Chat functionality continues normally.`;
        // Also show a feedback message for memory errors
        showFeedback('Memory processing error - please refresh if needed', 'error');
      } else {
        errorMessage = `Sorry, I encountered an error: ${error.message}`;
      }
      
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
      const highlightClass = isHighlighted ? `highlighted ${highlightType || ''}` : '';

      return (
        <div
          key={item.key}
          className={`memory-item ${isItemLoading ? 'loading' : ''} ${highlightClass}`}
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
      <div className={`memory-area ${!memoryEnabled ? 'disabled' : ''}`}>
        <div className="memory-header">
          <h2>Memory</h2>
          <div className="memory-toggle-container">
            <label className="memory-toggle">
              <input
                type="checkbox"
                checked={memoryEnabled}
                onChange={(e) => toggleMemory(e.target.checked)}
                className="memory-toggle-input"
              />
              <span className="memory-toggle-slider">
                <span className="memory-toggle-label">
                  {memoryEnabled ? 'ON' : 'OFF'}
                </span>
              </span>
            </label>
            <button 
              onClick={() => window.location.reload()} 
              className="refresh-button"
              title="Refresh page to reload memories if real-time updates fail"
              style={{
                marginLeft: '10px',
                padding: '4px 8px',
                fontSize: '12px',
                background: 'transparent',
                border: '1px solid #ccc',
                borderRadius: '4px',
                cursor: 'pointer',
                color: '#666'
              }}
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        {!memoriesLoaded ? (
          <div className="memory-loading">
            <div className="loading-spinner"></div>
            <h3>Loading memories...</h3>
            <p>Retrieving your personal knowledge base</p>
          </div>
        ) : (
          <>
            {!memoryEnabled && (
              <div className="memory-disabled-message">
                <h3>Memory disabled</h3>
                <p>Memory extraction and usage is currently turned off</p>
              </div>
            )}
            
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