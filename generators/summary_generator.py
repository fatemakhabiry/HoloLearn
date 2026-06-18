from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage  # fixed import path
import os
import re
from typing import Optional
from dotenv import load_dotenv


from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import Image as RLImage

import tiktoken


# ── Constants ──────────────────────────────────────────────────────────────────
_DEFAULT_MODEL      = "llama-3.3-70b-versatile"
_CHUNK_MAX_TOKENS   = 2500   # map phase: tokens per content chunk
_CHUNK_OVERLAP      = 200    # overlap between consecutive chunks
_SYNTHESIS_MAX_TOKENS = 5000  # reduce phase: combined summaries token cap
                               # (prompt template ~500 tokens + ~4500 for content)
_MAX_RETRIES          = 2     # retry attempts per LLM call


class SummaryGenerator:
    """
    Generate student-friendly summaries via map-reduce chunking.

    Map   : summarise each content chunk independently
    Reduce: synthesise all chunk summaries into one final document

    This means the full lecture is always covered regardless of length,
    and no single request ever exceeds the free-tier TPM limit.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        temperature: float = 0.5,
        max_tokens: int = 8000,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY_SUMMARY")
        if not self.api_key:
            raise ValueError(
                "No API key supplied. Pass api_key= or set GROQ_API_KEY_SUMMARY."
            )

        self.model = model
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoding = None

    # ── Token helpers ──────────────────────────────────────────────────────────

    def count_tokens(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        return max(1, len(text) // 4)

    def _encode(self, text: str):
        if self.encoding:
            return self.encoding.encode(text)
        return list(text)

    def _decode(self, tokens) -> str:
        if self.encoding:
            return self.encoding.decode(tokens)
        return "".join(tokens)

    # ── Chunking ───────────────────────────────────────────────────────────────

    def _split_into_chunks(self, text: str) -> list[str]:
        """Split text into overlapping token windows of _CHUNK_MAX_TOKENS."""
        tokens = self._encode(text)
        if len(tokens) <= _CHUNK_MAX_TOKENS:
            return [text]

        chunks, start = [], 0
        while start < len(tokens):
            end = min(start + _CHUNK_MAX_TOKENS, len(tokens))
            chunks.append(self._decode(tokens[start:end]))
            if end == len(tokens):
                break
            start += _CHUNK_MAX_TOKENS - _CHUNK_OVERLAP

        print(f"   📦 Content split into {len(chunks)} chunk(s) "
              f"({_CHUNK_MAX_TOKENS}-token windows, {_CHUNK_OVERLAP}-token overlap).")
        return chunks

    # ── Prompts ────────────────────────────────────────────────────────────────

    def _chunk_prompt(self, chunk: str, course: str, title: str) -> str:
        return f"""Summarise this section of a lecture. Extract ALL key concepts,
definitions, equations, and examples. Be thorough — nothing important should be lost.

Course: {course}
Title: {title}

CONTENT SECTION:
{chunk}

Write a structured summary using:
- DEFINITIONS: bullet points for each term defined
- KEY CONCEPTS: numbered topics with brief explanation
- EQUATIONS: any formulas present (preserve exactly)
- EXAMPLES: any examples mentioned

Be concise but complete. This summary will be combined with summaries of other
sections to produce the final student summary."""

    def _synthesis_prompt(self, combined: str, course: str, title: str) -> str:
        return f"""Synthesise these section summaries into one comprehensive student summary.

Course: {course}
Title: {title}

SECTION SUMMARIES:
{combined}

FORMAT YOUR FINAL SUMMARY EXACTLY LIKE THIS:

OVERVIEW
========
[2-3 sentences introducing the topic and why it matters]

DEFINITIONS
============
• [Definition 1]
• [Definition 2]
[Continue for ALL definitions across all sections]

MAIN TOPICS
===========

1. [Topic Title]
   [Explain in 2-4 clear sentences]

   Key Points:
   • [Point 1]
   • [Point 2]

   Examples:
   → [Example 1]

