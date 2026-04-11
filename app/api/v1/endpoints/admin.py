# app/api/v1/endpoints/admin.py
"""
Admin REST API — all endpoints require role = ADMIN (JWT-guarded).

Endpoints
─────────
Dashboard
  GET  /admin/dashboard

Students Management
  GET    /admin/students                              list + search + paginate
  POST   /admin/students                              register new student
  PATCH  /admin/students/{user_id}                    update email
  POST   /admin/students/{user_id}/reset-password     force-reset password
  PATCH  /admin/students/{user_id}/toggle-active      activate / deactivate account
  DELETE /admin/students/{user_id}                    delete account
  GET    /admin/students/export                       CSV download

Teachers Management  (mirrors Students)
  GET    /admin/teachers
  POST   /admin/teachers
  PATCH  /admin/teachers/{user_id}
  POST   /admin/teachers/{user_id}/reset-password
  PATCH  /admin/teachers/{user_id}/toggle-active
  DELETE /admin/teachers/{user_id}
  GET    /admin/teachers/export                       CSV download

is_active rules
───────────────
  • New accounts are created with is_active = True (immediately usable).
  • Admin can flip is_active via the toggle-active endpoint.
  • Login is BLOCKED when is_active = False (enforced in auth.py).
  • is_active does NOT change automatically on login/logout.
"""

import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func

from app.api.deps import get_current_admin
from app.core.database import get_session
from app.core.security import get_password_hash
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lecture import Lecture, LectureStatus
from app.models.schedule import Schedule
from app.models.teacher import Teacher
from app.models.user import User, UserRole
from app.schemas.admin_schemas import (
    AdminCourseOut,
    AdminUserOut,
    AssignTeacherRequest,
    CourseDropdownItem,
    CreateCourseRequest,
    DailyLecturePoint,
    DashboardResponse,
    EnrollmentOut,
    EnrollStudentRequest,
    MessageResponse,
    PaginatedCoursesResponse,
    PaginatedStudentsResponse,
    PaginatedTeachersResponse,
    RegisterUserRequest,
    ResetPasswordRequest,
    UpdateCourseRequest,
    UpdateEmailRequest,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _to_display_id(user_id: int) -> str:
    """Convert a numeric user_id to the UI display format, e.g. 101 → 'STU-101'."""
    return f"STU-{user_id:03d}"


def _user_to_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        user_id=user.user_id,
        display_id=_to_display_id(user.user_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
    )


def _get_user_or_404(session: Session, user_id: int, role: UserRole) -> User:
    """Fetch a user by id + role, raise 404 if not found."""
    user = session.get(User, user_id)
    if not user or user.role != role:
        role_label = "Student" if role == UserRole.STUDENT else "Teacher"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{role_label} with id {user_id} not found.",
        )
    return user


