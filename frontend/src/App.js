import React, { useState, useEffect } from 'react';
import './App.css';

// Mock data for memories
const MOCK_MEMORIES = {
  insights: [
    { key: 'Allergy', value: 'Daughter is allergic to dairy' },
    { key: 'Dislike', value: 'Wife doesn\'t eat meat' },
    { key: 'Preference', value: 'I don\'t eat meat' }
  ],
  anchors: [
    { key: 'Health', value: 'Exercise 30 minutes daily' },
    { key: 'Family', value: 'Spend quality time with kids every evening' },
    { key: 'Work', value: 'No meetings after 6 PM' }
  ],
  routines: [
    { key: 'Morning', value: 'Coffee and journal writing at 6 AM' },
    { key: 'Lunch', value: 'Walk outside for 15 minutes' },
    { key: 'Evening', value: 'Read for 30 minutes before bed' }
  ],
  notes: [
    { key: 'Stress', value: 'Feel overwhelmed when inbox has 50+ emails' },
    { key: 'Energy', value: 'Most productive between 9-11 AM' },
    { key: 'Mood', value: 'Need sunlight to feel positive' }
  ]
};

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Memory state - using mock data
  const [insights, setInsights] = useState(MOCK_MEMORIES.insights);
  const [anchors, setAnchors] = useState(MOCK_MEMORIES.anchors);
  const [routines, setRoutines] = useState(MOCK_MEMORIES.routines);
  const [notes, setNotes] = useState(MOCK_MEMORIES.notes);
  
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

  const saveEdit = () => {
    if (!editValue.trim() || !editingMemory) return;
    
    // Validate 240 char limit
    if (editValue.trim().length > 240) {
      showFeedback('Value must be 240 characters or less', 'error');
      return;
    }
    
    const loadingKey = `${editingMemory.type}-${editingMemory.key}`;
    setMemoryLoading(prev => ({ ...prev, [loadingKey]: true }));
    
    // Simulate API delay
    setTimeout(() => {
      // Update local state
      const newItem = { key: editingMemory.key, value: editValue.trim() };
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
          console.warn('Unknown memory type:', editingMemory.type);
          break;
      }
      
      setMemoryLoading(prev => {
        const newState = { ...prev };
        delete newState[loadingKey];
        return newState;
      });
      
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
    }, 500); // 500ms delay to simulate API call
  };

  const deleteMemory = (type, key) => {
    const loadingKey = `${type}-${key}`;
    setMemoryLoading(prev => ({ ...prev, [loadingKey]: true }));
    
    // Simulate API delay
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
          console.warn('Unknown memory type:', type);
          break;
      }
      
      setMemoryLoading(prev => {
        const newState = { ...prev };
        delete newState[loadingKey];
        return newState;
      });
      
      showFeedback('Memory deleted successfully');
    }, 300); // 300ms delay to simulate API call
  };

  // Mock chat responses
  const MOCK_RESPONSES = [
    "That's really insightful. How does that connect to your core values?",
    "I can see how that experience shaped your perspective. What did you learn from it?",
    "That sounds like an important realization. How might you apply this going forward?",
    "Thanks for sharing that reflection. What patterns do you notice in your thinking?",
    "That's a meaningful observation. How does this relate to your personal growth?",
    "I appreciate your openness. What would you like to explore further about this?",
    "That's an interesting point. How has this insight influenced your recent decisions?",
    "Your reflection shows real self-awareness. What questions does this raise for you?"
  ];

  const sendMessage = (userMessage) => {
    // Add user message immediately
    const newUserMessage = { id: Date.now(), text: userMessage, sender: 'user' };
    setMessages(prev => [...prev, newUserMessage]);
    
    setIsLoading(true);
    
    // Simulate API call with random response
    setTimeout(() => {
      const randomResponse = MOCK_RESPONSES[Math.floor(Math.random() * MOCK_RESPONSES.length)];
      const botResponse = { 
        id: Date.now() + 1, 
        text: randomResponse, 
        sender: 'bot' 
      };
      setMessages(prev => [...prev, botResponse]);
      setIsLoading(false);
    }, 1500);
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
              <span className="message-text">Bot is typing...</span>
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
      </div>
    </div>
  );
}

export default App;