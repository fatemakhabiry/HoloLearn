from langchain_groq import ChatGroq
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
        
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.3-70b-versatile",
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

if __name__ == "__main__":
    load_dotenv()

    content = read_text_file("nips_2017_attention_is_all_you_need_paper_text.txt")

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