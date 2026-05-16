from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage  # FIX 1: correct import path
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




_MATH_RULES = """
========================
MATHEMATICAL REQUIREMENTS
========================

If the lecture contains equations, formulas, derivations, or numerical relationships:

1) DO NOT ask students to simply write or restate equations in the QUESTION.
2) Generate calculation-based problems.
3) Provide numerical values for some parameters and ask to calculate the missing variable.
4) Include BOTH:
   - Direct substitution problems.
   - Indirect / multi-step / conceptual problems that test understanding.
5) Questions must test:
   - Variable relationships
   - Interpretation of parameters
   - Application under different conditions (e.g., change in load, power factor, scaling, etc.)
6) Do NOT introduce equations that are not explicitly present in the content.
"""

_EQUATION_COVERAGE_RULES = """
========================
EQUATION COVERAGE CONSTRAINTS (HARD)
========================

If the content contains more than 3 distinct equations/relationships:

1) Diversity requirement (mandatory):
   - The WRITTEN section MUST use AT LEAST min(6, number_of_distinct_equations_in_content) different equations/relationships.
   - No single equation/relationship may be used in more than 3 written questions.

2) Coverage requirement (mandatory):
   - Distribute written questions across the FULL set of equation types/topics.
   - Ensure at least one written question targets EACH major equation group.

3) Difficulty requirement (mandatory):
   - Include BOTH direct (single-step) AND indirect/advanced (multi-step, rearranging, combining) questions.

4) Anti-pattern rule (mandatory):
   - DO NOT generate many variants of the same template with only numbers changed.
   - If you reuse an equation, it must test a clearly different skill.

5) Self-check rule (mandatory):
   - Before producing final JSON, verify coverage, repetition limits, and equation group completeness.
"""

_ANSWER_FORMAT_RULES = """
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
- Answer in 2-4 clear sentences.
"""

_GENERAL_RULES = """
========================
GENERAL RULES
========================

- No repeated questions/statements.
- Cover the full content across all topics.
- Keep questions concise.
- Ensure difficulty progression (basic -> intermediate -> advanced).
- Output VALID JSON ONLY.
- No markdown.
- No explanations.
- No extra text outside JSON.
"""

# Per-section JSON schemas used in chunked generation
_MCQ_SCHEMA = """
{
  "mcq": [
    {
      "question": "...",
      "options": {"A":"...","B":"...","C":"...","D":"..."},
      "correct_answer": "A"
    }
  ]
}
"""

_TF_SCHEMA = """
{
  "true_false": [
    {
      "statement": "...",
      "correct_answer": "True"
    }
  ]
}
"""

_WRITTEN_SCHEMA = """
{
  "written": [
    {
      "question": "...",
      "answer": "Step 1: State the equation:\\n...\\n\\nStep 2: Substitute the given values:\\n...\\n\\nStep 3: Compute and solve:\\n...\\n\\nFinal Answer: ..."
    }
  ]
}
"""

# Default model used when none is provided
_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Max JSON-parse retries per chunk
_MAX_RETRIES = 2

# ── Chunking settings ──────────────────────────────────────────────────────
# Free-tier TPM = 12,000.  Prompt rules cost ~8,500 tokens worst-case,
# leaving ~3,000 safe tokens for content per request.
# Each chunk is CHUNK_SIZE tokens; adjacent chunks share CHUNK_OVERLAP tokens
# so concepts that span a boundary are not silently dropped.
_MAX_CONTENT_TOKENS = 3000   # hard cap for a single-chunk content (fallback)
_CHUNK_SIZE         = 2500   # content tokens per chunk
_CHUNK_OVERLAP      = 200    # overlap between consecutive chunks

# Similarity threshold for deduplication (0–1).  Questions whose longest
# common subsequence ratio exceeds this are considered duplicates.
_DEDUP_THRESHOLD = 0.85


