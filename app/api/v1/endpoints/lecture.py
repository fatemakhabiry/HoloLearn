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
from app.models.agent_session import AgentSession
from app.models.lecture_version import LectureVersion, VersionStatus
from app.models.resource import Resource
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
    ALLOWED_EXTENSIONS = {".pdf", ".pptx",".ppt", ".txt"}
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
        # ── Save permanent copy for RAG (triggered at publish time) ───
        permanent_dir  = Path(settings.UPLOADS_DIR) / "lectures" / str(lecture.lecture_id)
        permanent_dir.mkdir(parents=True, exist_ok=True)
        permanent_path = permanent_dir / f"lecture{file_ext}"

        with open(temp_path, "rb") as src, open(permanent_path, "wb") as dst:
            dst.write(src.read())

        # Store permanent path on lecture for later use
        lecture.local_file_path = str(permanent_path.resolve())
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        # ─────────────────────────────────────────────────────────────

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

# @router.post("/{lecture_id}/confirm-and-publish", response_model=ConfirmPublishResponse)
# async def confirm_and_publish_lecture(
#     lecture_id: int,
#     request_data: ConfirmPublishRequest,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_teacher)
# ):
#     """
#     Confirm and publish lecture by reserving a schedule slot
    
#     ✅ UPDATED: No schedule ownership check - schedules are public!
#     Any teacher can use any available slot.
#     """
    
#     # Get lecture
#     lecture = session.get(Lecture, lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Lecture with ID {lecture_id} not found"
#         )
    
#     # Verify lecture ownership
#     if lecture.teacher_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only publish your own lectures"
#         )
    
#     # Get schedule slot
#     schedule = session.get(Schedule, request_data.schedule_id)
    
#     if not schedule:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Schedule slot with ID {request_data.schedule_id} not found"
#         )
    
#     # ✅ REMOVED: schedule.teacher_id check (schedules are public!)
    
#     # Verify schedule is available
#     if schedule.lecture_id is not None:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="This schedule slot is already reserved"
#         )
    
#     if schedule.status != "available":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"This schedule slot is not available (status: {schedule.status})"
#         )
    
#     # Reserve the schedule
#     schedule.lecture_id = lecture_id
#     schedule.status = "scheduled"
#     session.add(schedule)
    
#     # Update lecture status
#     lecture.status = LectureStatus.COMPLETED
#     session.add(lecture)
    
#     session.commit()
#     session.refresh(lecture)
#     session.refresh(schedule)
#     # ── Trigger RAG indexing ───────────────────────────────────────
#     # Only for prepared lectures — generated lectures trigger from
#     # generation_worker.py after agent completes
#     if lecture.lecture_type == LectureType.PREPARED:
#         if lecture.local_file_path and Path(lecture.local_file_path).exists():
#             from arq import create_pool
#             from arq.connections import RedisSettings

#             redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
#             await redis.enqueue_job(
#                 "run_rag_ingest",
#                 lecture_id = lecture.lecture_id,
#                 file_path  = lecture.local_file_path,
#             )
#             await redis.close()
#         else:
#             # Log warning — file missing but don't block publish
#             import logging
#             logging.getLogger(__name__).warning(
#                 f"[RAG] Prepared lecture {lecture.lecture_id} published "
#                 f"but local_file_path missing or not on disk — skipping RAG ingest"
#             )
#     # ─────────────────────────────────────────────────────────────
#     return ConfirmPublishResponse(
#         message="Lecture published and scheduled successfully",
#         lecture_id=lecture.lecture_id,
#         schedule_id=schedule.schedule_id,
#         lecture_title=lecture.title,
#         course_code=lecture.course_code,
#         lecture_status=lecture.status.value,
#         schedule_status=schedule.status,
#         scheduled_date=schedule.date,
#         start_time=schedule.start_time,
#         end_time=schedule.end_time
#     )


