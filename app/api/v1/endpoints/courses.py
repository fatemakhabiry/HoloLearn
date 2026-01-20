from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional

from app.core.database import get_session
from app.api.deps import get_current_user, get_current_teacher, get_current_student
from app.models.user import User
from app.models.course import Course, CoursePublic


router = APIRouter()

# =============== Public Endpoints ===============

@router.get("/", response_model=List[str])
def get_all_courses(
    current_user: User = Depends(get_current_teacher),  # ✅ Any authenticated user
    session: Session = Depends(get_session)
):
    courses = session.exec(
        select(Course.course_code).where(
            Course.teacher_id == current_user.user_id,
        ).order_by(Course.course_code)
    ).all()

    return courses