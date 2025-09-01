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
from models import ChatRequest, ChatResponse, ErrorResponse

# Create FastAPI app instance with comprehensive metadata
app = FastAPI(
    title="Chat Backend API",
    description="A simple chat backend service with FastAPI that provides a /chat endpoint for processing messages",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

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


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that processes user messages and returns responses.
    
    Args:
        request: ChatRequest containing the user's message
        
    Returns:
        ChatResponse: Response containing the system's reply (200 OK)
        
    Raises:
        HTTPException: For any processing errors (500 Internal Server Error)
        RequestValidationError: For validation errors (422 Unprocessable Entity)
        ValueError: For bad request data (400 Bad Request)
    """
    try:
        # Validate that message is not just whitespace
        if not request.message or not request.message.strip():
            raise ValueError("Message cannot be empty or contain only whitespace")
        
        # Basic chat logic - simple pattern matching and responses
        user_message = request.message.lower().strip()
        
        # Generate response based on input patterns
        if "hello" in user_message or "hi" in user_message:
            response_text = "Hello! How can I help you today?"
        elif "how are you" in user_message:
            response_text = "I'm doing well, thank you for asking! How are you?"
        elif "bye" in user_message or "goodbye" in user_message:
            response_text = "Goodbye! Have a great day!"
        elif "help" in user_message:
            response_text = "I'm here to help! You can ask me questions or just chat with me."
        elif "thank" in user_message:
            response_text = "You're welcome! Is there anything else I can help you with?"
        elif "?" in user_message:
            response_text = f"That's an interesting question about '{request.message}'. Let me think about that..."
        else:
            # Default response for unmatched patterns
            response_text = f"I received your message: '{request.message}'. Thanks for chatting with me!"
        
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