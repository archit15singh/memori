# memori (working title)

**Reflective and policy-safe memory layer for AI agents**

> Episodic log (Postgres) + Semantic index (pgvector) + Short-term cache (Redis) + Lightweight KG.
> With PII redaction, provenance links, right-to-delete, and reflective summarization built in.

---

## 🌍 Vision

Current “agent memory” is brittle: ad-hoc vector stores, no provenance, no deletion, no reflection. **memori** treats memory as infrastructure:

* **Truth anchored in a database** (Postgres, append-only episodic log).
* **Semantic retrieval** via `pgvector`.
* **Reasoning-grade recall** using a **lightweight knowledge graph (KG)** of concepts, claims, and evidence.
* **Reflective jobs** that cluster, summarize, and decay old memories.
* **Privacy & governance by default** — PII redaction, provenance tracking, and the right-to-delete.

This is not a library tacked onto an LLM. This is a **memory substrate** you can build production agents on.

---

## ✨ Key Differentiators

* 🔹 **Reflective memory**: summarization, clustering, and decay jobs keep memory structured and self-organizing.
* 🔹 **Policy hooks**: redact PII on ingest, propagate deletes, track provenance for audits.
* 🔹 **Hybrid model**: combine vector recall, relational queries, and KG reasoning.
* 🔹 **Composable API**: FastAPI endpoints you can drop into any agent framework.
* 🔹 **OSS-first**: Apache-2.0 license, designed for contributions.

---

## 🛠️ Features (v0 scope)

* `POST /ingest` — log an event (with optional PII redaction + semantic index).
* `GET /remember` — retrieve relevant events via semantic search + KG hops.
* `GET /reflect` — trigger background summarization, clustering, and decay jobs.
* `GET /audit` — trace provenance and policy history for a memory.
* `POST /policy/delete` — enforce right-to-delete (with forward pointers).

---

## ⚙️ Architecture

```
Client → FastAPI API layer
         │
         ├─► Postgres (episodic_log)
         │       └─► pgvector (semantic_index)
         │
         ├─► Redis (short-term cache)
         │
         ├─► Reflector jobs (summarize / cluster / decay)
         │
         └─► Knowledge Graph (concepts / claims / evidence)
                 └─► Provenance layer (summaries, clusters, deletes)
```

*Add diagram.png here with arrows & boxes.*

---

## 📦 Quickstart

### Prerequisites

* Python 3.11+
* Docker + Docker Compose
* OpenAI key (or alternative embedding provider) if you want embeddings.

### 1. Clone & configure

```bash
git clone https://github.com/<you>/memori.git
cd memori
cp .env.example .env
```

### 2. Run services

```bash
docker compose up --build
```

