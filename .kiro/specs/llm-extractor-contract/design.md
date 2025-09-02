# Design

## Function Signature
```python
def extract_memory_actions(
    user_message: str,
    assistant_response: str, 
    existing_keys_by_bucket: Dict[str, List[str]]
) -> List[MemoryAction]
```

## Data Model
```python
@dataclass
class MemoryAction:
    action: Literal["Write", "Update", "Delete"]
    bucket: Literal["identity", "principles", "focus", "signals"] 
    key: str  # lower_snake_case, ≤30 chars
    value: str  # ≤140 chars, empty for Delete
    confidence: float  # 0.0 to 1.0
```

## Prompt Structure
1. **System**: Rules + schema + thresholds + max-3 + explicit-only
2. **Few-shots**: Write/Update, Delete+Write, No-op (3 examples)
3. **User**: Turn data + existing keys by bucket

## Processing Flow
1. Build prompt from inputs
2. LLM call (temp=0.1, max_tokens=256)
3. Parse JSON → repair if broken → [] if still broken
4. Filter by confidence thresholds
5. Apply bucket priority, select top 3

## Buckets
- **identity**: name, location, role
- **principles**: values, beliefs, approaches  
- **focus**: goals, projects, timeboxes
- **signals**: preferences, patterns