@router.post("/{lecture_id}/confirm-and-publish", response_model=ConfirmPublishResponse)
async def confirm_and_publish_lecture(
    lecture_id: int,
    request_data: ConfirmPublishRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    Confirm and publish lecture by reserving a schedule slot.
    Triggers RAG ingest deferred to 15 minutes before lecture start.
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
    schedule.status     = "scheduled"
    session.add(schedule)

    # Update lecture status
    lecture.status = LectureStatus.COMPLETED
    session.add(lecture)

    session.commit()
    session.refresh(lecture)
    session.refresh(schedule)

    # ── Trigger RAG indexing — deferred to 15 min before lecture start ──
    import logging
    from datetime import timedelta
    _logger = logging.getLogger(__name__)

    print(f"\n[ConfirmPublish] ========== DEBUG START ==========")
    print(f"[ConfirmPublish] lecture_id={lecture.lecture_id}")
    print(f"[ConfirmPublish] lecture_type={lecture.lecture_type}")
    print(f"[ConfirmPublish] extracted_txt_path={lecture.extracted_txt_path}")
    print(f"[ConfirmPublish] local_file_path={lecture.local_file_path}")

    file_to_index = None

    if lecture.lecture_type == LectureType.PREPARED:
        extracted_exists = (
            Path(lecture.extracted_txt_path).exists()
            if lecture.extracted_txt_path else False
        )
        local_exists = (
            Path(lecture.local_file_path).exists()
            if lecture.local_file_path else False
        )
        print(f"[ConfirmPublish] extracted_txt_path exists on disk={extracted_exists}")
        print(f"[ConfirmPublish] local_file_path exists on disk={local_exists}")

        if lecture.extracted_txt_path and extracted_exists:
            file_to_index = lecture.extracted_txt_path
            _logger.info(
                f"[RAG] Using extracted txt for lecture {lecture.lecture_id}: "
                f"{file_to_index}"
            )
        elif lecture.local_file_path and local_exists:
            file_to_index = lecture.local_file_path
            _logger.warning(
                f"[RAG] extracted_txt_path missing — "
                f"falling back to original file for lecture {lecture.lecture_id}"
            )
        else:
            _logger.warning(
                f"[RAG] Prepared lecture {lecture.lecture_id} published "
                f"but no file found to index — skipping RAG ingest"
            )

    elif lecture.lecture_type == LectureType.GENERATED:
        latest_version = session.exec(
            select(LectureVersion)
            .where(
                LectureVersion.lecture_id == lecture.lecture_id,
                LectureVersion.status     == VersionStatus.APPROVED,
            )
            .order_by(LectureVersion.version_number.desc())
        ).first()

        print(f"[ConfirmPublish] latest_version={latest_version}")
        print(f"[ConfirmPublish] latest_version.txt_path={latest_version.txt_path if latest_version else 'NO VERSION'}")

        if latest_version and latest_version.txt_path and Path(latest_version.txt_path).exists():
            file_to_index = latest_version.txt_path
            _logger.info(
                f"[RAG] Using approved version txt for lecture {lecture.lecture_id}: "
                f"{file_to_index}"
            )
        else:
            _logger.warning(
                f"[RAG] No approved LectureVersion.txt_path found for "
                f"generated lecture {lecture.lecture_id} — skipping RAG ingest"
            )

    print(f"[ConfirmPublish] FINAL file_to_index={file_to_index}")

    if file_to_index:
        from arq import create_pool
        from arq.connections import RedisSettings
        from zoneinfo import ZoneInfo

        # Schedule times are stored as naive LOCAL Cairo time (admin enters
        # them directly with no tz conversion — see schedule creation endpoint).
        # Convert to UTC before comparing against datetime.utcnow().
        CAIRO_TZ = ZoneInfo("Africa/Cairo")

        lecture_start_naive = datetime.combine(schedule.date, schedule.start_time)
        lecture_start_local = lecture_start_naive.replace(tzinfo=CAIRO_TZ)
        lecture_start_utc   = lecture_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        trigger_at = lecture_start_utc - timedelta(minutes=3)
        now        = datetime.utcnow()

        defer_by = trigger_at - now
        if defer_by.total_seconds() < 0:
            defer_by = timedelta(seconds=0)   # already within window — ingest now

        redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await redis.enqueue_job(
            "run_rag_ingest",
            lecture_id = lecture.lecture_id,
            file_path  = file_to_index,
            _defer_by  = defer_by,
        )
        await redis.close()

        _logger.info(
            f"[RAG] Ingest scheduled for lecture {lecture.lecture_id} "
            f"at {trigger_at.isoformat()} UTC (defer={defer_by})"
    )
    else:
        print(f"[ConfirmPublish] SKIPPED — file_to_index is None, no job enqueued")

    print(f"[ConfirmPublish] ========== DEBUG END ==========\n")
    # ─────────────────────────────────────────────────────────────

    return ConfirmPublishResponse(
        message          = "Lecture published and scheduled successfully",
        lecture_id       = lecture.lecture_id,
        schedule_id      = schedule.schedule_id,
        lecture_title    = lecture.title,
        course_code      = lecture.course_code,
        lecture_status   = lecture.status.value,
        schedule_status  = schedule.status,
        scheduled_date   = schedule.date,
        start_time       = schedule.start_time,
        end_time         = schedule.end_time
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
                        status=schedule.status,
                        lecture_type=lecture.lecture_type
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
                    status=lecture.status.value,
                    lecture_type=lecture.lecture_type

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
    
    # ── 1. Free all schedules (don't delete — just unlink) ────────
    schedules = session.exec(
        select(Schedule).where(Schedule.lecture_id == lecture_id)
    ).all()
    for schedule in schedules:
        schedule.lecture_id = None
        schedule.status = "available"
        session.add(schedule)

    # ── 2. Delete child rows that have NOT NULL FK to lectures ────
    for row in session.exec(select(AgentSession).where(AgentSession.lecture_id == lecture_id)).all():
        session.delete(row)

    for row in session.exec(select(LectureVersion).where(LectureVersion.lecture_id == lecture_id)).all():
        session.delete(row)

    for row in session.exec(select(GeneratedContent).where(GeneratedContent.lecture_id == lecture_id)).all():
        session.delete(row)

    for row in session.exec(select(Resource).where(Resource.lecture_id == lecture_id)).all():
        session.delete(row)

    pipeline = session.get(LecturePipeline, lecture_id)
    if pipeline:
        session.delete(pipeline)

    # ── 3. Delete the lecture itself ──────────────────────────────
    session.delete(lecture)
    session.commit()

    return DeleteLectureResponse(
        message="Lecture deleted successfully"
    )


# ============================================
# 7: Start Pipeline
# (combines prepare-pipeline + trigger-pipeline)
# ============================================
#
# CHANGED: this endpoint now enqueues run_tts (local TTS + transcript) via
# ARQ instead of calling the GPU machine directly. run_tts itself decides
# whether to chain into run_generation (GPU leg) based on
# settings.GPU_PIPELINE_ENABLED — see tts_worker.py.
#
# This means: as long as Redis + the ARQ worker are running, this endpoint
# works fully offline from the GPU machine. The old AI_SERVER_URL /
# BACKEND_PUBLIC_URL / INTERNAL_API_TOKEN config checks and the inline
# httpx call are gone from here — they now live inside generation_worker.py,
# only reached if/when run_tts chains into run_generation.

from pydantic import BaseModel
from arq.connections import create_pool, RedisSettings

_PIPELINE_DEFAULTS = dict(
    num_steps      = 20,
    audio_cfg      = 4.0,
    text_cfg       = 4.0,
    seed           = 42,
    preset         = "engaging_narration",
    avatar_backend = "local",
)


@router.post(
    "/{lecture_id}/start-pipeline",
    response_model=LecturePipelineTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reads script → creates LecturePipeline → enqueues run_tts",
)
async def start_pipeline(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher),
):
    """
    Single endpoint that combines prepare + trigger in one call.

    Steps performed internally:
      1. Verify lecture ownership
      2. Read script from generated_content (must exist)
      3. Create / reset LecturePipeline record with fixed defaults
      4. Verify teacher onboarding_status = 'ready'
      5. Enqueue run_tts (ARQ) — local TTS + transcript, chains into
         run_generation (GPU leg) only if GPU_PIPELINE_ENABLED=true
      6. Set lecture + pipeline status → QUEUED

    Prerequisites:
      - Agent session must be done (script saved in generated_content)
      - Teacher onboarding_status must be 'ready' (set by AI server)

    Returns 202 immediately — TTS + (optionally) video generation runs
    in the background via ARQ.
    """

    # ── 1. Lecture exists and belongs to this teacher ─────────────
    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Lecture {lecture_id} not found.")
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only start pipeline for your own lectures.")

    # ── 2. Read script from generated_content ─────────────────────
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
            detail=f"Script file not found on disk: {script.file_path}.",
        )

    # ── 3. Create / reset LecturePipeline ─────────────────────────
    pipeline = session.get(LecturePipeline, lecture_id)
    if not pipeline:
        pipeline = LecturePipeline(lecture_id=lecture_id, **_PIPELINE_DEFAULTS)
    else:
        if pipeline.status == PipelineStatus.GENERATING:
            raise HTTPException(
                status_code=409,
                detail="Pipeline is already generating. Wait for it to finish or fail first.",
            )
        for field, value in _PIPELINE_DEFAULTS.items():
            setattr(pipeline, field, value)

    pipeline.script_path     = script.file_path
    pipeline.status          = PipelineStatus.QUEUED
    pipeline.audio_path      = None   # fresh start — don't reuse audio from a previous run
    pipeline.transcript_path = None   # fresh start — old transcript shouldn't linger
    session.add(pipeline)
    session.commit()
    session.refresh(pipeline)

    # ── 4. Teacher onboarding must be ready ───────────────────────
    teacher = session.get(Teacher, lecture.teacher_id)
    if not teacher or teacher.onboarding_status != "ready":
        current_onboarding = teacher.onboarding_status if teacher else "no teacher record"
        raise HTTPException(
            status_code=409,
            detail=f"Teacher onboarding not complete. "
                   f"onboarding_status: '{current_onboarding}'. Must be 'ready'.",
        )

    # ── 5. Enqueue run_tts via ARQ ──────────────────────────────────
    # NOTE: this uses arq.connections.create_pool directly as a minimal,
    # explicit example. If your app already has a shared ARQ redis pool
    # (e.g. set up on startup and exposed via a dependency or app.state),
    # use that instead of creating a new pool per request — creating one
    # per request works but is wasteful under real load.
    try:
        redis_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await redis_pool.enqueue_job("run_tts", lecture_id)
        await redis_pool.close()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not enqueue generation job — is Redis running? ({e})",
        )

    return LecturePipelineTriggerResponse(
        lecture_id=lecture_id,
        status="queued",
        message=f"TTS job queued. Poll GET /lecture/{lecture_id}/transcript once ready "
                f"(video status depends on GPU_PIPELINE_ENABLED).",
    )



