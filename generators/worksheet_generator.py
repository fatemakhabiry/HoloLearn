from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.messages import SystemMessage, HumanMessage
import os
import json
import re
from typing import Optional

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

import tiktoken
from xml.sax.saxutils import escape


class WorksheetGenerator:
    """Generate comprehensive worksheets with MCQ, True/False, and written questions"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY_WORKSHEET")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY_WORKSHEET not found")

        self.llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model_name="arcee-ai/trinity-large-preview:free",
        temperature=0.2,
        max_tokens=8000,
    )

        # Token counter (optional)
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        return max(1, len(text) // 4)

    # -------------------------
    # JSON extraction (robust)
    # -------------------------
    def _extract_first_json_object(self, text: str) -> str:
        """
        Extract the first balanced JSON object from model output.
        This prevents failures if model adds extra text.
        """
        text = text.strip()
        text = re.sub(r"```(?:json)?", "", text)
        text = text.replace("```", "").strip()

        # Normalize smart quotes
        text = text.replace("“", '"').replace("”", '"').replace("’", "'")

        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in model response.")

        depth = 0
        end = None
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end is None:
            raise ValueError("JSON appears truncated / unbalanced braces.")

        json_str = text[start:end]
        # Remove trailing commas (common model mistake)
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)
        return json_str

    def _parse_json(self, text: str) -> dict:
        json_str = self._extract_first_json_object(text)
        return json.loads(json_str)

    # -------------------------
    # Prompt
    # -------------------------
    def _create_prompt(
        self,
        content: str,
        course_code: str,
        title: str,
        num_mcq: int,
        num_tf: int,
        num_written: int,
    ) -> str:
        return f"""
Generate a worksheet STRICTLY from the provided content and cover all content (do not introduce external topics).

Course: {course_code}
Title: {title}

CONTENT:
{content}

Create EXACTLY:
- {num_mcq} MCQ questions
- {num_tf} True/False statements
- {num_written} Written questions

========================
MATHEMATICAL REQUIREMENTS
========================

If the lecture contains equations, formulas, derivations, or numerical relationships:

1) DO NOT ask students to simply write or restate equations in the QUESTION.
2) Generate calculation-based problems.
3) Provide numerical values for some parameters and ask to calculate the missing variable.
4) Include BOTH:
   • Direct substitution problems.
   • Indirect / multi-step / conceptual problems that test understanding.
5) Questions must test:
   • Variable relationships
   • Interpretation of parameters
   • Application under different conditions (e.g., change in load, power factor, scaling, etc.)
6) Do NOT introduce equations that are not explicitly present in the content.

========================
EQUATION COVERAGE CONSTRAINTS (HARD)
========================

If the content contains more than 3 distinct equations/relationships:

1) Diversity requirement (mandatory):
- The WRITTEN section MUST use AT LEAST min(6, number_of_distinct_equations_in_content) different equations/relationships from the lecture.
- No single equation/relationship may be used in more than 3 written questions.

2) Coverage requirement (mandatory):
- Distribute written questions across the FULL set of equation types/topics that appear in the lecture.
- Ensure at least one written question targets EACH major equation group when present.
  A “major equation group” means a set of equations about the same concept (same dependent variable or same physical/technical meaning).

3) Difficulty requirement (mandatory):
- Include BOTH:
  - Direct questions (single-step substitution).
  - Indirect/advanced questions (multi-step, rearranging equations, interpreting variables, combining two equations, edge cases, unit reasoning, or “what happens if parameter X increases?”).

4) Anti-pattern rule (mandatory):
- DO NOT generate many variants of the same template with only numbers changed.
- If you reuse an equation, it must test a clearly different skill (e.g., solve for different variable, multi-step combo, conceptual interpretation).

5) Self-check rule (mandatory):
- Before producing final JSON, verify:
  - You used enough distinct equations.
  - No equation exceeds the repetition limit.
  - Written questions cover all equation groups that exist in the content.

========================
ANSWER FORMAT RULES
========================

For mathematical written questions:
- The ANSWER MUST explicitly show the equation/formula (typed).
- The QUESTION must NOT ask the student to "write the equation".
- The ANSWER MUST be multi-line using newline characters.
- Use HTML subscripts/superscripts when needed, e.g.:
  V<sub>1</sub>, I<sub>2</sub><sup>2</sup>, R<sub>eq</sub>, X<sub>m</sub>, etc.
- Use only these HTML tags in answers: <sub>, </sub>, <sup>, </sup>, <br/> (optional)
  Do NOT use any other HTML tags.

