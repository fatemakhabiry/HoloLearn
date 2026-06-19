# from fastapi import APIRouter
# from app.api.v1.endpoints import (
#     auth,
#     users,
#     teachers,
#     password_reset,
#     courses,
#     schedules,
#     lecture,
#     student,
#     admin,
#     sessions,
#     internal,
#     qa,
#     research

# )

# api_router = APIRouter()

# api_router.include_router(auth.router,           prefix="/auth",           tags=["Authentication"])
# api_router.include_router(admin.router,          prefix="/admin",          tags=["Admin"])
# api_router.include_router(users.router,          prefix="/users",          tags=["Users"])
# api_router.include_router(teachers.router,       prefix="/teachers",       tags=["Teachers"])
# api_router.include_router(password_reset.router, prefix="/password_reset", tags=["Password Reset"])
# api_router.include_router(courses.router,        prefix="/courses",        tags=["Courses"])
# api_router.include_router(schedules.router,      prefix="/schedules",      tags=["Schedules"])
# api_router.include_router(lecture.router,        prefix="/lecture",        tags=["Lecture"])
# api_router.include_router(student.router,        prefix="/student",        tags=["Student"])
# api_router.include_router(sessions.router,       prefix="/session",        tags=["Sessions"])
# api_router.include_router(internal.router,       prefix="/internal",       tags=["Internal"])
# api_router.include_router(qa.router,             prefix="/qa",             tags=["Q&A"])
# api_router.include_router(
#     research.router,
#     prefix="/research",
#     tags=["research"],
# )

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    teachers,
    password_reset,
    courses,
    schedules,
    lecture,
    student,
    admin,
    sessions,
    internal,
    qa,
    research,
    identity,

)

api_router = APIRouter()

api_router.include_router(auth.router,           prefix="/auth",           tags=["Authentication"])
api_router.include_router(admin.router,          prefix="/admin",          tags=["Admin"])
api_router.include_router(users.router,          prefix="/users",          tags=["Users"])
api_router.include_router(teachers.router,       prefix="/teachers",       tags=["Teachers"])
api_router.include_router(password_reset.router, prefix="/password_reset", tags=["Password Reset"])
api_router.include_router(courses.router,        prefix="/courses",        tags=["Courses"])
api_router.include_router(schedules.router,      prefix="/schedules",      tags=["Schedules"])
api_router.include_router(lecture.router,        prefix="/lecture",        tags=["Lecture"])
api_router.include_router(student.router,        prefix="/student",        tags=["Student"])
api_router.include_router(sessions.router,       prefix="/session",        tags=["Sessions"])
api_router.include_router(internal.router,       prefix="/internal",       tags=["Internal"])
api_router.include_router(qa.router,             prefix="/qa",             tags=["Q&A"])
api_router.include_router(
    research.router,
    prefix="/research",
    tags=["research"],
)

# No prefix here on purpose — identity.py's route is already declared as
# "/lecture/{lecture_id}/verify-identity", so this lands under the same
# /lecture/{id}/... path family as lecture.router without double-prefixing.
api_router.include_router(identity.router,       tags=["Identity Verification"])