from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from langchain.messages import SystemMessage, HumanMessage
import os
import re
from dotenv import load_dotenv

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from typing import Optional
import tiktoken


class SummaryGenerator:
    """Generate student-friendly summaries - Simple text output"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found")
        
        self.llm =  ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model_name="z-ai/glm-4.5-air:free",
        temperature=0.5,
        max_tokens=8000,
    )
        
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens"""
        if self.encoding:
            return len(self.encoding.encode(text))
        return len(text) // 4
    
    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = ""
    ) -> str:
        """
        Generate comprehensive summary as structured text
        
        Returns:
            Structured text summary (NOT JSON)
        """
        
        print(f"📚 Generating comprehensive summary...")
        print(f"   Content length: {len(content)} characters")
        
        tokens = self.count_tokens(content)
        print(f"   Content tokens: {tokens}")
        

        summary = self._generate_summary(content, course_code, title)
        
        print(f"✅ Summary generated: {len(summary)} characters")
        
        return summary
    
    
    def _generate_summary(self, content: str, course: str, title: str) -> str:
        """Generate structured summary"""
        
        prompt = self._create_prompt(content, course, title)
        
        messages = [
            SystemMessage(content="You are an expert educational summarizer. Create clear, comprehensive summaries for students."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        return response.content
    
    def _create_prompt(self, content: str, course: str, title: str) -> str:
        """Create generation prompt"""
        
        return f"""Create a comprehensive student summary of this lecture.

Course: {course}
Title: {title}

CONTENT:
{content}

FORMAT YOUR SUMMARY EXACTLY LIKE THIS:

OVERVIEW
========
[Write 2-3 sentences introducing the topic and why it matters]

DEFINITIONS
============
• [Definition 1]
• [Definition 2]
• [Definition 3]
• [Definition 4]
• [Definition 5]
[Continue for all Definition in the lecture]

MAIN TOPICS
===========

1. [Topic Title]
   [Explain this topic in 2-4 clear sentences]
   
   Key Points:
   • [Point 1]
   • [Point 2]
   • [Point 3]
   
   Examples:
   → [Example 1]
   → [Example 2]

2. [Next Topic Title]
   [Explanation...]
   
   Key Points:
   • [Point 1]
   • [Point 2]
   
   Examples:
   → [Example 1]

[Continue for ALL major topics in the content]


[And if there equations in the content provide equations section if not skip this section ]

EQUATIONS
===========
1-The full equation
2-Define each parameter in the equation
3- provide example for the equation
[continue for all equations in the content]


REQUIREMENTS:
- Cover ALL major topics from the content
- Use simple, clear language
- Include practical examples
- Make it student-friendly
- Be comprehensive

Generate the complete summary now following this exact format."""
    
    def generate_pdf(
        self,
        content: str,
        output_path: str,
        course_code: str = "",
        title: str = ""
    ):
        """Generate summary and create PDF"""
        
        # Generate summary
        summary_text = self.generate(content, course_code, title)
        
        
        # Create PDF
        print(f"📄 Creating PDF...")
        self._create_pdf(summary_text, output_path, course_code, title)
        
        print(f"✅ Summary PDF: {output_path}")

        
        return output_path
    
    def _strip_empty_equations_section(self, text: str) -> str:
        m = re.search(r"(?mi)^EQUATIONS\s*\n=+\s*\n", text)
        if not m:
            return text

        start = m.start()
        after = text[m.end():]

        # Find next section header (ALL CAPS + =====)
        next_sec = re.search(r"(?m)^[A-Z][A-Z ]+\n=+\s*\n", after)
        end = m.end() + (next_sec.start() if next_sec else len(after))

        block = text[m.end():end].strip().lower()

        bad = [
            "not applicable", "n/a", "none", "no equations", "there are no equations",
            "not available", "does not include equations"
        ]

        if (not block) or any(b in block for b in bad):
            return (text[:start] + text[end:]).strip()

        return text
    
    def _create_pdf(self, summary_text: str, path: str, course: str, title: str):
        """Create PDF from structured text"""
        
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        summary_text = self._strip_empty_equations_section(summary_text)

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1565c0'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        section_style = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1976d2'),
            spaceAfter=15,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=14
        )
        
        # Header
        story.append(Paragraph(f"Comprehensive Summary", title_style))
        story.append(Paragraph(f"{title}", subtitle_style))
        story.append(Paragraph(f"Course: {course}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Parse and format the text
        lines = summary_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Section headers (all caps with ===)
            if line.isupper() and not line.startswith('•') and not line.startswith('→'):
                story.append(Paragraph(line.title(), section_style))
                
                # Add colored box for certain sections
                if 'OVERVIEW' in line:
                    # Next lines are overview
                    pass
            
            # Numbered items (1. 2. etc)
            elif line[0].isdigit() and '. ' in line[:4]:
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(f"<b>{line}</b>", body_style))
            
            # Bullet points
            elif line.startswith('•'):
                content = line[1:].strip()
                story.append(Paragraph(f"• {content}", body_style))
            
            # Examples
            elif line.startswith('→'):
                content = line[1:].strip()
                story.append(Paragraph(f"    → {content}", body_style))
            
            # Section labels like "Key Points:", "Examples:"
            elif line.endswith(':') and len(line.split()) <= 3:
                story.append(Spacer(1, 0.05*inch))
                story.append(Paragraph(f"<b>{line}</b>", styles['Normal']))
            
            # Regular text
            else:
                story.append(Paragraph(line, body_style))
        
        # Build PDF
        doc.build(story)

def read_text_file(path: str) -> str:
    """Read lecture content from a .txt file safely."""
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

# if __name__ == "__main__":
#     load_dotenv()

#     content = read_text_file("nips_2017_attention_is_all_you_need_paper_text.txt")

#     generator = SummaryGenerator()
    
#     print("="*80)
#     print("GENERATING STUDENT SUMMARY ")
#     print("="*80)
    
#     generator.generate_pdf(
#         content=content,
#         output_path="student_summary.pdf",
#         course_code="IS101",
#         title="Introduction to NetSecurity"
#     )
#     print("✅ Complete!")




# from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI

# from langchain.messages import SystemMessage, HumanMessage
# import os
# import re
# from typing import Optional

# from reportlab.lib.pagesizes import letter
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
# from reportlab.lib import colors
# from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# import tiktoken


# # ── Shared chunking helper ────────────────────────────────────────────────────

# def _chunk_text(text: str, max_chars: int = 6000, overlap: int = 300) -> list[str]:
#     if len(text) <= max_chars:
#         return [text]
#     chunks, start = [], 0
#     while start < len(text):
#         end = start + max_chars
#         if end >= len(text):
#             chunks.append(text[start:])
#             break
#         split_pos = text.rfind("\n\n", start, end)
#         if split_pos == -1 or split_pos <= start:
#             split_pos = text.rfind(". ", start, end)
#         if split_pos == -1 or split_pos <= start:
#             split_pos = end
#         chunks.append(text[start : split_pos + 1])
#         start = max(start + 1, split_pos + 1 - overlap)
#     return chunks


# class SummaryGenerator:
#     """
#     Generate student-friendly summaries.
#     Handles content of any length via map-reduce chunking — no 413 errors.

#     Map  : summarise each chunk independently
#     Reduce: synthesise all chunk summaries into one final summary
#     """

#     # Chunk size for the map phase
#     CHUNK_MAX_CHARS = 6_000
#     CHUNK_OVERLAP   = 300

#     # Synthesis input limit — combined chunk summaries fed into final pass
#     # Each chunk summary is ~1 500 chars, so 8 chunks ≈ 12 000 chars ≈ safe
#     SYNTHESIS_MAX_CHARS = 12_000

#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv("GROQ_API_KEY")
#         if not self.api_key:
#             raise ValueError("GROQ_API_KEY not found")

#         self.llm = ChatOpenAI(
#         api_key=api_key,
#         base_url="https://openrouter.ai/api/v1",
#         model_name="arcee-ai/trinity-large-preview:free",
#         temperature=0.5,
#         max_tokens=16000,
#     )

#         try:
#             self.encoding = tiktoken.get_encoding("cl100k_base")
#         except Exception:
#             self.encoding = None

#     # ── Token counting ────────────────────────────────────────────────────────

#     def count_tokens(self, text: str) -> int:
#         if self.encoding:
#             return len(self.encoding.encode(text))
#         return max(1, len(text) // 4)

#     # ── Prompts ───────────────────────────────────────────────────────────────

#     def _chunk_summary_prompt(self, chunk: str, course: str, title: str) -> str:
#         return f"""Summarise this section of a lecture. Extract ALL key concepts,
# definitions, equations, and examples. Be thorough — nothing important should be lost.

# Course: {course}
# Title: {title}

# CONTENT SECTION:
# {chunk}

# Write a structured summary using:
# - DEFINITIONS: bullet points for each term defined
# - KEY CONCEPTS: numbered topics with brief explanation
# - EQUATIONS: any formulas present (preserve exactly)
# - EXAMPLES: any examples mentioned

# Be concise but complete. This summary will be combined with summaries of other
# sections to produce a final student summary."""

#     def _synthesis_prompt(
#         self,
#         combined_summaries: str,
#         course: str,
#         title: str,
#     ) -> str:
#         return f"""You are synthesising section summaries into one comprehensive student summary.

# Course: {course}
# Title: {title}

# SECTION SUMMARIES:
# {combined_summaries}

# FORMAT YOUR FINAL SUMMARY EXACTLY LIKE THIS:

# OVERVIEW
# ========
# [2-3 sentences introducing the topic and why it matters]

# DEFINITIONS
# ============
# • [Definition 1]
# • [Definition 2]
# [Continue for ALL definitions across all sections]

# MAIN TOPICS
# ===========

# 1. [Topic Title]
#    [Explain in 2-4 clear sentences]

#    Key Points:
#    • [Point 1]
#    • [Point 2]

#    Examples:
#    → [Example 1]

# [Continue for ALL major topics]

# EQUATIONS
# ===========
# [Only include this section if equations were present in the summaries]
# 1. [Full equation]
#    - [Define each parameter]
#    - Example: [worked example]
# [Continue for all equations]

# REQUIREMENTS:
# - Merge and deduplicate content across all section summaries
# - Cover ALL topics — nothing should be lost
# - Use simple, clear language
# - Be comprehensive — this is the student's main study resource"""

#     # ── Map phase — summarise one chunk ──────────────────────────────────────

#     def _summarise_chunk(self, chunk: str, course: str, title: str) -> str:
#         prompt = self._chunk_summary_prompt(chunk, course, title)
#         messages = [
#             SystemMessage(content="You are an expert educational summariser. Extract all key information."),
#             HumanMessage(content=prompt),
#         ]
#         response = self.llm.invoke(messages)
#         return response.content or ""

#     # ── Reduce phase — synthesise all chunk summaries ─────────────────────────

#     def _synthesise(self, chunk_summaries: list[str], course: str, title: str) -> str:
#         combined = "\n\n" + "─" * 40 + "\n\n".join(chunk_summaries)

#         # If combined summaries are too long, truncate to synthesis limit
#         if len(combined) > self.SYNTHESIS_MAX_CHARS:
#             combined = combined[:self.SYNTHESIS_MAX_CHARS]
#             print(f"   [synthesis] Combined summaries truncated to "
#                   f"{self.SYNTHESIS_MAX_CHARS:,} chars")

#         prompt = self._synthesis_prompt(combined, course, title)
#         messages = [
#             SystemMessage(content="You are an expert educational summariser. Create clear, comprehensive student summaries."),
#             HumanMessage(content=prompt),
#         ]
#         response = self.llm.invoke(messages)
#         return response.content or ""

#     # ── Main generation (chunked map-reduce) ──────────────────────────────────

#     def generate(
#         self,
#         content: str,
#         course_code: str = "",
#         title: str = "",
#     ) -> str:
#         """
#         Generate a comprehensive summary for content of any length.

#         Strategy (map-reduce):
#         1. Split content into chunks of ~6 000 chars.
#         2. MAP: summarise each chunk independently.
#         3. REDUCE: synthesise all chunk summaries into one final summary.

#         If content fits in a single chunk, the map phase produces one summary
#         and the reduce phase formats it — no extra LLM calls wasted.
#         """
#         chunks = _chunk_text(content, self.CHUNK_MAX_CHARS, self.CHUNK_OVERLAP)
#         n      = len(chunks)

#         print(f"📚 Generating summary ({n} chunk(s), "
#               f"{self.count_tokens(content):,} tokens total)...")

#         if n == 1:
#             # No need for two-phase — just generate directly
#             print("   Single chunk — direct generation")
#             summary = self._synthesise([self._summarise_chunk(content, course_code, title)],
#                                        course_code, title)
#         else:
#             # MAP phase
#             chunk_summaries = []
#             for i, chunk in enumerate(chunks, 1):
#                 print(f"   [map] chunk {i}/{n} ({len(chunk):,} chars)...")
#                 chunk_summaries.append(
#                     self._summarise_chunk(chunk, course_code, title)
#                 )

#             # REDUCE phase
#             print(f"   [reduce] synthesising {n} summaries...")
#             summary = self._synthesise(chunk_summaries, course_code, title)

#         print(f"✅ Summary generated: {len(summary):,} chars")
#         return summary

#     # ── PDF output (unchanged from original) ─────────────────────────────────

#     def generate_pdf(
#         self,
#         content: str,
#         output_path: str,
#         course_code: str = "",
#         title: str = "",
#     ) -> str:
#         summary_text = self.generate(content, course_code, title)
#         print("📄 Creating PDF...")
#         self._create_pdf(summary_text, output_path, course_code, title)
#         print(f"✅ Summary PDF: {output_path}")
#         return output_path

#     def _strip_empty_equations_section(self, text: str) -> str:
#         m = re.search(r"(?mi)^EQUATIONS\s*\n=+\s*\n", text)
#         if not m:
#             return text
#         start = m.start()
#         after = text[m.end():]
#         next_sec = re.search(r"(?m)^[A-Z][A-Z ]+\n=+\s*\n", after)
#         end   = m.end() + (next_sec.start() if next_sec else len(after))
#         block = text[m.end():end].strip().lower()
#         bad   = ["not applicable", "n/a", "none", "no equations",
#                  "there are no equations", "not available",
#                  "does not include equations"]
#         if (not block) or any(b in block for b in bad):
#             return (text[:start] + text[end:]).strip()
#         return text

#     def _create_pdf(self, summary_text: str, path: str, course: str, title: str):
#         doc    = SimpleDocTemplate(path, pagesize=letter)
#         styles = getSampleStyleSheet()
#         story  = []

#         summary_text = self._strip_empty_equations_section(summary_text)

#         title_style = ParagraphStyle(
#             "CustomTitle", parent=styles["Heading1"],
#             fontSize=24, textColor=colors.HexColor("#1565c0"),
#             spaceAfter=10, alignment=TA_CENTER, fontName="Helvetica-Bold",
#         )
#         subtitle_style = ParagraphStyle(
#             "Subtitle", parent=styles["Normal"],
#             fontSize=12, textColor=colors.HexColor("#666666"),
#             spaceAfter=30, alignment=TA_CENTER,
#         )
#         section_style = ParagraphStyle(
#             "Section", parent=styles["Heading2"],
#             fontSize=16, textColor=colors.HexColor("#1976d2"),
#             spaceAfter=15, spaceBefore=20, fontName="Helvetica-Bold",
#         )
#         body_style = ParagraphStyle(
#             "Body", parent=styles["Normal"],
#             fontSize=11, alignment=TA_JUSTIFY, spaceAfter=10, leading=14,
#         )

#         story.append(Paragraph("Comprehensive Summary", title_style))
#         story.append(Paragraph(title, subtitle_style))
#         story.append(Paragraph(f"Course: {course}", styles["Normal"]))
#         story.append(Spacer(1, 0.3 * inch))

#         for line in summary_text.split("\n"):
#             line = line.strip()
#             if not line:
#                 continue
#             if line.isupper() and not line.startswith(("•", "→")):
#                 story.append(Paragraph(line.title(), section_style))
#             elif line[0].isdigit() and ". " in line[:4]:
#                 story.append(Spacer(1, 0.1 * inch))
#                 story.append(Paragraph(f"<b>{line}</b>", body_style))
#             elif line.startswith("•"):
#                 story.append(Paragraph(f"• {line[1:].strip()}", body_style))
#             elif line.startswith("→"):
#                 story.append(Paragraph(f"    → {line[1:].strip()}", body_style))
#             elif line.endswith(":") and len(line.split()) <= 3:
#                 story.append(Spacer(1, 0.05 * inch))
#                 story.append(Paragraph(f"<b>{line}</b>", styles["Normal"]))
#             else:
#                 story.append(Paragraph(line, body_style))

#         doc.build(story)