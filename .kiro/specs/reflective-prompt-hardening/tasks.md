# Implementation Plan

- [x] 1. Replace system prompt function with hardened version
  - Update `get_system_prompt()` function in `backend/main.py` with the new prompt template
  - Implement GOAL, CONTEXT BLOCKS, STYLE, and SAFETY sections as specified
  - Ensure function maintains existing signature and logging patterns
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Replace memory extraction system prompt with hardened version
  - Update the `system_prompt` variable within `extract_memories()` function in `backend/main.py`
  - Implement BUCKETS, STRICT RULES, OUTPUT, and NEGATIVE EXAMPLES sections
  - Add source discipline rules and identity inference constraints
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 3. Enhance memory extraction user prompt with update constraints
  - Add explicit instruction to `user_prompt` variable in `extract_memories()` function
  - Include "ONLY UPDATE A KEY IF THE USER CLEARLY REPLACES IT IN THIS TURN" instruction
  - Maintain existing conversation context format and existing memory keys context
  - _Requirements: 2.3, 2.4_

- [x] 4. Validate demo scenarios work as expected
  - Test OFF→ON contrast scenario with "Wrapped up a late-night Postgres migration… need to plan better"
  - Test correction/demotion scenario with "I'm not a K8s engineer; I'm a backend engineer at Abnormal"
  - Test retrieve & use scenario with "What did I say I'm working on this week?"
  - Verify no identity overreach occurs and memory extraction follows strict rules
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_