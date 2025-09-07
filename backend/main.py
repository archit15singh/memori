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
from models import ChatRequest, ChatResponse, ErrorResponse, MemoryItem, MemoryResponse, MessageItem, MessagesResponse, MemoryChange, ClearResponse

# Load environment variables from .env file
logger_setup_start = time.time()
load_dotenv()
logger_setup_env_time = round((time.time() - logger_setup_start) * 1000, 2)

# Configure logging for product insights
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Log environment setup completion
logger_setup_total_time = round((time.time() - logger_setup_start) * 1000, 2)
logger.info(f"🔧 Environment setup completed in {logger_setup_total_time}ms (env: {logger_setup_env_time}ms)")

# Log environment variables status (without exposing sensitive data)
openai_key_status = "✅ SET" if os.getenv("OPENAI_API_KEY") else "❌ MISSING"
logger.info(f"🔑 Environment variables status: OPENAI_API_KEY={openai_key_status}")

# Log Python and system information
import sys
import platform
logger.info(f"🐍 Python version: {sys.version}")
logger.info(f"💻 Platform: {platform.system()} {platform.release()}")
logger.info(f"📁 Working directory: {os.getcwd()}")
logger.info(f"📄 Database path: {os.path.abspath('chat_app.db')}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application startup and shutdown.
    """
    startup_start = time.time()
    
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 CHAT BACKEND STARTUP SEQUENCE INITIATED")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        logger.info("📊 Step 1/3: Initializing database...")
        init_database()
        
        # Verify OpenAI client
        logger.info("📊 Step 2/3: Verifying OpenAI client...")
        if not client:
            raise Exception("OpenAI client not initialized")
        logger.info("✅ OpenAI client verified")
        
        # Final startup checks
        logger.info("📊 Step 3/3: Performing final startup checks...")
        startup_time = round((time.time() - startup_start) * 1000, 2)
        
        logger.info("=" * 80)
        logger.info("✅ CHAT BACKEND STARTUP COMPLETED SUCCESSFULLY")
        logger.info(f"⏱️ Total startup time: {startup_time}ms")
        logger.info("🌟 Backend is ready to serve requests")
        logger.info("=" * 80)
        
        yield
        
    except Exception as startup_error:
        startup_time = round((time.time() - startup_start) * 1000, 2)
        logger.error("=" * 80)
        logger.error("❌ CHAT BACKEND STARTUP FAILED")
        logger.error(f"⏱️ Failed after: {startup_time}ms")
        logger.error(f"💥 Error: {str(startup_error)}")
        logger.error("=" * 80)
        raise
    
    # Shutdown
    shutdown_start = time.time()
    logger.info("=" * 80)
    logger.info("🛑 CHAT BACKEND SHUTDOWN SEQUENCE INITIATED")
    logger.info("=" * 80)
    
    try:
        # Perform cleanup operations
        logger.info("🧹 Performing cleanup operations...")
        
        # Log final statistics if possible
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories")
            final_memory_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM messages")
            final_message_count = cursor.fetchone()[0]
            conn.close()
            
            logger.info(f"📊 Final statistics:")
            logger.info(f"   - Memories: {final_memory_count}")
            logger.info(f"   - Messages: {final_message_count}")
        except Exception as stats_error:
            logger.warning(f"⚠️ Could not retrieve final statistics: {str(stats_error)}")
        
        shutdown_time = round((time.time() - shutdown_start) * 1000, 2)
        logger.info("=" * 80)
        logger.info("✅ CHAT BACKEND SHUTDOWN COMPLETED")
        logger.info(f"⏱️ Shutdown time: {shutdown_time}ms")
        logger.info("👋 Goodbye!")
        logger.info("=" * 80)
        
    except Exception as shutdown_error:
        shutdown_time = round((time.time() - shutdown_start) * 1000, 2)
        logger.error(f"❌ Shutdown error after {shutdown_time}ms: {str(shutdown_error)}")


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

# Model constants for single source of truth
CHAT_MODEL = "gpt-5"
EXTRACTOR_MODEL = "gpt-5-mini"

# Initialize OpenAI client with API key from environment
openai_init_start = time.time()
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY environment variable is not set")
        raise ValueError("OPENAI_API_KEY environment variable must be set")
    
    client = OpenAI(api_key=api_key)
    openai_init_time = round((time.time() - openai_init_start) * 1000, 2)
    logger.info(f"🤖 OpenAI client initialized successfully in {openai_init_time}ms")
    logger.info(f"🔑 API key length: {len(api_key)} characters (masked: {api_key[:8]}...{api_key[-4:]})")
    logger.info(f"🎯 Model configuration: Chat={CHAT_MODEL}, Memory Extraction={EXTRACTOR_MODEL}")
except Exception as e:
    openai_init_time = round((time.time() - openai_init_start) * 1000, 2)
    logger.error(f"❌ OpenAI client initialization failed after {openai_init_time}ms: {str(e)}")
    raise



# Database file path
DB_PATH = "chat_app.db"





def init_database():
    """
    Initialize SQLite database and create memories and messages tables if they don't exist.
    """
    db_init_start = time.time()
    logger.info(f"💾 Starting database initialization at {DB_PATH}")
    
    try:
        # Log database file status before connection
        db_exists = os.path.exists(DB_PATH)
        if db_exists:
            db_size = os.path.getsize(DB_PATH)
            logger.info(f"📄 Database file exists: {DB_PATH} ({db_size} bytes)")
        else:
            logger.info(f"📄 Database file will be created: {DB_PATH}")
        
        conn_start = time.time()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        conn_time = round((time.time() - conn_start) * 1000, 2)
        logger.info(f"🔗 Database connection established in {conn_time}ms")
        
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
        
        # Add unique index to prevent duplicate memories with same type and key
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_type_key
            ON memories(type, key)
        """)
        
        # Check existing memory count for product insights
        cursor.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]
        
        # Check existing message count for product insights
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        commit_start = time.time()
        conn.commit()
        commit_time = round((time.time() - commit_start) * 1000, 2)
        
        conn.close()
        
        db_init_total_time = round((time.time() - db_init_start) * 1000, 2)
        logger.info(f"💾 Database initialization completed in {db_init_total_time}ms (commit: {commit_time}ms)")
        logger.info(f"📊 Database contents: {memory_count} memories, {message_count} messages")
        
        # Log final database file size
        final_db_size = os.path.getsize(DB_PATH)
        logger.info(f"📄 Final database size: {final_db_size} bytes")
        
    except Exception as e:
        db_init_time = round((time.time() - db_init_start) * 1000, 2)
        logger.error(f"❌ Database initialization failed after {db_init_time}ms: {str(e)}")
        logger.error(f"❌ Database path: {DB_PATH}")
        logger.error(f"❌ Error type: {type(e).__name__}")
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
    Get the hardened system prompt for the reflective journaling bot.
    
    Returns a hardened system prompt that handles user profile context blocks
    correctly and enforces strict identity boundaries to prevent overreach.
    
    Returns:
        str: Hardened system prompt with GOAL, CONTEXT BLOCKS, USAGE OF USER CONTEXT, STYLE, and SAFETY sections
    """
    prompt = """GOAL:
