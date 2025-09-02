# Implementation Plan

- [x] 1. Create new system prompt function
  - Replace `build_memory_aware_prompt()` with clean system prompt
  - Remove memory context from system role
  - _Requirements: R1, R3_

- [x] 2. Create profile rendering function  
  - Extract key fields from memories (name, role, interests, values, location)
  - Format as "USER PROFILE (reference only, do not impersonate)" block
  - Handle empty memories gracefully
  - _Requirements: R2_

- [x] 3. Update message assembly in get_ai_response()
  - Use fixed system prompt
  - Add profile context to user message, not system
  - Maintain existing error handling
  - _Requirements: R1, R2_

- [-] 4. Test the fix
  - Verify "hi" response uses "you" not "I"
  - Verify "Who am I?" gets "You're Alex..." response
  - Verify empty profile still works
  - _Requirements: R1, R2, R3_