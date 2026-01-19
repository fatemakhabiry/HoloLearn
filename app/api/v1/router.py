from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, teachers, password_reset

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    teachers.router,
    prefix="/teachers",
    tags=["Teachers"]
)

api_router.include_router(
    password_reset.router,
    prefix="/password-reset",  # Uses same /auth prefix
    tags=["Password Reset"]
)