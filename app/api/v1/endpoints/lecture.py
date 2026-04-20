# app/api/v1/endpoints/lecture.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import Optional, List
from datetime import time, date, datetime
from pathlib import Path
import httpx
import os
from app.services.google_drive import drive_service
from app.core.config import settings
from app.core.database import get_session
from app.models.lecture import Lecture, LectureType, LectureStatus, LecturePublic, LecturePipelineTriggerResponse
from app.models.schedule import Schedule, SchedulePublic, ScheduleCreate
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.lecture_pipeline import LecturePipeline, PipelineStatus
from app.models.generated_content import GeneratedContent, ContentType
from app.api.deps import get_current_user, get_current_teacher
from app.schemas.schedule_schemas import (
    ConfirmPublishResponse,
    ConfirmPublishRequest,
    LectureEditDetails,
    EditLectureResponse,
    FullTimeSlot2,
    EditLectureRequest,
    DeleteLectureResponse
)

router = APIRouter()


# ============================================
# 1: Create Draft Lecture
# ============================================

@router.post("/create-draft", response_model=LecturePublic, status_code=status.HTTP_201_CREATED)
async def create_lecture_draft(
    title: str = Form(...),
    course_code: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """Create lecture draft with file upload to Google Drive"""
    
    # Verify course exists and belongs to teacher
    course = session.get(Course, course_code)
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_code}' not found"
        )
    
    if course.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create lectures for your own courses"
        )
    
    # Validate file
    ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".txt"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed: PDF, PPTX, TXT"
        )
    
    # Save file temporarily and upload to Drive
    temp_dir = "/tmp/hololearn_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_filename = f"temp_{current_user.user_id}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_filename = f"{course_code}_{title}_{timestamp}{file_ext}"
        
        drive_result = drive_service.upload_file(
            file_path=temp_path,
            filename=drive_filename,
            mime_type=file.content_type
        )
        
        # Create lecture
        lecture = Lecture(
            title=title,
            teacher_id=current_user.user_id,
            course_code=course_code,
            lecture_type=LectureType.PREPARED,
            status=LectureStatus.DRAFT,
            final_content=drive_result['view_link']
        )
        
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        
        return lecture
        
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lecture: {str(e)}"
        )
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


# ============================================
# 2: Confirm & Publish (PUBLIC SCHEDULE)
# ============================================

