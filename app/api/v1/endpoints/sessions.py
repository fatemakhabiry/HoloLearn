# app/api/v1/endpoints/sessions.py

import uuid
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import re
import tempfile

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select
import httpx

from app.api.deps import get_current_teacher
from app.core.config import settings
from app.core.database import get_session, engine
from app.models.user import User
from app.models.lecture import Lecture, LectureStatus, LectureType
from app.models.resource import Resource, ResourceType
from app.models.agent_session import AgentSession, AgentStatus
from app.models.lecture_version import LectureVersion, VersionStatus
from app.models.generated_content import GeneratedContent, ContentType
from app.services.agent_client import start_agent, resume_agent, get_agent_state, extract_resource

router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────────

class ResourceIn(BaseModel):
    resource_type: ResourceType
    file_path:     str
    query:         str


class StartGeneratedRequest(BaseModel):
    title:       str
    course_code: str
    resources:   list[ResourceIn]


class RejectRequest(BaseModel):
    feedback: str


# ── Helper utilities ───────────────────────────────────────────────────────────

def _guess_extension(content_type: str) -> str:
    """Map HTTP content-type header to file extension."""
    mapping = {
        "application/pdf":  ".pdf",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document":   ".docx",
        "text/plain": ".txt",
    }
    for mime, ext in mapping.items():
        if mime in content_type:
            return ext
    return ".pdf"


def _get_session_or_404(
    session_id: int,
    db:         Session,
    teacher:    User,
) -> tuple[AgentSession, Lecture]:
    """Load agent session and verify ownership."""
    agent_session = db.exec(
        select(AgentSession).where(AgentSession.id == session_id)
    ).first()

    if not agent_session:
        raise HTTPException(404, "Session not found")

    lecture = db.get(Lecture, agent_session.lecture_id)
    if not lecture or lecture.teacher_id != teacher.user_id:
        raise HTTPException(403, "Not your session")

    return agent_session, lecture


async def _build_agent_state(
    lecture:    Lecture,
    resources:  list[Resource],
    session_id: int,
    thread_id:  str,
) -> dict:
    """Build the AgentState dict the LangGraph graph expects."""
    output_dir = str(Path(settings.OUTPUTS_DIR) / str(lecture.lecture_id))

    source: dict = {
        "type":          "generated_lecture",
        "prepared_text": None,
        "pdf":     None, "docx": None, "pptx":    None,
        "audio":   None, "video": None, "website": None,
        "images":  None,
    }

    type_map: dict[str, list] = {}

    for r in resources:
        key = r.resource_type.value.lower()
        if key == "document":
            key = "docx"

        if key not in type_map:
            type_map[key] = []

        if key == "image":
            type_map.setdefault("images", []).append({
                "path":    r.file_path,
                "caption": r.query,
            })
        else:
            file_ext = Path(r.file_path).suffix.lower()

            if file_ext == ".txt":
                text = Path(r.file_path).read_text(
                    encoding="utf-8", errors="ignore"
                )
            else:
                text = await extract_resource(r.file_path, key)

            if not text:
                print(f"[sessions] ⚠ empty text from {r.file_path}")
                continue

            type_map[key].append({"text": text, "query": r.query})

    for key, entries in type_map.items():
        if key != "images":
            source[key] = entries
        else:
            source["images"] = entries

    return {
        "meta": {
            "session_id":  str(session_id),
            "teacher_id":  str(lecture.teacher_id),
            "course_code": lecture.course_code,
            "title":       lecture.title,
            "output_dir":  output_dir,
        },
        "source":           source,
        "final_lecture":    None,
        "lecture_paths":    None,
        "lecture_approval": {
            "status":           "pending",
            "teacher_feedback": None,
            "iteration":        0,
            "max_iterations":   3,
        },
        "generated_content": {
            "script": None, "worksheet": None, "quiz": None,
            "summary": None, "flowchart": None, "knowledge_graph": None,
        },
        "current_step": "starting",
        "error":        None,
    }


async def _upload_to_drive(
    file_path: str,
    filename:  str,
    lecture:   Lecture,
    db:        Session,
) -> str:
    """Upload a file to Google Drive and update lectures.final_content."""
    try:
        from app.api.v1.endpoints.lecture import drive_service

        result     = drive_service.upload_file(
            file_path  = file_path,
            filename   = filename,
            mime_type  = "application/pdf",
        )
        drive_link = result.get("view_link", "")

        if drive_link:
            lecture.final_content = drive_link
            db.add(lecture)
            db.commit()
            print(f"[sessions] ✓ uploaded to Drive: {drive_link}")

        return drive_link

    except Exception as e:
        print(f"[sessions] Drive upload failed: {e}")
        return ""


