#!/usr/bin/env python3
"""
Main entry point for FastAPI application
This file allows running the app with: fastapi dev main.py
"""

from app.main import app

# This is required for fastapi dev to work
app = app



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 