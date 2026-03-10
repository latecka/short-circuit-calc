"""Short-Circuit Calculator API - FastAPI application."""
from fastapi import FastAPI

app = FastAPI(
    title="Short-Circuit Calculator",
    description="IEC 60909-0 compliant short-circuit calculation API",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
