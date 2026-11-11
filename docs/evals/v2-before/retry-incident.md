---
id: retry-incident
type: debugging
tags: [http, retries]
---
# HTTP retries: investigation notes

During a synthetic debugging task, an HTTP client kept hammering a rate-limited server. We inspected responses, reproduced a 429, retried a few times, discussed timing, and eventually found the same immediate retry bug again. The useful lesson is: for HTTP 429, honor the server's Retry-After delay before retrying. A 503 may also supply Retry-After. This avoids hammering a server asking for time to recover.

Source: synthetic reproduction; a stub server returned 429 and Retry-After: 2, and the corrected client waited at least two seconds. We verified only this stub behavior, not a production deployment. Related procedure: [[retry-procedure]].
