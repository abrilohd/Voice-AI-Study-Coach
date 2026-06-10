"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.routers.auth import router as auth_router

# Create main API router
api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth_router)

# Import and include additional sub-routers here as they are created
# Example:
# from app.api.v1.routers.users import router as users_router
# api_router.include_router(users_router, prefix="/users", tags=["users"])