Use EXACT format:

Step 1: State the equation:
<equation line 1>
<equation line 2 if needed>

Step 2: Substitute the given values:
<substitution line 1>
<substitution line 2 if needed>

Step 3: Compute and solve:
<calculation lines>

Final Answer: <final value with units>

Notes:
- Put the equation on its own line(s), NOT inside the Step sentence.
- Use the SAME variables/symbols as the content.
- Keep it neat and readable.

For conceptual written questions:
- Answer in 2–4 clear sentences.

========================
GENERAL RULES
========================

- No repeated questions/statements.
- Cover the full content across all topics.
- Keep questions concise.
- Ensure difficulty progression (basic → intermediate → advanced).
- Output VALID JSON ONLY.
- No markdown.
- No explanations.
- No extra text outside JSON.

========================
JSON SCHEMA (MUST MATCH EXACTLY)
========================

{{
  "mcq": [
    {{
      "question": "...",
      "options": {{"A":"...","B":"...","C":"...","D":"..."}},
      "correct_answer": "A"
    }}
  ],
  "true_false": [
    {{
      "statement": "...",
      "correct_answer": "True"
    }}
  ],
  "written": [
    {{
      "question": "...",
      "answer": "Step 1: State the equation:\\n...\\n\\nStep 2: Substitute the given values:\\n...\\n\\nStep 3: Compute and solve:\\n...\\n\\nFinal Answer: ..."
    }}
  ]
}}
"""

    # -------------------------
    # Render multi-line answers (slide-like)
    # -------------------------
    def _append_multiline_solution(self, story, answer_text: str, step_style, equation_style, final_style):
        """
        Renders a multi-line solution in a slide-like style:
        - "Step ..." lines normal
        - equation/substitution/calculation lines centered and larger
        - "Final Answer" emphasized

        Allows ONLY: <sub>, <sup> tags inside lines.
        """
        if not answer_text:
            return

        # Normalize newlines
        raw_lines = answer_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        # Keep single blank lines for spacing
        lines = []
        prev_blank = False
        for ln in raw_lines:
            ln = ln.strip()
            if ln == "":
                if not prev_blank:
                    lines.append("")
                prev_blank = True
            else:
                lines.append(ln)
                prev_blank = False

        in_step_block = False

        for ln in lines:
            if ln == "":
                story.append(Spacer(1, 0.08 * inch))
                continue

            lower_ln = ln.lower()

            # Final Answer
            if lower_ln.startswith("final answer"):
                safe = escape(ln)
                story.append(Paragraph(f"<b>{safe}</b>", final_style))
                continue

            # Step header
            if lower_ln.startswith("step 1") or lower_ln.startswith("step 2") or lower_ln.startswith("step 3"):
                in_step_block = True
                safe = escape(ln)
                story.append(Paragraph(f"<b>{safe}</b>", step_style))
                continue

            # For math-like lines: we want to KEEP <sub>/<sup> tags, but escape everything else safely.
            # Strategy:
            # 1) Temporarily protect allowed tags.
            # 2) Escape the rest.
            # 3) Restore allowed tags.

            protected = (
                ln.replace("<sub>", "__SUB_OPEN__")
                  .replace("</sub>", "__SUB_CLOSE__")
                  .replace("<sup>", "__SUP_OPEN__")
                  .replace("</sup>", "__SUP_CLOSE__")
            )
            protected = escape(protected)
            restored = (
                protected.replace("__SUB_OPEN__", "<sub>")
                         .replace("__SUB_CLOSE__", "</sub>")
                         .replace("__SUP_OPEN__", "<sup>")
                         .replace("__SUP_CLOSE__", "</sup>")
            )

            looks_like_math = any(sym in ln for sym in ["=", "/", "×", "*", "^", "(", ")", "∑", "√"])
            if in_step_block and looks_like_math:
                story.append(Paragraph(f"{restored}", equation_style))
            else:
                story.append(Paragraph(f"{restored}", step_style))

    # -------------------------
    # Generation (ONE LLM call)
    # -------------------------
    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = "",
        num_mcq: int = 20,
        num_tf: int = 10,
        num_written: int = 15,
    ) -> dict:

        print("📝 Generating worksheet ...")
        print(f"   MCQ: {num_mcq} | TF: {num_tf} | Written: {num_written}")
        print(f"   Content tokens (approx): {self.count_tokens(content)}")

        prompt = self._create_prompt(content, course_code, title, num_mcq, num_tf, num_written)

        messages = [
            SystemMessage(content="You are an expert educational assessment creator. Output VALID JSON ONLY."),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)

        try:
            worksheet = self._parse_json(response.content or "")
        except Exception as e:
            print(f"❌ Error parsing JSON: {e}")
            return {"mcq": [], "true_false": [], "written": []}

        # Ensure keys exist
        worksheet.setdefault("mcq", [])
        worksheet.setdefault("true_false", [])
        worksheet.setdefault("written", [])

        print(f"✅ Generated MCQ={len(worksheet['mcq'])}, TF={len(worksheet['true_false'])}, Written={len(worksheet['written'])}")
        return worksheet

    # -------------------------
    # PDF generation
    # -------------------------
    def generate_pdfs(
        self,
        content: str,
        questions_path: str,
        answers_path: str,
        course_code: str = "",
        title: str = "",
        num_mcq: int = 20,
        num_tf: int = 10,
        num_written: int = 10,
    ):
        worksheet = self.generate(content, course_code, title, num_mcq, num_tf, num_written)

        print("📄 Creating PDFs...")
        self._create_questions_pdf(worksheet, questions_path, course_code, title)
        self._create_answers_pdf(worksheet, answers_path, course_code, title)

        print(f"✅ Questions PDF: {questions_path}")
        print(f"✅ Answers PDF: {answers_path}")
        return (questions_path, answers_path)

    def _create_questions_pdf(self, worksheet: dict, path: str, course_code: str, title: str):
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#1a237e"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        story.append(Paragraph(f"Worksheet: {escape(title)}", title_style))
        story.append(Paragraph(f"Course: {escape(course_code)}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("<b>Student Name:</b> _______________________", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Part I: MCQ
        if worksheet.get("mcq"):
            story.append(Paragraph("<b>Part I: Multiple Choice Questions</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.15 * inch))

            for i, q in enumerate(worksheet["mcq"], 1):
                story.append(Paragraph(f"<b>{i}. {escape(q.get('question',''))}</b>", styles["Normal"]))
                opts = q.get("options", {}) or {}
                for letter_ in ["A", "B", "C", "D"]:
                    story.append(Paragraph(f"   {letter_}. {escape(opts.get(letter_, ''))}", styles["Normal"]))
                story.append(Spacer(1, 0.12 * inch))

            story.append(PageBreak())

        # Part II: True/False
        if worksheet.get("true_false"):
            story.append(Paragraph("<b>Part II: True / False</b>", styles["Heading2"]))
            story.append(Paragraph("Write True or False for each statement.", styles["Normal"]))
            story.append(Spacer(1, 0.15 * inch))

            for i, q in enumerate(worksheet["true_false"], 1):
                story.append(Paragraph(f"<b>{i}.</b> _____ {escape(q.get('statement',''))}", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))

            story.append(PageBreak())

        # Part III: Written
        if worksheet.get("written"):
            story.append(Paragraph("<b>Part III: Written Questions</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.15 * inch))

            for i, q in enumerate(worksheet["written"], 1):
                story.append(Paragraph(f"<b>{i}. {escape(q.get('question',''))}</b>", styles["Normal"]))
                story.append(Spacer(1, 0.35 * inch))
                for _ in range(4):
                    story.append(Paragraph("_" * 80, styles["Normal"]))
                    story.append(Spacer(1, 0.06 * inch))
                story.append(Spacer(1, 0.12 * inch))

        doc.build(story)

    def _create_answers_pdf(self, worksheet: dict, path: str, course_code: str, title: str):
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Slide-like styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#1b5e20"),  # green-ish like your slide (change/remove if you want black)
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        step_style = ParagraphStyle(
            "StepStyle",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            spaceAfter=6,
        )

        equation_style = ParagraphStyle(
            "EquationStyle",
            parent=styles["Normal"],
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=10,
            # textColor=colors.black,  # uncomment if you want black
        )

        final_style = ParagraphStyle(
            "FinalStyle",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            spaceBefore=8,
            spaceAfter=12,
            textColor=colors.HexColor("#0d47a1"),  # optional emphasis
        )

        story.append(Paragraph(f"Answer Key: {escape(title)}", title_style))
        story.append(Paragraph(f"Course: {escape(course_code)}", styles["Normal"]))
        story.append(Spacer(1, 0.25 * inch))

        # MCQ answers
        if worksheet.get("mcq"):
            story.append(Paragraph("<b>Part I: MCQ Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["mcq"], 1):
                story.append(Paragraph(f"<b>{i}. Answer:</b> {escape(q.get('correct_answer',''))}", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))
            story.append(PageBreak())

        # TF answers
        if worksheet.get("true_false"):
            story.append(Paragraph("<b>Part II: True / False Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["true_false"], 1):
                story.append(Paragraph(f"<b>{i}. Answer:</b> {escape(q.get('correct_answer',''))}", styles["Normal"]))
                story.append(Paragraph(f"Statement: {escape(q.get('statement',''))}", styles["Normal"]))
                story.append(Spacer(1, 0.10 * inch))
            story.append(PageBreak())

        # Written answers (slide-like formatting)
        if worksheet.get("written"):
            story.append(Paragraph("<b>Part III: Written Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["written"], 1):
                story.append(Paragraph(f"<b>{i}. {escape(q.get('question',''))}</b>", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))
                story.append(Paragraph("<b>Answer:</b>", styles["Normal"]))
                self._append_multiline_solution(
                    story,
                    q.get("answer", ""),
                    step_style=step_style,
                    equation_style=equation_style,
                    final_style=final_style
                )
                story.append(Spacer(1, 0.15 * inch))

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


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Sample content
    content = read_text_file(r"utils\output\pow1705_transformer\pow1705_transformer_text.txt")

    generator = WorksheetGenerator()

    generator.generate_pdfs(
        content=content,
        questions_path="worksheet11_questions.pdf",
        answers_path="worksheet11_answers.pdf",
        course_code="POW1705",
        title="Transformer Worksheet",
        num_mcq=20,
        num_tf=10,
        num_written=15,
    )

    print("\n✅ Complete! Check the PDF files.")










# from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI

# from langchain.messages import SystemMessage, HumanMessage
# import os
# import json
# import re
# from typing import Optional

# from reportlab.lib.pagesizes import letter
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
# from reportlab.lib import colors
# from reportlab.lib.enums import TA_CENTER

# import tiktoken
# from xml.sax.saxutils import escape


# # ─────────────────────────────────────────────────────────────────────────────
# # CHUNKING HELPER — shared logic, keeps generator clean
# # ─────────────────────────────────────────────────────────────────────────────

# def _chunk_text(text: str, max_chars: int = 6000, overlap: int = 300) -> list[str]:
#     """
#     Split text into overlapping chunks of max_chars characters.
#     Tries to split on paragraph boundaries first, then sentence boundaries.
#     overlap keeps context between chunks so questions don't repeat concepts
#     from the very end of one chunk that appear at the start of the next.
#     """
#     if len(text) <= max_chars:
#         return [text]

