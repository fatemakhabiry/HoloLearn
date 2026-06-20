# app/workers/qa_export_worker.py

import logging
from datetime import datetime
from pathlib import Path
from sqlmodel import Session, select

from app.core.database import engine
from app.models.qa_export import QAExport, ExportStatus

logger = logging.getLogger(__name__)


async def cleanup_expired_qa_exports(ctx: dict) -> None:
    """
    ARQ cron job — runs hourly.
    Deletes expired QA export PDF files from disk and marks rows EXPIRED.
    """
    with Session(engine) as session:
        expired = session.exec(
            select(QAExport).where(
                QAExport.status     == ExportStatus.READY,
                QAExport.expires_at <= datetime.utcnow(),
            )
        ).all()

        if not expired:
            return

        count = 0
        for export in expired:
            if export.file_path:
                try:
                    Path(export.file_path).unlink(missing_ok=True)
                except OSError as e:
                    logger.warning(f"[QAExportCleanup] Failed to delete {export.file_path}: {e}")

            export.status = ExportStatus.EXPIRED
            session.add(export)
            count += 1

        session.commit()
        logger.info(f"[QAExportCleanup] Cleaned up {count} expired export(s)")