async def _extract_from_drive(drive_link: str) -> str:
    """Download file from Drive and extract text via AI service extractor."""
    if "drive.google.com/file/d/" not in drive_link:
        print(f"[sessions] cannot parse Drive link: {drive_link}")
        return ""

    file_id      = drive_link.split("/file/d/")[1].split("/")[0]
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        async with httpx.AsyncClient(
            timeout=120.0,
            follow_redirects=True,
        ) as client:
            r = await client.get(download_url)

            # Handle large file virus scan warning page
            if (
                r.status_code == 200
                and "text/html" in r.headers.get("content-type", "")
            ):
                match = re.search(r'confirm=([0-9A-Za-z_\-]+)', r.text)
                if match:
                    confirm = match.group(1)
                    r = await client.get(
                        f"https://drive.google.com/uc"
                        f"?export=download&id={file_id}&confirm={confirm}"
                    )

            if r.status_code != 200:
                print(f"[sessions] Drive download failed: {r.status_code}")
                return ""

            content_type = r.headers.get("content-type", "application/pdf")

            if "text/html" in content_type:
                print("[sessions] Drive returned HTML — check file permissions")
                return ""

            suffix = _guess_extension(content_type)

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix
            ) as tmp:
                tmp.write(r.content)
                tmp_path = tmp.name

        resource_type = suffix.lstrip(".")
        text = await extract_resource(tmp_path, resource_type)
        Path(tmp_path).unlink(missing_ok=True)
        return text

    except Exception as e:
        print(f"[sessions] Drive extraction error: {e}")
        return ""


async def _sync_state_to_db(
    agent_session: AgentSession,
    lecture:       Lecture,
    state:         dict,
    db:            Session,
) -> None:
    """Sync agent state to DB after every status poll."""
    current_step  = state.get("current_step")
    lecture_paths = state.get("lecture_paths") or {}
    approval      = state.get("lecture_approval") or {}

    # ── Priority map — used to prevent background loop from
    # overwriting a more advanced DB status with a stale checkpoint step
    priority = {
        "starting":           0,
        "generating_lecture": 1,
        "awaiting_approval":  2,
        "regenerating":       3,
        "generating_content": 4,
        "done":               5,
        "failed":             6,
    }

    # ── Update agent session status ───────────────────────────────
    try:
         agent_session.status = AgentStatus(current_step)

    except ValueError:
        pass

    agent_session.updated_at = datetime.utcnow()

    # ── Upsert lecture_version (generated lectures only) ──────────
    if lecture_paths.get("txt") and lecture.lecture_type == LectureType.GENERATED:

        existing_versions = db.exec(
            select(LectureVersion).where(
                LectureVersion.lecture_id == lecture.lecture_id
            )
        ).all()

        existing = next(
            (v for v in existing_versions
             if v.pdf_path == lecture_paths.get("pdf")),
            None,
        )

        approval_status = approval.get("status", "pending")
        version_status  = (
            VersionStatus.APPROVED  if approval_status == "approved"
            else VersionStatus.REJECTED if approval_status == "rejected"
            else VersionStatus.PENDING
        )

        if not existing:
            version_number = len(existing_versions) + 1
            print(f"[sync] saving lecture version {version_number}")
            db.add(LectureVersion(
                lecture_id       = lecture.lecture_id,
                version_number   = version_number,
                pdf_path         = lecture_paths.get("pdf"),
                txt_path         = lecture_paths.get("txt"),
                json_path        = lecture_paths.get("json"),
                status           = version_status,
                teacher_feedback = approval.get("teacher_feedback"),
            ))
        else:
            # Same PDF — only update status if it is more advanced
            # pending → rejected is an advancement
            # rejected → pending would be a downgrade — skip it
            version_priority = {
                "pending":  0,
                "rejected": 1,
                "approved": 2,
            }
            current_version_priority = version_priority.get(
                existing.status.value if hasattr(existing.status, 'value') else str(existing.status), 0
            )
            new_version_priority = version_priority.get(
                version_status.value if hasattr(version_status, 'value') else str(version_status), 0
            ) 

            if new_version_priority >= current_version_priority:
                existing.status           = version_status
                existing.teacher_feedback = approval.get("teacher_feedback")
                db.add(existing)
            else:
                print(
                    f"[sync] skipping version status downgrade: "
                    f"{version_status} < {existing.status}"
                )

    # ── Save generated content + finalize lecture ─────────────────
    if current_step == "done":
        gc = state.get("generated_content") or {}

        type_to_key = {
            ContentType.SCRIPT:          "script",
            ContentType.WORKSHEET:       "worksheet",
            ContentType.QUIZ:            "quiz",
            ContentType.SUMMARY:         "summary",
            ContentType.KNOWLEDGE_GRAPH: "knowledge_graph",
        }

        for content_type, gc_key in type_to_key.items():
            paths = gc.get(gc_key)
            if not paths:
                continue

            already = db.exec(
                select(GeneratedContent).where(
                    GeneratedContent.lecture_id   == lecture.lecture_id,
                    GeneratedContent.content_type == content_type,
                )
            ).first()
            if already:
                continue

            primary_path = (
                paths.get("txt")           or
                paths.get("pdf")           or
                paths.get("questions_pdf") or
                paths.get("quiz_pdf")      or
                paths.get("html")          or
                paths.get("script_path")   or
                next((v for v in paths.values() if v), None)
            )

            if not primary_path:
                print(f"[sync] ⚠ no primary path for {gc_key}: {paths}")
                continue

            answers_path = (
                paths.get("answers_pdf") or
                paths.get("answer_pdf")  or
                paths.get("answers")
            )

            extra_path = (
                paths.get("mmd")  or
                paths.get("json") or
                paths.get("extra")
            )

            print(f"[sync] saving {gc_key} → {primary_path}")
            db.add(GeneratedContent(
                lecture_id   = lecture.lecture_id,
                content_type = content_type,
                file_path    = primary_path,
                answers_path = answers_path,
                extra_path   = extra_path,
            ))

        # Upload approved PDF to Drive for generated lectures
        if (
            lecture.lecture_type == LectureType.GENERATED
            and lecture_paths.get("pdf")
            and not lecture.final_content
        ):
            pdf_path = lecture_paths["pdf"]
            filename = f"{lecture.course_code}_{lecture.title}_approved.pdf"
            await _upload_to_drive(pdf_path, filename, lecture, db)

        lecture.status = LectureStatus.DRAFT

    elif current_step == "failed":
        lecture.status = LectureStatus.FAILED

    db.add(agent_session)
    db.add(lecture)
    db.commit()


