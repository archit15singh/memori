# Requirements

## Core Function
Extract ≤3 memory actions from conversation turns as JSON array.

## I/O Contract
- **Input**: user_message, assistant_response, existing_keys_by_bucket
- **Output**: JSON array with action, bucket, key, value, confidence fields
- **Constraints**: keys ≤30 chars lower_snake_case, values ≤140 chars

## Safety Rules
- Confidence thresholds: identity/principles ≥0.8, focus/signals ≥0.7
- Explicit facts only, no guessing
- Priority: focus > principles > identity > signals
- Max 3 items per turn

## Error Handling
- Invalid JSON → single repair pass → empty array if still broken
- Strip prose, validate fields, drop invalid items