#     chunks = []
#     start  = 0

#     while start < len(text):
#         end = start + max_chars

#         if end >= len(text):
#             chunks.append(text[start:])
#             break

#         # Try to split on a paragraph boundary within the last 500 chars
#         split_pos = text.rfind("\n\n", start, end)
#         if split_pos == -1 or split_pos <= start:
#             # Fall back to sentence boundary
#             split_pos = text.rfind(". ", start, end)
#         if split_pos == -1 or split_pos <= start:
#             # Last resort: hard split
#             split_pos = end

#         chunks.append(text[start : split_pos + 1])
#         # Overlap: go back `overlap` chars so the next chunk has context
#         start = max(start + 1, split_pos + 1 - overlap)

#     return chunks


# class WorksheetGenerator:
#     """
#     Generate comprehensive worksheets with MCQ, True/False, and written questions.
#     Handles content of any length via chunking — no 413 errors.
#     """

#     # How many chars to send per LLM call.
#     # ~6 000 chars ≈ ~1 500 tokens of content.
#     # With prompt overhead we stay comfortably under 12 000 TPM.
#     CHUNK_MAX_CHARS = 6_000
#     CHUNK_OVERLAP   = 300

#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv("OPENROUTER_API_KEY_WORKSHEET")
#         if not self.api_key:
#             raise ValueError("OPENROUTER_API_KEY_WORKSHEET not found")

