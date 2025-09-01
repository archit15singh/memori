#!/usr/bin/env python3
"""
Development server runner with hot reload enabled.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./"],  # Watch current directory
        log_level="info"
    )