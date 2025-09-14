# memori (working title)

# Reflective Journaling Bot  
*PyCon India 2025 Demo: "Memory is the Agent: Edit the Memory, Edit the Agent"*

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


# Future Roadmap (looking for contributors)

---

# Memory Layer

## Overview

This project implements a **production-ready memory layer** for LLM agents.
It is **append-only, typed, multi-tenant, and retrievable** with deterministic context packing.

The design balances **research-backed features** (Generative Agents, MemGPT/Letta, cognitive memory surveys) with **practical system engineering**.

---

## Goals

* Ship a **production-credible spine** (core features 1–14).
* Keep scope ruthless: defer QoL and advanced features (15–23) until the core is stable.

---

## Core Features (1–14)

1. **Postgres + pgvector storage** (structured + semantic memory)
2. **Append-only log + versioning** (immutable history, tombstones)
3. **Typed schemas (Pydantic)** (`fact|event|goal|rule|trait|signal|document`)
4. **Hybrid retrieval** (BM25 + KNN, with filters)
5. **Context packer** (token budget, provenance, deterministic ordering)
6. **Importance/recency scoring** (importance, last\_accessed\_at, decay)
7. **Reflection & distillation** (episodic → semantic summaries)
8. **Teach / Correct / Forget APIs** (editable memory)
9. **AuthN/AuthZ + tenant scoping** (roles, quotas, isolation)
10. **Async embedding worker** (retries, DLQ, idempotency)
11. **PII scrubbing + retention/decay** (regex detectors, TTL, pinned items)
12. **Backups + restore drills** (PITR, weekly tests, RPO/RTO targets)
13. **Metrics + tracing** (Prometheus + OTEL)
14. **Topic/namespace isolation** (per-session or per-agent scoping)

---

## API Surface

* `POST /v1/memories` → create memory
* `POST /v1/memories/{id}/versions` → append new version
* `GET /v1/memories/{id}/history` → view version history
* `POST /v1/retrieve/search` → hybrid recall
* `POST /v1/retrieve/context` → budgeted context bundle
* `POST /v1/teach` → labeled memory write
* `POST /v1/correct` → correction version
* `POST /v1/forget` → tombstone

---

## Roadmap (Milestones & Sprints)

### ✅ M0 — Project Setup (Week 0)

* Repo scaffold (FastAPI, Alembic, CI, Docker Compose).
* Labels + PR template.
* **Exit**: `make up` boots local stack, CI green.

### 🟩 M1 — Storage & Types (Weeks 1–2)

* DB schema (`memories`, `versions`, `embeddings`).
* Append-only write path + tombstones.
* Pydantic schemas + OpenAPI.
* **Exit**: roundtrip CRUD tests; p95 write < 50ms local.

### 🟦 M2 — Retrieval & Context (Weeks 3–4)

* BM25 + pgvector KNN + fusion scoring.
* Filters: tenant, type, tags, namespace.
* Context packer + provenance.
* **Exit**: retrieval p95 < 120ms; deterministic pack.

### 🟨 M3 — Learning & Editability (Weeks 5–6)

* Reflection jobs (periodic + threshold).
* Teach / Correct / Forget APIs.
* **Exit**: distillation reduces tokens with equal coverage; corrections auditable.

### 🟥 M4 — Prod Hardening (Weeks 7–8)

* AuthN/AuthZ + quotas.
* Async embedding worker + DLQ.
* PII scrub + TTL + decay.
* PITR backups + restore drill.
* Metrics + OTEL traces.
* **Exit**: staging meets SLOs, runbook + dashboards ready.

---

## Deliverables by Milestone

* **M1**: CRUD + versioning + types
* **M2**: Retrieval + packer + namespaces
* **M3**: Reflection + teach/correct/forget
* **M4**: Auth + worker + PII + backups + metrics

➡️ Result: **Production-ready spine** (Core 1–14 complete).

---

## Success Metrics (v1)

* Reliability: p95 write < 80ms; retrieval < 150ms.
* Quality: retrieval precision\@10 ≥ 0.7; pack determinism = 100%.
* Safety: 0 PII leaks; weekly restore pass = 100%.
* Ops: DLQ < 0.5% of jobs; alerts on p95/queue spikes.

---

## Definition of Done

* Code + migrations + tests + docs updated.
* Metrics/traces added.
* Load test at target RPS.
* Security review for PII endpoints.

---

## Risk Register

* **Embedding drift** → store model ID, re-embed job, eval harness.
* **Unbounded growth** → TTL + decay + roll-ups; cold storage later.
* **Namespace leakage** → enforce predicates + denial tests.
* **Worker backlog** → back-pressure, quotas, autoscale, DLQ alarms.

---

## Later Extensions (15–23)

### Developer & Ops QoL

15. Python SDK (sync/async)
16. Admin Inspector (UI/CLI)
17. Eval Suite (precision\@k, OFF→ON deltas, long-term tests)
18. Golden-set Harness (YAML fixtures for CI)

### Advanced Research-Driven

19. Knowledge Graph Overlay (Cypher/Gremlin)
20. Multi-agent Sharing (role-scoped vaults)
21. Multimodal Episodic Memory (image/audio embeddings)
22. Compliance Automation (DSR APIs)
23. Multi-region Replication (HA/DR)

---

## Issue Template

```
Title: [feat] Retrieval fusion scoring (α/β/γ/δ)
Scope: Implement score fusion + filters + tests.
Acceptance:
- Unit tests for normalization + fusion.
- Golden queries match expected order.
- p95 retrieval < 150ms on staging dataset.
Telemetry:
- Metrics: retrieval_hits_total{type}, db_latency_ms{op="knn_search"}.
- Trace spans: bm25_search, knn_search, fuse_rank.
Docs: Update API.md (/retrieve/search) with examples.
```

---

## Environments

* **dev**: docker-compose (PG, app, worker, grafana/prometheus).
* **staging**: seeded dataset, nightly backup restore, load tests.
* **prod**: managed PG (PITR), object storage for backups, alerts to on-call.

---

## Hand-off Artifacts

* `README.md` (this doc: spec + roadmap)
* `API.md` (endpoint contracts + examples)
* `RUNBOOK.md` (backups, restore, DLQ, alerts)
* `SECURITY.md` (PII handling, auth, key rotation)

---