#         self.llm = ChatOpenAI(
#         api_key=api_key,
#         base_url="https://openrouter.ai/api/v1",
#         model_name="arcee-ai/trinity-large-preview:free",
#         temperature=0.2,
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

#     # ── JSON helpers ──────────────────────────────────────────────────────────

#     def _extract_first_json_object(self, text: str) -> str:
#         text = text.strip()
#         text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
#         text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")

#         start = text.find("{")
#         if start == -1:
#             raise ValueError("No JSON object found in model response.")

#         depth = 0
#         end   = None
#         for i in range(start, len(text)):
#             if text[i] == "{":
#                 depth += 1
#             elif text[i] == "}":
#                 depth -= 1
#                 if depth == 0:
#                     end = i + 1
#                     break

#         if end is None:
#             raise ValueError("JSON appears truncated / unbalanced braces.")

#         json_str = text[start:end]
#         json_str = re.sub(r",\s*}", "}", json_str)
#         json_str = re.sub(r",\s*]", "]", json_str)
#         return json_str

#     def _parse_json(self, text: str) -> dict:
#         return json.loads(self._extract_first_json_object(text))

# #     # -------------------------
# #     # Prompt
# #     # -------------------------
#     def _create_prompt(
#         self,
#         content: str,
#         course_code: str,
#         title: str,
#         num_mcq: int,
#         num_tf: int,
#         num_written: int,
#     ) -> str:
#         return f"""
# Generate a worksheet STRICTLY from the provided content and cover all content (do not introduce external topics).