@router.post("/{lecture_id}/confirm-and-publish", response_model=ConfirmPublishResponse)
async def confirm_and_publish_lecture(
    lecture_id: int,
    request_data: ConfirmPublishRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    Confirm and publish lecture by reserving a schedule slot
    
    ✅ UPDATED: No schedule ownership check - schedules are public!
    Any teacher can use any available slot.
    """
    
    # Get lecture
    lecture = session.get(Lecture, lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with ID {lecture_id} not found"
        )
    
    # Verify lecture ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own lectures"
        )
    
    # Get schedule slot
    schedule = session.get(Schedule, request_data.schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule slot with ID {request_data.schedule_id} not found"
        )
    
    # ✅ REMOVED: schedule.teacher_id check (schedules are public!)
    
    # Verify schedule is available
    if schedule.lecture_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This schedule slot is already reserved"
        )
    
    if schedule.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This schedule slot is not available (status: {schedule.status})"
        )
    
    # Reserve the schedule
    schedule.lecture_id = lecture_id
    schedule.status = "scheduled"
    session.add(schedule)
    
    # Update lecture status
    lecture.status = LectureStatus.COMPLETED
    session.add(lecture)
    
    session.commit()
    session.refresh(lecture)
    session.refresh(schedule)
    
    return ConfirmPublishResponse(
        message="Lecture published and scheduled successfully",
        lecture_id=lecture.lecture_id,
        schedule_id=schedule.schedule_id,
        lecture_title=lecture.title,
        course_code=lecture.course_code,
        lecture_status=lecture.status.value,
        schedule_status=schedule.status,
        scheduled_date=schedule.date,
        start_time=schedule.start_time,
        end_time=schedule.end_time
    )


# ============================================
# 3: Get Lecture Details for Editing
# ============================================

@router.get("/schedule/{schedule_id}/edit-details", response_model=LectureEditDetails)
async def get_lecture_edit_details_by_schedule(
    schedule_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """Get lecture details for editing"""
    
    schedule = session.get(Schedule, schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )
    
    # ✅ REMOVED: schedule.teacher_id check (schedules are public!)
    
    if schedule.lecture_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This schedule has no lecture assigned"
        )
    
    lecture = session.get(Lecture, schedule.lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found"
        )
    
    # ✅ KEPT: Verify lecture ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own lectures"
        )
    
    return LectureEditDetails(
        lecture_id=lecture.lecture_id,
        schedule_id=schedule.schedule_id,
        title=lecture.title,
        course_code=lecture.course_code,
        current_file_url=lecture.final_content or "",
        scheduled_date=schedule.date,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        status=schedule.status
    )


# ============================================
# 4: Edit Lecture and Schedule
# ============================================

@router.put("/schedule/{schedule_id}/edit", response_model=EditLectureResponse)
async def edit_lecture_by_schedule(
    schedule_id: int,
    request_data: EditLectureRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    Edit lecture title, course code, and/or schedule

    ✅ UPDATED: No schedule ownership checks - schedules are public!
    """

    current_schedule = session.get(Schedule, schedule_id)
    
    if not current_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )
    
    # ✅ REMOVED: schedule.teacher_id check
    
    if current_schedule.lecture_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This schedule has no lecture assigned"
        )
    
    lecture = session.get(Lecture, current_schedule.lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found"
        )
    
    # ✅ KEPT: Verify lecture ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own lectures"
        )
    
    try:
        # Update title
        if request_data.title is not None:
            lecture.title = request_data.title
        
        # Update course code
        if request_data.course_code is not None and request_data.course_code != lecture.course_code:
            course = session.get(Course, request_data.course_code)
            
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Course '{request_data.course_code}' not found"
                )
            
            if course.teacher_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only assign lectures to your own courses"
                )
            
            lecture.course_code = request_data.course_code
        
        # Handle schedule change
        schedule_changed = False
        final_schedule = current_schedule
        
        if request_data.new_schedule_id and request_data.new_schedule_id != schedule_id:
            new_schedule = session.get(Schedule, request_data.new_schedule_id)
            
            if not new_schedule:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"New schedule with ID {request_data.new_schedule_id} not found"
                )
            
            # ✅ REMOVED: new_schedule.teacher_id check (schedules are public!)
            
            # Verify new schedule is available
            if new_schedule.lecture_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The new schedule slot is already reserved"
                )
            
            if new_schedule.status != "available":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The new schedule slot is not available (status: {new_schedule.status})"
                )
            
            # Free old schedule
            current_schedule.lecture_id = None
            current_schedule.status = "available"
            session.add(current_schedule)
            
            # Reserve new schedule
            new_schedule.lecture_id = lecture.lecture_id
            new_schedule.status = "scheduled"
            session.add(new_schedule)
            
            final_schedule = new_schedule
            schedule_changed = True
        
        # Save changes
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        session.refresh(final_schedule)
        
        return EditLectureResponse(
            message="Lecture updated successfully",
            lecture_id=lecture.lecture_id,
            schedule_id=final_schedule.schedule_id,
            lecture_title=lecture.title,
            course_code=lecture.course_code,
            lecture_status=lecture.status.value,
            scheduled_date=final_schedule.date,
            start_time=final_schedule.start_time,
            end_time=final_schedule.end_time,
            schedule_status=final_schedule.status,
            schedule_changed=schedule_changed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lecture: {str(e)}"
        )


# ============================================
# 5: Get All My Lectures
# ============================================

