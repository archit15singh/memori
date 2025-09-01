"""
FastAPI Chat Backend

A simple FastAPI application with a chat endpoint.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from models import ChatRequest, ChatResponse, ErrorResponse, MemoryItem, MemoryResponse

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app instance with comprehensive metadata
app = FastAPI(
    title="Chat Backend API",
    description="A simple chat backend service with FastAPI that provides a /chat endpoint for processing messages",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Initialize OpenAI client with API key from environment
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# In-memory storage for memories with mock data
MEMORY_STORE = {
    "identity": [
        MemoryItem(id="id1", key="Role", value="Software Developer"),
        MemoryItem(id="id2", key="Experience", value="5 years in web development")
    ],
    "principles": [
        MemoryItem(id="p1", key="Quality", value="Write clean, maintainable code"),
        MemoryItem(id="p2", key="Learning", value="Continuously improve skills")
    ],
    "focus": [
        MemoryItem(id="f1", key="Current Project", value="Building chat application"),
        MemoryItem(id="f2", key="Goal", value="Complete memory integration")
    ],
    "signals": [
        MemoryItem(id="s1", key="Deadline", value="End of sprint"),
        MemoryItem(id="s2", key="Priority", value="High importance feature")
    ]
}

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
        return MemoryResponse(
            identity=MEMORY_STORE["identity"],
            principles=MEMORY_STORE["principles"],
            focus=MEMORY_STORE["focus"],
            signals=MEMORY_STORE["signals"]
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
        if memory_type not in MEMORY_STORE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid memory type: {memory_type}. Must be one of: identity, principles, focus, signals"
            )
        
        # Find the memory item to update
        memory_list = MEMORY_STORE[memory_type]
        for i, item in enumerate(memory_list):
            if item.id == memory_id:
                # Update the memory item
                updated_item = MemoryItem(
                    id=memory_id,  # Keep the original ID
                    key=memory_item.key,
                    value=memory_item.value
                )
                memory_list[i] = updated_item
                return updated_item
        
        # Memory item not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item with id '{memory_id}' not found in type '{memory_type}'"
        )
        
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
        if memory_type not in MEMORY_STORE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid memory type: {memory_type}. Must be one of: identity, principles, focus, signals"
            )
        
        # Find and remove the memory item
        memory_list = MEMORY_STORE[memory_type]
        for i, item in enumerate(memory_list):
            if item.id == memory_id:
                memory_list.pop(i)
                return
        
        # Memory item not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item with id '{memory_id}' not found in type '{memory_type}'"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting memory: {str(e)}"
        )


async def get_ai_response(message: str) -> str:
    """
    Get AI response using OpenAI API.
    
    Args:
        message: User's input message
        
    Returns:
        str: AI-generated response
        
    Raises:
        Exception: For OpenAI API errors
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": message}]
        )
        return resp.choices[0].message.content
    except Exception as e:
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
    try:
        # Validate that message is not just whitespace
        if not request.message or not request.message.strip():
            raise ValueError("Message cannot be empty or contain only whitespace")
        
        # Get AI response
        response_text = await get_ai_response(request.message)
        
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