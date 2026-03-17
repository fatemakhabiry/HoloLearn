import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.pdfgen import canvas as rl_canvas

from Config import (
    SLIDE_WIDTH, SLIDE_HEIGHT, SLIDE_SIZE,
    SLIDE_MARGIN_H, SLIDE_MARGIN_T, SLIDE_MARGIN_B,
    IMAGE_COL_RATIO, IMAGE_COL_GAP,
)
from Helpers import fix_latex, make_rl_image


# Style setup

def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Normal'],
        fontSize=32, textColor=colors.white,
        spaceAfter=16, alignment=TA_CENTER,
        fontName='Helvetica-Bold', leading=40,
    ))
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        parent=styles['Normal'],
        fontSize=14, textColor=colors.HexColor('#bbdefb'),
        spaceAfter=8, alignment=TA_CENTER,
        fontName='Helvetica', leading=18,
    ))
    styles.add(ParagraphStyle(
        name='SlideTitle',
        parent=styles['Normal'],
        fontSize=20, textColor=colors.white,
        spaceAfter=0, spaceBefore=0,
        fontName='Helvetica-Bold', leading=26,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name='SlideBody',
        parent=styles['BodyText'],
        fontSize=14, textColor=colors.HexColor('#1a1a2e'),
        alignment=TA_JUSTIFY, spaceAfter=6, leading=14,
    ))
    styles.add(ParagraphStyle(
        name='SlideBullet',
        parent=styles['BodyText'],
        fontSize=14, textColor=colors.HexColor('#1a1a2e'),
        leftIndent=14, spaceAfter=5, leading=14,
    ))
    styles.add(ParagraphStyle(
        name='SlideObjective',
        parent=styles['BodyText'],
        fontSize=12, textColor=colors.HexColor('#0d47a1'),
        leftIndent=14, spaceAfter=5, leading=14,
    ))
    styles.add(ParagraphStyle(
        name='EquationStyle',
        parent=styles['BodyText'],
        fontSize=12, textColor=colors.HexColor('#000000'),
        leftIndent=20, rightIndent=20,
        spaceAfter=6, spaceBefore=6,
        alignment=TA_LEFT,
        backColor=colors.HexColor('#f5f5f5'),
        borderPadding=6, wordWrap='CJK',
    ))
    styles.add(ParagraphStyle(
        name='DerivationStyle',
        parent=styles['BodyText'],
        fontSize=12, textColor=colors.HexColor('#1a237e'),
        leftIndent=20, rightIndent=20,
        spaceAfter=6, spaceBefore=6,
        alignment=TA_LEFT,
        backColor=colors.HexColor('#e8eaf6'),
        borderPadding=8, wordWrap='CJK',
    ))
    styles.add(ParagraphStyle(
        name='ExampleCardTitle',
        parent=styles['Normal'],
        fontSize=12, textColor=colors.HexColor('#0d47a1'),
        fontName='Helvetica-Bold',
        spaceAfter=5, spaceBefore=0, leading=15,
    ))
    styles.add(ParagraphStyle(
        name='ExampleCardBody',
        parent=styles['BodyText'],
        fontSize=12, textColor=colors.HexColor('#1a237e'),
        spaceAfter=4, spaceBefore=0, leading=13,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name='ExampleCardBullet',
        parent=styles['BodyText'],
        fontSize=12, textColor=colors.HexColor('#263238'),
        leftIndent=14, spaceAfter=3, spaceBefore=0, leading=13,
    ))
    styles.add(ParagraphStyle(
        name='ReviewQ',
        parent=styles['BodyText'],
        fontSize=10, textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=8, leading=14,
    ))
    styles.add(ParagraphStyle(
        name='MiscStyle',
        parent=styles['BodyText'],
        fontSize=12, textColor=colors.HexColor('#4a0000'),
        leftIndent=10, rightIndent=10,
        spaceAfter=7, leading=13,
        backColor=colors.HexColor('#fff3e0'),
        borderPadding=6,
    ))
    styles.add(ParagraphStyle(
        name='TOCItem',
        parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#1a237e'),
        spaceAfter=6, leading=16,
    ))
    styles.add(ParagraphStyle(
        name='SectionHeading',
        parent=styles['Normal'],
        fontSize=16, textColor=colors.HexColor('#283593'),
        spaceAfter=8, spaceBefore=8, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        name='SubsectionHeading',
        parent=styles['Normal'],
        fontSize=12, textColor=colors.HexColor('#3949ab'),
        spaceAfter=6, spaceBefore=6, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['BodyText'],
        fontSize=12, textColor=colors.HexColor('#1a1a2e'),
        alignment=TA_JUSTIFY, spaceAfter=6, leading=14,
    ))

    return styles