@router.get("/all-my-lectures", response_model=List[FullTimeSlot2])
def get_all_my_lectures(
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """Get ALL lectures created by teacher (scheduled + draft)"""
    
    lectures = session.exec(
        select(Lecture)
        .where(Lecture.teacher_id == current_user.user_id)
        .order_by(Lecture.lecture_id.desc())
    ).all()
    
    result = []
    teacher_name = current_user.full_name or "Unknown"
    
    for lecture in lectures:
        schedules = session.exec(
            select(Schedule)
            .where(
                Schedule.lecture_id == lecture.lecture_id,
                Schedule.status == "scheduled"
            )
            .order_by(Schedule.date, Schedule.start_time)
        ).all()
        
        if schedules:
            for schedule in schedules:
                start_datetime = datetime.combine(schedule.date, schedule.start_time)
                end_datetime = datetime.combine(schedule.date, schedule.end_time)
                
                result.append(
                    FullTimeSlot2(
                        schedule_id=schedule.schedule_id,
                        lecture_id=lecture.lecture_id,
                        course_code=lecture.course_code,
                        lecture_title=lecture.title,
                        teacher_name=teacher_name,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        status=schedule.status
                    )
                )
        else:
            result.append(
                FullTimeSlot2(
                    schedule_id=None,
                    lecture_id=lecture.lecture_id,
                    course_code=lecture.course_code,
                    lecture_title=lecture.title,
                    teacher_name=teacher_name,
                    start_time=None,
                    end_time=None,
                    status=lecture.status.value
                )
            )
    
    return result


# ============================================
# 6: Delete Lecture
# ============================================

@router.delete("/{lecture_id}", response_model=DeleteLectureResponse)
async def delete_lecture(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """Delete lecture and free all its schedules"""
    
    lecture = session.get(Lecture, lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with ID {lecture_id} not found"
        )
    
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own lectures"
        )
    
    # Free all schedules
    schedules = session.exec(
        select(Schedule).where(Schedule.lecture_id == lecture_id)
    ).all()
    
    for schedule in schedules:
        schedule.lecture_id = None
        schedule.status = "available"
        session.add(schedule)
    
    # Delete lecture
    session.delete(lecture)
    session.commit()

    return DeleteLectureResponse(
        message="Lecture deleted successfully"
    )


# ============================================
# 7: Prepare Pipeline
# ============================================

from pydantic import BaseModel

# ── Fixed pipeline defaults (not exposed to caller) ──────────────────────────
_PIPELINE_DEFAULTS = dict(
    num_steps      = 20,
    audio_cfg      = 4.0,
    text_cfg       = 4.0,
    seed           = 42,
    preset         = "engaging_narration",
    avatar_backend = "local",
)


class PreparePipelineResponse(BaseModel):
    lecture_id:     int
    lecture_type:   str
    script_path:    str
    status:         str
    avatar_backend: str
    message:        str


@router.post(
    "/{lecture_id}/prepare-pipeline",
    response_model=PreparePipelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Bridge: reads script from generated_content → creates/updates LecturePipeline",
)
def prepare_pipeline(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher),
):
    """
    Connects the agent session output to the avatar pipeline.

    Works for **any** lecture type (PREPARED or GENERATED) as long as a script
    row exists in generated_content for that lecture.

    Prerequisites (must be done first):
      1. POST /session/start           → agent generates content
      2. POST /session/{id}/approve    → lecture approved
      → agent saves script to generated_content table

    What this endpoint does:
      - Verifies lecture ownership (any type accepted)
      - Reads GeneratedContent where content_type = 'script' for this lecture
      - Creates or updates a LecturePipeline record with fixed default params:
            num_steps=20, audio_cfg=4.0, text_cfg=4.0, seed=42,
            preset="engaging_narration", avatar_backend="local"
      - Returns confirmation so teacher can call trigger-pipeline next

    No request body required — all pipeline params are fixed in the backend.
    """

    # ── 1. Verify lecture exists and belongs to this teacher ──────────────
    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Lecture {lecture_id} not found.")

    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only prepare your own lectures.")

    # ── 2. Read script from generated_content ────────────────────────────
    script = session.exec(
        select(GeneratedContent).where(
            GeneratedContent.lecture_id   == lecture_id,
            GeneratedContent.content_type == ContentType.SCRIPT,
        )
    ).first()

    if not script:
        raise HTTPException(
            status_code=404,
            detail="Script not found in generated_content. "
                   "Run the agent session and approve the lecture first.",
        )

    if not Path(script.file_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Script file not found on disk: {script.file_path}. "
                   "The agent may need to re-run.",
        )

    # ── 3. Create or update LecturePipeline with fixed defaults ──────────
    pipeline = session.get(LecturePipeline, lecture_id)

    if not pipeline:
        pipeline = LecturePipeline(lecture_id=lecture_id, **_PIPELINE_DEFAULTS)
    else:
        # Reset to fixed defaults on every call (no drift from old values)
        for field, value in _PIPELINE_DEFAULTS.items():
            setattr(pipeline, field, value)

    pipeline.script_path = script.file_path
    pipeline.status      = PipelineStatus.QUEUED

    session.add(pipeline)
    session.commit()
    session.refresh(pipeline)

    return PreparePipelineResponse(
        lecture_id=lecture_id,
        lecture_type=lecture.lecture_type.value,
        script_path=script.file_path,
        status=pipeline.status.value,
        avatar_backend=pipeline.avatar_backend,
        message=f"Pipeline ready. Call POST /lecture/{lecture_id}/trigger-pipeline to start video generation.",
    )