You are a reflective journaling companion. Respond naturally and conversationally, like a thoughtful friend who remembers what matters to you.

CONTEXT BLOCKS:
If you see USER IDENTITY/PRINCIPLES/FOCUS/SIGNALS blocks in your context, treat these as user profile context, NOT your identity:
- These blocks describe the USER, not you
- Use this context to understand them better and respond more personally
- When USER FOCUS exists, connect your responses to their current priorities
- When no profile context exists, respond based on what they share

CONVERSATIONAL STYLE:
- Keep responses under 30 words total
- Be warm and natural, not robotic
- You can ask questions, make observations, or offer encouragement as feels right
- Don't force a question if a simple acknowledgment or insight fits better
- Focus on being genuinely helpful rather than following a formula

TONE:
- Be concise but human
- Use second person ("you/your") when referring to the user
- Avoid therapy speak and generic responses
- Sound like someone who actually cares and pays attention

SAFETY:
- NEVER use "I" to describe the user or claim their identity
- NEVER impersonate the user or speak as if you are them
- NEVER make assumptions about user identity from technical mentions alone
- Treat all USER context blocks as external profile information, not your own characteristics"""
    
    logger.info(f"🔧 Built hardened system prompt ({len(prompt)} chars)")
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

STRICT RULES: 
1) EXTRACT ONLY FROM THE USER'S WORDS IN THIS TURN. Ignore the assistant content completely for all buckets. 
2) IDENTITY requires explicit self-identification ("I am…", "I work as…"). Never infer from tech mentions. 
3) Only UPDATE an existing key if the user clearly replaces it in THIS TURN. 
4) Max 3 actions. Keys must be lower_snake_case. Values concise.

OUTPUT:
Return ONLY a JSON object with a single field "actions" that is an array. No prose, no backticks. Example: {"actions":[{"action":"create","bucket":"focus","key":"current_goal","value":"..."}]}

Format:
{
  "actions": [
    {"action": "create", "bucket": "identity", "key": "name", "value": "Alex"},
    {"action": "update", "bucket": "focus", "key": "current_project", "value": "chat app"}
  ]
}

EXTRACTION EXAMPLES:
✅ "Wrapped up a late-night Postgres migration… need to plan better" → 
   focus.current_project = "database migration", principles.deployment_practices = "plan changes before production"
✅ "I'm working on the frontend redesign" → focus.current_project = "frontend redesign"
✅ "I learned to always test in staging first" → principles.testing_approach = "always test in staging first"

NEGATIVE EXAMPLES:
❌ DON'T create identity from: "You mentioned Kubernetes" → identity.role = "DevOps engineer"
✅ DO create signals from: "You mentioned Kubernetes" → signals.tech_mentions = "Kubernetes"
❌ DON'T infer identity from assistant: "As a backend developer..." → identity.role = "backend developer"  
✅ DO wait for user claim: "I'm a backend developer" → identity.role = "backend developer"
❌ DON'T update without clear replacement: User says "working on the app" when current_project = "database migration"
✅ DO update with clear replacement: User says "switching to the frontend work" → focus.current_project = "frontend work" """

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

