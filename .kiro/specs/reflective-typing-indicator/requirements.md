# Requirements Document

## Introduction

Replace "Bot is typing..." with random reflective phrases from a predefined pool.

## Requirements

### Requirement 1

**User Story:** As a user, I want to see random reflective phrases instead of "Bot is typing...", so that the waiting experience feels more thoughtful.

#### Acceptance Criteria

1. WHEN the bot is typing THEN the system SHALL pick one random phrase from the pool
2. WHEN the bot finishes THEN the system SHALL hide the phrase
3. WHEN selecting phrases THEN the system SHALL use this pool: "Pausing to reflect…", "Holding space for your words…", "Settling into what this means…", "Listening deeply…", "Exploring that thought…", "Turning it over gently…", "In this moment…", "Gathering reflections…"

### Requirement 2

**User Story:** As a user, I want each chat to show a different random phrase, so that it feels varied.

#### Acceptance Criteria

1. WHEN starting a new chat response THEN the system SHALL randomly pick from the pool
2. WHEN the same chat continues THEN the system SHALL pick randomly again