# Course: {course_code}
# Title: {title}

# CONTENT:
# {content}

# Create EXACTLY:
# - {num_mcq} MCQ questions
# - {num_tf} True/False statements
# - {num_written} Written questions

# ========================
# MATHEMATICAL REQUIREMENTS
# ========================

# If the lecture contains equations, formulas, derivations, or numerical relationships:

# 1) DO NOT ask students to simply write or restate equations in the QUESTION.
# 2) Generate calculation-based problems.
# 3) Provide numerical values for some parameters and ask to calculate the missing variable.
# 4) Include BOTH:
#    • Direct substitution problems.
#    • Indirect / multi-step / conceptual problems that test understanding.
# 5) Questions must test:
#    • Variable relationships
#    • Interpretation of parameters
#    • Application under different conditions (e.g., change in load, power factor, scaling, etc.)
# 6) Do NOT introduce equations that are not explicitly present in the content.

# ========================
# EQUATION COVERAGE CONSTRAINTS (HARD)
# ========================

# If the content contains more than 3 distinct equations/relationships:

# 1) Diversity requirement (mandatory):
# - The WRITTEN section MUST use AT LEAST min(6, number_of_distinct_equations_in_content) different equations/relationships from the lecture.
# - No single equation/relationship may be used in more than 3 written questions.

# 2) Coverage requirement (mandatory):
# - Distribute written questions across the FULL set of equation types/topics that appear in the lecture.
# - Ensure at least one written question targets EACH major equation group when present.
#   A “major equation group” means a set of equations about the same concept (same dependent variable or same physical/technical meaning).

# 3) Difficulty requirement (mandatory):
# - Include BOTH:
#   - Direct questions (single-step substitution).
#   - Indirect/advanced questions (multi-step, rearranging equations, interpreting variables, combining two equations, edge cases, unit reasoning, or “what happens if parameter X increases?”).

# 4) Anti-pattern rule (mandatory):
# - DO NOT generate many variants of the same template with only numbers changed.
# - If you reuse an equation, it must test a clearly different skill (e.g., solve for different variable, multi-step combo, conceptual interpretation).

# 5) Self-check rule (mandatory):
# - Before producing final JSON, verify:
#   - You used enough distinct equations.
#   - No equation exceeds the repetition limit.
#   - Written questions cover all equation groups that exist in the content.

# ========================
# ANSWER FORMAT RULES
# ========================

# For mathematical written questions:
# - The ANSWER MUST explicitly show the equation/formula (typed).
# - The QUESTION must NOT ask the student to "write the equation".
# - The ANSWER MUST be multi-line using newline characters.
# - Use HTML subscripts/superscripts when needed, e.g.:
#   V<sub>1</sub>, I<sub>2</sub><sup>2</sup>, R<sub>eq</sub>, X<sub>m</sub>, etc.
# - Use only these HTML tags in answers: <sub>, </sub>, <sup>, </sup>, <br/> (optional)
#   Do NOT use any other HTML tags.

# Use EXACT format:

# Step 1: State the equation:
# <equation line 1>
# <equation line 2 if needed>

# Step 2: Substitute the given values:
# <substitution line 1>
# <substitution line 2 if needed>

# Step 3: Compute and solve:
# <calculation lines>

# Final Answer: <final value with units>

# Notes:
# - Put the equation on its own line(s), NOT inside the Step sentence.
# - Use the SAME variables/symbols as the content.
# - Keep it neat and readable.

