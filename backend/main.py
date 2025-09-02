"""
FastAPI Chat Backend

A simple FastAPI application with a chat endpoint.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from contextlib import asynccontextmanager
import json
import os
import sqlite3
import logging
import time
import uuid
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI
from models import ChatRequest, ChatResponse, ErrorResponse, MemoryItem, MemoryResponse, MessageItem, MessagesResponse

# Load environment variables from .env file
load_dotenv()

# Configure logging for product insights
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application startup and shutdown.
    """
    # Startup
    logger.info("🚀 Chat Backend starting up...")
    init_database()
    logger.info("✅ Backend ready - database initialized")
    yield
    # Shutdown (if needed)
    logger.info("🛑 Chat Backend shutting down...")


# Create FastAPI app instance with comprehensive metadata
app = FastAPI(
    title="Chat Backend API",
    description="A simple chat backend service with FastAPI that provides a /chat endpoint for processing messages",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Initialize OpenAI client with API key from environment
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)



# Database file path
DB_PATH = "chat_app.db"





def init_database():
    """
    Initialize SQLite database and create memories and messages tables if they don't exist.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create memories table with id, type, key, value columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL
            )
        """)
        
        # Create messages table with id, content, sender, timestamp columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                sender TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
        """)
        
        # Check existing memory count for product insights
        cursor.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]
        
        # Check existing message count for product insights
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        logger.info(f"💾 Database ready - {memory_count} memories, {message_count} messages loaded")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise


def get_all_memories():
    """
    Get all memories from the database organized by type.
    
    Returns:
        dict: Dictionary with memory types as keys and lists of MemoryItem objects as values
    """
    start_time = time.time()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, type, key, value FROM memories")
    rows = cursor.fetchall()
    conn.close()
    
    # Organize memories by type
    memories = {
        "identity": [],
        "principles": [],
        "focus": [],
        "signals": []
    }
    
    for row in rows:
        memory_id, memory_type, key, value = row
        memory_item = MemoryItem(id=memory_id, key=key, value=value)
        if memory_type in memories:
            memories[memory_type].append(memory_item)
    
    # Log memory retrieval metrics
    total_memories = sum(len(memories[t]) for t in memories)
    query_time = round((time.time() - start_time) * 1000, 2)
    logger.info(f"🧠 Retrieved {total_memories} memories in {query_time}ms")
    
    return memories


def get_all_messages():
    """
    Get all messages from the database in chronological order.
    
    Returns:
        List[MessageItem]: List of all messages ordered by timestamp
    """
    start_time = time.time()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, content, sender, timestamp FROM messages ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    conn.close()
    
    # Convert database rows to MessageItem objects
    messages = []
    for row in rows:
        message_id, content, sender, timestamp = row
        message_item = MessageItem(id=message_id, content=content, sender=sender, timestamp=timestamp)
        messages.append(message_item)
    
    # Log message retrieval metrics
    query_time = round((time.time() - start_time) * 1000, 2)
    logger.info(f"💬 Retrieved {len(messages)} messages in {query_time}ms")
    
    return messages


def load_all_memories_for_chat():
    """
    Load all memories for chat context.
    
    This function wraps the existing get_all_memories() function to provide
    a dedicated interface for chat functionality.
    
    Returns:
        dict: Dictionary with memory types as keys and lists of MemoryItem objects as values
              Categories: identity, principles, focus, signals
    """
    logger.info("🧠 Loading memories for chat context")
    return get_all_memories()


def format_memories_for_prompt(memories):
    """
    Format memories into readable text for LLM prompt context.
    
    Converts memory objects organized by category into a structured text format
    suitable for inclusion in system prompts.
    
    Args:
        memories (dict): Dictionary with memory types as keys and lists of MemoryItem objects as values
                        Expected keys: identity, principles, focus, signals
    
    Returns:
        str: Formatted memory context text with clear headers and structure
    """
    formatted_sections = []
    
    # Define category headers and their descriptions
    category_info = {
        "identity": ("IDENTITY (who you are)", "These define your core identity and characteristics:"),
        "principles": ("PRINCIPLES (how you operate)", "These guide your behavior and decision-making:"),
        "focus": ("FOCUS (what matters now)", "These are your current priorities and areas of attention:"),
        "signals": ("SIGNALS (patterns you notice)", "These are patterns and insights you've observed:")
    }
    
    for category, (header, description) in category_info.items():
        memory_items = memories.get(category, [])
        
        if memory_items:
            # Add category header and description
            section = [f"{header}", description, ""]
            
            # Add each memory item in a readable format
            for item in memory_items:
                section.append(f"• {item.key}: {item.value}")
            
            # Add empty line after section
            section.append("")
            formatted_sections.append("\n".join(section))
    
    # Join all sections with newlines
    formatted_context = "\n".join(formatted_sections).strip()
    
    # Log formatting metrics
    total_memories = sum(len(memories.get(cat, [])) for cat in category_info.keys())
    context_length = len(formatted_context)
    logger.info(f"📝 Formatted {total_memories} memories into {context_length} character context")
    
    return formatted_context


def render_user_context(memories):
    """
    Render user context from memories using only the generic bucket structure.
    
    Creates a simple context block using the predefined memory categories
    without hardcoding specific field names or content expectations.
    
    Args:
        memories (dict): Dictionary with memory types as keys and lists of MemoryItem objects as values
                        Expected keys: identity, principles, focus, signals
    
    Returns:
        str: Formatted user context block or empty string if no memories
    """
    # Define the bucket meanings (only hardcoded part)
    bucket_info = {
        "identity": "who the user is",
        "principles": "how the user operates", 
        "focus": "what matters to the user now",
        "signals": "patterns the user notices"
    }
    
    context_sections = []
    total_memories = 0
    
    # Build context using only bucket structure
    for bucket_type, description in bucket_info.items():
        memory_items = memories.get(bucket_type, [])
        
        if memory_items:
            # Add bucket header
            section_lines = [f"USER {bucket_type.upper()} ({description}):"]
            
            # Add all memories in this bucket generically
            for item in memory_items:
                section_lines.append(f"• {item.key}: {item.value}")
            
            context_sections.append("\n".join(section_lines))
            total_memories += len(memory_items)
    
    # If no memories found, return empty string
    if total_memories == 0:
        logger.info("📋 No memories found for user context")
        return ""
    
    # Join all sections
    context_text = "\n\n".join(context_sections)
    
    # Log context rendering metrics
    context_length = len(context_text)
    logger.info(f"📋 Rendered user context with {total_memories} memories ({context_length} chars)")
    
    return context_text


def get_system_prompt() -> str:
    """
    Get the clean system prompt for the reflective journaling bot.
    
    Returns a fixed system prompt that establishes the AI's role without
    including any user memory context or identity confusion.
    
    Returns:
        str: Clean system prompt defining the AI's role and behavior
    """
    prompt = """You are Reflective Journaling Bot.
