"""FastAPI application entry point."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database connection verification on startup
    - Logging of application lifecycle events
    """
    # Startup
    logger.info("application_startup", app_name=settings.app_name, version=settings.app_version)

    # Verify database connection
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("database_connection_verified")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("application_shutdown")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Response:
    """
    Add unique request ID to each request.

    Generates a UUID4 for each request and adds it to response headers.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# Include API v1 router
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Dictionary with status, version, and primary LLM configuration.
    """
    return {
        "status": "ok",
        "version": settings.app_version,
        "primary_llm": settings.primary_llm,
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Args:
        request: The request that caused the exception.
        exc: The exception that was raised.

    Returns:
        JSONResponse with 500 status and generic error message.
    """
    logger.error(
        "unhandled_exception",
        error=str(exc),
        request_id=getattr(request.state, "request_id", None),
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
