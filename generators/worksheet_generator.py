from langchain_groq import ChatGroq
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


class WorksheetGenerator:
    """Generate comprehensive worksheets with MCQ, True/False, and written questions"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found")

        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.2,  # lower temp => cleaner JSON, fewer duplicates
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

RULES:
- No repeated questions/statements.
- Cover the full content across all topics.
- Keep questions concise.
- Written answers must be 2–4 sentences.
- Output VALID JSON ONLY. No markdown. No explanations. No extra text.

JSON SCHEMA (MUST MATCH EXACTLY):
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
      "answer": "..."
    }}
  ]
}}
"""

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

        story.append(Paragraph(f"Worksheet: {title}", title_style))
        story.append(Paragraph(f"Course: {course_code}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("<b>Student Name:</b> _______________________", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Part I: MCQ
        if worksheet.get("mcq"):
            story.append(Paragraph("<b>Part I: Multiple Choice Questions</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.15 * inch))

            for i, q in enumerate(worksheet["mcq"], 1):
                story.append(Paragraph(f"<b>{i}. {q['question']}</b>", styles["Normal"]))
                for letter_ in ["A", "B", "C", "D"]:
                    story.append(Paragraph(f"   {letter_}. {q['options'].get(letter_, '')}", styles["Normal"]))
                story.append(Spacer(1, 0.12 * inch))

            story.append(PageBreak())

        # Part II: True/False
        if worksheet.get("true_false"):
            story.append(Paragraph("<b>Part II: True / False</b>", styles["Heading2"]))
            story.append(Paragraph("Write True or False for each statement.", styles["Normal"]))
            story.append(Spacer(1, 0.15 * inch))

            for i, q in enumerate(worksheet["true_false"], 1):
                story.append(Paragraph(f"<b>{i}.</b> _____ {q['statement']}", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))

            story.append(PageBreak())

        # Part III: Written
        if worksheet.get("written"):
            story.append(Paragraph("<b>Part III: Written Questions</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.15 * inch))

            for i, q in enumerate(worksheet["written"], 1):
                story.append(Paragraph(f"<b>{i}. {q['question']}</b>", styles["Normal"]))
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
            textColor=colors.HexColor("#c62828"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        story.append(Paragraph(f"Answer Key: {title}", title_style))
        story.append(Paragraph(f"Course: {course_code}", styles["Normal"]))
        story.append(Spacer(1, 0.25 * inch))

        # MCQ answers
        if worksheet.get("mcq"):
            story.append(Paragraph("<b>Part I: MCQ Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["mcq"], 1):
                story.append(Paragraph(f"<b>{i}. Answer:</b> {q.get('correct_answer','')}", styles["Normal"]))
                story.append(Spacer(1, 0.08 * inch))
            story.append(PageBreak())

        # TF answers
        if worksheet.get("true_false"):
            story.append(Paragraph("<b>Part II: True / False Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["true_false"], 1):
                story.append(Paragraph(f"<b>{i}. Answer:</b> {q.get('correct_answer','')}", styles["Normal"]))
                story.append(Paragraph(f"Statement: {q.get('statement','')}", styles["Normal"]))
                story.append(Spacer(1, 0.10 * inch))
            story.append(PageBreak())

        # Written answers
        if worksheet.get("written"):
            story.append(Paragraph("<b>Part III: Written Answers</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.12 * inch))
            for i, q in enumerate(worksheet["written"], 1):
                story.append(Paragraph(f"<b>{i}. {q.get('question','')}</b>", styles["Normal"]))
                story.append(Paragraph(f"<b>Answer:</b> {q.get('answer','')}", styles["Normal"]))
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
    content = read_text_file("nips_2017_attention_is_all_you_need_paper_text.txt")

    generator = WorksheetGenerator()

    generator.generate_pdfs(
        content=content,
        questions_path="worksheet2_questions.pdf",
        answers_path="worksheet2_answers.pdf",
        course_code="AI101",
        title="Introduction to Transformers",
        num_mcq=20,
        num_tf=10,
        num_written=15,
    )

    print("\n✅ Complete! Check the PDF files.")
