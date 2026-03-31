# Routes module initialization
from fastapi import APIRouter

# Create main router that will be included in server.py
router = APIRouter()

# Import all route modules
from . import auth, users, notifications, presence, reports

# Include all routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(presence.router, prefix="/presence", tags=["Presence"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