async def _background_sync_loop(
    session_id: int,
    thread_id:  str,
    db_factory,
) -> None:
    """
    Polls agent state every 10 seconds in the background.
    Ensures DB is synced even if teacher never calls /status.
    Stops when terminal state is reached.
    """
    terminal = {"done", "failed"}

    while True:
        await asyncio.sleep(60)

        try:
            state = await get_agent_state(thread_id)
            if not state:
                continue

            current_step = state.get("current_step")

            # Open a fresh Session for background task
            with Session(db_factory) as db:
                agent_session = db.exec(
                    select(AgentSession).where(AgentSession.id == session_id)
                ).first()
                if not agent_session:
                    print(f"[background_sync] session {session_id} not found — stopping")
                    break

                lecture = db.get(Lecture, agent_session.lecture_id)
                if not lecture:
                    print(f"[background_sync] lecture not found — stopping")
                    break

                await _sync_state_to_db(agent_session, lecture, state, db)

            if current_step in terminal:
                print(f"[background_sync] session {session_id} → {current_step} — stopping")
                break

        except Exception as e:
            print(f"[background_sync] error for session {session_id}: {e}")
            continue


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_generated_session(
    body:    StartGeneratedRequest,
    db:      Session = Depends(get_session),
    teacher: User    = Depends(get_current_teacher),
):
    """Start a generated lecture session."""
    lecture = Lecture(
        title        = body.title,
        teacher_id   = teacher.user_id,
        course_code  = body.course_code,
        lecture_type = LectureType.GENERATED,
        status       = LectureStatus.DRAFT,
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)

    resource_rows = []
    for r in body.resources:
        row = Resource(
            lecture_id    = lecture.lecture_id,
            resource_type = r.resource_type,
            file_path     = r.file_path,
            query         = r.query,
        )
        db.add(row)
        resource_rows.append(row)
    db.commit()

    thread_id     = str(uuid.uuid4())
    agent_session = AgentSession(
        lecture_id = lecture.lecture_id,
        thread_id  = thread_id,
        status     = AgentStatus.STARTING,
    )
    db.add(agent_session)
    db.commit()
    db.refresh(agent_session)

    initial_state = await _build_agent_state(
        lecture, resource_rows,
        agent_session.id, thread_id,
    )

    await start_agent(thread_id, initial_state)

    agent_session.status = AgentStatus.GENERATING_LECTURE
    db.add(agent_session)
    db.commit()

    asyncio.create_task(
        _background_sync_loop(
            session_id = agent_session.id,
            thread_id  = thread_id,
            db_factory = engine,
        )
    )

    return {
        "session_id": agent_session.id,
        "lecture_id": lecture.lecture_id,
        "thread_id":  thread_id,
        "status":     "started",
    }


