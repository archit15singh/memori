# Design Document

## Overview

Fix the identity confusion by restructuring the chat endpoint's prompt assembly. Move user profile data out of the system prompt and into a separate context block, ensuring the AI maintains its role as a reflective journaling assistant.

## Architecture

### Current Problem
- User memories are formatted into system prompt as "Here is what you know about yourself"
- This makes the AI think it IS Alex
- System prompt incorrectly frames memories as AI's own identity

### Solution
- Clean system prompt: AI is journaling bot, never impersonates user
- User profile as separate data context, not system identity
- Second-person framing for all user references

## Components and Interfaces

### System Prompt (Fixed)
```
You are Reflective Journaling Bot.
- Reflect back in 1–2 lines.
- Ask exactly 1 incisive follow-up question.
- Use second person ("you/your") when referring to the user.
- Never impersonate the user or claim their identity.
```

### Profile Context (New Format)
```
USER PROFILE (reference only, do not impersonate):
name: Alex
role: Senior Backend Developer at a fintech; API design & scalability
interests: ML, OSS, rock climbing, cooking
values: Empowering, human-centered tech
location: San Francisco
```

### Message Assembly
```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": f"{render_user_profile(profile)}\n\n{user_msg}"}
]
```

## Data Models

### Profile Rendering
- Extract key fields from memories: name, role, interests, values, location
- Format as "USER PROFILE" block
- Include disclaimer: "reference only, do not impersonate"

### Memory Context
- Identity → name, role, location
- Principles → values  
- Focus → current priorities
- Signals → behavioral patterns

## Error Handling

- If no memories exist: respond normally without profile context
- If OpenAI API fails: existing error handling remains unchanged
- Profile rendering errors: skip profile, continue with basic prompt

## Testing Strategy

- AT1: "hi" → must use "you" when referencing profile
- AT2: "Who am I?" → "You're Alex..." + question
- AT3: Empty profile → still works, 1-2 lines + question
- AT4: Focus mention → ties to profile using second person