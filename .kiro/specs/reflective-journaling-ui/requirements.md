# Requirements Document

## Introduction

A simple React demo UI for a reflective journaling bot. Two-panel layout: chat interface (3/4 width) and memory management (1/4 width). Focus on core functionality that demonstrates the concept.

## Requirements

### Requirement 1

**User Story:** As a user, I want to chat with a journaling bot, so that I can see the basic interaction flow.

#### Acceptance Criteria

1. WHEN the user types and presses enter THEN the system SHALL show the message in chat
2. WHEN the user submits THEN the system SHALL call stubbed API and show response after 2 seconds
3. WHEN displaying messages THEN the system SHALL show user/bot message pairs
4. WHEN the chat loads THEN the system SHALL occupy 3/4 of screen width

### Requirement 2

**User Story:** As a user, I want to manage memory items, so that I can see the edit and delete functionality working.

#### Acceptance Criteria

1. WHEN the memory panel loads THEN the system SHALL show four sections: Insights, Anchors, Routines, Notes
2. WHEN the user edits a memory THEN the system SHALL call the appropriate API endpoint (PUT /insights/{key}, etc.)
3. WHEN the user deletes a memory THEN the system SHALL call the delete endpoint (DELETE /insights/{key}, etc.)
4. WHEN the memory panel loads THEN the system SHALL occupy 1/4 of screen width
5. WHEN the app starts THEN the system SHALL fetch existing memories from all four endpoints
6. WHEN the user clicks edit on a memory THEN the system SHALL show an inline edit form
7. WHEN the user saves an edit THEN the system SHALL update the memory and hide the edit form

### Requirement 3

**User Story:** As a user, I want basic visual feedback, so that the demo feels responsive.

#### Acceptance Criteria

1. WHEN waiting for responses THEN the system SHALL show simple loading indicators
2. WHEN operations succeed/fail THEN the system SHALL provide basic feedback
3. WHEN the interface loads THEN the system SHALL have clean 75%/25% layout split