# memori (working title)

# Reflective Journaling Bot  
*PyCon India 2025 Demo — "Memory is the Agent: Edit the Memory, Edit the Agent"*

---

## What It Does  
A chat app with **editable AI memory**, fully powered by the LLM:  
- **Split UI:** Chat on the left, memory on the right  
- **4 Memory Types:** Identity, Principles, Focus, Signals  
- **Real-Time Memory Ops:** LLM handles **create, update, and delete** of memories automatically  
- **Direct Editing:** Users can override or tweak memories anytime  
- **Memory-Aware Responses:** Bot adapts instantly based on stored memory  

---

## Tech Stack  
- **Backend:** FastAPI + SQLite + OpenAI GPT  
- **Frontend:** React with live updates  
- **Persistence:** Memories survive page refreshes  

---

## Quick Start  

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app:app --reload

# Frontend
cd frontend
npm install
npm start
````

Open **[http://localhost:3000](http://localhost:3000)**

---

## Demo Flow

1. Chat → LLM creates memories in real-time
2. Edit/Delete → LLM updates memory state + bot behavior instantly


