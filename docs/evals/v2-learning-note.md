---
created_at: 1794429180.743686
id: b879d311-f2b0-4bb1-8d47-f21c051f2189
tags:
- debugging
type: procedure
updated_at: 1794429180.743686
---

# Roll back the whole SQLite replacement batch

Verified 2026-11-12 in `transaction_demo.py`: run `python3 transaction_demo.py` from the project root. Before the fix, a duplicate insert raised `sqlite3.IntegrityError` but left the preceding DELETE and first INSERT pending; the check read `[('duplicate',)]` instead of the original row.

Wrap DELETE and all INSERTs in `with connection:` instead of committing only at the end. The context rolls back on failure and commits on success; let the exception propagate.

Verification passed (exit 0): failed batch preserves original rows; successful batch commits replacement.

Limits: verified only by the built-in in-memory check using default implicit transactions and a committed starting state. This context does not create a nested transaction; pending caller writes share its commit/rollback. Autocommit mode and concurrent/file-backed workloads were not tested.
