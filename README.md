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




# V1 Components

1. **Schema Registry (Postgres)**

   * Stores user-defined classes (name, description, columns: dtype/enum/desc/pii).
   * Stores **LLM annotations**: `searchable_fields[]` (+ boosts), `identity_fields[]`, confidence.

2. **LLM Annotator (one-shot per schema version)**

   * Input: the class + columns (+ a tiny sample, optional).
   * Output: `searchable_fields`, `identity_fields`, confidence.
   * Gate: if identity confidence low → require human approve.

3. **Memory Extractor (per message)**

   * Emits **create-proposals** for classes in the active schema version.

4. **Validator/Normalizer**

   * Enforces schema constraints; drops junk; applies basic normalizers (trim/lower).

5. **Resolver + Decision**

   * **Identity-first**: if identity matches → **UPDATE**.
   * Else **BM25 (Postgres FTS)** over **annotated searchable fields** of that class:

     * score ≥ **0.80** → UPDATE
     * **0.55–0.80** → UPSERT if partial identity overlap; else CREATE
     * < **0.55** → CREATE
   * **DELETE** only if extractor says delete **and** identity matches → soft-delete.

6. **Memory Store (Postgres) + FTS**

   * Single source of truth (rows + JSONB payload).
   * `tsvector` index built **only** on `searchable_fields` (GIN). Auto-refresh on write.

# Flow (one diagram)

```
User Msg → Extractor → Proposals
            │
            ▼
       Validate/Normalize
            │
            ▼
      Identity Lookup (PG)
        ├─ found → UPDATE
        └─ not found → FTS(BM25) on searchable fields
                         ├─ score≥0.80 → UPDATE
                         ├─ 0.55–0.80 → UPSERT heuristics
                         └─ <0.55 → CREATE
            │
            ▼
        Write to Postgres  (FTS auto-updates)
            │
            ▼
        Log metrics (create/update/reject, scores)
```

# Defaults (don’t overthink)

* **Searchable fields**: short `string`, `enum`, `list[string]` (titles/names/tags/notes). No dates/numbers/bools.
* **Boosts**: `name/title/subject:3`, `enum/tags:2`, `notes/desc:1`.
* **Caps**: none needed yet (this is about writes, not prompt packing).
* **Idempotency (per turn)**: drop dupes by hash of `{class + identity_fields + values}`.

# Minimal tables (conceptual)

* `schema_versions`: classes, columns, LLM annotations, status.
* `memories`: `tenant_id, class, schema_version, object_key (identity hash), payload jsonb, is_deleted, created_at, updated_at`.
* `memories_fts`: `tsvector` generated from annotated fields (or as a computed column + GIN index).
* `audit_log` (optional): action, basis, bm25\_score.

# Ops you actually need

* **Schema change = new version** → run **backfill**: compute identity keys, rebuild FTS.
* **Monitors**: false-update rate (should \~0), missed-update rate, zero-hit rate on FTS, index size.
* **Kill switch**: if identity confidence low or false-updates spike, fall back to **create-only**.

# What you get

* One database (Postgres) running everything.
* LLM decides *what to search* and *how to identify*; backend makes final calls.
* Deterministic writes with simple, explainable rules.
