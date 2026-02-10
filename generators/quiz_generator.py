from langchain_groq import ChatGroq
from langchain.messages import SystemMessage, HumanMessage
import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from typing import Optional
import tiktoken


class QuizGenerator:
    """Generate comprehensive quizzes with MCQ questions"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found")
        
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=8000,
        )
        
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        return len(text) // 4
    
    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = "",
        num_questions: int = 20
    ) -> dict:
        """Generate quiz questions"""
        
        print(f"📝 Generating quiz with {num_questions} questions...")
        
        
        prompt = self._create_prompt(content, course_code, title, num_questions)
        
        messages = [
            SystemMessage(content="You are an expert quiz creator. Generate challenging questions that test deep understanding."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        try:
            quiz = self._parse_json(response.content)
            print(f"✅ Generated {len(quiz.get('questions', []))} questions")
            return quiz
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"questions": []}
    
    
    def _create_prompt(self, content: str, course_code: str, title: str, num_questions: int) -> str:
        return f"""Create a comprehensive quiz.

Course: {course_code}
Title: {title}

Content:
{content}

Generate {num_questions} multiple choice questions.

REQUIREMENTS:
- Cover ALL major topics evenly
- Mix difficulty: 30% easy, 50% medium, 20% hard
- 4 options per question (A, B, C, D)
- Only ONE correct answer
- All options should be plausible

RETURN VALID JSON:

{{
    "questions": [
        {{
            "question": "What is machine learning?",
            "options": {{
                "A": "Option 1",
                "B": "Option 2",
                "C": "Option 3",
                "D": "Option 4"
            }},
            "correct_answer": "B"
        }},
        ...{num_questions} total
    ]
}}"""
    
    def _parse_json(self, text: str) -> dict:
        import re
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        return json.loads(text.strip())
    
    def generate_pdfs(
        self,
        content: str,
        quiz_path: str,
        answers_path: str,
        course_code: str = "",
        title: str = "",
        num_questions: int = 20,
        time_limit: int = 30
    ):
        """Generate quiz and answer PDFs"""
        
        quiz = self.generate(content, course_code, title, num_questions)
        
        print(f"📄 Creating PDFs...")
        self._create_quiz_pdf(quiz, quiz_path, course_code, title, time_limit)
        self._create_answers_pdf(quiz, answers_path, course_code, title)
        
        print(f"✅ Quiz PDF: {quiz_path}")
        print(f"✅ Answers PDF: {answers_path}")
        
        return (quiz_path, answers_path)
    
    def _create_quiz_pdf(self, quiz: dict, path: str, course: str, title: str, time_limit: int):
        """Create quiz PDF (no answers)"""
        
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'QuizTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1565c0'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph(f"QUIZ: {title}", title_style))
        story.append(Paragraph(f"Course: {course}", styles['Normal']))
        story.append(Paragraph(f"Time Limit: {time_limit} minutes", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Student info
        story.append(Paragraph("<b>Name:</b> _________________________   <b>Date:</b> __________", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Instructions
        story.append(Paragraph("<b>Instructions:</b>", styles['Heading3']))
        story.append(Paragraph("• Read each question carefully", styles['Normal']))
        story.append(Paragraph("• Choose the BEST answer for each question", styles['Normal']))
        story.append(Paragraph("• Mark your answers clearly", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Questions
        for i, q in enumerate(quiz.get('questions', []), 1):
            # Question
            q_text = f"<b>{i}. {q['question']}</b>"
            story.append(Paragraph(q_text, styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            
            # Options
            for letter_ in ['A', 'B', 'C', 'D']:
                option = q['options'].get(letter_, '')
                story.append(Paragraph(f"   {letter_}. {option}", styles['Normal']))
            
            story.append(Spacer(1, 0.2*inch))
            
            # Page break every 10 questions
            if i % 10 == 0 and i < len(quiz.get('questions', [])):
                story.append(PageBreak())
        
        doc.build(story)
    
    def _create_answers_pdf(self, quiz: dict, path: str, course: str, title: str):
        """Create answer key PDF (answers listed vertically)"""
    
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
    
    # Title
        title_style = ParagraphStyle(
            'AnswerTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#d32f2f'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
    
        story.append(Paragraph(f"ANSWER KEY: {title}", title_style))
        story.append(Paragraph(f"Course: {course}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
    
        # Section title
        story.append(Paragraph("<b>Answer Key:</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2 * inch))
    
        # Vertical answers
        questions = quiz.get('questions', [])
    
        for i, q in enumerate(questions, 1):
            answer = q.get('correct_answer', '?')
            story.append(
                Paragraph(f"<b>{i}.</b> {answer}", styles['Normal'])
            )
            story.append(Spacer(1, 0.1 * inch))
    
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

# if __name__ == "__main__":
#     from dotenv import load_dotenv
#     load_dotenv()
    
#     content =read_text_file("1_introduction_to_infosec_text.txt")
    
#     generator = QuizGenerator()
    
#     generator.generate_pdfs(
#         content=content,
#         quiz_path="quiz.pdf",
#         answers_path="quiz_answers.pdf",
#         course_code="IS101",
#         title="InfoSecurity Quiz",
#         num_questions=15,
#         time_limit=15
#     )
    
#     print("\n✅ Complete!")