# ============================================
# 8: Retry Generation (GPU leg only)
# ============================================
#
# Distinct from start-pipeline (which always wipes audio_path/transcript_path
# and starts fully fresh from the script). This endpoint is for the case
# where run_tts already succeeded — audio.wav + transcript.txt exist and
# are stored on LecturePipeline — but run_generation failed downstream
# (GPU unreachable, ngrok dropped, job timed out, etc).
#
# Re-enqueues run_generation directly with the stored audio_path. No TTS,
# no Chatterbox, no re-synthesis — just resends the existing audio to the
# GPU machine.

from arq.connections import create_pool, RedisSettings


@router.post(
    "/{lecture_id}/retry-generation",
    response_model=LecturePipelineTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-enqueues run_generation using the already-stored audio_path — no TTS re-run",
)
async def retry_generation(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher),
):
    """
    Retries ONLY the avatar-generation (GPU) leg of the pipeline.

    Requires:
      - LecturePipeline record exists for this lecture
      - pipeline.audio_path is set AND the file still exists on disk
        (i.e. run_tts has already succeeded at least once)
      - pipeline.status is not currently GENERATING (avoid double-dispatch)

    Use this instead of start-pipeline when:
      - run_tts succeeded (audio + transcript already produced)
      - run_generation failed for a reason unrelated to the script/audio
        itself (GPU machine was down, network drop, timeout, etc.)
      - The script hasn't changed, so there's no need to re-run TTS

    If the script HAS changed, use start-pipeline instead — it wipes
    audio_path/transcript_path and runs the full chain fresh.
    """

    # ── 1. Lecture exists and belongs to this teacher ─────────────
    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail=f"Lecture {lecture_id} not found.")
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only retry generation for your own lectures.")

    # ── 2. Pipeline must exist ──────────────────────────────────────
    pipeline = session.get(LecturePipeline, lecture_id)
    if not pipeline:
        raise HTTPException(
            status_code=404,
            detail="No pipeline record found. Run start-pipeline first.",
        )

    if pipeline.status == PipelineStatus.GENERATING:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already generating. Wait for it to finish or fail first.",
        )

    # ── 3. Audio must already exist — this endpoint does not run TTS ──
    if not pipeline.audio_path:
        raise HTTPException(
            status_code=409,
            detail="No audio_path on this pipeline — run_tts hasn't succeeded yet. "
                   "Use start-pipeline instead.",
        )

    if not Path(pipeline.audio_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"audio_path is set but the file is missing on disk: {pipeline.audio_path}. "
                   "Use start-pipeline to regenerate it.",
        )

    # ── 4. Enqueue run_generation directly ──────────────────────────
    try:
        redis_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await redis_pool.enqueue_job("run_generation", lecture_id, pipeline.audio_path)
        await redis_pool.close()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not enqueue run_generation — is Redis running? ({e})",
        )

    return LecturePipelineTriggerResponse(
        lecture_id=lecture_id,
        status="queued",
        message=f"run_generation re-queued using existing audio at {pipeline.audio_path}. "
                f"No TTS re-run — transcript is unaffected.",
    )

# ============================================
# 9: Stream Generated Video
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
