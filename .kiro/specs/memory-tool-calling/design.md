# Design Document

## Overview

This design enables automatic memory management through OpenAI tool calling. The LLM will have access to memory management tools (create, update, delete) and can call them during conversations to keep its memory store current and accurate.

## Architecture

```
User Message → Enhanced Prompt with Tools → LLM Response + Tool Calls → Execute Tools → Final Response
                                                    ↓                        ↓
                                              Tool Definitions ←──── Memory Database
```

## Components and Interfaces

### Memory Management Tools

**Tool Function Definitions**
```python
MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_memory",
            "description": "Create a new memory entry",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["identity", "principles", "focus", "signals"],
                        "description": "Memory category"
                    },
                    "key": {
                        "type": "string",
                        "description": "Short descriptive key for the memory"
                    },
                    "value": {
                        "type": "string",
                        "description": "The memory content"
                    }
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "update_memory",
            "description": "Update an existing memory entry",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["identity", "principles", "focus", "signals"]
                    },
                    "key": {
                        "type": "string",
                        "description": "Key of the memory to update"
                    },
                    "value": {
                        "type": "string", 
                        "description": "New memory content"
                    }
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory", 
            "description": "Delete a memory entry",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["identity", "principles", "focus", "signals"]
                    },
                    "key": {
                        "type": "string",
                        "description": "Key of the memory to delete"
                    }
                },
                "required": ["category", "key"]
            }
        }
    }
]
```

### Tool Execution Functions

**Memory Tool Handlers**
```python
def execute_create_memory(category: str, key: str, value: str) -> Dict:
    # Create new memory in database
    # Generate UUID and insert into memories table
    # Return success/failure status
    
def execute_update_memory(category: str, key: str, value: str) -> Dict:
    # Find existing memory by category and key
    # Update value in database
    # Return success/failure status
    
def execute_delete_memory(category: str, key: str) -> Dict:
    # Find and delete memory by category and key
    # Return success/failure status
```

### Enhanced Chat Pipeline

**Tool-Enabled Chat Function**
```python
async def get_ai_response_with_tools(message: str) -> str:
    # Load current memories for context
    memories = load_all_memories_for_chat()
    
    # Build prompt with memory context and tool instructions
    enhanced_prompt = build_tool_enabled_prompt(memories, message)
    
    # Call OpenAI with tools enabled
    response = await openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": enhanced_prompt}],
        tools=MEMORY_TOOLS,
        tool_choice="auto"
    )
    
    # Execute any tool calls
    if response.choices[0].message.tool_calls:
        await execute_tool_calls(response.choices[0].message.tool_calls)
    
    # Return the conversational response
    return response.choices[0].message.content
```

## Implementation Strategy

### Enhanced System Prompt

**Tool-Aware Prompt Template**
```python
TOOL_ENABLED_SYSTEM_PROMPT = """
You are a reflective journaling AI bot with access to your memory store and tools to manage it.

Your current memories:
{memory_context}

You have access to these tools to manage your memories:
- create_memory: Add new memories when you learn something new
- update_memory: Update existing memories when information changes  
- delete_memory: Remove outdated or incorrect memories

Use these tools automatically when:
- You learn new information about yourself (identity, principles, focus, signals)
- Existing information needs to be updated or corrected
- Information becomes outdated or irrelevant

After using tools, continue with a natural conversational response. Don't mention the tool usage to the user.

User: {user_message}
"""
```

### Tool Call Processing

**Tool Execution Pipeline**
```python
async def execute_tool_calls(tool_calls: List) -> List[Dict]:
    results = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        try:
            if function_name == "create_memory":
                result = execute_create_memory(**arguments)
            elif function_name == "update_memory":
                result = execute_update_memory(**arguments)
            elif function_name == "delete_memory":
                result = execute_delete_memory(**arguments)
            else:
                result = {"error": f"Unknown function: {function_name}"}
                
            results.append(result)
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            results.append({"error": str(e)})
    
    return results
```

## Data Models

### Tool Call Response
```python
class ToolCallResult(BaseModel):
    success: bool
    message: str
    memory_id: Optional[str] = None
    error: Optional[str] = None
```

### Enhanced Chat Response (Internal)
```python
class ToolEnabledChatResponse(BaseModel):
    response: str
    tool_calls_made: List[Dict] = []
    tool_results: List[ToolCallResult] = []
    memory_operations: int = 0
```

## Database Integration

### Memory Operations

**Create Memory Function**
```python
def create_memory_db(memory_type: str, key: str, value: str) -> str:
    # Generate UUID for new memory
    # Insert into memories table
    # Return memory ID or raise exception
    
def find_memory_by_key(memory_type: str, key: str) -> Optional[MemoryItem]:
    # Find existing memory by category and key
    # Return memory item or None
    
def delete_memory_by_key(memory_type: str, key: str) -> bool:
    # Delete memory by category and key
    # Return success status
```

## Error Handling

### Tool Execution Failures
- **Graceful Degradation**: Continue conversation even if tool calls fail
- **Logging**: Log all tool execution errors for debugging
- **User Experience**: Don't expose tool failures to user

### Database Operation Failures
- **Retry Logic**: Retry failed database operations once
- **Error Logging**: Track database failures
- **Fallback**: Continue chat even if memory operations fail

### Invalid Tool Calls
- **Validation**: Validate tool parameters before execution
- **Error Response**: Return clear error messages for invalid calls
- **Recovery**: Continue processing other valid tool calls

## Performance Considerations

### Tool Call Optimization
- **Batch Operations**: Execute multiple tool calls efficiently
- **Database Connections**: Reuse connections for multiple operations
- **Async Processing**: Use async operations where possible

### Response Time Management
- **Tool Execution**: Keep tool operations under 500ms total
- **Database Optimization**: Use efficient queries for memory operations
- **Parallel Processing**: Execute independent tool calls in parallel

## Testing Strategy

### Tool Function Testing
- Test each tool function with valid and invalid parameters
- Test database operations for create, update, delete
- Test error handling for various failure scenarios
- Validate tool call parameter parsing and validation

### Integration Testing
- Test end-to-end conversations with tool calls
- Verify memory operations are executed correctly
- Test multiple tool calls in single conversation
- Validate conversation flow continues naturally after tool calls

### LLM Behavior Testing
- Test that LLM makes appropriate tool calls for different conversation types
- Verify tool calls are made automatically without user prompting
- Test that conversational responses remain natural after tool usage
- Validate memory consistency after tool operations