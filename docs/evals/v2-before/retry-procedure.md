---
id: retry-procedure
type: procedure
tags: [http, retries]
---
# HTTP retries: reusable procedure

Retry transient HTTP 429 or 503 failures. When no explicit server delay is available, use exponential backoff with jitter and at most three attempts. Retry only idempotent operations automatically; a non-idempotent write requires an idempotency key or an explicit decision because a repeated request may apply its side effect twice. Stop after the third attempt and report failure.

A deterministic stub confirmed the client stopped at three attempts. This does not prove every API is safe to retry. The rate-limit investigation is [[retry-incident]].
