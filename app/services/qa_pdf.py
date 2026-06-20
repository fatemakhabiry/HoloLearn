# app/services/qa_pdf.py

import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import List

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from app.core.config import settings
from app.models.qa_message import QAMessage, MessageRole

logger = logging.getLogger(__name__)


def build_qa_pdf(
    messages       : List[QAMessage],
    lecture_id     : int,
    student_id     : int,
    lecture_title  : str,
    student_name   : str,
) -> str:
    """
    Render a student's Q&A history for one lecture as a PDF.
    Returns the absolute path to the saved file.
    """
    export_dir = Path(settings.QA_EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    filename = f"qa_{lecture_id}_{student_id}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = export_dir / filename

    styles = getSampleStyleSheet()

    question_style = ParagraphStyle(
        "Question",
        parent=styles["Normal"],
        textColor=colors.HexColor("#1a4d8f"),
        spaceBefore=10,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    answer_style = ParagraphStyle(
        "Answer",
        parent=styles["Normal"],
        spaceBefore=2,
        spaceAfter=12,
        leftIndent=14,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        textColor=colors.grey,
        fontSize=8,
        spaceAfter=2,
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []

    # ── Header ──────────────────────────────────────────────
    story.append(Paragraph("Q&A Transcript", styles["Title"]))
    story.append(Spacer(1, 6))

    header_table = Table(
        [
            ["Lecture", lecture_title],
            ["Student", student_name],
            ["Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
            ["Total Messages", str(len(messages))],
        ],
        colWidths=[1.3 * inch, 4.5 * inch],
    )
    header_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))

    # ── Q&A pairs ───────────────────────────────────────────
    if not messages:
        story.append(Paragraph("No questions asked yet.", styles["Normal"]))
    else:
        for msg in messages:
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M")
            if msg.role == MessageRole.STUDENT:
                story.append(Paragraph(f"Q: {_escape(msg.content_text)}", question_style))
                story.append(Paragraph(timestamp, meta_style))
            else:
                story.append(Paragraph(f"A: {_escape(msg.content_text)}", answer_style))

    doc.build(story)

    logger.info(f"[QAPDF] Built PDF → {output_path}")
    return str(output_path.resolve())


def _escape(text: str) -> str:
    """Minimal XML escaping for ReportLab Paragraph (uses XML-like markup)."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )