"""
Pydantic models for the Chat Backend API

This module contains the request and response models used by the FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import List


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


class MemoryItem(BaseModel):
    """
    Model for individual memory items.
    
    Represents a single memory entry with id, key, and value.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the memory item",
        example="unique-id-123"
    )
    key: str = Field(
        ...,
        description="Label or title for the memory item",
        example="Core Value"
    )
    value: str = Field(
        ...,
        description="Description or content of the memory item",
        example="Always prioritize user experience"
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "id": "unique-id-123",
                "key": "Core Value",
                "value": "Always prioritize user experience"
            }
        }


class MemoryResponse(BaseModel):
    """
    Response model for memories endpoint.
    
    Represents all memories organized by type.
    """
    identity: List[MemoryItem] = Field(
        default_factory=list,
        description="Identity-related memories"
    )
    principles: List[MemoryItem] = Field(
        default_factory=list,
        description="Principle-related memories"
    )
    focus: List[MemoryItem] = Field(
        default_factory=list,
        description="Focus-related memories"
    )
    signals: List[MemoryItem] = Field(
        default_factory=list,
        description="Signal-related memories"
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "identity": [
                    {"id": "id1", "key": "Role", "value": "Software Developer"}
                ],
                "principles": [
                    {"id": "p1", "key": "Quality", "value": "Write clean code"}
                ],
                "focus": [],
                "signals": []
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