[Continue for ALL major topics]

EQUATIONS
===========
[Only include this section if equations appear in the summaries]
1. [Full equation]
   - [Define each parameter]
   - Example: [worked example]
[Continue for all equations]

REQUIREMENTS:
- Merge and deduplicate content across all section summaries
- Cover ALL topics — nothing should be lost
- Use simple, clear language
- Be comprehensive — this is the student's main study resource"""

    # ── LLM calls ─────────────────────────────────────────────────────────────

    def _invoke(self, system: str, human: str, label: str = "") -> str:
        """
        Call the LLM with retry logic.
        - Retries up to _MAX_RETRIES times on transient failures.
        - Skips retries immediately on 413 (request too large).
        - Returns "" on total failure instead of raising, so the
          rest of the pipeline still produces partial output.
        """
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=human),
        ]
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 2):
            try:
                response = self.llm.invoke(messages)
                return response.content or ""
            except Exception as e:
                last_error = e
                tag = f" [{label}]" if label else ""
                print(f"   ⚠️  Attempt {attempt}/{_MAX_RETRIES + 1}{tag} failed: {e}")
                if "413" in str(e):
                    print(f"   🚫 Request too large{tag} — skipping retries.")
                    break
                if attempt <= _MAX_RETRIES:
                    print("   🔄 Retrying...")
        print(f"   ❌ All attempts failed{' [' + label + ']' if label else ''}. "
              f"Last error: {last_error}")
        return ""

    # ── Map-reduce generation ─────────────────────────────────────────────────

    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = "",
    ) -> str:
        """
        Generate a comprehensive summary for content of any length.

        Strategy (map-reduce):
        1. Split content into overlapping token windows.
        2. MAP : summarise each chunk independently (fits within TPM limit).
        3. REDUCE : synthesise all chunk summaries into one final summary.

        If the content fits in a single chunk the map phase is skipped
        and generation goes directly to synthesis — no wasted API calls.
        """
        chunks = self._split_into_chunks(content)
        n = len(chunks)

        print(f"📚 Generating summary ({n} chunk(s), "
              f"{self.count_tokens(content):,} tokens total)...")
        print(f"   Model: {self.model}")

        system_map = "You are an expert educational summariser. Extract all key information."
        system_syn = "You are an expert educational summariser. Create clear, comprehensive student summaries."

        # MAP phase
        chunk_summaries = []
        for i, chunk in enumerate(chunks, 1):
            print(f"   [map] chunk {i}/{n} ({self.count_tokens(chunk):,} tokens)...")
            chunk_summaries.append(
                self._invoke(system_map, self._chunk_prompt(chunk, course_code, title), label=f'map chunk {i}/{n}')
            )

        # REDUCE phase — cap combined summaries to synthesis token limit
        separator = "\n\n" + "─" * 40 + "\n\n"
        combined = separator.join(chunk_summaries)
        combined_tokens = self._encode(combined)
        if len(combined_tokens) > _SYNTHESIS_MAX_TOKENS:
            combined = self._decode(combined_tokens[:_SYNTHESIS_MAX_TOKENS])
            print(f"   [reduce] Combined summaries capped at {_SYNTHESIS_MAX_TOKENS} tokens.")

        print(f"   [reduce] Synthesising {n} summary/summaries...")
        summary = self._invoke(system_syn, self._synthesis_prompt(combined, course_code, title), label='reduce')

        print(f"✅ Summary generated: {len(summary):,} chars")
        return summary

    # ── PDF generation ─────────────────────────────────────────────────────────

    def generate_pdf(
        self,
        content: str,
        output_path: str,
        course_code: str = "",
        title: str = "",
    ) -> str:
        summary_text = self.generate(content, course_code, title)
        print("📄 Creating PDF...")
        self._create_pdf(summary_text, output_path, course_code, title)
        print(f"✅ Summary PDF: {output_path}")
        return output_path

    # ── PDF helpers ────────────────────────────────────────────────────────────

    def _strip_empty_equations_section(self, text: str) -> str:
        m = re.search(r"(?mi)^EQUATIONS\s*\n=+\s*\n", text)
        if not m:
            return text
        start = m.start()
        after = text[m.end():]
        next_sec = re.search(r"(?m)^[A-Z][A-Z ]+\n=+\s*\n", after)
        end = m.end() + (next_sec.start() if next_sec else len(after))
        block = text[m.end():end].strip().lower()
        bad = [
            "not applicable", "n/a", "none", "no equations",
            "there are no equations", "not available",
            "does not include equations",
        ]
        if (not block) or any(b in block for b in bad):
            return (text[:start] + text[end:]).strip()
        return text

    def _create_pdf(self, summary_text: str, path: str, course: str, title: str):
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        summary_text = self._strip_empty_equations_section(summary_text)

        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"],
            fontSize=24, textColor=colors.HexColor("#1565c0"),
            spaceAfter=10, alignment=TA_CENTER, fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "Subtitle", parent=styles["Normal"],
            fontSize=12, textColor=colors.HexColor("#666666"),
            spaceAfter=30, alignment=TA_CENTER,
        )
        section_style = ParagraphStyle(
            "Section", parent=styles["Heading2"],
            fontSize=16, textColor=colors.HexColor("#1976d2"),
            spaceAfter=15, spaceBefore=20, fontName="Helvetica-Bold",
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["Normal"],
            fontSize=11, alignment=TA_JUSTIFY, spaceAfter=10, leading=14,
        )
        import os
        logo_path = os.path.join(os.path.dirname(__file__), "icon-01.png")
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=0.7 * inch, height=0.7 * inch)
            logo.hAlign = "CENTER"
            story.append(logo)
            story.append(Spacer(1, 0.1 * inch))

        story.append(Paragraph("Comprehensive Summary", title_style))
        story.append(Paragraph(title, subtitle_style))
        story.append(Paragraph(f"Course: {course}", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        for line in summary_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # FIX: skip decorator lines (===, ---) — they come from the
            # prompt format template and should not render as text
            if re.fullmatch(r"[=\-]{3,}", line):
                continue
            if line.isupper() and not line.startswith(("•", "→")):
                story.append(Paragraph(line.title(), section_style))
            elif line and line[0].isdigit() and ". " in line[:4]:
                clean_line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)  # strip **bold** markdown
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph(f"<b>{clean_line}</b>", body_style))
            elif line.startswith("•") or line.startswith("-"):
                content = line.lstrip("•-").strip()
                if ": " in content:
                    term, _, definition = content.partition(": ")
                    content = f"<b>{term}:</b> {definition}"
                story.append(Paragraph(f"• {content}", body_style))
            elif line.startswith("→"):
                story.append(Paragraph(f"• {line[1:].strip()}", body_style))
            elif line.endswith(":") and len(line.split()) <= 3:
                story.append(Spacer(1, 0.05 * inch))
                story.append(Paragraph(f"<b>{line}</b>", styles["Normal"]))
            else:
                story.append(Paragraph(line, body_style))

        doc.build(story)


# ── Helpers ────────────────────────────────────────────────────────────────────

def read_text_file(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Lecture file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise ValueError(f"Lecture file is empty: {path}")
    return content

# ============================================
# USAGE EXAMPLE
# ============================================

if __name__ == "__main__":
    load_dotenv()

    content = read_text_file("1_introduction_to_infosec_text.txt")

    generator = SummaryGenerator()
    
    print("="*80)
    print("GENERATING STUDENT SUMMARY ")
    print("="*80)
    
    generator.generate_pdf(
        content=content,
        output_path="student_summary.pdf",
        course_code="IS101",
        title="Introduction to NetSecurity"
    )
    print("✅ Complete!")



































































