# For conceptual written questions:
# - Answer in 2–4 clear sentences.

# ========================
# GENERAL RULES
# ========================

# - No repeated questions/statements.
# - Cover the full content across all topics.
# - Keep questions concise.
# - Ensure difficulty progression (basic → intermediate → advanced).
# - Output VALID JSON ONLY.
# - No markdown.
# - No explanations.
# - No extra text outside JSON.

# ========================
# JSON SCHEMA (MUST MATCH EXACTLY)
# ========================

# {{
#   "mcq": [
#     {{
#       "question": "...",
#       "options": {{"A":"...","B":"...","C":"...","D":"..."}},
#       "correct_answer": "A"
#     }}
#   ],
#   "true_false": [
#     {{
#       "statement": "...",
#       "correct_answer": "True"
#     }}
#   ],
#   "written": [
#     {{
#       "question": "...",
#       "answer": "Step 1: State the equation:\\n...\\n\\nStep 2: Substitute the given values:\\n...\\n\\nStep 3: Compute and solve:\\n...\\n\\nFinal Answer: ..."
#     }}
#   ]
# }}
# """

#     # ── Single chunk generation ───────────────────────────────────────────────

#     def _generate_from_chunk(
#         self,
#         chunk: str,
#         course_code: str,
#         title: str,
#         num_mcq: int,
#         num_tf: int,
#         num_written: int,
#     ) -> dict:
#         prompt = self._create_prompt(chunk, course_code, title, num_mcq, num_tf, num_written)
#         messages = [
#             SystemMessage(content="You are an expert educational assessment creator. Output VALID JSON ONLY."),
#             HumanMessage(content=prompt),
#         ]
#         response = self.llm.invoke(messages)
#         try:
#             result = self._parse_json(response.content or "")
#         except Exception as e:
#             print(f"   ⚠  JSON parse error on chunk: {e}")
#             result = {}
#         result.setdefault("mcq", [])
#         result.setdefault("true_false", [])
#         result.setdefault("written", [])
#         return result

#     # ── Deduplication ─────────────────────────────────────────────────────────

#     @staticmethod
#     def _dedup(items: list, key: str) -> list:
#         """
#         Remove duplicate questions/statements by normalising whitespace and
#         lowercasing. Keeps the first occurrence.
#         """
#         seen   = set()
#         unique = []
#         for item in items:
#             sig = re.sub(r"\s+", " ", item.get(key, "")).strip().lower()[:120]
#             if sig and sig not in seen:
#                 seen.add(sig)
#                 unique.append(item)
#         return unique

#     # ── Main generation (chunked) ─────────────────────────────────────────────

#     def generate(
#         self,
#         content: str,
#         course_code: str = "",
#         title: str = "",
#         num_mcq: int = 20,
#         num_tf: int = 10,
#         num_written: int = 15,
#     ) -> dict:
#         """
#         Generate a complete worksheet for content of any length.

#         Strategy:
#         1. Split content into chunks of ~6 000 chars.
#         2. Ask each chunk for a proportional share of questions.
#         3. Merge all results and deduplicate.
#         4. Trim to the requested totals.
#         """
#         chunks = _chunk_text(content, self.CHUNK_MAX_CHARS, self.CHUNK_OVERLAP)
#         n      = len(chunks)

#         print(f"📝 Generating worksheet ({n} chunk(s), "
#               f"{self.count_tokens(content):,} tokens total)...")
#         print(f"   MCQ: {num_mcq} | TF: {num_tf} | Written: {num_written}")

#         # Distribute questions proportionally across chunks
#         # Ask for slightly more per chunk so we have room to deduplicate
#         per_mcq     = max(4, -(-num_mcq     // n) + 2)   # ceiling + buffer
#         per_tf      = max(3, -(-num_tf      // n) + 1)
#         per_written = max(3, -(-num_written // n) + 2)

#         all_mcq, all_tf, all_written = [], [], []

#         for i, chunk in enumerate(chunks, 1):
#             print(f"   chunk {i}/{n} ({len(chunk):,} chars)...")
#             fragment = self._generate_from_chunk(
#                 chunk, course_code, title,
#                 per_mcq, per_tf, per_written,
#             )
#             all_mcq     += fragment["mcq"]
#             all_tf      += fragment["true_false"]
#             all_written += fragment["written"]

#         # Deduplicate across chunks
#         all_mcq     = self._dedup(all_mcq,     "question")
#         all_tf      = self._dedup(all_tf,      "statement")
#         all_written = self._dedup(all_written, "question")

