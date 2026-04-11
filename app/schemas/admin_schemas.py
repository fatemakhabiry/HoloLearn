# app/schemas/admin_schemas.py
"""
Pydantic schemas for all Admin endpoints.
Covers: Dashboard, Students Management, Teachers Management.
"""

from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class DailyLecturePoint(BaseModel):
    """Single data point on the Weekly Lecture Rate chart."""
    date: date
    lecture_count: int


class DashboardResponse(BaseModel):
    """
    Response for GET /admin/dashboard.
    Feeds every KPI card and the weekly chart on the Dashboard page.
    """
    # KPI cards
    total_students: int
    total_teachers: int
    total_lectures: int
    scheduled_this_week: int
    student_growth_percent: float       # e.g. 12.0 → "+12% this month"

    # Weekly Lecture Rate chart (last 7 days)
    weekly_chart: List[DailyLecturePoint]

    # Chart footer stats
    total_weekly_lectures: int
    average_daily_rate: float           # lectures / 7 days
    completion_rate: float              # completed lectures / total * 100


# ─────────────────────────────────────────────────────────────────────────────
# Shared User output (used for both Students and Teachers)
# ─────────────────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    """
    A single user row as displayed in the admin table.
    display_id is computed as 'STU-<zero-padded user_id>'.
    """
    user_id: int
    display_id: str         # e.g. "STU-101"
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class PaginatedStudentsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    students: List[AdminUserOut]


class PaginatedTeachersResponse(BaseModel):
    total: int
    page: int
    page_size: int
    teachers: List[AdminUserOut]


# ─────────────────────────────────────────────────────────────────────────────
# Register new user (student or teacher)
# ─────────────────────────────────────────────────────────────────────────────

class RegisterUserRequest(BaseModel):
    """
    Body for POST /admin/students  and  POST /admin/teachers.
    Maps to the 'Register New Student / Teacher' form in the UI.
    """
    full_name: str
    email: EmailStr
    password: str


# ─────────────────────────────────────────────────────────────────────────────
# Update email
# ─────────────────────────────────────────────────────────────────────────────

class UpdateEmailRequest(BaseModel):
    """
    Body for PATCH /admin/students/{id}  and  PATCH /admin/teachers/{id}.
    Maps to the 'Update Student / Teacher Details' panel.
    """
    email: EmailStr


# ─────────────────────────────────────────────────────────────────────────────
# Reset password
# ─────────────────────────────────────────────────────────────────────────────

class ResetPasswordRequest(BaseModel):
    """
    Body for POST /admin/students/{id}/reset-password
    and POST /admin/teachers/{id}/reset-password.
    Maps to the 'Manage Password' panel.
    """
    new_password: str


# ─────────────────────────────────────────────────────────────────────────────
# Courses (Lectures Management page)
# ─────────────────────────────────────────────────────────────────────────────

class AdminCourseOut(BaseModel):
    """Single course row as shown in the Course Directory table."""
    course_code: str
    title: str
    description: Optional[str]
    teacher_id: Optional[int]
    teacher_name: Optional[str]     # denormalized for the table display

    class Config:
        from_attributes = True


class PaginatedCoursesResponse(BaseModel):
    total: int
    page: int
    page_size: int
    courses: List[AdminCourseOut]


class CreateCourseRequest(BaseModel):
    """
    Body for POST /admin/courses — 'Create New Course' panel.
    Teacher is assigned separately via POST /courses/{code}/assign-teacher.
    """
    course_code: str                # e.g. "CS-402", must be unique
    title: str
    description: Optional[str] = None


class UpdateCourseRequest(BaseModel):
    """Body for PATCH /admin/courses/{code} — 'Update Course Details' panel."""
    title: str


class AssignTeacherRequest(BaseModel):
    """Body for POST /admin/courses/{code}/assign-teacher."""
    teacher_id: int


class EnrollStudentRequest(BaseModel):
    """Body for POST /admin/courses/{code}/enroll-student."""
    student_id: int


class EnrollmentOut(BaseModel):
    """Response after successfully enrolling a student."""
    enrollment_id: int
    course_code: str
    student_id: int


class CourseDropdownItem(BaseModel):
    """
    Lightweight item used to populate Course ID dropdowns.
    Used by:
      - GET /admin/teachers/{id}/courses  → 'Update Teacher Assignment' panel
      - GET /admin/students/{id}/courses  → 'Update Student Assignment' panel
    """
    course_code: str
    title: str
    label: str          # e.g. "CS-402 - Quantum Algorithms"  (ready for <option> text)


# ─────────────────────────────────────────────────────────────────────────────
# Generic message response
# ─────────────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    detail: str