class WorksheetGenerator:
    """Generate comprehensive worksheets with MCQ, True/False, and written questions."""

    # FIX 6: model is now a configurable constructor parameter
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 8000,
    ):
        # FIX 2: single consistent path for resolving the API key
        self.api_key = api_key or os.getenv("GROQ_API_KEY_WORKSHEET")
        if not self.api_key:
            raise ValueError(
                "No API key supplied. Pass api_key= or set GROQ_API_KEY_WORKSHEET."
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

    # ------------------------------------------------------------------ utils

    def count_tokens(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        return max(1, len(text) // 4)

    def _truncate_content(self, text: str, max_tokens: int = _MAX_CONTENT_TOKENS) -> str:
        """Truncate content to max_tokens so every prompt fits within the TPM limit."""
        if self.encoding:
            tokens = self.encoding.encode(text)
            if len(tokens) > max_tokens:
                text = self.encoding.decode(tokens[:max_tokens])
                print(f"   ✂️  Content truncated to {max_tokens} tokens to fit model TPM limit.")
        else:
            # Fallback: rough char estimate (1 token ≈ 4 chars)
            char_limit = max_tokens * 4
            if len(text) > char_limit:
                text = text[:char_limit]
                print(f"   ✂️  Content truncated to ~{max_tokens} tokens (char estimate).")
        return text

    # ------------------------------------------------------------------ chunking

    def _split_into_chunks(self, text: str) -> list[str]:
        """
        Split *text* into overlapping token windows of _CHUNK_SIZE tokens,
        with _CHUNK_OVERLAP tokens of overlap between consecutive chunks.
        Returns a list of decoded text strings (one per chunk).
        If the whole text fits in a single chunk it is returned as-is.
        """
        if self.encoding:
            tokens = self.encoding.encode(text)
        else:
            # Rough fallback: 1 token ≈ 4 chars
            tokens = list(text)   # treat each char as a "token"

        if len(tokens) <= _CHUNK_SIZE:
            return [text]   # no splitting needed

        chunks, start = [], 0
        while start < len(tokens):
            end = min(start + _CHUNK_SIZE, len(tokens))
            chunk_tokens = tokens[start:end]
            if self.encoding:
                chunk_text = self.encoding.decode(chunk_tokens)
            else:
                chunk_text = "".join(chunk_tokens)
            chunks.append(chunk_text)
            if end == len(tokens):
                break
            start += _CHUNK_SIZE - _CHUNK_OVERLAP   # slide with overlap

        print(f"   📦 Content split into {len(chunks)} chunk(s) "
              f"({_CHUNK_SIZE}-token windows, {_CHUNK_OVERLAP}-token overlap).")
        return chunks

    # ------------------------------------------------------------------ deduplication

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """
        Compute a simple character-level similarity ratio between two strings.
        Uses the same algorithm as difflib.SequenceMatcher but inline so there
        is no extra import dependency.
        """
        import difflib
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _deduplicate(self, items: list[dict], text_key: str) -> list[dict]:
        """
        Remove near-duplicate entries from *items*.
        Two items are duplicates when their *text_key* field similarity
        exceeds _DEDUP_THRESHOLD.  The first occurrence is kept.
        """
        kept: list[dict] = []
        for candidate in items:
            cand_text = candidate.get(text_key, "")
            is_dup = any(
                self._similarity(cand_text, seen.get(text_key, "")) >= _DEDUP_THRESHOLD
                for seen in kept
            )
            if not is_dup:
                kept.append(candidate)
        removed = len(items) - len(kept)
        if removed:
            print(f"   🗑️  Removed {removed} duplicate(s) from '{text_key}' pool.")
        return kept

    # ------------------------------------------------------------------ JSON helpers


    def _extract_first_json_object(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"```(?:json)?", "", text)
        text = text.replace("```", "").strip()
        text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")

        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in model response.")

        depth, end = 0, None
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
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)
        return json_str

    def _parse_json(self, text: str) -> dict:
        json_str = self._extract_first_json_object(text)
        return json.loads(json_str)

    # ------------------------------------------------------------------ prompts

    def _build_mcq_prompt(self, content: str, course_code: str, title: str, num_mcq: int) -> str:
        return f"""
Generate EXACTLY {num_mcq} MCQ questions STRICTLY from the provided content.

Course: {course_code}
Title: {title}

CONTENT:
{content}

{_MATH_RULES}
{_GENERAL_RULES}

Output ONLY this JSON schema (no other text):
{_MCQ_SCHEMA}
"""

    def _build_tf_prompt(self, content: str, course_code: str, title: str, num_tf: int) -> str:
        return f"""
Generate EXACTLY {num_tf} True/False statements STRICTLY from the provided content.

Course: {course_code}
Title: {title}

CONTENT:
{content}

{_GENERAL_RULES}

Output ONLY this JSON schema (no other text):
{_TF_SCHEMA}
"""

    def _build_written_prompt(self, content: str, course_code: str, title: str, num_written: int) -> str:
        return f"""
Generate EXACTLY {num_written} written questions STRICTLY from the provided content.

Course: {course_code}
Title: {title}

CONTENT:
{content}

{_MATH_RULES}
{_EQUATION_COVERAGE_RULES}
{_ANSWER_FORMAT_RULES}
{_GENERAL_RULES}

Output ONLY this JSON schema (no other text):
{_WRITTEN_SCHEMA}
"""

    # ------------------------------------------------------------------ LLM call with retry

    # FIX 3: retry logic — each chunk retried independently up to _MAX_RETRIES times
    def _invoke_with_retry(self, prompt: str, section_key: str) -> list:
        """
        Call the LLM and parse JSON for a single section.
        Retries up to _MAX_RETRIES times on parse failure.
        Returns the list under section_key, or [] on total failure.
        """
        messages = [
            SystemMessage(content="You are an expert educational assessment creator. Output VALID JSON ONLY."),
            HumanMessage(content=prompt),
        ]

        last_error = None
        for attempt in range(1, _MAX_RETRIES + 2):  # attempts: 1, 2, 3
            try:
                response = self.llm.invoke(messages)
                parsed = self._parse_json(response.content or "")
                result = parsed.get(section_key, [])
                if not isinstance(result, list):
                    raise ValueError(f"Expected a list under '{section_key}', got {type(result)}")
                return result
            except Exception as e:
                last_error = e
                print(f"   ⚠️  Attempt {attempt}/{_MAX_RETRIES + 1} failed for '{section_key}': {e}")
                # 413 = request too large: retrying with the same prompt won't help
                if '413' in str(e):
                    print(f"   🚫 Request too large — skipping retries for '{section_key}'.")
                    break
                if attempt <= _MAX_RETRIES:
                    print(f"   🔄 Retrying...")

        print(f"   ❌ All attempts failed for '{section_key}'. Returning empty list. Last error: {last_error}")
        return []

    # ------------------------------------------------------------------ chunked generation (FIX 7)

    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = "",
        num_mcq: int = 20,
        num_tf: int = 10,
        num_written: int = 15,  # FIX 5: consistent default across all methods
    ) -> dict:
        """
        Generate all worksheet sections using overlapping content chunks.

        Strategy
        --------
        1. Split the lecture into overlapping windows of _CHUNK_SIZE tokens.
        2. For each chunk generate MCQ, TF, and Written questions independently
           (each as a separate LLM call with retry).
        3. Pool all results across chunks, deduplicate near-identical items,
           then trim to the requested counts.

        This ensures full lecture coverage without ever exceeding the free-tier
        TPM limit, at the cost of (n_chunks × 3) API calls.
        """
        print("📝 Generating worksheet (chunk-and-merge mode)...")
        print(f"   MCQ: {num_mcq} | TF: {num_tf} | Written: {num_written}")
        print(f"   Content tokens (approx): {self.count_tokens(content)}")
        print(f"   Model: {self.model}")

        chunks = self._split_into_chunks(content)
        n = len(chunks)

        # How many items to request from each chunk so that after dedup we
        # still have enough to meet the final targets.
        # Ask for ceil(target / n) + a small surplus buffer (2 extra per chunk).
        import math
        mcq_per_chunk     = math.ceil(num_mcq     / n) + 2
        tf_per_chunk      = math.ceil(num_tf      / n) + 2
        written_per_chunk = math.ceil(num_written / n) + 2

        all_mcq, all_tf, all_written = [], [], []

        for idx, chunk in enumerate(chunks, 1):
            print(f"\n   ── Chunk {idx}/{n} ──────────────────────────────")

            print(f"   [MCQ] requesting {mcq_per_chunk} questions...")
            chunk_mcq = self._invoke_with_retry(
                self._build_mcq_prompt(chunk, course_code, title, mcq_per_chunk),
                "mcq",
            )
            all_mcq.extend(chunk_mcq)

            print(f"   [TF]  requesting {tf_per_chunk} statements...")
            chunk_tf = self._invoke_with_retry(
                self._build_tf_prompt(chunk, course_code, title, tf_per_chunk),
                "true_false",
            )
            all_tf.extend(chunk_tf)

            print(f"   [Written] requesting {written_per_chunk} questions...")
            chunk_written = self._invoke_with_retry(
                self._build_written_prompt(chunk, course_code, title, written_per_chunk),
                "written",
            )
            all_written.extend(chunk_written)

        # ── Deduplicate across chunks ──────────────────────────────────────
        print("\n   🔍 Deduplicating...")
        all_mcq     = self._deduplicate(all_mcq,     text_key="question")
        all_tf      = self._deduplicate(all_tf,      text_key="statement")
        all_written = self._deduplicate(all_written, text_key="question")

        # ── Trim to requested counts (take first N after dedup) ───────────
        mcq     = all_mcq[:num_mcq]
        true_false = all_tf[:num_tf]
        written = all_written[:num_written]

        if len(mcq) < num_mcq:
            print(f"   ⚠️  Only {len(mcq)}/{num_mcq} MCQ available after dedup.")
        if len(true_false) < num_tf:
            print(f"   ⚠️  Only {len(true_false)}/{num_tf} TF available after dedup.")
        if len(written) < num_written:
            print(f"   ⚠️  Only {len(written)}/{num_written} Written available after dedup.")

        worksheet = {"mcq": mcq, "true_false": true_false, "written": written}

        print(
            f"\n✅ Generated MCQ={len(mcq)}, TF={len(true_false)}, Written={len(written)}"
        )
        return worksheet

    # ------------------------------------------------------------------ PDF helpers

    def _append_multiline_solution(
        self, story, answer_text: str, step_style, equation_style, final_style
    ):
        if not answer_text:
            return

        raw_lines = answer_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        lines, prev_blank = [], False
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

            if lower_ln.startswith("final answer"):
                safe = escape(ln)
                story.append(Paragraph(f"<b>{safe}</b>", final_style))
                continue

            if re.match(r"step\s+[123]", lower_ln):
                in_step_block = True
                safe = escape(ln)
                story.append(Paragraph(f"<b>{safe}</b>", step_style))
                continue

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

            looks_like_math = any(
                sym in ln for sym in ["=", "/", "×", "*", "^", "(", ")", "∑", "√"]
            )
            if in_step_block and looks_like_math:
                story.append(Paragraph(restored, equation_style))
            else:
                story.append(Paragraph(restored, step_style))

    # ------------------------------------------------------------------ public API

    def generate_pdfs(
        self,
        content: str,
        questions_path: str,
        answers_path: str,
        course_code: str = "",
        title: str = "",
        num_mcq: int = 20,
        num_tf: int = 10,
        num_written: int = 15,  # FIX 5: consistent default
    ):
        worksheet = self.generate(content, course_code, title, num_mcq, num_tf, num_written)

        print("\n📄 Creating PDFs...")
        self._create_questions_pdf(worksheet, questions_path, course_code, title)
        self._create_answers_pdf(worksheet, answers_path, course_code, title)

        print(f"✅ Questions PDF: {questions_path}")
        print(f"✅ Answers PDF:   {answers_path}")
        return questions_path, answers_path

    # ------------------------------------------------------------------ PDF builders

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

        if worksheet.get("mcq"):
            story.append(Paragraph("<b>Part I: Multiple Choice Questions</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.15 * inch))
            for i, q in enumerate(worksheet["mcq"], 1):
                story.append(Paragraph(f"<b>{i}. {escape(q.get('question', ''))}</b>", styles["Normal"]))
                for letter_ in ["A", "B", "C", "D"]:
                    story.append(
                        Paragraph(
                            f"   {letter_}. {escape(q.get('options', {}).get(letter_, ''))}",
                            styles["Normal"],
                        )
                    )
                story.append(Spacer(1, 0.12 * inch))
            story.append(PageBreak())

        if worksheet.get("true_false"):
            story.append(Paragraph("<b>Part II: True / False</b>", styles["Heading2"]))
            story.append(Paragraph("Write True or False for each statement.", styles["Normal"]))
            story.append(Spacer(1, 0.15 * inch))
            for i, q in enumerate(worksheet["true_false"], 1):
                story.append(
                    Paragraph(f"<b>{i}.</b> _____ {escape(q.get('statement', ''))}", styles["Normal"])
                )
                story.append(Spacer(1, 0.08 * inch))
            story.append(PageBreak())

        if worksheet.get("written"):
            story.append(Paragraph("<b>Part III: Written Questions</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.15 * inch))
            for i, q in enumerate(worksheet["written"], 1):
                story.append(
                    Paragraph(f"<b>{i}. {escape(q.get('question', ''))}</b>", styles["Normal"])
                )
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

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#1b5e20"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        step_style = ParagraphStyle(
            "StepStyle", parent=styles["Normal"], fontSize=11, leading=15, spaceAfter=6
        )
        equation_style = ParagraphStyle(
            "EquationStyle",
            parent=styles["Normal"],
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=10,
        )
        final_style = ParagraphStyle(
            "FinalStyle",
            parent=styles["Normal"],
            fontSize=12,
            leading=16,
            spaceBefore=8,
            spaceAfter=12,
            textColor=colors.HexColor("#0d47a1"),
        )

        story.append(Paragraph(f"Answer Key: {escape(title)}", title_style))
        story.append(Paragraph(f"Course: {escape(course_code)}", styles["Normal"]))
        story.append(Spacer(1, 0.25 * inch))

        if worksheet.get("mcq"):
            story.append(Paragraph("<b>Part I: MCQ Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["mcq"], 1):
                story.append(
                    Paragraph(
                        f"<b>{i}. Answer:</b> {escape(q.get('correct_answer', ''))}",
                        styles["Normal"],
                    )
                )
                story.append(Spacer(1, 0.08 * inch))
            story.append(PageBreak())

        if worksheet.get("true_false"):
            story.append(Paragraph("<b>Part II: True / False Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["true_false"], 1):
                story.append(
                    Paragraph(
                        f"<b>{i}. Answer:</b> {escape(q.get('correct_answer', ''))}",
                        styles["Normal"],
                    )
                )
                story.append(
                    Paragraph(f"Statement: {escape(q.get('statement', ''))}", styles["Normal"])
                )
                story.append(Spacer(1, 0.10 * inch))
            story.append(PageBreak())

        if worksheet.get("written"):
            story.append(Paragraph("<b>Part III: Written Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["written"], 1):
                story.append(
                    Paragraph(f"<b>{i}. {escape(q.get('question', ''))}</b>", styles["Normal"])
                )
                story.append(Spacer(1, 0.08 * inch))
                story.append(Paragraph("<b>Answer:</b>", styles["Normal"]))
                self._append_multiline_solution(
                    story,
                    q.get("answer", ""),
                    step_style=step_style,
                    equation_style=equation_style,
                    final_style=final_style,
                )
                story.append(Spacer(1, 0.15 * inch))

        doc.build(story)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_text_file(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Lecture file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise ValueError(f"Lecture file is empty: {path}")
    return content


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    content = read_text_file(r"1_introduction_to_infosec_text.txt")

    # FIX 6: model passed explicitly — easy to swap
    generator = WorksheetGenerator(
        model="llama-3.3-70b-versatile",
    )

    generator.generate_pdfs(
        content=content,
        questions_path="worksheet12_questions.pdf",
        answers_path="worksheet12_answers.pdf",
        course_code="InfoSec1705",
        title="InfoSec Worksheet",
        num_mcq=20,
        num_tf=10,
        num_written=15,
    )

    print("\n✅ Complete! Check the PDF files.")