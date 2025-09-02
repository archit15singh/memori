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
from dotenv import load_dotenv
from openai import OpenAI
from models import ChatRequest, ChatResponse, ErrorResponse, MemoryItem, MemoryResponse

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application startup and shutdown.
    """
    # Startup
    init_database()
    yield
    # Shutdown (if needed)


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
    Initialize SQLite database and create memories and conversation_history tables if they don't exist.
    """
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
    
    # Create conversation_history table for storing chat messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def get_all_memories():
    """
    Get all memories from the database organized by type.
    
    Returns:
        dict: Dictionary with memory types as keys and lists of MemoryItem objects as values
    """
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
    
    return memories


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
    
    return rows_affected > 0


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
    
    return rows_affected > 0


def store_message(message_type: str, content: str):
    """
    Store a message in the conversation history database.
    
    Args:
        message_type: Type of message ('user' or 'assistant')
        content: The message content to store
        
    Returns:
        bool: True if storage was successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO conversation_history (message_type, content) VALUES (?, ?)",
            (message_type, content)
        )
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        # Log the error but don't raise it to ensure graceful degradation
        print(f"Error storing message: {str(e)}")
        try:
            conn.close()
        except:
            pass
        return False


def get_recent_conversation_history():
    """
    Retrieve the last 10 message pairs (20 messages total) from conversation history.
    
    Returns:
        List[dict]: List of message dictionaries with keys: message_type, content, timestamp
                   Ordered by timestamp (oldest first for proper conversation flow)
                   Limited to 20 messages total (10 pairs)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Use a subquery to get the last 20 messages, then order them oldest first
        cursor.execute("""
            SELECT message_type, content, timestamp 
            FROM (
                SELECT message_type, content, timestamp 
                FROM conversation_history 
                ORDER BY timestamp DESC 
                LIMIT 20
            ) 
            ORDER BY timestamp ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        messages = []
        for row in rows:
            message_type, content, timestamp = row
            messages.append({
                "message_type": message_type,
                "content": content,
                "timestamp": timestamp
            })
        
        return messages
        
    except Exception as e:
        # Log the error but don't raise it to ensure graceful degradation
        print(f"Error retrieving conversation history: {str(e)}")
        try:
            conn.close()
        except:
            pass
        return []  # Return empty list on error


def build_messages_for_openai(user_message: str, history: list) -> list:
    """
    Build messages array for OpenAI API by combining system message, conversation history, and current user message.
    
    Args:
        user_message: The current user message to process
        history: List of conversation history dictionaries with keys: message_type, content, timestamp
        
    Returns:
        List[dict]: Messages array formatted for OpenAI API with role/content structure
    """
    # Start with the system message
    messages = [
        {"role": "system", "content": "You are a reflective journaling AI bot. Reply to user messages in very, very short responses that encourage reflection and self-awareness."}
    ]
    
    # Add conversation history, converting internal format to OpenAI format
    for message in history:
        # Convert message_type to OpenAI role format
        if message["message_type"] == "user":
            role = "user"
        elif message["message_type"] == "assistant":
            role = "assistant"
        else:
            # Skip unknown message types
            continue
            
        messages.append({
            "role": role,
            "content": message["content"]
        })
    
    # Add the current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages

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
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


@app.get("/")
async def root():
    """Root endpoint for health check"""
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
        memories = get_all_memories()
        return MemoryResponse(
            identity=memories["identity"],
            principles=memories["principles"],
            focus=memories["focus"],
            signals=memories["signals"]
        )
    except Exception as e:
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
        # Validate memory type
        valid_types = ["identity", "principles", "focus", "signals"]
        if memory_type not in valid_types:
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
        # Validate memory type
        valid_types = ["identity", "principles", "focus", "signals"]
        if memory_type not in valid_types:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting memory: {str(e)}"
        )


async def get_ai_response(message: str, history: list = None) -> str:
    """
    Get AI response using OpenAI API with conversation history.
    
    Args:
        message: User's input message
        history: List of conversation history dictionaries (optional)
        
    Returns:
        str: AI-generated response
        
    Raises:
        Exception: For OpenAI API errors
    """
    try:
        # Use the messages builder function to construct the full messages array
        if history is None:
            history = []
        
        messages = build_messages_for_openai(message, history)
        
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages
        )
        return resp.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that processes user messages and returns AI-generated responses with conversation history.
    
    Args:
        request: ChatRequest containing the user's message
        
    Returns:
        ChatResponse: Response containing the AI's reply (200 OK)
        
    Raises:
        HTTPException: For any processing errors (500 Internal Server Error)
        RequestValidationError: For validation errors (422 Unprocessable Entity)
        ValueError: For bad request data (400 Bad Request)
    """
    try:
        # Validate that message is not just whitespace
        if not request.message or not request.message.strip():
            raise ValueError("Message cannot be empty or contain only whitespace")
        
        # Store the incoming user message
        store_message("user", request.message)
        
        # Retrieve conversation history before calling OpenAI API
        history = get_recent_conversation_history()
        
        # Get AI response with conversation history
        response_text = await get_ai_response(request.message, history)
        
        # Store the AI response after receiving it from OpenAI
        store_message("assistant", response_text)
        
        return ChatResponse(response=response_text)
        
    except ValueError as e:
        # Re-raise ValueError to be handled by the custom exception handler
        raise e
    except Exception as e:
        # Handle any unexpected errors during processing
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)