@router.post("/start-prepared/{lecture_id}")
async def start_prepared_session(
    lecture_id: int,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    """Start content generation for an existing prepared lecture."""
    lecture = db.get(Lecture, lecture_id)

    if not lecture:
        raise HTTPException(404, "Lecture not found")
    if lecture.teacher_id != teacher.user_id:
        raise HTTPException(403, "Not your lecture")
    if lecture.lecture_type != LectureType.PREPARED:
        raise HTTPException(400, "Use /start for generated lectures")
    if not lecture.final_content:
        raise HTTPException(400, "Lecture has no file — upload first")

    existing = db.exec(
        select(AgentSession).where(AgentSession.lecture_id == lecture_id)
    ).first()
    if existing:
        if existing.status == AgentStatus.DONE:
            raise HTTPException(400, "Content already generated for this lecture")
        if existing.status not in (AgentStatus.FAILED,):
            raise HTTPException(400, f"Session already active: {existing.status}")

    prepared_text = await _extract_from_drive(lecture.final_content)

    if not prepared_text:
        raise HTTPException(422, "Could not extract text from lecture file")

    print(f"[sessions] extracted {len(prepared_text):,} chars for lecture {lecture_id}")

    thread_id     = str(uuid.uuid4())
    agent_session = AgentSession(
        lecture_id = lecture.lecture_id,
        thread_id  = thread_id,
        status     = AgentStatus.GENERATING_CONTENT,
    )
    db.add(agent_session)
    db.commit()
    db.refresh(agent_session)

    output_dir    = str(Path(settings.OUTPUTS_DIR) / str(lecture.lecture_id))
    initial_state = {
        "meta": {
            "session_id":  str(agent_session.id),
            "teacher_id":  str(lecture.teacher_id),
            "course_code": lecture.course_code,
            "title":       lecture.title,
            "output_dir":  output_dir,
        },
        "source": {
            "type":          "prepared_lecture",
            "prepared_text": prepared_text,
            "pdf":     None, "docx": None, "pptx":    None,
            "audio":   None, "video": None, "website": None,
            "images":  None,
        },
        "final_lecture":    prepared_text,
        "lecture_paths":    None,
        "lecture_approval": None,
        "generated_content": {
            "script": None, "worksheet": None, "quiz": None,
            "summary": None, "flowchart": None, "knowledge_graph": None,
        },
        "current_step": "starting",
        "error":        None,
    }

    await start_agent(thread_id, initial_state)

    asyncio.create_task(
        _background_sync_loop(
            session_id = agent_session.id,
            thread_id  = thread_id,
            db_factory = engine,
        )
    )

    return {
        "session_id": agent_session.id,
        "lecture_id": lecture.lecture_id,
        "thread_id":  thread_id,
        "status":     "started",
    }


@router.get("/{session_id}/status")
async def get_status(
    session_id: int,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    agent_session, lecture = _get_session_or_404(session_id, db, teacher)

    state = await get_agent_state(agent_session.thread_id)

    if state:
        await _sync_state_to_db(agent_session, lecture, state, db)

    # Checkpoint is always accurate now — no priority fallback needed
    current_step = state.get("current_step") if state else agent_session.status.value

    latest_version = db.exec(
        select(LectureVersion)
        .where(LectureVersion.lecture_id == lecture.lecture_id)
        .order_by(LectureVersion.version_number.desc())
    ).first()

    return {
        "session_id":      session_id,
        "lecture_id":      lecture.lecture_id,
        "current_step":    current_step,
        "approval_status": state.get("approval_status") if state else None,
        "iteration":       state.get("iteration", 0)    if state else 0,
        "max_iterations":  state.get("max_iterations", 3) if state else 3,
        "lecture_version": {
            "version_number": latest_version.version_number,
            "pdf_path":       latest_version.pdf_path,
            "status":         latest_version.status,
        } if latest_version else None,
        "error": state.get("error") if state else None,
    }


@router.get("/{session_id}/stream")
async def stream_status(
    session_id: int,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    """SSE endpoint — Flutter connects here for real-time updates."""
    agent_session, lecture = _get_session_or_404(session_id, db, teacher)
    thread_id = agent_session.thread_id

    async def event_generator():
        terminal = {"awaiting_approval", "done", "failed"}
        while True:
            state = await get_agent_state(thread_id)
            if state:
                await _sync_state_to_db(agent_session, lecture, state, db)
                payload = {
                    "current_step":    state.get("current_step"),
                    "approval_status": state.get("approval_status"),
                    "iteration":       state.get("iteration", 0),
                    "lecture_paths":   state.get("lecture_paths"),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                if state.get("current_step") in terminal:
                    break
            await asyncio.sleep(1.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{session_id}/approve")
async def approve_lecture(
    session_id: int,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    """Teacher approves the generated lecture."""
    agent_session, lecture = _get_session_or_404(session_id, db, teacher)

    state     = await get_agent_state(agent_session.thread_id)
    iteration = state.get("iteration", 0) if state else 0

    version = db.exec(
        select(LectureVersion).where(
            LectureVersion.lecture_id     == lecture.lecture_id,
            LectureVersion.version_number == max(iteration, 1),
        )
    ).first()

    if version:
        version.status = VersionStatus.APPROVED
        db.add(version)

    agent_session.status     = AgentStatus.GENERATING_CONTENT
    agent_session.updated_at = datetime.utcnow()
    db.add(agent_session)
    db.commit()

    await resume_agent(agent_session.thread_id, status="approved")

    return {"status": "approved", "session_id": session_id}

@router.post("/{session_id}/reject")
async def reject_lecture(
    session_id: int,
    body:       RejectRequest,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    agent_session, lecture = _get_session_or_404(session_id, db, teacher)

    state     = await get_agent_state(agent_session.thread_id)
    iteration = state.get("iteration", 0) if state else 0

    print(f"[reject] iteration={iteration} looking for version {max(iteration, 1)}")

    version = db.exec(
        select(LectureVersion).where(
            LectureVersion.lecture_id     == lecture.lecture_id,
            LectureVersion.version_number == max(iteration, 1),
        )
    ).first()

    print(f"[reject] found version: {version}")

    if version:
        version.status           = VersionStatus.REJECTED
        version.teacher_feedback = body.feedback
        db.add(version)

    agent_session.status     = AgentStatus.REGENERATING
    agent_session.updated_at = datetime.utcnow()
    db.add(agent_session)
    db.commit()    # ← this commits BOTH version update AND agent_session update

    print(f"[reject] committed — agent_session status = REGENERATING")

    await resume_agent(
        agent_session.thread_id,
        status   = "rejected",
        feedback = body.feedback,
    )

    return {"status": "rejected", "session_id": session_id}


@router.get("/{session_id}/content")
async def get_content(
    session_id: int,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    """Return all generated content for a completed session."""
    agent_session, lecture = _get_session_or_404(session_id, db, teacher)

    content_rows = db.exec(
        select(GeneratedContent).where(
            GeneratedContent.lecture_id == lecture.lecture_id
        )
    ).all()

    if not content_rows:
        raise HTTPException(425, "Content not ready yet")

    return {
        "lecture_id": lecture.lecture_id,
        "content": [
            {
                "type":         row.content_type,
                "file_path":    row.file_path,
                "answers_path": row.answers_path,
                "extra_path":   row.extra_path,
            }
            for row in content_rows
        ],
    }


@router.get("/{session_id}/script")
async def get_script_path(
    session_id: int,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    """Returns script file path for TTS pipeline."""
    agent_session, lecture = _get_session_or_404(session_id, db, teacher)

    script = db.exec(
        select(GeneratedContent).where(
            GeneratedContent.lecture_id   == lecture.lecture_id,
            GeneratedContent.content_type == ContentType.SCRIPT,
        )
    ).first()

    if not script:
        raise HTTPException(404, "Script not generated yet")

    return {
        "lecture_id":  lecture.lecture_id,
        "script_path": script.file_path,
    }


@router.get("/{session_id}/lecture-pdf")
async def get_lecture_pdf(
    session_id: int,
    db:         Session = Depends(get_session),
    teacher:    User    = Depends(get_current_teacher),
):
    """
    Stream the latest generated lecture PDF to Flutter.
    Called when current_step = awaiting_approval.
    """
    agent_session, lecture = _get_session_or_404(session_id, db, teacher)

    latest_version = db.exec(
        select(LectureVersion)
        .where(LectureVersion.lecture_id == lecture.lecture_id)
        .order_by(LectureVersion.version_number.desc())
    ).first()

    if not latest_version or not latest_version.pdf_path:
        raise HTTPException(404, "No lecture PDF available yet")

    pdf_path = Path(latest_version.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(404, f"PDF file not found on disk: {pdf_path}")

    return FileResponse(
        path       = str(pdf_path),
        media_type = "application/pdf",
        filename   = f"lecture_v{latest_version.version_number}.pdf",
    )