ONLY UPDATE A KEY IF THE USER CLEARLY REPLACES IT IN THIS TURN.

Extract memories from this conversation:"""

        # Call OpenAI API with enhanced error handling
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info("🚀 MEMORY EXTRACTION OPENAI API CALL")
        logger.info(f"📤 MEMORY EXTRACTION API REQUEST:")
        logger.info(f"   Model: {EXTRACTOR_MODEL}")
        logger.info(f"   Messages Count: {len(messages)}")
        for i, msg in enumerate(messages):
            logger.info(f"   Message {i+1}:")
            logger.info(f"     Role: {msg['role']}")
            logger.info(f"     Content: '{msg['content']}'")
            logger.info(f"     Content Length: {len(msg['content'])} characters")
        
        try:
            logger.info("🌐 Calling OpenAI API for memory extraction...")
            response = client.chat.completions.create(
                model=EXTRACTOR_MODEL,
                messages=messages,
                response_format={"type": "json_object"},  # forces a single JSON object
                seed=42
            )
            
            logger.info("📥 MEMORY EXTRACTION API RESPONSE RECEIVED")
            logger.info(f"🔍 MEMORY EXTRACTION API RESPONSE DATA:")
            logger.info(f"   Response Object Type: {type(response)}")
            logger.info(f"   Choices Count: {len(response.choices)}")
            logger.info(f"   Model Used: {response.model}")
            logger.info(f"   Usage: {response.usage}")
            
            # Verify we got the expected model
            if not response.model.startswith(EXTRACTOR_MODEL):
                logger.warning(f"⚠️ Expected model {EXTRACTOR_MODEL}, got {response.model}")
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"📝 MEMORY EXTRACTION RAW RESPONSE:")
            logger.info(f"   Content: '{response_text}'")
            logger.info(f"   Length: {len(response_text)} characters")
            logger.info(f"   Message Role: {response.choices[0].message.role}")
            logger.info(f"   Finish Reason: {response.choices[0].finish_reason}")
            
        except Exception as api_error:
            api_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"❌ OpenAI API call failed after {api_time}ms: {str(api_error)}")
            logger.error(f"❌ API Error Type: {type(api_error).__name__}")
            # Return empty list on API failure to prevent chat disruption
            return []
        
        # Parse structured JSON response with enhanced handling
        memory_actions = []
        try:
            if response_text:
                parsed = json.loads(response_text or "{}")
                if isinstance(parsed, dict) and "actions" in parsed:
                    memory_actions = parsed.get("actions", [])[:3]  # limit to 3 actions
                elif isinstance(parsed, list):
                    memory_actions = parsed[:3]  # handle direct array response
                else:
                    memory_actions = []
                logger.info(f"✅ Successfully parsed JSON response with {len(memory_actions)} potential actions")
            else:
                logger.info("ℹ️ Empty response from OpenAI, no memories to extract")
                memory_actions = []
        except json.JSONDecodeError as json_error:
            logger.warning(f"⚠️ Memory extraction returned invalid JSON: {json_error}")
            logger.warning(f"⚠️ Raw response was: {response_text[:200]}...")
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


def _normalize_key(key: str) -> str:
    """
    Normalize memory keys to prevent duplicates with different formatting.
    
    Converts keys to lowercase and replaces spaces with underscores to ensure
    consistent key formatting (e.g., "Current Goal" -> "current_goal").
    
    Args:
        key: Raw key string from memory extraction
        
    Returns:
        str: Normalized key in lowercase with underscores
    """
    return "_".join(key.strip().lower().split())


def apply_memory_actions(memory_actions: List[Dict]) -> List[Dict]:
    """
    Apply extracted memory actions to the database and return successful changes.
    
    Processes a list of memory actions by either creating new memories with generated UUIDs
    or updating existing memories by finding their IDs. Returns only the changes that were
    successfully committed to the database.
    
    Args:
        memory_actions: List of memory actions from extractor
                       Format: [{"action": "create|update", "bucket": "identity", "key": "name", "value": "Alex"}]
    
    Returns:
        List[Dict]: List of successful memory changes in MemoryChange format
                   Format: [{"action": "created|updated", "type": "identity", "id": "uuid", "key": "name", "value": "Alex"}]
    """
    if not memory_actions:
        logger.info("🧠 No memory actions to apply")
        return []
    
    start_time = time.time()
    logger.info(f"🧠 Starting to apply {len(memory_actions)} memory actions")
    
    conn = None
    cursor = None
    
    created_count = 0
    updated_count = 0
    failed_count = 0
    successful_changes = []
    
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
            raw_key = action.get("key")
            value = action.get("value")
            
            # Normalize key before processing to prevent duplicates
            key = _normalize_key(raw_key) if raw_key else ""
            
            try:
                logger.info(f"🔄 Processing action {i+1}/{len(memory_actions)}: {action_type} {bucket}.{key}")
                
                if action_type == "create":
                    
                    # Check if memory with this type and key already exists (upsert logic)
                    cursor.execute("SELECT id FROM memories WHERE type=? AND key=? LIMIT 1", (bucket, key))
                    row = cursor.fetchone()
                    
                    if row:
                        # Memory exists, update it instead of creating duplicate
                        memory_id = row[0]
                        cursor.execute("UPDATE memories SET value=? WHERE id=?", (value, memory_id))
                        updated_count += 1
                        logger.info(f"✏️ Updated existing {bucket} memory: '{key}' = '{value[:50]}...' (id: {memory_id[:8]}...)")
                        
                        # Add successful change to return list
                        successful_changes.append({
                            "action": "updated",
                            "type": bucket,
                            "id": memory_id,
                            "key": key,
                            "value": value
                        })
                    else:
                        # Memory doesn't exist, create new one
                        memory_id = str(uuid.uuid4())
                        cursor.execute(
                            "INSERT INTO memories (id, type, key, value) VALUES (?, ?, ?, ?)",
                            (memory_id, bucket, key, value)
                        )
                        created_count += 1
                        logger.info(f"➕ Created {bucket} memory: '{key}' = '{value[:50]}...' (id: {memory_id[:8]}...)")
                        
                        # Add successful change to return list
                        successful_changes.append({
                            "action": "created",
                            "type": bucket,
                            "id": memory_id,
                            "key": key,
                            "value": value
                        })
                    
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
                        
                        # Add successful change to return list
                        successful_changes.append({
                            "action": "updated",
                            "type": bucket,
                            "id": memory_id,
                            "key": key,
                            "value": value
                        })
                    else:
                        # Memory not found for update, create it instead
                        memory_id = str(uuid.uuid4())
                        cursor.execute(
                            "INSERT INTO memories (id, type, key, value) VALUES (?, ?, ?, ?)",
                            (memory_id, bucket, key, value)
                        )
                        created_count += 1
                        logger.info(f"➕ Created {bucket} memory (update->create): '{key}' = '{value[:50]}...' (id: {memory_id[:8]}...)")
                        
                        # Add successful change to return list (created, not updated)
                        successful_changes.append({
                            "action": "created",
                            "type": bucket,
                            "id": memory_id,
                            "key": key,
                            "value": value
                        })
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
        logger.info(f"🔄 Returning {len(successful_changes)} successful memory changes")
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} memory actions failed - check logs above for details")
        
        return successful_changes
        
    except sqlite3.Error as db_error:
        if conn:
            conn.rollback()
        logger.error(f"❌ Database error during memory action processing: {str(db_error)}")
        logger.error(f"❌ Database error type: {type(db_error).__name__}")
        # Return empty list instead of raising exception to prevent chat disruption
        return []
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Memory action processing failed: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        # Return empty list instead of raising exception to prevent chat disruption
        return []
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
    
    # Generate unique request ID for tracking
    request_id = str(uuid.uuid4())[:8]
    
    # Log detailed request information
    logger.info(f"🌐 [{request_id}] {request.method} {request.url.path} - Request started")
    logger.info(f"📋 [{request_id}] Request details:")
    logger.info(f"   - URL: {request.url}")
    logger.info(f"   - Headers: {dict(request.headers)}")
    logger.info(f"   - Query params: {dict(request.query_params)}")
    logger.info(f"   - Client: {request.client.host if request.client else 'unknown'}")
    logger.info(f"   - User-Agent: {request.headers.get('user-agent', 'unknown')}")
    
    # Process request
    response = await call_next(request)
    
    # Log detailed response information
    process_time = round((time.time() - start_time) * 1000, 2)
    logger.info(f"📤 [{request_id}] {request.method} {request.url.path} - {response.status_code} completed in {process_time}ms")
    logger.info(f"📋 [{request_id}] Response details:")
    logger.info(f"   - Status: {response.status_code}")
    logger.info(f"   - Headers: {dict(response.headers)}")
    logger.info(f"   - Media type: {response.headers.get('content-type', 'unknown')}")
    
    # Log performance metrics
    if process_time > 1000:  # Slow request (>1s)
        logger.warning(f"🐌 [{request_id}] Slow request detected: {process_time}ms")
    elif process_time > 500:  # Medium request (>500ms)
        logger.info(f"⏱️ [{request_id}] Medium response time: {process_time}ms")
    else:
        logger.info(f"⚡ [{request_id}] Fast response: {process_time}ms")
    
    return response

# Configure CORS for frontend integration
cors_setup_start = time.time()
allowed_origins = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",  # Alternative localhost
    "http://localhost:3001",  # Alternative React port
]

logger.info("🌐 Configuring CORS middleware:")
logger.info(f"   - Allowed origins: {allowed_origins}")
logger.info(f"   - Allow credentials: True")
logger.info(f"   - Allowed methods: GET, POST, PUT, DELETE, OPTIONS")
logger.info(f"   - Allowed headers: *")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

cors_setup_time = round((time.time() - cors_setup_start) * 1000, 2)
logger.info(f"✅ CORS middleware configured in {cors_setup_time}ms")





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
    health_start = time.time()
    logger.info("💓 Health check requested")
    
    # Perform basic system health checks
    try:
        # Check database connectivity
        db_check_start = time.time()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        db_check_time = round((time.time() - db_check_start) * 1000, 2)
        
        # Check OpenAI client status
        openai_status = "✅ Ready" if client else "❌ Not initialized"
        
        health_time = round((time.time() - health_start) * 1000, 2)
        
        logger.info(f"💓 Health check completed in {health_time}ms:")
        logger.info(f"   - Database: ✅ Connected ({table_count} tables, {db_check_time}ms)")
        logger.info(f"   - OpenAI: {openai_status}")
        logger.info(f"   - Memory: ✅ Available")
        
        return {
            "message": "Chat Backend API is running",
            "status": "healthy",
            "checks": {
                "database": "connected",
                "openai": "ready" if client else "not_ready",
                "response_time_ms": health_time
            }
        }
    except Exception as e:
        health_time = round((time.time() - health_start) * 1000, 2)
        logger.error(f"❌ Health check failed after {health_time}ms: {str(e)}")
        return {
            "message": "Chat Backend API has issues",
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": health_time
        }


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


@app.delete("/clear", response_model=ClearResponse, status_code=status.HTTP_200_OK)
async def clear_all_data():
    """
    Clear all memories and messages from the database.
    
    This endpoint removes all stored memories and chat messages, providing a clean slate.
    The operation is performed within a transaction to ensure data consistency.
    
    Returns:
        ClearResponse: Success status and message
        
    Raises:
        HTTPException: For database errors (500 Internal Server Error)
    """
    start_time = time.time()
    conn = None
    
    try:
        logger.info("🧹 Starting clear all data operation")
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Clear memories table
        cursor.execute("DELETE FROM memories")
        memories_deleted = cursor.rowcount
        
        # Clear messages table  
        cursor.execute("DELETE FROM messages")
        messages_deleted = cursor.rowcount
        
        # Commit transaction
        conn.commit()
        
        # Log success metrics
        clear_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f"✅ Successfully cleared all data in {clear_time}ms")
        logger.info(f"   - Deleted {memories_deleted} memories")
        logger.info(f"   - Deleted {messages_deleted} messages")
        
        return ClearResponse(
            success=True,
            message="All data cleared successfully"
        )
        
    except sqlite3.Error as db_error:
        # Rollback transaction on database error
        if conn:
            try:
                conn.rollback()
                logger.warning("🔄 Transaction rolled back due to database error")
            except Exception as rollback_error:
                logger.error(f"❌ Failed to rollback transaction: {str(rollback_error)}")
        
        clear_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ Database error during clear operation after {clear_time}ms: {str(db_error)}")
        
        # Provide more specific error messages based on database error type
        error_message = "Database error during clear operation"
        if "database is locked" in str(db_error).lower():
            error_message = "Database is currently busy. Please try again in a moment."
        elif "no such table" in str(db_error).lower():
            error_message = "Database structure error. Please contact support."
        elif "disk" in str(db_error).lower() or "space" in str(db_error).lower():
            error_message = "Insufficient disk space. Please free up space and try again."
        else:
            error_message = f"Database error: {str(db_error)}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )
    except Exception as e:
        # Rollback transaction on any other error
        if conn:
            try:
                conn.rollback()
                logger.warning("🔄 Transaction rolled back due to unexpected error")
            except Exception as rollback_error:
                logger.error(f"❌ Failed to rollback transaction: {str(rollback_error)}")
        
        clear_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ Clear operation failed after {clear_time}ms: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        
        # Provide user-friendly error message
        error_message = "An unexpected error occurred while clearing data"
        if "permission" in str(e).lower():
            error_message = "Permission denied. Please check file permissions and try again."
        elif "connection" in str(e).lower():
            error_message = "Database connection error. Please try again."
        else:
            error_message = f"Error clearing data: {str(e)}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )
    finally:
        # Always close database connection
        if conn:
            try:
                conn.close()
            except Exception as close_error:
                logger.warning(f"⚠️ Error closing database connection: {str(close_error)}")


async def get_ai_response(message: str, memory_enabled: bool = True) -> str:
    """
    Get AI response using OpenAI API with optional user profile context.
    
    Uses a fixed system prompt and optionally adds user profile context to the user message
    to avoid identity confusion while maintaining memory-informed responses.
    
    Args:
        message: User's input message
        memory_enabled: Whether to use memory functionality for context
        
    Returns:
        str: AI-generated response with optional profile context
        
    Raises:
        Exception: For OpenAI API errors
    """
    start_time = time.time()
    try:
        logger.info(f"🧠 MEMORY ENABLED: {memory_enabled}")
        
        if memory_enabled:
            logger.info("🧠 LOADING MEMORIES FOR AI CONTEXT")
            # Load all memories for profile context
            memories = load_all_memories_for_chat()
            
            logger.info(f"📚 LOADED MEMORIES DATA:")
            for memory_type, memory_list in memories.items():
                logger.info(f"   - {memory_type}: {len(memory_list)} items")
                for i, memory in enumerate(memory_list):
                    logger.info(f"     [{i+1}] {memory.key}: {memory.value}")
            
            logger.info("👤 RENDERING USER CONTEXT FROM MEMORIES")
            # Render user context from memories
            user_context = render_user_context(memories)
            logger.info(f"📋 USER CONTEXT:")
            logger.info(f"   Content: '{user_context}'")
            logger.info(f"   Length: {len(user_context)} characters")
            
            # Add user context to user message, not system
            if user_context:
                user_message_with_context = f"{user_context}\n\n{message}"
                logger.info("✅ User context added to message")
            else:
                user_message_with_context = message
                logger.info("ℹ️ No user context to add")
        else:
            logger.info("🚫 MEMORY DISABLED - Skipping memory loading and context rendering")
            user_message_with_context = message
        
        logger.info("📝 GENERATING SYSTEM PROMPT")
        # Get fixed system prompt
        system_prompt = get_system_prompt()
        logger.info(f"🔧 SYSTEM PROMPT:")
        logger.info(f"   Content: '{system_prompt}'")
        logger.info(f"   Length: {len(system_prompt)} characters")
        
        logger.info(f"💬 FINAL USER MESSAGE WITH CONTEXT:")
        logger.info(f"   Content: '{user_message_with_context}'")
        logger.info(f"   Length: {len(user_message_with_context)} characters")
        
        # Use fixed system prompt and profile-enhanced user message
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_with_context}
        ]
        
        logger.info("🚀 PREPARING OPENAI API CALL")
        logger.info(f"📤 OPENAI API REQUEST DATA:")
        logger.info(f"   Model: {CHAT_MODEL}")
        logger.info(f"   Messages Count: {len(messages)}")
        for i, msg in enumerate(messages):
            logger.info(f"   Message {i+1}:")
            logger.info(f"     Role: {msg['role']}")
            logger.info(f"     Content: '{msg['content']}'")
            logger.info(f"     Content Length: {len(msg['content'])} characters")
        
        logger.info("🌐 CALLING OPENAI API...")
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages
        )
        
        logger.info("📥 OPENAI API RESPONSE RECEIVED")
        logger.info(f"🔍 OPENAI API RESPONSE DATA:")
        logger.info(f"   Response Object Type: {type(resp)}")
        logger.info(f"   Choices Count: {len(resp.choices)}")
        logger.info(f"   Model Used: {resp.model}")
        logger.info(f"   Usage: {resp.usage}")
        
        # Verify we got the expected model
        if not resp.model.startswith(CHAT_MODEL):
            logger.warning(f"⚠️ Expected model {CHAT_MODEL}, got {resp.model}")
        
        response_text = resp.choices[0].message.content
        logger.info(f"📝 EXTRACTED RESPONSE TEXT:")
        logger.info(f"   Content: '{response_text}'")
        logger.info(f"   Length: {len(response_text)} characters")
        logger.info(f"   Message Role: {resp.choices[0].message.role}")
        logger.info(f"   Finish Reason: {resp.choices[0].finish_reason}")
        
        api_time = round((time.time() - start_time) * 1000, 2)
        
        if memory_enabled:
            logger.info(f"✅ Profile-aware AI response generated in {api_time}ms")
        else:
            logger.info(f"✅ Memory-disabled AI response generated in {api_time}ms")
        return response_text
    except Exception as e:
        api_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"❌ OpenAI API failed after {api_time}ms: {str(e)}")
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Details: {str(e)}")
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
        logger.info("=" * 80)
        logger.info("🚀 CHAT ENDPOINT STARTED")
        logger.info("=" * 80)
        logger.info(f"📥 INCOMING REQUEST DATA:")
        logger.info(f"   - Message: '{request.message}'")
        logger.info(f"   - Message Length: {len(request.message)} characters")
        logger.info(f"   - Message Preview: '{message_preview}'")
        logger.info(f"   - Memory Enabled: {request.memory_enabled}")
        logger.info(f"   - Request Type: {type(request)}")
        logger.info(f"   - Timestamp: {time.time()}")
        
        # Validate that message is not just whitespace
        if not request.message or not request.message.strip():
            logger.warning("⚠️ Empty message rejected")
            raise ValueError("Message cannot be empty or contain only whitespace")
        
        logger.info("✅ Message validation passed")
        
        # Get AI response with detailed logging
        logger.info("🤖 STARTING AI RESPONSE GENERATION")
        response_text = await get_ai_response(request.message, request.memory_enabled)
        
        # Post-process response to replace em dashes with comma space
        response_text = response_text.replace("—", ", ")
        
        # Save user message and bot response to database
        try:
            logger.info("=" * 60)
            logger.info("💾 STARTING MESSAGE SAVING PROCESS")
            logger.info("=" * 60)
            
            logger.info(f"💬 SAVING USER MESSAGE:")
            logger.info(f"   Content: '{request.message}'")
            logger.info(f"   Sender: 'user'")
            logger.info(f"   Length: {len(request.message)} characters")
            
            # Save user message
            user_save_success = save_message(request.message, "user")
            if not user_save_success:
                logger.warning("⚠️ Failed to save user message, but continuing chat")
            else:
                logger.info("✅ User message saved successfully")
            
            logger.info(f"🤖 SAVING BOT RESPONSE:")
            logger.info(f"   Content: '{response_text}'")
            logger.info(f"   Sender: 'bot'")
            logger.info(f"   Length: {len(response_text)} characters")
            
            # Save bot response
            bot_save_success = save_message(response_text, "bot")
            if not bot_save_success:
                logger.warning("⚠️ Failed to save bot response, but continuing chat")
            else:
                logger.info("✅ Bot response saved successfully")
            
            logger.info(f"📊 MESSAGE SAVING SUMMARY:")
            if user_save_success and bot_save_success:
                logger.info("✅ Both messages saved successfully")
            elif user_save_success or bot_save_success:
                logger.info("⚠️ Partial message save success")
            else:
                logger.warning("⚠️ Failed to save both messages")
            logger.info("=" * 60)
                
        except Exception as save_error:
            logger.error(f"❌ Message saving failed: {str(save_error)}")
            logger.error(f"❌ Save Error Type: {type(save_error).__name__}")
            logger.error("❌ Chat will continue normally despite message saving failure")
        
        # Extract memories asynchronously after generating response with enhanced error handling
        memory_extraction_start = time.time()
        memory_changes = []  # Initialize memory changes list
        
        if request.memory_enabled:
            try:
                logger.info("=" * 60)
                logger.info("🧠 STARTING MEMORY EXTRACTION PROCESS")
                logger.info("=" * 60)
                
                # Load existing memory keys by bucket before extraction
                try:
                    logger.info("📚 Loading existing memory keys from database...")
                    existing_memory_keys = get_existing_memory_keys()
                    total_existing = sum(len(keys) for keys in existing_memory_keys.values())
                    logger.info(f"📚 EXISTING MEMORY KEYS LOADED:")
                    logger.info(f"   Total Keys: {total_existing}")
                    for bucket, keys in existing_memory_keys.items():
                        logger.info(f"   {bucket}: {len(keys)} keys - {keys}")
                except Exception as keys_error:
                    logger.error(f"❌ Failed to load existing memory keys: {str(keys_error)}")
                    # Use empty keys as fallback to allow extraction to continue
                    existing_memory_keys = {"identity": [], "principles": [], "focus": [], "signals": []}
                
                # Extract memories from the conversation
                try:
                    logger.info("🔍 CALLING MEMORY EXTRACTION WITH:")
                    logger.info(f"   User Message: '{request.message}'")
                    logger.info(f"   Assistant Response: '{response_text}'")
                    logger.info(f"   Existing Memory Keys: {existing_memory_keys}")
                    
                    memory_actions = await extract_memories(
                        user_message=request.message,
                        assistant_response=response_text,
                        existing_memories=existing_memory_keys
                    )
                    
                    logger.info(f"🧠 MEMORY EXTRACTION RESULTS:")
                    logger.info(f"   Actions Returned: {len(memory_actions)}")
                    for i, action in enumerate(memory_actions):
                        logger.info(f"   Action {i+1}: {action}")
                        
                except Exception as extraction_error:
                    logger.error(f"❌ Memory extraction failed: {str(extraction_error)}")
                    logger.error(f"❌ Extraction error type: {type(extraction_error).__name__}")
                    memory_actions = []
                
                # Apply memory actions to database and capture successful changes
                if memory_actions:
                    try:
                        logger.info(f"💾 APPLYING {len(memory_actions)} MEMORY ACTIONS TO DATABASE")
                        memory_changes = apply_memory_actions(memory_actions)
                        logger.info(f"✅ Memory actions applied successfully - {len(memory_changes)} changes returned")
                        for i, change in enumerate(memory_changes):
                            logger.info(f"   Change {i+1}: {change['action']} {change['type']}.{change['key']}")
                    except Exception as apply_error:
                        logger.error(f"❌ Failed to apply memory actions: {str(apply_error)}")
                        logger.error(f"❌ Apply error type: {type(apply_error).__name__}")
                        memory_changes = []  # Reset to empty list on error
                else:
                    logger.info("ℹ️ No memory actions to apply")
                
                memory_extraction_time = round((time.time() - memory_extraction_start) * 1000, 2)
                logger.info(f"✅ Memory extraction process completed in {memory_extraction_time}ms")
                logger.info("=" * 60)
                        
            except Exception as memory_error:
                # Enhanced error logging for memory extraction failures
                memory_extraction_time = round((time.time() - memory_extraction_start) * 1000, 2)
                logger.error(f"❌ Memory extraction process failed after {memory_extraction_time}ms: {str(memory_error)}")
                logger.error(f"❌ Memory error type: {type(memory_error).__name__}")
                logger.error(f"❌ Chat will continue normally despite memory extraction failure")
                memory_changes = []  # Reset to empty list on error
        else:
            logger.info("🚫 MEMORY DISABLED - Skipping memory extraction process")
            logger.info("=" * 60)
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info("=" * 80)
        logger.info("✅ CHAT ENDPOINT COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"📤 FINAL RESPONSE DATA:")
        logger.info(f"   - Response: '{response_text}'")
        logger.info(f"   - Response Length: {len(response_text)} characters")
        logger.info(f"   - Memory Changes: {len(memory_changes)} changes")
        logger.info(f"   - Total Processing Time: {total_time}ms")
        logger.info(f"   - Response Type: {type(ChatResponse(response=response_text, memory_changes=memory_changes if memory_changes else None))}")
        logger.info("=" * 80)
        
        # Include memory changes in response if any occurred
        return ChatResponse(
            response=response_text,
            memory_changes=memory_changes if memory_changes else None
        )
        
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
    
    # Log direct execution details
    logger.info("=" * 80)
    logger.info("🎯 DIRECT EXECUTION MODE")
    logger.info("=" * 80)
    logger.info("🚀 Starting uvicorn server with configuration:")
    logger.info("   - Host: 0.0.0.0 (all interfaces)")
    logger.info("   - Port: 8000")
    logger.info("   - Reload: True (development mode)")
    logger.info("   - App: main:app")
    logger.info("=" * 80)
    
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user (Ctrl+C)")
    except Exception as server_error:
        logger.error(f"❌ Server failed to start: {str(server_error)}")
        raise