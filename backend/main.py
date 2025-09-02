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
from dotenv import load_dotenv
from openai import OpenAI
from models import ChatRequest, ChatResponse, ErrorResponse, MemoryItem, MemoryResponse

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
    Initialize SQLite database and create memories table if it doesn't exist.
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
        
        # Check existing memory count for product insights
        cursor.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        logger.info(f"💾 Database ready - {memory_count} memories loaded")
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


def build_memory_aware_prompt(memory_context: str, user_message: str) -> str:
    """
    Build memory-aware system prompt that includes memory context and user message.
    
    Creates an enhanced system prompt that incorporates all stored memories
    to provide context for the LLM response generation.
    
    Args:
        memory_context (str): Formatted memory context from format_memories_for_prompt()
        user_message (str): The user's input message
    
    Returns:
        str: Complete system prompt with memory context and user message
    """
    # Memory-aware system prompt template
    if memory_context.strip():
        # Include memories if available
        prompt = f"""You are a reflective journaling AI bot. Here is what you know about yourself:

{memory_context}

Reply to user messages in short, reflective responses that naturally reference your memories when relevant.

User: {user_message}"""
    else:
        # Fallback to basic prompt if no memories available
        prompt = f"""You are a reflective journaling AI bot. Reply to user messages in very, very short responses that encourage reflection and self-awareness.

User: {user_message}"""
    
    # Log prompt construction metrics
    prompt_length = len(prompt)
    has_memories = bool(memory_context.strip())
    logger.info(f"🔧 Built {'memory-aware' if has_memories else 'basic'} prompt ({prompt_length} chars)")
    
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
    Get AI response using OpenAI API with memory-enhanced context.
    
    Loads all stored memories and includes them in the system prompt to provide
    context for generating responses that naturally reference relevant memories.
    
    Args:
        message: User's input message
        
    Returns:
        str: AI-generated response with memory context
        
    Raises:
        Exception: For OpenAI API errors
    """
    start_time = time.time()
    try:
        # Load all memories for chat context
        memories = load_all_memories_for_chat()
        
        # Format memories for prompt context
        memory_context = format_memories_for_prompt(memories)
        
        # Build memory-aware system prompt
        enhanced_prompt = build_memory_aware_prompt(memory_context, message)
        
        # Use enhanced prompt in OpenAI API call
        messages = [
            {"role": "system", "content": enhanced_prompt}
        ]
        
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages
        )
        
        response_text = resp.choices[0].message.content
        api_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"🤖 Memory-aware AI response generated in {api_time}ms (length: {len(response_text)} chars)")
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
    uvicorn.run(app, host="0.0.0.0", port=8000)