- Reflect back in 1–2 lines.
- Ask exactly 1 incisive follow-up question.
- Use second person ("you/your") when referring to the user.
- Never impersonate the user or claim their identity."""
    
    logger.info(f"🔧 Built clean system prompt ({len(prompt)} chars)")
    return prompt


def update_memory_db(memory_type: str, memory_id: str, key: str, value: str):
    """
    Update a memory item in the database.
    
    Args:
        memory_type: Type of memory (identity, principles, focus, signals)
        memory_id: ID of the memory item
        key: Memory key
        value: Memory value
        
    Returns:
        bool: True if update was successful, False if memory not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE memories SET key = ?, value = ? WHERE id = ? AND type = ?",
        (key, value, memory_id, memory_type)
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    success = rows_affected > 0
    if success:
        logger.info(f"✏️ Updated {memory_type} memory: '{key}' (id: {memory_id[:8]}...)")
    else:
        logger.warning(f"⚠️ Memory update failed - not found: {memory_type}/{memory_id[:8]}...")
    
    return success


def delete_memory_db(memory_type: str, memory_id: str):
    """
    Delete a memory item from the database.
    
    Args:
        memory_type: Type of memory (identity, principles, focus, signals)
        memory_id: ID of the memory item to delete
        
    Returns:
        bool: True if deletion was successful, False if memory not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM memories WHERE id = ? AND type = ?",
        (memory_id, memory_type)
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    success = rows_affected > 0
    if success:
        logger.info(f"🗑️ Deleted {memory_type} memory (id: {memory_id[:8]}...)")
    else:
        logger.warning(f"⚠️ Memory deletion failed - not found: {memory_type}/{memory_id[:8]}...")
    
    return success


def get_existing_memory_keys() -> Dict[str, List[str]]:
    """
    Get existing memory keys organized by bucket to avoid duplicates.
    
    Returns:
        dict: Dictionary with bucket names as keys and lists of existing memory keys as values
    """
    start_time = time.time()
    conn = None
    
    try:
        logger.info("📚 Loading existing memory keys from database")
        
        # Enhanced database connection with error handling
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
        except Exception as db_error:
            logger.error(f"❌ Failed to connect to database for memory keys: {str(db_error)}")
            raise Exception(f"Database connection failed: {str(db_error)}")
        
        # Execute query with error handling
        try:
            cursor.execute("SELECT type, key FROM memories")
            rows = cursor.fetchall()
            logger.info(f"📚 Retrieved {len(rows)} memory records from database")
        except sqlite3.Error as query_error:
            logger.error(f"❌ Failed to query memory keys: {str(query_error)}")
            raise Exception(f"Database query failed: {str(query_error)}")
        
        # Organize keys by bucket with validation
        existing_keys = {
            "identity": [],
            "principles": [],
            "focus": [],
            "signals": []
        }
        
        invalid_types = []
        for memory_type, key in rows:
            if memory_type in existing_keys:
                existing_keys[memory_type].append(key)
            else:
                invalid_types.append(memory_type)
        
        # Log any invalid memory types found
        if invalid_types:
            unique_invalid = list(set(invalid_types))
            logger.warning(f"⚠️ Found {len(invalid_types)} memories with invalid types: {unique_invalid}")
        
        # Log summary
        query_time = round((time.time() - start_time) * 1000, 2)
        total_keys = sum(len(keys) for keys in existing_keys.values())
        logger.info(f"✅ Loaded {total_keys} existing memory keys in {query_time}ms")
        
        for bucket, keys in existing_keys.items():
            if keys:
                logger.info(f"  - {bucket}: {len(keys)} keys")
        
        return existing_keys
        
    except Exception as e:
        query_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ Failed to get existing memory keys after {query_time}ms: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        # Return empty structure as fallback
        return {
            "identity": [],
            "principles": [],
            "focus": [],
            "signals": []
        }
    finally:
        if conn:
            try:
                conn.close()
            except Exception as close_error:
                logger.warning(f"⚠️ Error closing database connection: {str(close_error)}")


async def extract_memories(user_message: str, assistant_response: str, existing_memories: Dict[str, List[str]]) -> List[Dict]:
    """
    Extract memories from a conversation turn using OpenAI API.
    
    Args:
        user_message: The user's input message
        assistant_response: The AI's response
        existing_memories: Current memory keys organized by bucket
        
    Returns:
        List of memory actions: [{"action": "create|update", "bucket": "identity", "key": "name", "value": "Alex"}]
    """
    start_time = time.time()
    
    try:
        logger.info("🧠 Starting memory extraction from conversation")
        
        # Create system prompt for memory extraction
        system_prompt = """You are a memory extraction system. Analyze conversations and extract key-value memories into 4 buckets:

BUCKETS:
- identity: who the user is (name, role, background, characteristics)
- principles: how the user operates (values, beliefs, approaches, preferences)
- focus: what matters to the user now (current projects, goals, priorities)
- signals: patterns the user notices (behaviors, insights, observations)

RULES:
1. Extract maximum 3 memories per conversation
2. Only extract significant, lasting information worth remembering
3. Use clear, descriptive keys (e.g., "name", "current_role", "main_project")
4. Keep values concise but informative
5. If a key already exists, decide whether to update it
6. Output valid JSON array only

OUTPUT FORMAT:
[
  {"action": "create", "bucket": "identity", "key": "name", "value": "Alex"},
  {"action": "update", "bucket": "focus", "key": "current_project", "value": "chat app"}
]

If no memories should be extracted, return: []"""

        # Format existing memories for context
        existing_context = "EXISTING MEMORY KEYS:\n"
        for bucket, keys in existing_memories.items():
            if keys:
                existing_context += f"- {bucket}: {', '.join(keys)}\n"
            else:
                existing_context += f"- {bucket}: (none)\n"

        # Create user prompt with conversation context
        user_prompt = f"""{existing_context}

CONVERSATION TO ANALYZE:
User: {user_message}
Assistant: {assistant_response}

Extract memories from this conversation:"""

        # Call OpenAI API with enhanced error handling
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"🤖 OpenAI API response received (length: {len(response_text)} chars)")
            
        except Exception as api_error:
            api_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"❌ OpenAI API call failed after {api_time}ms: {str(api_error)}")
            # Return empty list on API failure to prevent chat disruption
            return []
        
        # Enhanced JSON parsing with better error handling
        memory_actions = []
        try:
            parsed_response = json.loads(response_text)
            if isinstance(parsed_response, list):
                memory_actions = parsed_response
                logger.info(f"✅ Successfully parsed JSON response with {len(memory_actions)} potential actions")
            else:
                logger.warning(f"⚠️ Memory extraction returned non-list type: {type(parsed_response)}, using empty list")
                memory_actions = []
        except json.JSONDecodeError as json_error:
            logger.warning(f"⚠️ Memory extraction returned invalid JSON: {json_error}")
            logger.warning(f"⚠️ Raw response was: {response_text[:200]}...")
            
            # Attempt to extract partial JSON if possible
            try:
                # Try to find JSON array in the response
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    partial_json = json_match.group(0)
                    memory_actions = json.loads(partial_json)
                    logger.info(f"✅ Recovered partial JSON with {len(memory_actions)} actions")
                else:
                    logger.warning("⚠️ No JSON array found in response, using empty list")
                    memory_actions = []
            except Exception as recovery_error:
                logger.warning(f"⚠️ JSON recovery failed: {recovery_error}, using empty list")
                memory_actions = []
        
        # Enhanced validation with detailed logging
        valid_actions = []
        invalid_actions = []
        valid_buckets = {"identity", "principles", "focus", "signals"}
        valid_action_types = {"create", "update"}
        
        for i, action in enumerate(memory_actions):
            if not isinstance(action, dict):
                invalid_actions.append(f"Action {i}: not a dictionary")
                continue
                
            action_type = action.get("action")
            bucket = action.get("bucket")
            key = action.get("key")
            value = action.get("value")
            
            # Detailed validation with specific error messages
            validation_errors = []
            if action_type not in valid_action_types:
                validation_errors.append(f"invalid action '{action_type}'")
            if bucket not in valid_buckets:
                validation_errors.append(f"invalid bucket '{bucket}'")
            if not key or not isinstance(key, str) or not key.strip():
                validation_errors.append("missing or empty key")
            if not value or not isinstance(value, str) or not value.strip():
                validation_errors.append("missing or empty value")
            
            if validation_errors:
                invalid_actions.append(f"Action {i}: {', '.join(validation_errors)}")
            else:
                valid_actions.append(action)
        
        # Log validation results
        if invalid_actions:
            logger.warning(f"⚠️ Skipped {len(invalid_actions)} invalid memory actions:")
            for invalid_action in invalid_actions:
                logger.warning(f"  - {invalid_action}")
        
        api_time = round((time.time() - start_time) * 1000, 2)
        if valid_actions:
            logger.info(f"✅ Successfully extracted {len(valid_actions)} valid memories in {api_time}ms")
            for action in valid_actions:
                logger.info(f"  - {action['action']} {action['bucket']}.{action['key']}: {action['value'][:50]}...")
        else:
            logger.info(f"ℹ️ No valid memories extracted from conversation in {api_time}ms")
        
        return valid_actions
        
    except Exception as e:
        api_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ Memory extraction failed after {api_time}ms: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        # Return empty list to prevent chat disruption
        return []


def save_message(content: str, sender: str) -> bool:
    """
    Save a chat message to the database.
    
    Args:
        content: The message content/text
        sender: Who sent the message ('user' or 'bot')
        
    Returns:
        bool: True if message was saved successfully, False otherwise
    """
    start_time = time.time()
    
    try:
        # Generate UUID and timestamp for the message
        message_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)  # Unix timestamp in milliseconds
        
        logger.info(f"💬 Saving {sender} message (id: {message_id[:8]}...)")
        
        # Connect to database following existing patterns
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert message into database
        cursor.execute(
            "INSERT INTO messages (id, content, sender, timestamp) VALUES (?, ?, ?, ?)",
            (message_id, content, sender, timestamp)
        )
        
        conn.commit()
        conn.close()
        
        # Log success metrics
        save_time = round((time.time() - start_time) * 1000, 2)
        content_preview = content[:50] + "..." if len(content) > 50 else content
        logger.info(f"✅ Saved {sender} message in {save_time}ms: '{content_preview}' (id: {message_id[:8]}...)")
        
        return True
        
    except sqlite3.Error as db_error:
        save_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ Database error saving {sender} message after {save_time}ms: {str(db_error)}")
        return False
    except Exception as e:
        save_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ Failed to save {sender} message after {save_time}ms: {str(e)}")
        return False


def apply_memory_actions(memory_actions: List[Dict]) -> None:
    """
    Apply extracted memory actions to the database.
    
    Processes a list of memory actions by either creating new memories with generated UUIDs
    or updating existing memories by finding their IDs.
    
    Args:
        memory_actions: List of memory actions from extractor
                       Format: [{"action": "create|update", "bucket": "identity", "key": "name", "value": "Alex"}]
    """
    if not memory_actions:
        logger.info("🧠 No memory actions to apply")
        return
    
    start_time = time.time()
    logger.info(f"🧠 Starting to apply {len(memory_actions)} memory actions")
    
    conn = None
    cursor = None
    
    created_count = 0
    updated_count = 0
    failed_count = 0
    
    try:
        # Enhanced database connection with error handling
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            logger.info("✅ Database connection established for memory actions")
        except Exception as db_error:
            logger.error(f"❌ Failed to connect to database: {str(db_error)}")
            raise Exception(f"Database connection failed: {str(db_error)}")
        
        # Process each memory action with detailed error handling
        for i, action in enumerate(memory_actions):
            action_type = action.get("action")
            bucket = action.get("bucket")
            key = action.get("key")
            value = action.get("value")
            
            try:
                logger.info(f"🔄 Processing action {i+1}/{len(memory_actions)}: {action_type} {bucket}.{key}")
                
                if action_type == "create":
                    # Generate new UUID for the memory
                    memory_id = str(uuid.uuid4())
                    
                    # Insert new memory into database
                    cursor.execute(
                        "INSERT INTO memories (id, type, key, value) VALUES (?, ?, ?, ?)",
                        (memory_id, bucket, key, value)
                    )
                    created_count += 1
                    logger.info(f"➕ Created {bucket} memory: '{key}' = '{value[:50]}...' (id: {memory_id[:8]}...)")
                    
                elif action_type == "update":
                    # Find existing memory by bucket and key
                    cursor.execute(
                        "SELECT id FROM memories WHERE type = ? AND key = ? LIMIT 1",
                        (bucket, key)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        memory_id = result[0]
                        # Update existing memory
                        cursor.execute(
                            "UPDATE memories SET value = ? WHERE id = ?",
                            (value, memory_id)
                        )
                        updated_count += 1
                        logger.info(f"✏️ Updated {bucket} memory: '{key}' = '{value[:50]}...' (id: {memory_id[:8]}...)")
                    else:
                        # Memory not found for update, create it instead
                        memory_id = str(uuid.uuid4())
                        cursor.execute(
                            "INSERT INTO memories (id, type, key, value) VALUES (?, ?, ?, ?)",
                            (memory_id, bucket, key, value)
                        )
                        created_count += 1
                        logger.info(f"➕ Created {bucket} memory (update->create): '{key}' = '{value[:50]}...' (id: {memory_id[:8]}...)")
                else:
                    # Invalid action type
                    failed_count += 1
                    logger.error(f"❌ Invalid action type '{action_type}' for action {i+1}")
                
            except sqlite3.IntegrityError as integrity_error:
                failed_count += 1
                logger.error(f"❌ Database integrity error for action {i+1} ({action_type} {bucket}.{key}): {str(integrity_error)}")
            except sqlite3.OperationalError as op_error:
                failed_count += 1
                logger.error(f"❌ Database operational error for action {i+1} ({action_type} {bucket}.{key}): {str(op_error)}")
            except Exception as action_error:
                failed_count += 1
                logger.error(f"❌ Failed to apply memory action {i+1} ({action_type} {bucket}.{key}): {str(action_error)}")
                logger.error(f"❌ Action data: {action}")
        
        # Enhanced commit with error handling
        try:
            conn.commit()
            logger.info("✅ All memory actions committed to database")
        except Exception as commit_error:
            logger.error(f"❌ Failed to commit memory actions: {str(commit_error)}")
            conn.rollback()
            raise Exception(f"Database commit failed: {str(commit_error)}")
        
        # Enhanced summary logging
        process_time = round((time.time() - start_time) * 1000, 2)
        total_processed = created_count + updated_count + failed_count
        success_rate = round((created_count + updated_count) / total_processed * 100, 1) if total_processed > 0 else 0
        
        logger.info(f"✅ Memory action processing completed in {process_time}ms")
        logger.info(f"📊 Results: {created_count} created, {updated_count} updated, {failed_count} failed ({success_rate}% success rate)")
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} memory actions failed - check logs above for details")
        
    except sqlite3.Error as db_error:
        if conn:
            conn.rollback()
        logger.error(f"❌ Database error during memory action processing: {str(db_error)}")
        logger.error(f"❌ Database error type: {type(db_error).__name__}")
        raise Exception(f"Database error: {str(db_error)}")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Memory action processing failed: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        raise Exception(f"Memory action processing failed: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
                logger.info("🔒 Database connection closed")
            except Exception as close_error:
                logger.warning(f"⚠️ Error closing database connection: {str(close_error)}")




# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for product insights"""
    start_time = time.time()
    
    # Log request
    logger.info(f"🌐 {request.method} {request.url.path} - User request started")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = round((time.time() - start_time) * 1000, 2)
    logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} in {process_time}ms")
    
    return response

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://127.0.0.1:3000",  # Alternative localhost
        "http://localhost:3001",  # Alternative React port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)





