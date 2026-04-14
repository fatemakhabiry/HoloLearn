from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, teachers, password_reset, courses, schedules, lecture, student, admin


api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
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
    prefix="/password_reset",
    tags=["Password_reset"]
)


api_router.include_router(
    courses.router,
    prefix="/courses",
    tags=["Courses"]
)


api_router.include_router(
    schedules.router,
    prefix="/schedules",
    tags=["Schedules"]
)

api_router.include_router(
    lecture.router,
    prefix="/lecture",
    tags=["Lecture"]
)

api_router.include_router(
    student.router,
    prefix="/student",
    tags=["student"]
)