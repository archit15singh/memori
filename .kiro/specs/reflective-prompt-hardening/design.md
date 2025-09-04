# Design Document

## Overview

Replace two critical prompt functions in the FastAPI backend to implement hardened prompts that prevent identity overreach and ensure predictable demo behavior. The changes focus on the `get_system_prompt()` function and the system prompt within `extract_memories()` function.

## Architecture

### Current Implementation
- `get_system_prompt()`: Returns basic reflective journaling bot prompt
- `extract_memories()`: Contains memory extraction system prompt with loose identity inference rules
- Both functions are in `backend/main.py`

### Target Implementation
- Enhanced `get_system_prompt()`: Handles user profile context blocks and enforces strict identity boundaries
- Hardened memory extraction prompt: Implements strict source discipline and prevents identity overreach
- Maintains existing function signatures and integration points

## Components and Interfaces

### 1. System Prompt Function (`get_system_prompt()`)

**Current Function Signature:**
```python
def get_system_prompt() -> str
```

**Enhanced Behavior:**
- Treats USER IDENTITY/PRINCIPLES/FOCUS/SIGNALS blocks as user profile context, not bot identity
- Uses second person ("you/your") exclusively when referring to user
- Prioritizes USER FOCUS in follow-up questions when profile context exists
- Falls back to practical next steps when no profile context available
- Avoids therapy clichés and praise, focusing on concrete specifics

**Key Changes:**
- Add explicit instructions about context block handling
- Strengthen identity boundary enforcement
- Add guidance for follow-up question prioritization
- Include safety constraints against identity assumptions

### 2. Memory Extraction Prompt (within `extract_memories()`)

**Current Location:** Line ~490 in `extract_memories()` function
**Variable:** `system_prompt` (local variable)

**Enhanced Behavior:**
- Implements strict source discipline: only user's own words create identity/principles
- Prevents assistant content from creating identity/principles (signals only)
- Requires explicit self-identification for identity bucket entries
- Prefers signals over identity for technical mentions unless explicitly stated
- Only updates existing keys when user clearly replaces the value

**Key Changes:**
- Add strict source discipline rules
- Implement identity vs signals preference logic
- Add explicit self-identification requirements
- Strengthen update conditions
- Include negative examples to prevent overreach

### 3. User Prompt Enhancement (within `extract_memories()`)

**Current Location:** Line ~530 in `extract_memories()` function
**Variable:** `user_prompt` (local variable)

**Enhancement:**
- Add explicit instruction to only update keys when user clearly replaces them
- Maintains existing conversation context format
- Preserves existing memory keys context

## Data Models

No changes to existing data models. The enhancements work within the current:
- Memory bucket structure (identity, principles, focus, signals)
- Memory action format (create/update with bucket, key, value)
- Function return types and parameters

## Error Handling

### Prompt Validation
- System prompt function maintains existing error handling
- Memory extraction maintains existing JSON parsing and validation
- No new error conditions introduced

### Fallback Behavior
- System prompt function continues to return valid prompt even if context processing fails
- Memory extraction continues to return empty array on prompt failures
- Existing logging and error reporting preserved

## Testing Strategy

### Demo Scenario Validation

**OFF→ON Contrast Test:**
- Input: "Wrapped up a late-night Postgres migration… need to plan better"
- Expected: Extract `focus.current_project = "database migration"` and `principles.deployment_practices = "plan changes before production"`
- Expected: No identity inference from technical mention

**Correction/Demotion Test:**
- Input: "By the way, I'm not a K8s engineer; I'm a backend engineer at Abnormal"
- Expected: Update `identity.role = "backend engineer"` (explicit self-claim)
- Expected: No promotion of previous soft inferences

**Retrieve & Use Test:**
- Input: "What did I say I'm working on this week?"
- Expected: System prompt guides bot to reference USER FOCUS first
- Expected: Response mentions stored `focus.current_project` and related principles

### Unit Testing Approach
- Test system prompt generation with various context scenarios
- Test memory extraction with edge cases (no self-identification, correction scenarios)
- Validate JSON output format consistency
- Verify existing functionality preservation

## Implementation Details

### System Prompt Template Structure
```
GOAL section: Core bot behavior
CONTEXT BLOCKS section: User profile handling rules  
STYLE section: Response formatting guidelines
SAFETY section: Identity boundary enforcement
```

### Memory Extraction Prompt Structure
```
BUCKETS section: Memory category definitions
STRICT RULES section: Source discipline and update conditions
OUTPUT section: JSON format requirements
NEGATIVE EXAMPLES section: What not to do
```

### Integration Points
- Maintains existing function signatures
- Preserves existing logging patterns
- Compatible with current OpenAI API usage
- No changes to database schema or API endpoints

## Performance Considerations

- Prompt length increase minimal (estimated 20-30% longer)
- No additional API calls required
- Memory extraction temperature remains at 0.1 for determinism
- Existing caching and optimization patterns preserved