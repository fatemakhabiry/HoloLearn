from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage  # fixed import path
import os
import json
import re
import math
import difflib
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

import tiktoken


# ── Constants ──────────────────────────────────────────────────────────────────
_DEFAULT_MODEL   = "llama-3.3-70b-versatile"
_MAX_RETRIES     = 2
_CHUNK_SIZE      = 2500   # content tokens per chunk
_CHUNK_OVERLAP   = 200    # overlap between consecutive chunks
_DEDUP_THRESHOLD = 0.85   # similarity ratio above which items are duplicates


class QuizGenerator:
    """Generate comprehensive quizzes with MCQ questions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 8000,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY_QUIZ")
        if not self.api_key:
            raise ValueError(
                "No API key supplied. Pass api_key= or set GROQ_API_KEY_QUIZ."
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

    # ── Chunking ───────────────────────────────────────────────────────────────

    def _split_into_chunks(self, text: str) -> list[str]:
        """Split text into overlapping token windows."""
        if self.encoding:
            tokens = self.encoding.encode(text)
        else:
            tokens = list(text)

        if len(tokens) <= _CHUNK_SIZE:
            return [text]

        chunks, start = [], 0
        while start < len(tokens):
            end = min(start + _CHUNK_SIZE, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens) if self.encoding else "".join(chunk_tokens)
            chunks.append(chunk_text)
            if end == len(tokens):
                break
            start += _CHUNK_SIZE - _CHUNK_OVERLAP

        print(f"   📦 Content split into {len(chunks)} chunk(s) "
              f"({_CHUNK_SIZE}-token windows, {_CHUNK_OVERLAP}-token overlap).")
        return chunks

    # ── Deduplication ──────────────────────────────────────────────────────────

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _deduplicate(self, items: list[dict], text_key: str) -> list[dict]:
        kept: list[dict] = []
        for candidate in items:
            cand_text = candidate.get(text_key, "")
            if not any(
                self._similarity(cand_text, seen.get(text_key, "")) >= _DEDUP_THRESHOLD
                for seen in kept
            ):
                kept.append(candidate)
        removed = len(items) - len(kept)
        if removed:
            print(f"   🗑️  Removed {removed} duplicate(s).")
        return kept

    # ── JSON parsing ───────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> dict:
        text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
        text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON found")
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
            raise ValueError("Unbalanced JSON")
        json_str = text[start:end]
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)
        return json.loads(json_str)

    # ── Prompt ─────────────────────────────────────────────────────────────────

    def _build_prompt(self, content: str, course_code: str, title: str, num_questions: int) -> str:
        return f"""Create a comprehensive quiz STRICTLY from the provided content.

Course: {course_code}
Title: {title}

Content:
{content}

Generate EXACTLY {num_questions} multiple choice questions.

REQUIREMENTS:
- Cover ALL major topics evenly
- Mix difficulty: 30% easy, 50% medium, 20% hard
- 4 options per question (A, B, C, D)
- Only ONE correct answer
- All options should be plausible
- Output VALID JSON ONLY — no markdown, no explanations

