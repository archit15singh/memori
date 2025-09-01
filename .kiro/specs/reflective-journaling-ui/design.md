# Design Document

## Overview
React demo: chat (75%) + memory panel (25%). One App component, basic styling, real backend APIs.

## Components
```
App
├── Chat area (input + messages)
└── Memory area (4 sections with edit/delete)
```

## State (all in App)
- `messages` - chat array
- `insights, anchors, routines, notes` - memory arrays  
- `editingMemory` - currently editing memory item
- `input` - current chat input

## APIs
- Chat: stubbed 2s delay
- Memory: real FastAPI endpoints (GET/PUT/DELETE)

## Styling
- CSS flexbox 75%/25% split
- Basic message bubbles
- Simple memory badges with edit/delete buttons
- Inline edit forms that appear when editing