# Custom exception handlers for proper error responses

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors (422 Unprocessable Entity).
    
    This handles cases where required fields are missing or invalid.
    """
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_details.append(f"{field}: {message}")
    
    detail = f"Validation error: {'; '.join(error_details)}"
    logger.warning(f"⚠️ Validation error on {request.method} {request.url.path}: {detail}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    Handle ValueError exceptions (400 Bad Request).
    
    This handles cases where data cannot be processed due to invalid values.
    """
    logger.warning(f"⚠️ Bad request on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"Bad request: {str(exc)}"}
    )


@app.exception_handler(json.JSONDecodeError)
async def json_decode_error_handler(request: Request, exc: json.JSONDecodeError):
    """
    Handle JSON decode errors (400 Bad Request).
    
    This handles cases where invalid JSON is sent.
    """
    logger.warning(f"⚠️ Invalid JSON on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid JSON format in request body"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle all other unexpected exceptions (500 Internal Server Error).
    
    This is a catch-all for any unhandled server errors.
    """
    logger.error(f"❌ Unexpected error on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


@app.get("/")
async def root():
    """Root endpoint for health check"""
    logger.info("💓 Health check requested")
    return {"message": "Chat Backend API is running"}


@app.get("/memories", response_model=MemoryResponse, status_code=status.HTTP_200_OK)
async def get_memories():
    """
    Get all memories organized by type.
    
    Returns:
        MemoryResponse: All memories organized by type (identity, principles, focus, signals)
        
    Raises:
        HTTPException: For any processing errors (500 Internal Server Error)
    """
    try:
        logger.info("📖 User requested all memories")
        memories = get_all_memories()
        return MemoryResponse(
            identity=memories["identity"],
            principles=memories["principles"],
            focus=memories["focus"],
            signals=memories["signals"]
        )
    except Exception as e:
        logger.error(f"❌ Memory retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving memories: {str(e)}"
        )


@app.get("/messages", response_model=MessagesResponse, status_code=status.HTTP_200_OK)
async def get_messages():
    """
    Get all chat messages in chronological order.
    
    Returns:
        MessagesResponse: All stored chat messages ordered by timestamp
        
    Raises:
        HTTPException: For any processing errors (500 Internal Server Error)
    """
    try:
        logger.info("💬 User requested all messages")
        messages = get_all_messages()
        return MessagesResponse(messages=messages)
    except Exception as e:
        logger.error(f"❌ Message retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving messages: {str(e)}"
        )


@app.put("/memories/{memory_type}/{memory_id}", response_model=MemoryItem, status_code=status.HTTP_200_OK)
async def update_memory(memory_type: str, memory_id: str, memory_item: MemoryItem):
    """
    Update an existing memory item.
    
    Args:
        memory_type: Type of memory (identity, principles, focus, signals)
        memory_id: ID of the memory item to update
        memory_item: Updated memory item data
        
    Returns:
        MemoryItem: The updated memory item (200 OK)
        
    Raises:
        HTTPException: For validation errors (400 Bad Request) or not found (404 Not Found)
    """
    try:
        logger.info(f"📝 User updating {memory_type} memory: '{memory_item.key}'")
        
        # Validate memory type
        valid_types = ["identity", "principles", "focus", "signals"]
        if memory_type not in valid_types:
            logger.warning(f"⚠️ Invalid memory type attempted: {memory_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid memory type: {memory_type}. Must be one of: identity, principles, focus, signals"
            )
        
        # Update the memory item in database
        success = update_memory_db(memory_type, memory_id, memory_item.key, memory_item.value)
        
        if not success:
            # Memory item not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory item with id '{memory_id}' not found in type '{memory_type}'"
            )
        
        # Return the updated memory item
        updated_item = MemoryItem(
            id=memory_id,  # Keep the original ID
            key=memory_item.key,
            value=memory_item.value
        )
        return updated_item
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Memory update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating memory: {str(e)}"
        )


@app.delete("/memories/{memory_type}/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_type: str, memory_id: str):
    """
    Delete a memory item.
    
    Args:
        memory_type: Type of memory (identity, principles, focus, signals)
        memory_id: ID of the memory item to delete
        
    Returns:
        None (204 No Content)
        
    Raises:
        HTTPException: For validation errors (400 Bad Request) or not found (404 Not Found)
    """
    try:
        logger.info(f"🗑️ User deleting {memory_type} memory (id: {memory_id[:8]}...)")
        
        # Validate memory type
        valid_types = ["identity", "principles", "focus", "signals"]
        if memory_type not in valid_types:
            logger.warning(f"⚠️ Invalid memory type for deletion: {memory_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid memory type: {memory_type}. Must be one of: identity, principles, focus, signals"
            )
        
        # Delete the memory item from database
        success = delete_memory_db(memory_type, memory_id)
        
        if not success:
            # Memory item not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory item with id '{memory_id}' not found in type '{memory_type}'"
            )
        
        # Return 204 No Content (implicit return)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Memory deletion failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting memory: {str(e)}"
        )


async def get_ai_response(message: str) -> str:
    """
    Get AI response using OpenAI API with user profile context.
    
    Uses a fixed system prompt and adds user profile context to the user message
    to avoid identity confusion while maintaining memory-informed responses.
    
    Args:
        message: User's input message
        
    Returns:
        str: AI-generated response with profile context
        
    Raises:
        Exception: For OpenAI API errors
    """
    start_time = time.time()
    try:
        # Load all memories for profile context
        memories = load_all_memories_for_chat()
        
        # Get fixed system prompt
        system_prompt = get_system_prompt()
        
        # Render user context from memories
        user_context = render_user_context(memories)
        
        # Add user context to user message, not system
        if user_context:
            user_message_with_context = f"{user_context}\n\n{message}"
        else:
            user_message_with_context = message
        
        # Use fixed system prompt and profile-enhanced user message
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_with_context}
        ]
        
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages
        )
        
        response_text = resp.choices[0].message.content
        api_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"🤖 Profile-aware AI response generated in {api_time}ms (length: {len(response_text)} chars)")
        return response_text
    except Exception as e:
        api_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ OpenAI API failed after {api_time}ms: {str(e)}")
        raise Exception(f"OpenAI API error: {str(e)}")


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that processes user messages and returns AI-generated responses.
    
    Args:
        request: ChatRequest containing the user's message
        
    Returns:
        ChatResponse: Response containing the AI's reply (200 OK)
        
    Raises:
        HTTPException: For any processing errors (500 Internal Server Error)
        RequestValidationError: For validation errors (422 Unprocessable Entity)
        ValueError: For bad request data (400 Bad Request)
    """
    start_time = time.time()
    message_preview = request.message[:50] + "..." if len(request.message) > 50 else request.message
    
    try:
        logger.info(f"💬 User message: '{message_preview}' (length: {len(request.message)})")
        
        # Validate that message is not just whitespace
        if not request.message or not request.message.strip():
            logger.warning("⚠️ Empty message rejected")
            raise ValueError("Message cannot be empty or contain only whitespace")
        
        # Get AI response
        response_text = await get_ai_response(request.message)
        
        # Save user message and bot response to database
        try:
            logger.info("💾 Saving messages to database")
            
            # Save user message
            user_save_success = save_message(request.message, "user")
            if not user_save_success:
                logger.warning("⚠️ Failed to save user message, but continuing chat")
            
            # Save bot response
            bot_save_success = save_message(response_text, "bot")
            if not bot_save_success:
                logger.warning("⚠️ Failed to save bot response, but continuing chat")
            
            if user_save_success and bot_save_success:
                logger.info("✅ Both messages saved successfully")
            elif user_save_success or bot_save_success:
                logger.info("⚠️ Partial message save success")
            else:
                logger.warning("⚠️ Failed to save both messages")
                
        except Exception as save_error:
            logger.error(f"❌ Message saving failed: {str(save_error)}")
            logger.error("❌ Chat will continue normally despite message saving failure")
        
        # Extract memories asynchronously after generating response with enhanced error handling
        memory_extraction_start = time.time()
        try:
            logger.info("🧠 Starting memory extraction process")
            
            # Load existing memory keys by bucket before extraction
            try:
                existing_memory_keys = get_existing_memory_keys()
                total_existing = sum(len(keys) for keys in existing_memory_keys.values())
                logger.info(f"📚 Loaded {total_existing} existing memory keys across all buckets")
            except Exception as keys_error:
                logger.error(f"❌ Failed to load existing memory keys: {str(keys_error)}")
                # Use empty keys as fallback to allow extraction to continue
                existing_memory_keys = {"identity": [], "principles": [], "focus": [], "signals": []}
            
            # Extract memories from the conversation
            try:
                memory_actions = await extract_memories(
                    user_message=request.message,
                    assistant_response=response_text,
                    existing_memories=existing_memory_keys
                )
                logger.info(f"🧠 Memory extraction returned {len(memory_actions)} actions")
            except Exception as extraction_error:
                logger.error(f"❌ Memory extraction failed: {str(extraction_error)}")
                logger.error(f"❌ Extraction error type: {type(extraction_error).__name__}")
                memory_actions = []
            
            # Apply memory actions to database
            if memory_actions:
                try:
                    apply_memory_actions(memory_actions)
                    logger.info("✅ Memory actions applied successfully")
                except Exception as apply_error:
                    logger.error(f"❌ Failed to apply memory actions: {str(apply_error)}")
                    logger.error(f"❌ Apply error type: {type(apply_error).__name__}")
            else:
                logger.info("ℹ️ No memory actions to apply")
            
            memory_extraction_time = round((time.time() - memory_extraction_start) * 1000, 2)
            logger.info(f"🧠 Memory extraction process completed in {memory_extraction_time}ms")
                
        except Exception as memory_error:
            # Enhanced error logging for memory extraction failures
            memory_extraction_time = round((time.time() - memory_extraction_start) * 1000, 2)
            logger.error(f"❌ Memory extraction process failed after {memory_extraction_time}ms: {str(memory_error)}")
            logger.error(f"❌ Memory error type: {type(memory_error).__name__}")
            logger.error(f"❌ Chat will continue normally despite memory extraction failure")
        
        total_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f"✅ Chat completed in {total_time}ms")
        
        return ChatResponse(response=response_text)
        
    except ValueError as e:
        # Re-raise ValueError to be handled by the custom exception handler
        raise e
    except Exception as e:
        total_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ Chat failed after {total_time}ms: {str(e)}")
        # Handle any unexpected errors during processing
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)