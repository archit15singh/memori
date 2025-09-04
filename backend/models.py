"""
Pydantic models for the Chat Backend API

This module contains the request and response models used by the FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


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
    memory_enabled: bool = Field(
        default=True,
        description="Whether to use memory functionality for this request",
        example=True
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "message": "Hello, how are you?",
                "memory_enabled": True
            }
        }


class MemoryChange(BaseModel):
    """
    Model for memory change notifications.
    
    Represents a change that occurred to a memory during chat processing.
    """
    action: str = Field(
        ...,
        description="Type of change: 'created', 'updated', or 'deleted'",
        example="created"
    )
    type: str = Field(
        ...,
        description="Memory category: 'identity', 'principles', 'focus', or 'signals'",
        example="identity"
    )
    id: str = Field(
        ...,
        description="Unique identifier for the memory item",
        example="mem-123e4567-e89b-12d3-a456-426614174000"
    )
    key: str = Field(
        ...,
        description="Label or title for the memory item",
        example="Current Project"
    )
    value: Optional[str] = Field(
        default=None,
        description="Memory content (None for deleted memories)",
        example="chat app development"
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "action": "created",
                "type": "identity",
                "id": "mem-123e4567-e89b-12d3-a456-426614174000",
                "key": "Current Project",
                "value": "chat app development"
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
    memory_changes: Optional[List[MemoryChange]] = Field(
        default=None,
        description="List of memory changes that occurred during chat processing",
        example=[]
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "response": "Hello! I'm doing well, thank you for asking.",
                "memory_changes": [
                    {
                        "action": "created",
                        "type": "identity",
                        "id": "mem-123e4567-e89b-12d3-a456-426614174000",
                        "key": "Current Project",
                        "value": "chat app development"
                    }
                ]
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


class MessageItem(BaseModel):
    """
    Model for individual chat messages.
    
    Represents a single chat message with id, content, sender, and timestamp.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the message",
        example="msg-123e4567-e89b-12d3-a456-426614174000"
    )
    content: str = Field(
        ...,
        description="The text content of the message",
        example="Hello, how are you?"
    )
    sender: str = Field(
        ...,
        description="Who sent the message: 'user' or 'bot'",
        example="user"
    )
    timestamp: int = Field(
        ...,
        description="Unix timestamp when the message was created",
        example=1640995200000
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "id": "msg-123e4567-e89b-12d3-a456-426614174000",
                "content": "Hello, how are you?",
                "sender": "user",
                "timestamp": 1640995200000
            }
        }


class MessagesResponse(BaseModel):
    """
    Response model for messages endpoint.
    
    Represents all stored chat messages in chronological order.
    """
    messages: List[MessageItem] = Field(
        default_factory=list,
        description="List of chat messages in chronological order"
    )

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "id": "msg-123e4567-e89b-12d3-a456-426614174000",
                        "content": "Hello, how are you?",
                        "sender": "user",
                        "timestamp": 1640995200000
                    },
                    {
                        "id": "msg-987fcdeb-51a2-43d7-8f9e-123456789abc",
                        "content": "Hello! I'm doing well, thank you for asking.",
                        "sender": "bot",
                        "timestamp": 1640995201000
                    }
                ]
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