#         # Trim to requested totals
#         worksheet = {
#             "mcq":        all_mcq[:num_mcq],
#             "true_false": all_tf[:num_tf],
#             "written":    all_written[:num_written],
#         }

#         print(f"✅ Final: MCQ={len(worksheet['mcq'])}, "
#               f"TF={len(worksheet['true_false'])}, "
#               f"Written={len(worksheet['written'])}")
#         return worksheet

#     # ── PDF helpers (unchanged from original) ────────────────────────────────

#     def _append_multiline_solution(self, story, answer_text, step_style, equation_style, final_style):
#         if not answer_text:
#             return
#         raw_lines = answer_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
#         lines, prev_blank = [], False
#         for ln in raw_lines:
#             ln = ln.strip()
#             if ln == "":
#                 if not prev_blank:
#                     lines.append("")
#                 prev_blank = True
#             else:
#                 lines.append(ln)
#                 prev_blank = False

#         in_step_block = False
#         for ln in lines:
#             if ln == "":
#                 story.append(Spacer(1, 0.08 * inch))
#                 continue
#             lower_ln = ln.lower()
#             if lower_ln.startswith("final answer"):
#                 story.append(Paragraph(f"<b>{escape(ln)}</b>", final_style))
#                 continue
#             if any(lower_ln.startswith(f"step {d}") for d in ["1", "2", "3"]):
#                 in_step_block = True
#                 story.append(Paragraph(f"<b>{escape(ln)}</b>", step_style))
#                 continue
#             protected = (ln
#                 .replace("<sub>",  "__SUB_OPEN__")
#                 .replace("</sub>", "__SUB_CLOSE__")
#                 .replace("<sup>",  "__SUP_OPEN__")
#                 .replace("</sup>", "__SUP_CLOSE__"))
#             protected = escape(protected)
#             restored = (protected
#                 .replace("__SUB_OPEN__",  "<sub>")
#                 .replace("__SUB_CLOSE__", "</sub>")
#                 .replace("__SUP_OPEN__",  "<sup>")
#                 .replace("__SUP_CLOSE__", "</sup>"))
#             looks_like_math = any(s in ln for s in ["=", "/", "×", "*", "^", "(", ")", "∑", "√"])
#             if in_step_block and looks_like_math:
#                 story.append(Paragraph(restored, equation_style))
#             else:
#                 story.append(Paragraph(restored, step_style))

#     def generate_pdfs(
#         self,
#         content: str,
#         questions_path: str,
#         answers_path: str,
#         course_code: str = "",
#         title: str = "",
#         num_mcq: int = 20,
#         num_tf: int = 10,
#         num_written: int = 10,
#     ):
#         worksheet = self.generate(content, course_code, title, num_mcq, num_tf, num_written)
#         print("📄 Creating PDFs...")
#         self._create_questions_pdf(worksheet, questions_path, course_code, title)
#         self._create_answers_pdf(worksheet, answers_path, course_code, title)
#         print(f"✅ Questions PDF: {questions_path}")
#         print(f"✅ Answers PDF:   {answers_path}")
#         return (questions_path, answers_path)

#     def _create_questions_pdf(self, worksheet, path, course_code, title):
#         doc    = SimpleDocTemplate(path, pagesize=letter)
#         styles = getSampleStyleSheet()
#         story  = []

#         title_style = ParagraphStyle(
#             "CustomTitle", parent=styles["Heading1"],
#             fontSize=18, textColor=colors.HexColor("#1a237e"),
#             spaceAfter=30, alignment=TA_CENTER,
#         )
#         story.append(Paragraph(f"Worksheet: {escape(title)}", title_style))
#         story.append(Paragraph(f"Course: {escape(course_code)}", styles["Normal"]))
#         story.append(Spacer(1, 0.2 * inch))
#         story.append(Paragraph("<b>Student Name:</b> _______________________", styles["Normal"]))
#         story.append(Spacer(1, 0.3 * inch))

#         if worksheet.get("mcq"):
#             story.append(Paragraph("<b>Part I: Multiple Choice Questions</b>", styles["Heading2"]))
#             story.append(Spacer(1, 0.15 * inch))
#             for i, q in enumerate(worksheet["mcq"], 1):
#                 story.append(Paragraph(f"<b>{i}. {escape(q.get('question',''))}</b>", styles["Normal"]))
#                 for ltr in ["A", "B", "C", "D"]:
#                     story.append(Paragraph(f"   {ltr}. {escape(q.get('options',{}).get(ltr,''))}", styles["Normal"]))
#                 story.append(Spacer(1, 0.12 * inch))
#             story.append(PageBreak())

