# Tasks

- [ ] 1. Create MemoryAction dataclass
  - action, bucket, key, value, confidence fields
  - Validation: key ≤30 chars lower_snake_case, value ≤140 chars

- [ ] 2. Build prompt system
  - System instructions template (rules + schema + thresholds)
  - 3 few-shot examples (Write/Update, Delete+Write, No-op)
  - User content formatter (turn data + existing keys)

- [ ] 3. JSON parsing + repair
  - Parse LLM output as JSON array
  - Repair function: strip prose, validate fields, drop invalid
  - Fallback to [] if repair fails

- [ ] 4. Selection logic
  - Filter by confidence thresholds (identity/principles ≥0.8, focus/signals ≥0.7)
  - Bucket priority: focus > principles > identity > signals
  - Select top 3 by confidence

- [ ] 5. Main extractor function
  - extract_memory_actions(user_message, assistant_response, existing_keys_by_bucket)
  - Integrate: prompt → LLM call → parse → filter → select
  - Model config: temp=0.1, max_tokens=256

- [ ] 6. Demo script
  - Test cases: "I'm Archit...", "Values: first-principles", "Drop evening_coding", "thanks!"
  - Verify outputs match expected actions