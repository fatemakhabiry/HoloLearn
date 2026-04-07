from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import List, Optional

from app.core.database import get_session
from app.api.deps import get_current_user, get_current_teacher, get_current_student
from app.models.user import User
from app.models.course import Course, CoursePublic


router = APIRouter()


# =============== Create Course ===============

class CourseCreate(BaseModel):
    course_code: str
    title: str


@router.post("/", response_model=CoursePublic, status_code=status.HTTP_201_CREATED)
def create_course(
    body: CourseCreate,
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session),
):
    """Create a new course. Only teachers can create courses."""
    existing = session.get(Course, body.course_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course code '{body.course_code}' already exists",
        )
    course = Course(
        course_code=body.course_code,
        title=body.title,
        teacher_id=current_user.user_id,
    )
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


# =============== List Courses ===============

@router.get("/", response_model=List[str])
def get_all_courses(
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    courses = session.exec(
        select(Course.course_code).where(
            Course.teacher_id == current_user.user_id,
        ).order_by(Course.course_code)
    ).all()

    return courses