#         if worksheet.get("true_false"):
#             story.append(Paragraph("<b>Part II: True / False</b>", styles["Heading2"]))
#             story.append(Paragraph("Write True or False for each statement.", styles["Normal"]))
#             story.append(Spacer(1, 0.15 * inch))
#             for i, q in enumerate(worksheet["true_false"], 1):
#                 story.append(Paragraph(f"<b>{i}.</b> _____ {escape(q.get('statement',''))}", styles["Normal"]))
#                 story.append(Spacer(1, 0.08 * inch))
#             story.append(PageBreak())

#         if worksheet.get("written"):
#             story.append(Paragraph("<b>Part III: Written Questions</b>", styles["Heading2"]))
#             story.append(Spacer(1, 0.15 * inch))
#             for i, q in enumerate(worksheet["written"], 1):
#                 story.append(Paragraph(f"<b>{i}. {escape(q.get('question',''))}</b>", styles["Normal"]))
#                 story.append(Spacer(1, 0.35 * inch))
#                 for _ in range(4):
#                     story.append(Paragraph("_" * 80, styles["Normal"]))
#                     story.append(Spacer(1, 0.06 * inch))
#                 story.append(Spacer(1, 0.12 * inch))

#         doc.build(story)

#     def _create_answers_pdf(self, worksheet, path, course_code, title):
#         doc    = SimpleDocTemplate(path, pagesize=letter)
#         styles = getSampleStyleSheet()
#         story  = []

#         title_style   = ParagraphStyle("AT", parent=styles["Heading1"],
#             fontSize=18, textColor=colors.HexColor("#1b5e20"),
#             spaceAfter=30, alignment=TA_CENTER)
#         step_style     = ParagraphStyle("SS", parent=styles["Normal"],
#             fontSize=11, leading=15, spaceAfter=6)
#         equation_style = ParagraphStyle("ES", parent=styles["Normal"],
#             fontSize=14, leading=18, alignment=TA_CENTER,
#             spaceBefore=6, spaceAfter=10)
#         final_style    = ParagraphStyle("FS", parent=styles["Normal"],
#             fontSize=12, leading=16, spaceBefore=8, spaceAfter=12,
#             textColor=colors.HexColor("#0d47a1"))

#         story.append(Paragraph(f"Answer Key: {escape(title)}", title_style))
#         story.append(Paragraph(f"Course: {escape(course_code)}", styles["Normal"]))
#         story.append(Spacer(1, 0.25 * inch))

#         if worksheet.get("mcq"):
#             story.append(Paragraph("<b>Part I: MCQ Answers</b>", styles["Heading2"]))
#             story.append(Spacer(1, 0.12 * inch))
#             for i, q in enumerate(worksheet["mcq"], 1):
#                 story.append(Paragraph(f"<b>{i}. Answer:</b> {escape(q.get('correct_answer',''))}", styles["Normal"]))
#                 story.append(Spacer(1, 0.08 * inch))
#             story.append(PageBreak())

#         if worksheet.get("true_false"):
#             story.append(Paragraph("<b>Part II: True / False Answers</b>", styles["Heading2"]))
#             story.append(Spacer(1, 0.12 * inch))
#             for i, q in enumerate(worksheet["true_false"], 1):
#                 story.append(Paragraph(f"<b>{i}. Answer:</b> {escape(q.get('correct_answer',''))}", styles["Normal"]))
#                 story.append(Paragraph(f"Statement: {escape(q.get('statement',''))}", styles["Normal"]))
#                 story.append(Spacer(1, 0.10 * inch))
#             story.append(PageBreak())

#         if worksheet.get("written"):
#             story.append(Paragraph("<b>Part III: Written Answers</b>", styles["Heading2"]))
#             story.append(Spacer(1, 0.12 * inch))
#             for i, q in enumerate(worksheet["written"], 1):
#                 story.append(Paragraph(f"<b>{i}. {escape(q.get('question',''))}</b>", styles["Normal"]))
#                 story.append(Spacer(1, 0.08 * inch))
#                 story.append(Paragraph("<b>Answer:</b>", styles["Normal"]))
#                 self._append_multiline_solution(
#                     story, q.get("answer", ""),
#                     step_style, equation_style, final_style,
#                 )
#                 story.append(Spacer(1, 0.15 * inch))

#         doc.build(story)