# Design Document

## Overview

Replace the hardcoded "Bot is typing..." text with a random selection from a pool of 8 reflective phrases. The implementation will be minimal and drop-in, requiring only a small change to the existing typing indicator logic.

## Architecture

The current typing indicator is rendered when `isLoading` is true:
```jsx
{isLoading && (
  <div className="message bot loading">
    <span className="message-text">Bot is typing...</span>
  </div>
)}
```

The new implementation will:
1. Define a constant array of reflective phrases
2. Create a function to randomly select from the pool
3. Replace the hardcoded text with the random selection

## Components and Interfaces

### Phrase Pool
```javascript
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
```

### Random Selection Function
```javascript
const getRandomReflectivePhrase = () => {
  const randomIndex = Math.floor(Math.random() * REFLECTIVE_PHRASES.length);
  return REFLECTIVE_PHRASES[randomIndex];
};
```

### Updated Typing Indicator
```jsx
{isLoading && (
  <div className="message bot loading">
    <span className="message-text">{getRandomReflectivePhrase()}</span>
  </div>
)}
```

## Data Models

No new data models required. The implementation uses:
- Static array of strings (REFLECTIVE_PHRASES)
- Existing `isLoading` boolean state

## Error Handling

No additional error handling needed. If the random selection fails, it would fall back to an empty string, which is acceptable for this feature.

## Testing Strategy

Manual testing approach:
1. Send multiple messages to trigger typing indicator
2. Verify different phrases appear across interactions
3. Confirm phrases disappear when bot responds
4. Ensure existing chat functionality remains intact