"""API v1 router aggregator."""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import and include sub-routers here as they are created
# Example:
# from app.api.v1.routers.users import router as users_router
# api_router.include_router(users_router, prefix="/users", tags=["users"])
