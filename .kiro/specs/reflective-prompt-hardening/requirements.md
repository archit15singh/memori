# Requirements Document

## Introduction

Replace the existing system prompt and memory extractor prompt in the reflective journaling bot with hardened versions that prevent identity overreach and ensure predictable demo behavior.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to replace the system prompt function, so that the bot treats user profile context correctly and avoids identity assumptions.

#### Acceptance Criteria

1. WHEN the system prompt is generated THEN it SHALL treat USER IDENTITY/PRINCIPLES/FOCUS/SIGNALS blocks as user profile context, not bot identity
2. WHEN responding THEN the system SHALL use second person ("you/your") and never use "I" to describe the user
3. WHEN profile context exists THEN the system SHALL tie follow-ups to USER FOCUS first
4. WHEN no profile context exists THEN the system SHALL ask about next practical steps
5. WHEN generating responses THEN the system SHALL avoid therapy clichés and praise, using concrete specifics instead

### Requirement 2

**User Story:** As a developer, I want to replace the memory extractor prompt, so that it follows strict rules about identity inference and memory creation.

#### Acceptance Criteria

1. WHEN extracting memories THEN the system SHALL only create identity/principles from user's own words, never from assistant content
2. WHEN processing technical mentions THEN the system SHALL prefer signals over identity unless user explicitly self-identifies
3. WHEN updating existing keys THEN the system SHALL only update if user clearly replaces the value in current turn
4. WHEN extracting memories THEN the system SHALL limit output to maximum 3 actions
5. WHEN no clear memories qualify THEN the system SHALL return empty JSON array
6. WHEN creating memory keys THEN the system SHALL use lower_snake_case and specific naming

### Requirement 3

**User Story:** As a demo presenter, I want the three demo scenarios to work predictably, so that I can reliably demonstrate the system capabilities.

#### Acceptance Criteria

1. WHEN demonstrating OFF→ON contrast THEN the system SHALL extract focus.current_project and principles.deployment_practices from "Wrapped up a late-night Postgres migration… need to plan better" without inferring identity
2. WHEN demonstrating correction/demotion THEN the system SHALL update identity.role when user says "I'm not a K8s engineer; I'm a backend engineer at Abnormal"
3. WHEN demonstrating retrieve & use THEN the system SHALL reference stored focus and principles when user asks "What did I say I'm working on this week?"
4. WHEN memory is OFF THEN the system SHALL show empty right pane
5. WHEN memory is ON THEN the system SHALL populate context from extracted memories