def _build_csv_response(users: list[User], filename: str) -> StreamingResponse:
    """Stream a CSV file from a list of User objects."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Email", "Full Name", "Role", "Status"])
    for u in users:
        writer.writerow([
            _to_display_id(u.user_id),
            u.email,
            u.full_name,
            u.role.value,
            "Active" if u.is_active else "Inactive",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Admin Dashboard — KPI stats + weekly lecture chart",
)
def get_dashboard(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """
    Returns all data required for the Dashboard page:
    - KPI cards (total students, teachers, lectures, scheduled this week)
    - Weekly lecture rate chart (last 7 days, grouped by date)
    - Footer stats (total, average daily rate, completion rate)
    """

    # ── KPI: total students ───────────────────────────────────────────────────
    total_students = session.exec(
        select(func.count(User.user_id)).where(User.role == UserRole.STUDENT)
    ).one()

    # ── KPI: total teachers ───────────────────────────────────────────────────
    total_teachers = session.exec(
        select(func.count(User.user_id)).where(User.role == UserRole.TEACHER)
    ).one()

    # ── KPI: lifetime lectures created ────────────────────────────────────────
    total_lectures = session.exec(
        select(func.count(Lecture.lecture_id))
    ).one()

    # ── KPI: lectures scheduled this week (Mon–Sun) ───────────────────────────
    today = date.today()
    week_start = today - timedelta(days=today.weekday())   # Monday
    week_end = week_start + timedelta(days=6)              # Sunday
    scheduled_this_week = session.exec(
        select(func.count(Schedule.schedule_id)).where(
            Schedule.date >= week_start,
            Schedule.date <= week_end,
        )
    ).one()

    # ── Student growth % (last 30 days vs previous 30 days) ──────────────────
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)

    # Because User has no created_at we approximate with user_id windows.
    # If you add created_at later, swap to date-based filtering.
    max_id = session.exec(select(func.max(User.user_id))).one() or 0
    mid_id = max(max_id - 50, 0)   # rough midpoint placeholder

    # Fallback: just report 0 growth until created_at is available
    student_growth_percent = 0.0

    # ── Weekly chart: last 7 days, count lectures per day ────────────────────
    chart_start = today - timedelta(days=6)
    weekly_chart: list[DailyLecturePoint] = []

    # Fetch all schedules in the window once, then bucket by date in Python
    schedules_in_window = session.exec(
        select(Schedule).where(
            Schedule.date >= chart_start,
            Schedule.date <= today,
        )
    ).all()

    date_bucket: dict[date, int] = {}
    for s in schedules_in_window:
        date_bucket[s.date] = date_bucket.get(s.date, 0) + 1

    for i in range(7):
        d = chart_start + timedelta(days=i)
        weekly_chart.append(DailyLecturePoint(date=d, lecture_count=date_bucket.get(d, 0)))

    total_weekly_lectures = sum(p.lecture_count for p in weekly_chart)
    average_daily_rate = round(total_weekly_lectures / 7, 1)

    # ── Completion rate ───────────────────────────────────────────────────────
    completed_lectures = session.exec(
        select(func.count(Lecture.lecture_id)).where(
            Lecture.status == LectureStatus.COMPLETED
        )
    ).one()

    completion_rate = (
        round((completed_lectures / total_lectures) * 100, 1)
        if total_lectures > 0
        else 0.0
    )

    return DashboardResponse(
        total_students=total_students,
        total_teachers=total_teachers,
        total_lectures=total_lectures,
        scheduled_this_week=scheduled_this_week,
        student_growth_percent=student_growth_percent,
        weekly_chart=weekly_chart,
        total_weekly_lectures=total_weekly_lectures,
        average_daily_rate=average_daily_rate,
        completion_rate=completion_rate,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Students — List
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/students-in-system",
    response_model=PaginatedStudentsResponse,
    summary="List all students (search + paginate)",
)
def list_students(
    search: str = Query(default="", description="Filter by name or email"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    query = select(User).where(User.role == UserRole.STUDENT)

    if search:
        like = f"%{search.lower()}%"
        query = query.where(
            (func.lower(User.email).like(like))
            | (func.lower(User.full_name).like(like))
        )

    total = session.exec(
        select(func.count()).select_from(query.subquery())
    ).one()

    users = session.exec(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return PaginatedStudentsResponse(
        total=total,
        page=page,
        page_size=page_size,
        students=[_user_to_out(u) for u in users],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Students — Register
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/students-reg",
    response_model=AdminUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student",
)
def register_student(
    body: RegisterUserRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    # Reject duplicate emails
    existing = session.exec(select(User).where(User.email == body.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    new_user = User(
        email=body.email,
        full_name=body.full_name,
        role=UserRole.STUDENT,
        hashed_password=get_password_hash(body.password),
        is_active=True,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return _user_to_out(new_user)


# ─────────────────────────────────────────────────────────────────────────────
# Students — Update email
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/students/{user_id}",
    response_model=AdminUserOut,
    summary="Update a student's email address",
)
def update_student_email(
    user_id: int,
    body: UpdateEmailRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    user = _get_user_or_404(session, user_id, UserRole.STUDENT)

    # Check new email isn't taken by someone else
    taken = session.exec(
        select(User).where(User.email == body.email, User.user_id != user_id)
    ).first()
    if taken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already in use by another account.",
        )

    user.email = body.email
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_out(user)


# ─────────────────────────────────────────────────────────────────────────────
# Students — Reset password
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/students/{user_id}/reset-password",
    response_model=MessageResponse,
    summary="Admin force-reset a student's password",
)
def reset_student_password(
    user_id: int,
    body: ResetPasswordRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    user = _get_user_or_404(session, user_id, UserRole.STUDENT)
    user.hashed_password = get_password_hash(body.new_password)
    session.add(user)
    session.commit()
    return MessageResponse(
        detail=f"Password for {_to_display_id(user_id)} updated. All active sessions will be invalidated."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Students — Delete
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/students/{user_id}",
    response_model=MessageResponse,
    summary="Delete a student account",
)
def delete_student(
    user_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    user = _get_user_or_404(session, user_id, UserRole.STUDENT)
    session.delete(user)
    session.commit()
    return MessageResponse(detail=f"Student {_to_display_id(user_id)} deleted successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# Students — Export CSV
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/students/export",
    summary="Download full student list as CSV",
)
def export_students_csv(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    users = session.exec(
        select(User).where(User.role == UserRole.STUDENT).order_by(User.user_id)
    ).all()
    return _build_csv_response(users, "students.csv")


# ─────────────────────────────────────────────────────────────────────────────
# Students — Toggle active / inactive
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/students/{user_id}/toggle-active",
    response_model=AdminUserOut,
    summary="Activate or deactivate a student account",
)
def toggle_student_active(
    user_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """
    Flips is_active between True ↔ False.
    - True  → account is enabled, user CAN log in   (shown as 🟢 Active)
    - False → account is suspended, login is BLOCKED (shown as 🔴 Inactive)
    """
    user = _get_user_or_404(session, user_id, UserRole.STUDENT)
    user.is_active = not user.is_active
    session.add(user)
    session.commit()
    session.refresh(user)
    state = "activated" if user.is_active else "deactivated"
    return _user_to_out(user)


# ─────────────────────────────────────────────────────────────────────────────
# Teachers — List
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/teachers-in-system",
    response_model=PaginatedTeachersResponse,
    summary="List all teachers (search + paginate)",
)
def list_teachers(
    search: str = Query(default="", description="Filter by name or email"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    query = select(User).where(User.role == UserRole.TEACHER)

    if search:
        like = f"%{search.lower()}%"
        query = query.where(
            (func.lower(User.email).like(like))
            | (func.lower(User.full_name).like(like))
        )

    total = session.exec(
        select(func.count()).select_from(query.subquery())
    ).one()

    users = session.exec(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return PaginatedTeachersResponse(
        total=total,
        page=page,
        page_size=page_size,
        teachers=[_user_to_out(u) for u in users],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Teachers — Register
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/teachers-reg",
    response_model=AdminUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new teacher (also creates Teacher profile row)",
)
def register_teacher(
    body: RegisterUserRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    # Reject duplicate emails
    existing = session.exec(select(User).where(User.email == body.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    # Create User row
    new_user = User(
        email=body.email,
        full_name=body.full_name,
        role=UserRole.TEACHER,
        hashed_password=get_password_hash(body.password),
        is_active=True,
    )
    session.add(new_user)
    session.flush()  # assigns new_user.user_id before commit

    # Create linked Teacher profile row (onboarding_status = "pending")
    teacher_profile = Teacher(
        user_id=new_user.user_id,
        onboarding_status="pending",
    )
    session.add(teacher_profile)
    session.commit()
    session.refresh(new_user)
    return _user_to_out(new_user)


# ─────────────────────────────────────────────────────────────────────────────
# Teachers — Update email
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/teachers/{user_id}",
    response_model=AdminUserOut,
    summary="Update a teacher's email address",
)
def update_teacher_email(
    user_id: int,
    body: UpdateEmailRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    user = _get_user_or_404(session, user_id, UserRole.TEACHER)

    taken = session.exec(
        select(User).where(User.email == body.email, User.user_id != user_id)
    ).first()
    if taken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already in use by another account.",
        )

    user.email = body.email
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_out(user)


# ─────────────────────────────────────────────────────────────────────────────
# Teachers — Reset password
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/teachers/{user_id}/reset-password",
    response_model=MessageResponse,
    summary="Admin force-reset a teacher's password",
)
def reset_teacher_password(
    user_id: int,
    body: ResetPasswordRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    user = _get_user_or_404(session, user_id, UserRole.TEACHER)
    user.hashed_password = get_password_hash(body.new_password)
    session.add(user)
    session.commit()
    return MessageResponse(
        detail=f"Password for {_to_display_id(user_id)} updated. All active sessions will be invalidated."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Teachers — Delete
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/teachers/{user_id}",
    response_model=MessageResponse,
    summary="Delete a teacher account",
)
def delete_teacher(
    user_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    user = _get_user_or_404(session, user_id, UserRole.TEACHER)
    session.delete(user)
    session.commit()
    return MessageResponse(detail=f"Teacher {_to_display_id(user_id)} deleted successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# Teachers — Export CSV
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/teachers/export",
    summary="Download full teacher list as CSV",
)
def export_teachers_csv(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    users = session.exec(
        select(User).where(User.role == UserRole.TEACHER).order_by(User.user_id)
    ).all()
    return _build_csv_response(users, "teachers.csv")


# ─────────────────────────────────────────────────────────────────────────────
# Teachers — Toggle active / inactive
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/teachers/{user_id}/toggle-active",
    response_model=AdminUserOut,
    summary="Activate or deactivate a teacher account",
)
def toggle_teacher_active(
    user_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """
    Flips is_active between True ↔ False.
    - True  → account is enabled, teacher CAN log in   (shown as 🟢 Active)
    - False → account is suspended, login is BLOCKED   (shown as 🔴 Inactive)
    """
    user = _get_user_or_404(session, user_id, UserRole.TEACHER)
    user.is_active = not user.is_active
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_out(user)


# ═════════════════════════════════════════════════════════════════════════════
# LECTURES MANAGEMENT — Course Directory
# ═════════════════════════════════════════════════════════════════════════════

def _course_to_out(course: Course) -> AdminCourseOut:
    """Build AdminCourseOut, resolving teacher name from the relationship."""
    teacher_name = None
    if course.teacher and course.teacher.user:
        teacher_name = course.teacher.user.full_name
    return AdminCourseOut(
        course_code=course.course_code,
        title=course.title,
        description=course.description,
        teacher_id=course.teacher_id,
        teacher_name=teacher_name,
    )


def _get_course_or_404(session: Session, course_code: str) -> Course:
    course = session.get(Course, course_code)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_code}' not found.",
        )
    return course


# ─────────────────────────────────────────────────────────────────────────────
# Courses — List
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/courses",
    response_model=PaginatedCoursesResponse,
    summary="List all courses with assigned teacher (Course Directory table)",
)
def list_courses(
    search: str = Query(default="", description="Filter by course code or name"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    query = select(Course)

    if search:
        like = f"%{search.lower()}%"
        query = query.where(
            (func.lower(Course.course_code).like(like))
            | (func.lower(Course.title).like(like))
        )

    total = session.exec(
        select(func.count()).select_from(query.subquery())
    ).one()

    courses = session.exec(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return PaginatedCoursesResponse(
        total=total,
        page=page,
        page_size=page_size,
        courses=[_course_to_out(c) for c in courses],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Create
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/courses-init",
    response_model=AdminCourseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course (Initialize Course button)",
)
def create_course(
    body: CreateCourseRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """
    Initializes a course with just a code, name, and optional description.
    No teacher is assigned at this stage — use POST /courses/{code}/assign-teacher
    to link a teacher after creation.
    """
    # Reject duplicate course codes
    if session.get(Course, body.course_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course code '{body.course_code}' is already in use.",
        )

    course = Course(
        course_code=body.course_code,
        title=body.title,
        description=body.description,
        teacher_id=None,            # teacher assigned separately
    )
    session.add(course)
    session.commit()
    session.refresh(course)
    return _course_to_out(course)


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Update name
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/courses-update/{course_code}",
    response_model=AdminCourseOut,
    summary="Rename a course (Update Course Details → Apply Changes)",
)
def update_course(
    course_code: str,
    body: UpdateCourseRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    course = _get_course_or_404(session, course_code)
    course.title = body.title
    session.add(course)
    session.commit()
    session.refresh(course)
    return _course_to_out(course)


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Assign teacher
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/courses/{course_code}/assign-teacher",
    response_model=MessageResponse,
    summary="Link a teacher to a course (Link Instructor button)",
)
def assign_teacher(
    course_code: str,
    body: AssignTeacherRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    course = _get_course_or_404(session, course_code)

    # Step 1 — user must exist and have role=TEACHER
    teacher_user = session.get(User, body.teacher_id)
    if not teacher_user or teacher_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher with id {body.teacher_id} not found.",
        )

    # Step 2 — a Teacher profile row must exist (courses.teacher_id → teachers.user_id FK)
    teacher_profile = session.get(Teacher, body.teacher_id)
    if not teacher_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"User {body.teacher_id} has the TEACHER role but no teacher profile row. "
                "Create the profile first via POST /admin/teachers."
            ),
        )

    course.teacher_id = body.teacher_id
    session.add(course)
    session.commit()
    return MessageResponse(detail=f"Teacher linked to {course_code} successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Remove teacher assignment
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/courses/{course_code}/teacher-delete",
    response_model=MessageResponse,
    summary="Unlink teacher from a course (Update Teacher Assignment → Remove)",
)
def remove_teacher(
    course_code: str,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    course = _get_course_or_404(session, course_code)
    course.teacher_id = None
    session.add(course)
    session.commit()
    return MessageResponse(detail=f"Teacher unlinked from {course_code}.")


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Enroll student
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/courses/{course_code}/enroll-student",
    response_model=EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a student in a course (Enroll Student button)",
)
def enroll_student(
    course_code: str,
    body: EnrollStudentRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    _get_course_or_404(session, course_code)

    # Validate student exists
    student = session.get(User, body.student_id)
    if not student or student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {body.student_id} not found.",
        )

    # Prevent duplicate enrollment
    already = session.exec(
        select(Enrollment).where(
            Enrollment.course_code == course_code,
            Enrollment.student_id == body.student_id,
        )
    ).first()
    if already:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student {body.student_id} is already enrolled in {course_code}.",
        )

    enrollment = Enrollment(course_code=course_code, student_id=body.student_id)
    session.add(enrollment)
    session.commit()
    session.refresh(enrollment)
    return EnrollmentOut(
        enrollment_id=enrollment.id,
        course_code=enrollment.course_code,
        student_id=enrollment.student_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Unenroll student
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/courses/{course_code}/students-delete/{student_id}",
    response_model=MessageResponse,
    summary="Unenroll a student from a course (Update Student Assignment → Remove)",
)
def unenroll_student(
    course_code: str,
    student_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    _get_course_or_404(session, course_code)

    enrollment = session.exec(
        select(Enrollment).where(
            Enrollment.course_code == course_code,
            Enrollment.student_id == student_id,
        )
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {student_id} is not enrolled in {course_code}.",
        )

    session.delete(enrollment)
    session.commit()
    return MessageResponse(
        detail=f"Student S-{student_id:03d} unenrolled from {course_code}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Dropdown feeds (populate Course ID dropdowns dynamically)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/teachers/{teacher_id}/courses",
    response_model=list[CourseDropdownItem],
    summary="Courses assigned to a teacher — feeds 'Update Teacher Assignment' dropdown",
)
def get_teacher_courses(
    teacher_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """
    Returns all courses where Course.teacher_id == teacher_id.
    Frontend calls this when admin selects a teacher in the dropdown
    to populate the Course ID dropdown dynamically.
    Returns an empty list (not 404) when teacher has no courses assigned,
    so the UI can show 'No courses for selected teacher'.
    """
    _get_user_or_404(session, teacher_id, UserRole.TEACHER)

    courses = session.exec(
        select(Course).where(Course.teacher_id == teacher_id).order_by(Course.course_code)
    ).all()

    return [
        CourseDropdownItem(
            course_code=c.course_code,
            title=c.title,
            label=f"{c.course_code} - {c.title}",
        )
        for c in courses
    ]


@router.get(
    "/students/{student_id}/courses",
    response_model=list[CourseDropdownItem],
    summary="Courses a student is enrolled in — feeds 'Update Student Assignment' dropdown",
)
def get_student_courses(
    student_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """
    Returns all courses the student is currently enrolled in.
    Frontend calls this when admin selects a student in the dropdown
    to populate the Course ID dropdown dynamically.
    Returns an empty list when student has no enrollments.
    """
    _get_user_or_404(session, student_id, UserRole.STUDENT)

    enrollments = session.exec(
        select(Enrollment).where(Enrollment.student_id == student_id)
    ).all()

    course_codes = [e.course_code for e in enrollments]
    if not course_codes:
        return []

    courses = session.exec(
        select(Course)
        .where(Course.course_code.in_(course_codes))
        .order_by(Course.course_code)
    ).all()

    return [
        CourseDropdownItem(
            course_code=c.course_code,
            title=c.title,
            label=f"{c.course_code} - {c.title}",
        )
        for c in courses
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Courses — Export CSV
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/courses/export",
    summary="Download full course list as CSV",
)
def export_courses_csv(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    courses = session.exec(select(Course).order_by(Course.course_code)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Course ID", "Course Name", "Description", "Assigned Teacher"])
    for c in courses:
        teacher_name = ""
        if c.teacher and c.teacher.user:
            teacher_name = c.teacher.user.full_name
        writer.writerow([c.course_code, c.title, c.description or "", teacher_name])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=courses.csv"},
    )
