# Product Overview

**memori** is a reflective and policy-safe memory layer for AI agents that treats memory as infrastructure rather than an afterthought.

## Core Value Proposition

- **Transparent Memory**: Unlike black-box vector stores, memori provides full visibility into what agents remember and why
- **Reflective Intelligence**: Agents can audit, summarize, and correct their own memory through built-in reflection jobs
- **Policy-First Design**: Built-in PII redaction, provenance tracking, and right-to-delete compliance
- **Production-Ready**: Designed as infrastructure you can build production agents on, not just a library

## Key Components

- **Episodic Log**: Postgres-based append-only memory storage
- **Semantic Index**: pgvector for intelligent retrieval
- **Knowledge Graph**: Lightweight KG for reasoning-grade recall
- **Reflection Engine**: Background jobs for memory organization and decay
- **Policy Layer**: Privacy and governance controls

## Target Users

- Developers building production AI agents
- Teams needing auditable, transparent AI systems
- Organizations requiring privacy-compliant AI memory
- Researchers working on agent memory and reflection

## Philosophy

"Agents that forget responsibly will outlast agents that don't. Memory isn't a vector DB feature—it's infrastructure."