# SlideBuilder

# Palette
_ACCENT      = colors.HexColor('#1a237e')
_ACCENT_LITE = colors.HexColor('#3949ab')
_BG_SLIDE    = colors.HexColor('#f0f4ff')
_BG_COVER    = colors.HexColor('#0d1b5e')
_GOLD        = colors.HexColor('#ffd54f')


class SlideBuilder:
    """All ReportLab / canvas slide-generation logic."""

    def __init__(self):
        self.styles = build_styles()

    # LaTeX-aware text → flowables

    def text_to_flowables(self, text: str, max_img_width: float = 340) -> List:
        flowables = []
        lines = text.split('\n')
        paragraph_buffer: List[str] = []

        def flush_paragraph():
            if paragraph_buffer:
                combined = ' '.join(paragraph_buffer).strip()
                if combined:
                    flowables.extend(self._render_inline_math_paragraph(combined, max_img_width))
                paragraph_buffer.clear()

        for line in lines:
            stripped = line.strip()
            display_match = re.match(r'^\$\$(.+?)\$\$$', stripped, re.DOTALL)
            if display_match:
                flush_paragraph()
                img = make_rl_image(display_match.group(1), max_width_pts=max_img_width)
                if img:
                    flowables.append(Spacer(1, 3))
                    flowables.append(img)
                    flowables.append(Spacer(1, 3))
                else:
                    cleaned = fix_latex(display_match.group(1))
                    flowables.append(Paragraph(
                        '<font name="Courier" size="8">' + cleaned + '</font>',
                        self.styles['EquationStyle']
                    ))
                continue

            lone_inline = re.match(r'^\$([^$]+)\$$', stripped)
            if lone_inline and stripped.count('$') == 2:
                flush_paragraph()
                img = make_rl_image(lone_inline.group(1), max_width_pts=max_img_width)
                if img:
                    flowables.append(Spacer(1, 3))
                    flowables.append(img)
                    flowables.append(Spacer(1, 3))
                else:
                    cleaned = fix_latex(lone_inline.group(1))
                    flowables.append(Paragraph(
                        '<font name="Courier" size="8">' + cleaned + '</font>',
                        self.styles['EquationStyle']
                    ))
                continue

            if not stripped:
                flush_paragraph()
                continue

            paragraph_buffer.append(stripped)

        flush_paragraph()
        return flowables if flowables else [Paragraph(text, self.styles['SlideBody'])]

    def _render_inline_math_paragraph(self, text: str, max_img_width: float) -> List:
        if '$' not in text:
            return [Paragraph(text, self.styles['SlideBody'])]
        parts = re.split(r'(\$[^$]+\$)', text)
        flowables = []
        prose_buf: List[str] = []

        def flush_prose():
            if prose_buf:
                chunk = ' '.join(prose_buf).strip()
                if chunk:
                    flowables.append(Paragraph(chunk, self.styles['SlideBody']))
                prose_buf.clear()

        for part in parts:
            if re.match(r'^\$[^$]+\$$', part):
                inner = part[1:-1].strip()
                img = make_rl_image(inner, max_width_pts=min(max_img_width, 260))
                if img:
                    flush_prose()
                    flowables.append(img)
                else:
                    prose_buf.append(fix_latex(inner))
            else:
                if part.strip():
                    prose_buf.append(part.strip())

        flush_prose()
        return flowables if flowables else [Paragraph(text, self.styles['SlideBody'])]

    # Low-level canvas helpers

    def _content_frame(self):
        """Return (x, y, w, h) of the usable content area below the title bar."""
        bar_h    = 0.72 * inch
        footer_h = 0.28 * inch
        x = SLIDE_MARGIN_H
        y = footer_h + SLIDE_MARGIN_B
        w = SLIDE_WIDTH  - 2 * SLIDE_MARGIN_H
        h = SLIDE_HEIGHT - bar_h - 3 - footer_h - SLIDE_MARGIN_B - SLIDE_MARGIN_T * 0.3
        return x, y, w, h

    def _draw_slide_background(self, c: rl_canvas.Canvas, title: str, slide_type: str = "content"):
        W, H = SLIDE_WIDTH, SLIDE_HEIGHT
        if slide_type == "cover":
            c.setFillColor(_BG_COVER)
            c.rect(0, 0, W, H, fill=1, stroke=0)
            c.setFillColor(_GOLD)
            c.rect(0, H * 0.38, W, 4, fill=1, stroke=0)
            return

        c.setFillColor(_BG_SLIDE)
        c.rect(0, 0, W, H, fill=1, stroke=0)

        bar_h = 0.72 * inch
        c.setFillColor(_ACCENT)
        c.rect(0, H - bar_h, W, bar_h, fill=1, stroke=0)
        c.setFillColor(_GOLD)
        c.rect(0, H - bar_h - 3, W, 3, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(SLIDE_MARGIN_H, H - bar_h + 0.18 * inch, title)
        c.setFillColor(_ACCENT)
        c.rect(0, 0, W, 0.28 * inch, fill=1, stroke=0)

    def _begin_slide(self, c: rl_canvas.Canvas, title: str, slide_type: str = "content"):
        self._draw_slide_background(c, title, slide_type)

    def _end_slide(self, c: rl_canvas.Canvas, page_num: int):
        c.setFillColor(colors.HexColor('#bbdefb'))
        c.setFont("Helvetica", 8)
        c.drawRightString(SLIDE_WIDTH - 0.2 * inch, 0.08 * inch, str(page_num))
        c.showPage()

    # Generic flowable renderer (lazy – never emits a blank slide)

    def render_flowables_on_slide(
        self,
        c: rl_canvas.Canvas,
        flowables: List,
        page_num_ref: List[int],
        slide_title: str,
        slide_type: str = "content",
        start_fresh: bool = True,
    ) -> int:
        if not flowables:
            return 0

        x, y, w, h = self._content_frame()
        slides_used  = 0
        slide_open   = False
        cursor_y     = y + h
        title_for_page = slide_title

        def open_slide():
            nonlocal slide_open, cursor_y, slides_used, title_for_page
            self._begin_slide(c, title_for_page, slide_type)
            slide_open = True
            slides_used += 1
            cursor_y = y + h
            title_for_page = slide_title + " (cont.)"

        def close_slide():
            nonlocal slide_open
            if slide_open:
                self._end_slide(c, page_num_ref[0])
                page_num_ref[0] += 1
                slide_open = False

        for fl in flowables:
            try:
                fl.canv = c
                needed_w, needed_h = fl.wrap(w, h)
            except Exception:
                needed_w, needed_h = w, 20

            if needed_h <= 0:
                if slide_open:
                    cursor_y -= needed_h + 2
                continue

            if not slide_open:
                open_slide()

            if needed_h > (cursor_y - y):
                close_slide()
                open_slide()

            try:
                fl.drawOn(c, x, cursor_y - needed_h)
            except Exception:
                pass
            cursor_y -= needed_h + 2

            if cursor_y < y + 4:
                close_slide()

        close_slide()
        return slides_used

    # Individual slide-type builders

    def draw_cover_slide(self, c: rl_canvas.Canvas, lecture_data: Dict, page_num_ref: List[int]):
        W, H = SLIDE_WIDTH, SLIDE_HEIGHT
        self._begin_slide(c, "", "cover")

        title = lecture_data.get("title", "Lecture Notes")
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 28)
        words = title.split()
        lines, cur = [], []
        for w in words:
            test = ' '.join(cur + [w])
            if c.stringWidth(test, "Helvetica-Bold", 28) > W - 1.4 * inch:
                lines.append(' '.join(cur))
                cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(' '.join(cur))

        line_h  = 36
        start_y = H * 0.70
        for i, ln in enumerate(lines):
            c.drawCentredString(W / 2, start_y - i * line_h, ln)

        c.setFillColor(colors.HexColor('#bbdefb'))
        c.setFont("Helvetica", 13)
        c.drawCentredString(W / 2, H * 0.40, "Comprehensive Lecture Notes")

        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor('#90caf9'))
        c.drawCentredString(W / 2, H * 0.32, datetime.now().strftime('%B %d, %Y'))

        c.setFillColor(_ACCENT_LITE)
        c.rect(0, 0, W, 0.28 * inch, fill=1, stroke=0)

        self._end_slide(c, page_num_ref[0])
        page_num_ref[0] += 1

    def draw_toc_slide(self, c: rl_canvas.Canvas, lecture_data: Dict, page_num_ref: List[int]):
        toc_items = ["Learning Objectives", "Introduction"]
        for i, s in enumerate(lecture_data.get("main_sections", []), 1):
            toc_items.append(f"{i}. {s['title']}")
        if lecture_data.get("mathematical_derivations", "").strip():
            toc_items.append("Mathematical Derivations")
        if lecture_data.get("real_world_examples"):
            toc_items.append("Real-World Examples")
        if lecture_data.get("misconceptions"):
            toc_items.append("Common Misconceptions")
        if lecture_data.get("summary"):
            toc_items.append("Summary & Key Takeaways")
        if lecture_data.get("review_questions"):
            toc_items.append("Review Questions")

        flowables = []
        for item in toc_items:
            flowables.append(Paragraph("• " + item, self.styles['TOCItem']))
            flowables.append(Spacer(1, 2))

        self.render_flowables_on_slide(c, flowables, page_num_ref, "Table of Contents")

    def draw_objectives_slide(self, c: rl_canvas.Canvas, objectives: List[str], page_num_ref: List[int]):
        flowables = []
        for i, obj in enumerate(objectives, 1):
            flowables.append(Paragraph(f"{i}. {obj}", self.styles['SlideObjective']))
            flowables.append(Spacer(1, 3))
        self.render_flowables_on_slide(c, flowables, page_num_ref, "Learning Objectives")

    def draw_section_slides(self, c: rl_canvas.Canvas, section: Dict, number: int, page_num_ref: List[int]):
        title     = f"{number}. {section['title']}"
        flowables = self.text_to_flowables(section['content'])
        self.render_flowables_on_slide(c, flowables, page_num_ref, title)

    def draw_section_slides_with_image(
        self,
        c: rl_canvas.Canvas,
        section: Dict,
        number: int,
        page_num_ref: List[int],
        image_path: str,
        image_caption: str = "",
    ):
        """
        Render a section slide with text on the LEFT and a user image on the RIGHT.

        The image panel is drawn only on the FIRST slide.  Continuation slides
        (when text overflows) use the full content width — no empty right column.

        Layout of the first slide
        ┌─────────────────────────┬──────────────────────┐
        │  text column            │  image column        │
        │  (1-IMAGE_COL_RATIO)    │  IMAGE_COL_RATIO     │
        │  of content width       │  of content width    │
        └─────────────────────────┴──────────────────────┘
                                  ↑ IMAGE_COL_GAP gap
        """
        from PIL import Image as PILImage
        from reportlab.lib import colors as _colors

        title = f"{number}. {section['title']}"
        cx, cy, cw, ch = self._content_frame()

        # ── Column widths ──────────────────────────────────────────────
        img_col_w  = cw * IMAGE_COL_RATIO
        text_col_w = cw - img_col_w - IMAGE_COL_GAP

        # ── Load & scale the image to fit the right column ─────────────
        img_rl      = None
        img_draw_w  = img_col_w
        img_draw_h  = ch
        try:
            pil_img = PILImage.open(image_path)
            px_w, px_h = pil_img.size
            scale = img_col_w / (px_w * 72 / 96)
            natural_h = px_h * 72 / 96 * scale
            if natural_h > ch:
                scale      = ch / (px_h * 72 / 96)
                img_draw_w = px_w * 72 / 96 * scale
                img_draw_h = ch
            else:
                img_draw_w = img_col_w
                img_draw_h = natural_h
            img_rl = RLImage(image_path, width=img_draw_w, height=img_draw_h)
        except Exception as e:
            print(f"[WARN] Could not load image '{image_path}': {e}")

        # ── Slide lifecycle ─────────────────────────────────────────────
        slides_used    = 0
        slide_open     = False
        title_for_page = title

        def open_slide():
            nonlocal slide_open, slides_used, title_for_page
            self._begin_slide(c, title_for_page)
            slide_open    = True
            slides_used  += 1
            title_for_page = title + " (cont.)"

        def close_slide():
            nonlocal slide_open
            if slide_open:
                self._end_slide(c, page_num_ref[0])
                page_num_ref[0] += 1
                slide_open = False

        # ── Build text flowables ────────────────────────────────────────
        # First slide uses the narrower text column; continuation slides use
        # the full content width (no image panel there).
        flowables_first = self.text_to_flowables(section['content'], max_img_width=int(text_col_w))
        flowables_cont  = self.text_to_flowables(section['content'], max_img_width=int(cw))

        # We render in two passes:
        #   Pass 1 – fit as much as possible into the first slide's text column.
        #   Pass 2 – any overflow goes onto continuation slides at full width.

        # ── Pass 1: first slide ─────────────────────────────────────────
        open_slide()

        # Draw image panel on the first slide only
        img_x = cx + text_col_w + IMAGE_COL_GAP
        c.setFillColor(_colors.HexColor('#dce8f8'))
        c.rect(img_x - 4, cy, img_col_w + 8, ch, fill=1, stroke=0)

        if img_rl:
            img_y         = cy + (ch - img_draw_h) / 2
            img_x_centred = img_x + (img_col_w - img_draw_w) / 2
            try:
                img_rl.drawOn(c, img_x_centred, img_y)
            except Exception as e:
                print(f"[WARN] Could not draw image on slide: {e}")

            if image_caption:
                cap_y = img_y - 14
                if cap_y > cy:
                    c.setFillColor(_colors.HexColor('#37474f'))
                    c.setFont("Helvetica-Oblique", 7)
                    cap = image_caption if len(image_caption) <= 55 else image_caption[:52] + "…"
                    c.drawCentredString(img_x + img_col_w / 2, cap_y, cap)

        # Render flowables into the LEFT column of the first slide.
        # Track which flowables didn't fit so we can overflow them.
        cursor_y  = cy + ch
        overflow_start = 0   # index into flowables_first where overflow begins

        for idx, fl in enumerate(flowables_first):
            try:
                fl.canv = c
                needed_w, needed_h = fl.wrap(text_col_w, ch)
            except Exception:
                needed_w, needed_h = text_col_w, 20

            if needed_h <= 0:
                overflow_start = idx + 1
                continue

            if needed_h > (cursor_y - cy):
                # This flowable doesn't fit — everything from here is overflow
                overflow_start = idx
                break

            try:
                fl.drawOn(c, cx, cursor_y - needed_h)
            except Exception:
                pass
            cursor_y -= needed_h + 2
            overflow_start = idx + 1   # everything up to here fitted

        close_slide()

        # ── Pass 2: overflow onto continuation slides (full width) ──────
        overflow_flowables = flowables_cont[overflow_start:]
        if overflow_flowables:
            self.render_flowables_on_slide(
                c, overflow_flowables, page_num_ref,
                title + " (cont.)",
            )

    def draw_derivations_slides(self, c: rl_canvas.Canvas, derivations: str, page_num_ref: List[int]):
        flowables = self.text_to_flowables(derivations)
        self.render_flowables_on_slide(c, flowables, page_num_ref, "Mathematical Derivations")

    def draw_introduction_slides(self, c: rl_canvas.Canvas, intro: str, page_num_ref: List[int]):
        flowables = self.text_to_flowables(intro)
        self.render_flowables_on_slide(c, flowables, page_num_ref, "Introduction")

    def draw_misconceptions_slides(self, c: rl_canvas.Canvas, misconceptions: List[str], page_num_ref: List[int]):
        flowables = []
        for i, misc in enumerate(misconceptions, 1):
            flowables.append(Paragraph(f"⚠  Misconception {i}: {misc}", self.styles['MiscStyle']))
            flowables.append(Spacer(1, 4))
        self.render_flowables_on_slide(c, flowables, page_num_ref, "Common Misconceptions")

    def draw_summary_slides(self, c: rl_canvas.Canvas, summary: str, page_num_ref: List[int]):
        flowables = self.text_to_flowables(summary)
        self.render_flowables_on_slide(c, flowables, page_num_ref, "Summary & Key Takeaways")

    def draw_questions_slides(self, c: rl_canvas.Canvas, questions: List[str], page_num_ref: List[int]):
        flowables = []
        for i, q in enumerate(questions, 1):
            flowables.append(Paragraph(f"Q{i}. {q}", self.styles['ReviewQ']))
            flowables.append(Spacer(1, 5))
        self.render_flowables_on_slide(c, flowables, page_num_ref, "Review Questions")

    def draw_examples_slides(self, c: rl_canvas.Canvas, examples: List[Dict], page_num_ref: List[int]):
        x, y_base, w, h = self._content_frame()
        slide_open     = False
        cursor_y       = y_base + h
        title_for_page = "Real-World Examples"

        def open_slide():
            nonlocal slide_open, cursor_y, title_for_page
            self._begin_slide(c, title_for_page)
            slide_open     = True
            cursor_y       = y_base + h
            title_for_page = "Real-World Examples (cont.)"

        def close_slide():
            nonlocal slide_open
            if slide_open:
                self._end_slide(c, page_num_ref[0])
                page_num_ref[0] += 1
                slide_open = False

        for example in examples:
            title   = example.get("title", "Example")
            body    = example.get("body", "")
            bullets = example.get("bullets", [])

            inner: List[Any] = []
            if title:
                inner.append(Paragraph(title, self.styles['ExampleCardTitle']))
                inner.append(Spacer(1, 4))
            if body:
                inner.append(Paragraph(body, self.styles['ExampleCardBody']))
                if bullets:
                    inner.append(Spacer(1, 4))
            for b in bullets:
                inner.append(Paragraph("• " + b, self.styles['ExampleCardBullet']))

            if not inner:
                continue

            tbl = Table([[inner]], colWidths=[w])
            tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#e3f2fd')),
                ('BOX',           (0, 0), (-1, -1), 1, colors.HexColor('#90caf9')),
                ('TOPPADDING',    (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING',   (0, 0), (-1, -1), 12),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ]))

            tbl.canv = c
            tbl_w, tbl_h = tbl.wrap(w, h)

            if not slide_open:
                open_slide()
            elif tbl_h > (cursor_y - y_base):
                close_slide()
                open_slide()

            tbl.drawOn(c, x, cursor_y - tbl_h)
            cursor_y -= tbl_h + 10

            if cursor_y < y_base + 10:
                close_slide()

        close_slide()

    # Master PDF creator

    def create_pdf(self, lecture_data: Dict[str, Any], output_path: str,
                   images: List[Dict] | None = None) -> str:
        """
        Build the slide PDF.

        Parameters
        ----------
        lecture_data : dict
            Parsed lecture structure returned by parse_lecture_response().
        output_path : str
            Destination PDF file path.
        images : list of {"path": str, "caption": str}, optional
            User-supplied images.  Each image is paired with a main-content
            section in order (images[0] → section 1, images[1] → section 2,
            etc.).  Sections that exceed the number of images are rendered
            without an image.
        """
        if images is None:
            images = []

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        c = rl_canvas.Canvas(output_path, pagesize=SLIDE_SIZE)
        c.setTitle(lecture_data.get("title", "Lecture Notes"))

        page_num_ref = [1]

        self.draw_cover_slide(c, lecture_data, page_num_ref)
        self.draw_toc_slide(c, lecture_data, page_num_ref)

        if lecture_data.get("learning_objectives"):
            self.draw_objectives_slide(c, lecture_data["learning_objectives"], page_num_ref)

        if lecture_data.get("introduction"):
            self.draw_introduction_slides(c, lecture_data["introduction"], page_num_ref)

        for i, section in enumerate(lecture_data.get("main_sections", []), 1):
            # Pair image index 0-based: section 1 → images[0], section 2 → images[1], …
            img_index = i - 1
            if img_index < len(images):
                img_info = images[img_index]
                self.draw_section_slides_with_image(
                    c, section, i, page_num_ref,
                    image_path=img_info["path"],
                    image_caption=img_info.get("caption", ""),
                )
            else:
                self.draw_section_slides(c, section, i, page_num_ref)

        if lecture_data.get("mathematical_derivations", "").strip():
            self.draw_derivations_slides(c, lecture_data["mathematical_derivations"], page_num_ref)

        if lecture_data.get("real_world_examples"):
            self.draw_examples_slides(c, lecture_data["real_world_examples"], page_num_ref)

        if lecture_data.get("misconceptions"):
            self.draw_misconceptions_slides(c, lecture_data["misconceptions"], page_num_ref)

        if lecture_data.get("summary"):
            self.draw_summary_slides(c, lecture_data["summary"], page_num_ref)

        if lecture_data.get("review_questions"):
            self.draw_questions_slides(c, lecture_data["review_questions"], page_num_ref)

        c.save()
        return output_path