# ============================================
# 8: Trigger Pipeline (already exists below)
# ============================================

# # app/api/v1/endpoints/lecture.py
# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
# from fastapi.responses import FileResponse
# from pydantic import BaseModel
# from sqlmodel import SQLModel, Session, select
# from typing import Optional, List
# from datetime import time, date, datetime
# from pathlib import Path
# from arq import create_pool
# from arq.connections import RedisSettings
# import os

# ============================================
# 7: Trigger Pipeline
# ============================================

@router.post(
    "/{lecture_id}/trigger-pipeline",
    response_model=LecturePipelineTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def trigger_lecture_pipeline(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger avatar video generation for a GENERATED lecture.

    Requires:
    - Lecture exists with lecture_type = GENERATED
    - Teacher onboarding_status = 'ready'
    - LecturePipeline record exists with script_path set and file on disk
    - Pipeline status is not already GENERATING or COMPLETED

    Returns 202 immediately — generation runs in background (5–25 min).
    """

    # Check 1: Lecture exists
    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Lecture {lecture_id} not found")

    # Check 2: Caller owns the lecture
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only trigger generation for your own lectures")

    # Check 3: Teacher onboarding must be ready (set by AI server after preprocessing)
    teacher = session.get(Teacher, lecture.teacher_id)
    if not teacher or teacher.onboarding_status != "ready":
        current_onboarding = teacher.onboarding_status if teacher else "no teacher record"
        raise HTTPException(
            status_code=409,
            detail=f"Teacher onboarding not complete. "
                   f"onboarding_status: '{current_onboarding}'. Must be 'ready'."
        )

    # Check 4: LecturePipeline record must exist
    pipeline = session.get(LecturePipeline, lecture_id)
    if not pipeline:
        raise HTTPException(
            status_code=400,
            detail="No LecturePipeline record found for this lecture. "
                   "Upstream module must create it and set script_path first."
        )

    # Check 6: script_path must be set
    if not pipeline.script_path:
        raise HTTPException(
            status_code=400,
            detail="pipeline.script_path is not set. "
                   "Upstream module must write the script and set script_path first."
        )

    # Check 7: Script file must exist on disk
    if not Path(pipeline.script_path).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Script file not found on disk: {pipeline.script_path}"
        )

    # Check 8: Not already running or completed
    if pipeline.status in (PipelineStatus.GENERATING, PipelineStatus.COMPLETED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot trigger. Pipeline status is already '{pipeline.status.value}'. "
                   f"Only QUEUED or FAILED pipelines can be triggered."
        )

    # All checks passed — dispatch job to AI server via HTTP
    if not settings.AI_SERVER_URL:
        raise HTTPException(
            status_code=503,
            detail="AI_SERVER_URL is not configured. Set it in .env to point to the AI server's ngrok URL.",
        )
    if not settings.BACKEND_PUBLIC_URL:
        raise HTTPException(
            status_code=503,
            detail="BACKEND_PUBLIC_URL is not configured. Set it in .env to your laptop's ngrok URL.",
        )
    if not settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="INTERNAL_API_TOKEN is not configured. Set it in .env.",
        )

    base = settings.BACKEND_PUBLIC_URL.rstrip("/")
    token = settings.INTERNAL_API_TOKEN

    def _file_url(path: str) -> str:
        """Build a signed download URL for the AI server to fetch a file from this laptop."""
        return f"{base}/api/v1/internal/files?path={path}"

    payload = {
        "lecture_id":          lecture_id,
        "script_download_url": _file_url(pipeline.script_path),
        "image_download_url":  _file_url(teacher.preprocessed_image_path) if teacher.preprocessed_image_path else None,
        "voice_download_url":  _file_url(teacher.voice_sample) if teacher.voice_sample else None,
        "pipeline_params": {
            "num_steps":      pipeline.num_steps,
            "audio_cfg":      pipeline.audio_cfg,
            "text_cfg":       pipeline.text_cfg,
            "seed":           pipeline.seed,
            "preset":         pipeline.preset,
            "avatar_backend": pipeline.avatar_backend,
        },
        "callback_url": f"{base}/api/v1/internal/pipeline-done",
        "token":        token,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.AI_SERVER_URL.rstrip('/')}/ai/generate",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code not in (200, 202):
            raise HTTPException(
                status_code=502,
                detail=f"AI server rejected the job (HTTP {response.status_code}): {response.text[:300]}",
            )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach AI server at {settings.AI_SERVER_URL}. Is ngrok running on friend's PC?",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="AI server did not respond within 15 seconds.",
        )

    # Update status so frontend polling sees it immediately
    lecture.status  = LectureStatus.GENERATING
    pipeline.status = PipelineStatus.GENERATING
    session.add(lecture)
    session.add(pipeline)
    session.commit()

    return LecturePipelineTriggerResponse(
        lecture_id=lecture_id,
        status="generating",
        message=f"Job dispatched to AI server. Poll GET /lecture/{lecture_id}/video for progress.",
    )


# ============================================
# 8: Stream Generated Video
# ============================================

@router.get("/{lecture_id}/video")
async def stream_lecture_video(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Stream the generated avatar MP4 for a completed lecture.

    
200: Video streaming
404: Lecture not found
409: Video not ready yet
410: File was deleted from disk
"""

    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Lecture {lecture_id} not found")

    # Check pipeline record
    pipeline = session.get(LecturePipeline, lecture_id)
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No pipeline record found for this lecture."
        )

    if pipeline.status != PipelineStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Video not ready. Pipeline status: '{pipeline.status.value}'."
        )

    if not pipeline.output_video_path:
        raise HTTPException(
            status_code=409,
            detail="Pipeline completed but no output_video_path recorded."
        )

    video_path = Path(pipeline.output_video_path)
    if not video_path.exists():
        raise HTTPException(
            status_code=410,
            detail="Video file no longer available on disk."
        )

    return FileResponse(
        path=str(video_path),
        mediatype="video/mp4",
        filename=f"lecture{lecture_id}.mp4"
    )
