"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.chat import router as chat_router
from app.api.v1.routers.chat_rag import router as chat_rag_router
from app.api.v1.routers.documents import router as documents_router

# Create main API router
api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth_router)

# Include chat routes
api_router.include_router(chat_router)

# Include RAG-augmented chat routes
api_router.include_router(chat_rag_router)

# Include document routes
api_router.include_router(documents_router)
