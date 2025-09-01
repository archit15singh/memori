"""
Pydantic models for the Chat Backend API

This module contains the request and response models used by the FastAPI endpoints.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.
    
    Represents the incoming chat message from the client.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's chat message",
        example="Hello, how are you?"
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "message": "Hello, how are you?"
            }
        }


class ChatResponse(BaseModel):
    """
    Response model for chat endpoint.
    
    Represents the response sent back to the client.
    """
    response: str = Field(
        ...,
        description="System response to the user's message",
        example="Hello! I'm doing well, thank you for asking."
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "response": "Hello! I'm doing well, thank you for asking."
            }
        }


class ErrorResponse(BaseModel):
    """
    Error response model for API errors.
    
    Represents error messages returned by the API.
    """
    detail: str = Field(
        ...,
        description="Error message describing what went wrong",
        example="Validation error: message field is required"
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "detail": "Validation error: message field is required"
            }
        }