RETURN THIS EXACT JSON SCHEMA:
{{
    "questions": [
        {{
            "question": "...",
            "options": {{
                "A": "...",
                "B": "...",
                "C": "...",
                "D": "..."
            }},
            "correct_answer": "B"
        }}
    ]
}}"""

    # ── LLM call with retry ────────────────────────────────────────────────────

    def _invoke_with_retry(self, prompt: str) -> list:
        messages = [
            SystemMessage(content="You are an expert quiz creator. Output VALID JSON ONLY."),
            HumanMessage(content=prompt),
        ]
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 2):
            try:
                response = self.llm.invoke(messages)
                parsed = self._parse_json(response.content or "")
                result = parsed.get("questions", [])
                if not isinstance(result, list):
                    raise ValueError("Expected a list under 'questions'")
                return result
            except Exception as e:
                last_error = e
                print(f"   ⚠️  Attempt {attempt}/{_MAX_RETRIES + 1} failed: {e}")
                if "413" in str(e):
                    print("   🚫 Request too large — skipping retries.")
                    break
                if attempt <= _MAX_RETRIES:
                    print("   🔄 Retrying...")
        print(f"   ❌ All attempts failed. Last error: {last_error}")
        return []

    # ── Main generation ────────────────────────────────────────────────────────

    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = "",
        num_questions: int = 20,
    ) -> dict:
        """
        Generate quiz questions using overlapping content chunks.
        Splits → generates per chunk → deduplicates → trims to requested count.
        """
        print(f"📝 Generating quiz (chunk-and-merge mode)...")
        print(f"   Questions: {num_questions}")
        print(f"   Content tokens (approx): {self.count_tokens(content)}")
        print(f"   Model: {self.model}")

        chunks = self._split_into_chunks(content)
        n = len(chunks)
        per_chunk = math.ceil(num_questions / n) + 2

        all_questions = []
        for idx, chunk in enumerate(chunks, 1):
            print(f"\n   ── Chunk {idx}/{n} — requesting {per_chunk} questions...")
            chunk_qs = self._invoke_with_retry(
                self._build_prompt(chunk, course_code, title, per_chunk)
            )
            all_questions.extend(chunk_qs)

        print("\n   🔍 Deduplicating...")
        all_questions = self._deduplicate(all_questions, text_key="question")

        # ── Interleaved sampling ───────────────────────────────────────────────
        # Naively slicing all_questions[:N] would over-represent chunk 1 because
        # results are ordered chunk-first after dedup.  Instead we round-robin
        # across per-chunk buckets so every part of the lecture contributes
        # roughly equally to the final question set.
        per_chunk_results = []
        idx = 0
        per = math.ceil(num_questions / n) + 2   # same budget used during generation
        for _ in range(n):
            per_chunk_results.append(all_questions[idx : idx + per])
            idx += per

        interleaved = []
        round_idx = 0
        while len(interleaved) < num_questions:
            added_any = False
            for bucket in per_chunk_results:
                if round_idx < len(bucket) and len(interleaved) < num_questions:
                    interleaved.append(bucket[round_idx])
                    added_any = True
            round_idx += 1
            if not added_any:
                break   # all buckets exhausted

        questions = interleaved

        if len(questions) < num_questions:
            print(f"   ⚠️  Only {len(questions)}/{num_questions} questions available after dedup.")

        print(f"\n✅ Generated {len(questions)} questions "
              f"(interleaved across {n} chunk(s)).")
        return {"questions": questions}

    # ── PDF generation ─────────────────────────────────────────────────────────

    def generate_pdfs(
        self,
        content: str,
        quiz_path: str,
        answers_path: str,
        course_code: str = "",
        title: str = "",
        num_questions: int = 20,
        time_limit: int = 30,
    ):
        quiz = self.generate(content, course_code, title, num_questions)

        print("📄 Creating PDFs...")
        self._create_quiz_pdf(quiz, quiz_path, course_code, title, time_limit)
        self._create_answers_pdf(quiz, answers_path, course_code, title)

        print(f"✅ Quiz PDF:    {quiz_path}")
        print(f"✅ Answers PDF: {answers_path}")
        return quiz_path, answers_path

    def _create_quiz_pdf(self, quiz: dict, path: str, course: str, title: str, time_limit: int):
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "QuizTitle", parent=styles["Heading1"],
            fontSize=20, textColor=colors.HexColor("#1565c0"),
            spaceAfter=20, alignment=TA_CENTER,
        )

        story.append(Paragraph(f"QUIZ: {title}", title_style))
        story.append(Paragraph(f"Course: {course}", styles["Normal"]))
        story.append(Paragraph(f"Time Limit: {time_limit} minutes", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(
            "<b>Name:</b> _________________________   <b>Date:</b> __________",
            styles["Normal"],
        ))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("<b>Instructions:</b>", styles["Heading3"]))
        story.append(Paragraph("• Read each question carefully", styles["Normal"]))
        story.append(Paragraph("• Choose the BEST answer for each question", styles["Normal"]))
        story.append(Paragraph("• Mark your answers clearly", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        questions = quiz.get("questions", [])
        for i, q in enumerate(questions, 1):
            # FIX: use .get() so malformed LLM output never crashes PDF build
            story.append(Paragraph(f"<b>{i}. {q.get('question', '')}</b>", styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))
            for letter_ in ["A", "B", "C", "D"]:
                story.append(Paragraph(
                    f"   {letter_}. {q.get('options', {}).get(letter_, '')}",
                    styles["Normal"],
                ))
            story.append(Spacer(1, 0.2 * inch))
            if i % 10 == 0 and i < len(questions):
                story.append(PageBreak())

        doc.build(story)

    def _create_answers_pdf(self, quiz: dict, path: str, course: str, title: str):
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "AnswerTitle", parent=styles["Heading1"],
            fontSize=20, textColor=colors.HexColor("#d32f2f"),
            spaceAfter=20, alignment=TA_CENTER,
        )

        story.append(Paragraph(f"ANSWER KEY: {title}", title_style))
        story.append(Paragraph(f"Course: {course}", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("<b>Answer Key:</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        for i, q in enumerate(quiz.get("questions", []), 1):
            story.append(Paragraph(f"<b>{i}.</b> {q.get('correct_answer', '?')}", styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))

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

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    content =read_text_file("1_introduction_to_infosec_text.txt")
    
    generator = QuizGenerator()
    
    generator.generate_pdfs(
        content=content,
        quiz_path="quiz.pdf",
        answers_path="quiz_answers.pdf",
        course_code="IS101",
        title="InfoSecurity Quiz",
        num_questions=15,
        time_limit=15
    )
    
    print("\n✅ Complete!")




