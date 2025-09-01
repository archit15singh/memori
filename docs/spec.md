### **`memori`: An Actionable Project Specification**

**Project Charter:** This document outlines the development of `memori`, an open-source tool for building and managing AI agents with transparent, debuggable, and self-correcting memory. Our goal is to move beyond "black box" agents by creating a system where a developer can inspect, control, and understand every step of an agent's reasoning process.

**Core Technology Stack:**
* **Backend:** Python 3.10+ with FastAPI for serving the API.
* **Frontend:** Vanilla JavaScript, HTML, and CSS for v0.1. We will graduate to Svelte or Vue for v1.0+.
* **Orchestration:** We will be wrapping a third-party API that provides the necessary endpoints for agent and memory management.

---

### ## Version 0.1: The Memory Core

**Goal:** To establish the foundational memory infrastructure. This version is a success if a developer can programmatically control an agent's knowledge base through a simple web interface.



#### **User Stories:**
* **As a developer, I want to** create a new agent instance so that I have a dedicated container for its memory.
* **As a developer, I want to** add a text-based memory to the agent so that I can populate its knowledge base.
* **As a developer, I want to** view all of the agent's long-term memories in a list so that I can audit its knowledge.
* **As a developer, I want to** delete a specific memory so that I can correct or remove outdated information.

#### **Technical Implementation:**
1.  **Backend Setup:**
    * Initialize a FastAPI project.
    * Create a single API endpoint, e.g., `POST /create_agent`, which calls the external `POST /api-reference/agents/create` endpoint and returns the new agent's ID.
    * Create endpoints for memory management (`POST /add_memory`, `GET /list_memories`, `DELETE /delete_memory`) that take an `agent_id` and a memory string. These endpoints will wrap the corresponding external API calls:
        * `POST /api-reference/sources/create` (for adding memory).
        * `GET /api-reference/sources/list` (for listing memories).
        * `DELETE /api-reference/sources/delete` (for deleting memories).

2.  **Frontend Setup:**
    * Create a single `index.html` file.
    * Build a UI with:
        * A "Create Agent" button that calls our `/create_agent` backend endpoint.
        * An input form to submit new memories, which calls our `/add_memory` endpoint.
        * A dynamic list area that is populated by calling our `/list_memories` endpoint on page load and after every change.
        * A delete button next to each memory item, which calls our `/delete_memory` endpoint.

**Definition of Done:** A developer can launch the application, create an agent, add and delete several memories, and see the UI update correctly after each action.

---

### ## Version 1.0: The Reasoning Inspector

**Goal:** To make the agent's thought process transparent. This version is successful if a developer can have a conversation with the agent and see a real-time, step-by-step breakdown of its reasoning.



#### **User Stories:**
* **As a developer, I want to** send a message to my agent and receive a response so that I can interact with it.
* **As a developer, I want to** see a live feed of the agent's internal steps (e.g., "searching memory," "calling LLM") while it formulates a response so that I can understand its process.
* **As a developer, I want to** click on any step in the feed to inspect the detailed data associated with it so that I can debug its logic.

#### **Technical Implementation:**
1.  **Backend Evolution:**
    * Create a new websocket or streaming HTTP endpoint, e.g., `/chat/{agent_id}`.
    * This endpoint will take a user's message and initiate a "run" by calling the external `POST /api-reference/runs/stream` endpoint.
    * As the run progresses, our backend will receive a `run_id`. It will then poll the `GET /api-reference/steps/list?run_id={run_id}` endpoint.
    * For each new step detected, our backend will stream this information to the frontend. It will also stream the final chat response.

2.  **Frontend Evolution:**
    * Redesign the UI into a two-panel layout: a chat window on the left and a "Reasoning Timeline" on the right.
    * Implement the chat input to send messages to our `/chat/{agent_id}` backend endpoint.
    * The "Reasoning Timeline" will connect to the backend stream and dynamically render each step as it's received.
    * Make each step in the timeline clickable. A click will trigger a call to a new backend endpoint (e.g., `/get_step_details/{step_id}`) which in turn calls the external `GET /api-reference/steps/{step_id}` to fetch and display the detailed data in a modal or side panel.

**Definition of Done:** A developer can chat with the agent. The timeline on the right populates with the agent's reasoning steps in real-time. Clicking any step reveals the underlying data for that action.

---

### ## Version 2.0: The Reflective Engine

**Goal:** To enable the agent to audit and correct its own memory. This version is successful if the agent can identify a contradiction in its knowledge base and, with user approval, resolve it.

#### **User Stories:**
* **As a developer, I want to** command my agent to reflect on its memory so that it can identify inconsistencies.
* **As a developer, I want to** be shown any detected contradictions or knowledge gaps in a clear format so that I can understand the issue.
* **As a developer, I want to** approve or deny the agent's proposed solution to fix its memory so that I retain final control.

#### **Technical Implementation:**
1.  **Backend Orchestration:**
    * Create a new endpoint, e.g., `POST /reflect/{agent_id}`.
    * When called, this endpoint initiates a new "run" by sending a carefully crafted **meta-prompt** to the `/chat/{agent_id}` endpoint. The prompt will be something like: *"System command: Analyze all memories in your knowledge base. Identify any two memories that contradict each other. Report the contradiction and a proposed solution."*
    * The backend will monitor the steps of this reflection run. It needs to parse the agent's final response to identify the proposed action (e.g., `{ "action": "delete", "target_memory_id": "xyz", "reason": "Contradicts memory abc" }`).
    * The backend will then hold this proposed action in a temporary state, waiting for user confirmation.

2.  **Frontend Interaction Flow:**
    * Add a "Reflect" button to the UI.
    * When the reflection run is complete, the frontend will receive the proposed action from the backend and render it in a confirmation dialog (e.g., "The agent wants to delete memory 'xyz'. Reason: ... Approve / Deny").
    * If the user clicks "Approve," the frontend calls a new backend endpoint (e.g., `/execute_action`), which then makes the final `DELETE /api-reference/sources/delete` call to correct the memory. The memory list is then refreshed.

**Definition of Done:** A developer can add two conflicting memories (e.g., "The sky is blue," "The sky is green"). They click "Reflect." The agent identifies the conflict and proposes deleting one memory. The developer approves the action, and the incorrect memory is removed from the system.