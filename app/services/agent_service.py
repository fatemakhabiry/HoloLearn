# app/services/agent_service.py
#
# Shared agent state sync logic.
# Lives in the service layer so both the endpoint (sessions.py)
# and the ARQ task (session_tasks_arq.py) can import it without
# creating a circular endpoint → task → endpoint import chain.

from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.models.agent_session import AgentSession, AgentStatus
from app.models.lecture import Lecture, LectureStatus, LectureType
from app.models.lecture_version import LectureVersion, VersionStatus
from app.models.generated_content import GeneratedContent, ContentType


async def sync_state_to_db(
    agent_session: AgentSession,
    lecture:       Lecture,
    state:         dict,
    db:            Session,
) -> None:
    """
    Sync LangGraph agent state into Postgres.

    Called by:
      • sessions.py  → _sync_state_to_db shim  (HTTP request path)
      • session_tasks_arq.py → sync_agent_state (ARQ background job)

    Handles:
      • AgentSession.status  mirror
      • LectureVersion upsert with priority guard (no status downgrades)
      • GeneratedContent rows written once on 'done'
      • Google Drive upload of approved PDF on 'done'
      • Lecture.status transitions
    """
    current_step  = state.get("current_step")
    lecture_paths = state.get("lecture_paths") or {}
    approval      = state.get("lecture_approval") or {}

    # ── Mirror current_step → AgentSession.status ──────────────────
    try:
        agent_session.status = AgentStatus(current_step)
    except ValueError:
        pass  # unknown step string — leave status unchanged

    agent_session.updated_at = datetime.utcnow()

    # ── Upsert LectureVersion ──────────────────────────────────────
    # Only for generated lectures that have produced a txt output
    if lecture_paths.get("txt") and lecture.lecture_type == LectureType.GENERATED:

        existing_versions = db.exec(
            select(LectureVersion).where(
                LectureVersion.lecture_id == lecture.lecture_id
            )
        ).all()

        # Match on pdf_path so we don't create duplicate version rows
        # when the same lecture is synced multiple times in the same state
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
            # Priority guard — never downgrade a version's status
            version_priority = {"pending": 0, "rejected": 1, "approved": 2}
            current_p = version_priority.get(
                existing.status.value if hasattr(existing.status, "value")
                else str(existing.status), 0
            )
            new_p = version_priority.get(
                version_status.value if hasattr(version_status, "value")
                else str(version_status), 0
            )

            if new_p >= current_p:
                existing.status           = version_status
                existing.teacher_feedback = approval.get("teacher_feedback")
                db.add(existing)
            else:
                print(
                    f"[sync] skipping version status downgrade: "
                    f"{version_status} < {existing.status}"
                )

    # ── On 'done': write GeneratedContent rows + Drive upload ──────
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

            # Idempotent — skip if already written
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

        # Upload approved PDF to Drive once
        if (
            lecture.lecture_type == LectureType.GENERATED
            and lecture_paths.get("pdf")
            and not lecture.final_content
        ):
            pdf_path = lecture_paths["pdf"]
            filename = f"{lecture.course_code}_{lecture.title}_approved.pdf"
            # Import lazily to avoid circular imports with the lecture endpoint
            from app.api.v1.endpoints.sessions import _upload_to_drive
            await _upload_to_drive(pdf_path, filename, lecture, db)

        lecture.status = LectureStatus.DRAFT

    elif current_step == "failed":
        lecture.status = LectureStatus.FAILED

    db.add(agent_session)
    db.add(lecture)
    db.commit()