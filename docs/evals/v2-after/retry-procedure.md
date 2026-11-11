---
id: retry-procedure
type: procedure
tags: [http, retries]
---
# HTTP retries: reusable procedure

Retry transient HTTP 429 or 503 failures, subject to these limits:

1. Retry only idempotent operations automatically. A non-idempotent write requires an idempotency key or an explicit decision because a repeated request may apply its side effect twice.
2. Honor the server's `Retry-After` delay before retrying. This applies to HTTP 429; a 503 may also supply `Retry-After`. Waiting avoids hammering a server asking for time to recover. When no explicit server delay is available, use exponential backoff with jitter.
3. Make at most three attempts. Stop after the third attempt and report failure.

## Evidence and limits

The [synthetic rate-limit investigation](archive/retry-incident.md) reproduced an immediate-retry bug: a stub returned HTTP 429 with `Retry-After: 2`, and the corrected client waited at least two seconds. That investigation verified only the stub behavior, not a production deployment; it does not establish 503 behavior.

A deterministic stub confirmed the client stopped at three attempts. This does not prove every API is safe to retry.