* API → [http://localhost:8000/docs](http://localhost:8000/docs)
* Postgres + pgvector
* Redis cache
* Worker for reflection jobs

### 3. First ingestion

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Discussed switching cache strategy to Redis TTL=600s."}'
```

### 4. Retrieval

```bash
curl "http://localhost:8000/remember?q=Redis"
```

---

## 🔑 Configuration

`.env.example`

```
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=memori
POSTGRES_USER=memori
POSTGRES_PASSWORD=memori

REDIS_URL=redis://redis:6379/0

LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=<key>
```

---

## 📜 API Reference (v0)

### `POST /ingest`

**Input**

```json
{
  "text": "Met with Priya about caching. Switch to Redis TTL=600s.",
  "tags": ["infra", "meeting"],
  "source": "slack://eng-thread-42"
}
```

**Pipeline**

1. Run PII redaction → annotate fields.
2. Insert into `episodic_log`.
3. Generate embeddings → insert into `semantic_index`.
4. Cache in Redis.

**Output**

```json
{
  "id": "uuid",
  "created_at": "2025-08-31T05:12:00Z"
}
```

---

### `GET /remember`

Query params:

* `q`: search query
* `k`: top-k results (default=10)
* `with_kg`: enrich with KG neighbors (default=false)

Response:

```json
[
  {
    "id": "uuid",
    "text": "Met with Priya about caching. Switch to Redis TTL=600s.",
    "score": 0.89,
    "provenance": ["slack://eng-thread-42"]
  }
]
```

---

### `GET /reflect`

Triggers clustering/summarization/decay jobs. Returns job status.

---

### `POST /policy/delete`

Input:

```json
{ "id": "uuid" }
```

Effect:

* Soft-delete in `episodic_log`
* Remove from `semantic_index`
* Insert forward pointer in `provenance`

---

## 🗄️ Data Model

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Episodic log
CREATE TABLE episodic_log (
  id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT now(),
  source TEXT,
  text TEXT NOT NULL,
  redaction JSONB DEFAULT '{}'::jsonb,
  deleted_at TIMESTAMPTZ
);

-- Semantic index
CREATE TABLE semantic_index (
  episode_id UUID PRIMARY KEY REFERENCES episodic_log(id) ON DELETE CASCADE,
  embedding VECTOR(1536) NOT NULL
);

-- Knowledge Graph
CREATE TABLE concept (
  id UUID PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE claim (
  id UUID PRIMARY KEY,
  subject UUID REFERENCES concept(id),
  predicate TEXT NOT NULL,
  object TEXT NOT NULL,
  evidence_episode UUID REFERENCES episodic_log(id)
);

-- Provenance
CREATE TABLE provenance (
  id UUID PRIMARY KEY,
  episode_id UUID REFERENCES episodic_log(id),
  parent_episode UUID REFERENCES episodic_log(id),
  relation TEXT NOT NULL -- e.g. "summary_of", "cluster_member"
);
```

---

## 🔄 Reflector Jobs

* **Summarize:** batch compress multiple episodes → summary entry.
* **Cluster:** group similar embeddings, label with centroid keyphrase.
* **Decay:** time/usage-based pruning; archive or delete.
* **Policy enforcement:** cascade deletes, re-index.

Worker options: Celery, RQ, Arq.

---

## 📈 Roadmap

* [ ] v0.1: Ingest / Remember / Reflect API, Dockerized
* [ ] v0.2: Provenance + delete propagation
* [ ] v0.3: KG extraction (concept/claim tables)
* [ ] v0.4: Observability (structured logs + traces)
* [ ] v0.5: Benchmarks (latency, recall, storage footprint)
* [ ] v1.0: Production-ready release (tests, docs, integrations)

---

## 👩‍💻 Contributing

We welcome contributors of all backgrounds.
**Ways to help:**

* Add ingestion connectors (Slack, Notion, GitHub).
* Build reflection jobs (summarize/cluster).
* Add KG extractors (NER, relation extraction).
* Improve PII redaction.
* Write tests + docs.

### Workflow

1. Fork the repo & create a branch.
2. Run `make check` (lint + tests).
3. Submit PR → every PR must include tests for new paths.
4. PRs will be reviewed by maintainers within \~48h.

Issues labeled **good first issue** are beginner-friendly.

---

## 🔐 Privacy & Policy

* **Right-to-Delete:** implemented as soft delete + index removal.
* **PII Redaction:** regex + model-based → stored in `redaction` JSON field.
* **Provenance:** every derived artifact (summary, cluster) links back to original.

---

## 🧠 Philosophy

Agents that forget responsibly will outlast agents that don’t.
Memory isn’t a “vector DB feature.” It’s **infrastructure**.
We build memory the way OSes built file systems: truth, indexing, provenance, and policy first.

---

## 📜 License

Apache-2.0 (intended). See `LICENSE`.

---

## 🙌 Maintainers

* [@your-handle](https://github.com/you) – Core architecture & API
* \[@co-maintainer] – Reflection jobs & KG modeling

---

## ❓ FAQ

**Why Postgres as source of truth?**
Because agents need auditable, durable memory, not just fuzzy embeddings.

**Why bundle reflection?**
Without summarization/decay, memory bloat kills recall. Reflection = scalability.

**Can I use another embedding model?**
Yes. Swap `core/embed.py`. Just keep dimensions consistent with `pgvector`.

**What happens on delete?**
Memory is soft-deleted, removed from semantic index, and all derived summaries mark forward pointers.

---

