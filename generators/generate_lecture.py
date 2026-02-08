import os
from dotenv import load_dotenv
load_dotenv()
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import re


class LectureGenerator:
    """
    Professional lecture generator with mathematical equation support
    
    This class handles:
    1. Content extraction from multiple sources (preserving mathematical notation)
    2. Lecture structure generation using LLM
    3. Professional PDF creation with equations
    """
    
    def __init__(self, groq_api_key: str, model_name: str = "llama-3.3-70b-versatile"):
        """
        Initialize the lecture generator
        
        Args:
            groq_api_key: Your Groq API key
            model_name: Groq model to use (default: llama-3.3-70b-versatile)
        """
        # Initialize Groq LLM with increased token limit for mathematical content
        self.llm = ChatGroq(
            api_key=os.os.getenv("GROQ_API_KEY"),
            model_name=model_name,
            temperature=0.5,
            max_tokens=8000  
        )
        
        # Text splitter for handling long documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=500,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # PDF styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configure custom PDF styles including math equation styles"""
        
        # Main title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Subsection heading style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#3949ab'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=colors.black,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14
        ))
        
        # Mathematical equation style (with wrapping support)
        self.styles.add(ParagraphStyle(
            name='EquationStyle',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#000000'),
            leftIndent=40,
            rightIndent=40,
            spaceAfter=10,
            spaceBefore=10,
            alignment=TA_LEFT,
            backColor=colors.HexColor('#f5f5f5'),
            borderPadding=8,
            wordWrap='CJK'  
        ))
        
        # Mathematical derivation style (with proper wrapping)
        self.styles.add(ParagraphStyle(
            name='DerivationStyle',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=colors.HexColor('#1a237e'),
            leftIndent=30,
            rightIndent=30,
            spaceAfter=8,
            spaceBefore=8,
            alignment=TA_LEFT,
            backColor=colors.HexColor('#e8eaf6'),
            borderPadding=10,
            wordWrap='CJK'  # Enable word wrapping
        ))
        
        # Example box style
        self.styles.add(ParagraphStyle(
            name='ExampleBox',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#1565c0'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            spaceBefore=12,
            backColor=colors.HexColor('#e3f2fd'),
            borderPadding=10
        ))
    
    async def extract_relevant_content(
        self,
        text: str,
        query: str,
        source_type: str
    ) -> str:
        """
        Extract relevant content including mathematical equations
        
        CRITICAL: This method now preserves mathematical notation, equations,
        formulas, and derivations from source materials.
        """
        if not text or not query:
            return ""
        
        # Enhanced extraction prompt that emphasizes mathematical content
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert content curator for educational materials with strong emphasis on mathematical and technical accuracy.

Your task is to extract and synthesize relevant information from source materials based on a specific query, making sure to stick to the source materials and not add any new information.

CRITICAL INSTRUCTIONS FOR MATHEMATICAL CONTENT:
- PRESERVE ALL mathematical equations EXACTLY as written
- PRESERVE ALL formulas, expressions, and mathematical notation
- PRESERVE ALL derivations step-by-step
- PRESERVE ALL mathematical symbols (∑, ∫, ∂, α, β, π, etc.)
- PRESERVE ALL subscripts, superscripts, and special characters
- Include the mathematical logic and reasoning behind equations
- Maintain the sequence of mathematical steps in derivations

Guidelines:
- Focus ONLY on information directly relevant to the query
- Maintain COMPLETE accuracy for all mathematical content
- Organize information logically
- Include important details, examples, and explanations
- Include ALL equations, formulas, and mathematical expressions mentioned
- Include step-by-step mathematical derivations when present
- Preserve technical terms and mathematical definitions
- Note key concepts and mathematical relationships

FORMATTING FOR EQUATIONS:
- Keep equations on separate lines when appropriate
- Preserve multi-line derivations
- Maintain equation numbering if present
- Keep mathematical notation intact"""),
            ("user", """Source Type: {source_type}

Query: {query}

Source Text:
{text}

Extract and organize the relevant information that addresses the query. 
IMPORTANT: Include ALL mathematical equations, formulas, and derivations found in the source that relate to the query.
Provide a clear, structured summary that preserves ALL mathematical content.
IMPORTANT: In case of conceptual lectures, make sure all the the topics are covered as per the query, and make sure to NOT include any mathematical content if not present in the source text.""")
        ])
        
        # Handle long texts by chunking
        if len(text) > 12000:
            chunks = self._split_text(text, chunk_size=4000)
            extracted_parts = []
            
            # Extract from first 3 chunks to avoid token limits
            for chunk in chunks[:3]:
                chain = extraction_prompt | self.llm
                result = await chain.ainvoke({
                    "source_type": source_type,
                    "query": query,
                    "text": chunk
                })
                extracted_parts.append(result.content)
            
            # Combine extracted parts
            combined_text = "\n\n".join(extracted_parts)
            
            # Final synthesis with emphasis on preserving math
            synthesis_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are synthesizing extracted information into a coherent summary.
CRITICAL: Preserve ALL mathematical equations, formulas, and derivations exactly as they appear. Make sure when encountering the * sign in a mathematical expression, it is retained as is."""),
                ("user", """Combine these extracted sections into a single, well-organized summary; Maintaining both Coneptual clarity and Mathematical accuracy.
Extracted Sections:
{text}""")
            ])
            
            chain = synthesis_prompt | self.llm
            final_result = await chain.ainvoke({"text": combined_text})
            return final_result.content
        
        else:
            # Text is short enough to process directly
            chain = extraction_prompt | self.llm
            result = await chain.ainvoke({
                "source_type": source_type,
                "query": query,
                "text": text
            })
            return result.content
    
    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks while trying to preserve equation blocks"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1
            
            if current_size >= chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    async def generate_lecture_structure(
        self,
        combined_content: str,
        lecture_topic: str
    ) -> Dict[str, Any]:
        """
        Generate complete lecture structure with mathematical equations
        """
        all_content = combined_content
        
        # Enhanced prompt that emphasizes mathematical content
        lecture_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert educator and instructional designer creating professional university-level lectures with strong mathematical content.

CRITICAL REQUIREMENTS FOR MATHEMATICAL CONTENT:
- Include ALL mathematical equations from source materials
- DO NOT include any mathematical content that is NOT present in the source materials
- Show step-by-step mathematical derivations
- Explain the mathematical logic and reasoning
- Include formulas with clear explanations
- Provide mathematical proofs when relevant
- Show worked examples with equations
- Use clear mathematical notation

Your lectures should:
- Have a clear, logical structure
- Build concepts progressively from foundational to advanced
- Include ALL relevant mathematical equations and derivations
- Explain mathematical concepts thoroughly
- Show conceptual and mathematical relationships 
- Include worked mathematical examples OR conceptual examples as appropriate
- Address common misconceptions
- Balance theory and practice along with conceptual understanding


IMPORTANT: Follow the EXACT format specified. Use EXACT section markers."""),
            ("user", """Create a comprehensive lecture on: {topic}

Source Materials:
{content}

Generate a complete lecture with the following EXACT structure:

# TITLE:
[Write an engaging, descriptive title]

# LEARNING_OBJECTIVES:
1. [First objective - include mathematical concepts]
2. [Second objective]
3. [Third objective]
4. [Fourth objective]
5. [Fifth objective]
6. [Sixth objective]

# INTRODUCTION:
[Write an engaging introduction (2-3 paragraphs) that hooks students' interest, explains relevance, and previews main concepts INCLUDING mathematical aspects]

# MAIN_CONTENT:

## SECTION: [Section 1 Title]
[Detailed explanation with 3-5 paragraphs]
[INCLUDE relevant mathematical equations, step-by-step formulas, and derivations IF FOUND IN SOURCE MATERIALS] 



## SECTION: [Section 2 Title]
[Detailed explanation as per query requirements]
[INCLUDE mathematical content, equations, proofs IF FOUND IN SOURCE MATERIALS]

## SECTION: [Section 3 Title]
[Detailed explanation as per query requirements]
[INCLUDE mathematical derivations where relevant IF FOUND IN SOURCE MATERIALS]

## SECTION: [Section 4 Title]
[Detailed explanation as per query requirements]
[INCLUDE formulas and mathematical relationships]

## SECTION: [Section 5 Title]
[Detailed explanation as per query requirements]
[INCLUDE formulas and mathematical relationships]

             
# MATHEMATICAL_DERIVATIONS:
[INCLUDE THIS SECTION ONLY IF the source materials contain explicit mathematical derivations or multi-step equation manipulations]
[If included:]
- Provide complete step-by-step mathematical derivations for key equations
- Show all intermediate steps clearly
- Explain the mathematical reasoning at each step
- Number each step (Step 1:, Step 2:, etc.)
- Show the progression from basic principles to final formulas

[If the source materials contain formulas WITHOUT derivations, integrate explanations within MAIN_CONTENT sections instead]
[If NO mathematical derivations exist in the source materials, OMIT this entire section - do not include the header]

Example format if derivations exist:
Step 1: Start with Bayes' Theorem
    P(A|B) = P(B|A) * P(A) / P(B)

Step 2: Apply to classification
    P(C|X) = P(X|C) * P(C) / P(X)

Step 3: [Continue with remaining steps...]

# REAL_WORLD_EXAMPLES:
    - Brief scenario description (2-3 sentences)
    - How the concept applies in practice
    - Include specific details and numbers when possible
            
# REAL_WORLD_APPLICATIONS:
1. **[Application Name]**: [Explanation]
2. **[Application Name]**: [Explanation]
3. **[Application Name]**: [Explanation]
4. **[Application Name]**: [Explanation]

# COMMON_MISCONCEPTIONS:
1. **[Misconception]**: [Explanation and correction]
2. **[Misconception]**: [Explanation and correction]
3. **[Misconception]**: [Explanation and correction]
4. **[Misconception]**: [Explanation and correction]

# SUMMARY:
[Concise summary including key mathematical formulas and concepts]

# REVIEW_QUESTIONS:
1. [Question 1 - include mathematical problems if applicable]
2. [Question 2]
3. [Question 3]
4. [Question 4]
5. [Question 5]
6. [Question 6]
7. [Question 7]

CRITICAL: Include ALL mathematical equations, formulas, and derivations from the source materials.
Use these EXACT section headers with # symbols. If a section like the mathematical section, has no information in the source, don NOT include it in the final lecture.
             """)
        ])
        
        # Generate the lecture
        chain = lecture_prompt | self.llm
        result = await chain.ainvoke({
            "topic": lecture_topic,
            "content": all_content[:15000]
        })
        
        # Parse the structured response
        return self._parse_lecture_response(result.content)
    
    def _parse_lecture_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response including mathematical content
        """
        lecture_data = {
            "title": "",
            "learning_objectives": [],
            "introduction": "",
            "main_sections": [],
            "mathematical_derivations": "",
            "real_world_examples": [],
            "applications": [],
            "misconceptions": [],
            "summary": "",
            "review_questions": []
        }
        
        # Split by # markers for major sections
        sections = re.split(r'\n(?=#\s+[A-Z_]+:)', response)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Extract TITLE
            if re.match(r'^#\s+TITLE:', section, re.IGNORECASE):
                title_match = re.search(r'#\s+TITLE:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if title_match:
                    lecture_data["title"] = title_match.group(1).strip()
            
            # Extract LEARNING_OBJECTIVES
            elif re.match(r'^#\s+LEARNING_OBJECTIVES:', section, re.IGNORECASE):
                obj_match = re.search(r'#\s+LEARNING_OBJECTIVES:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if obj_match:
                    obj_text = obj_match.group(1).strip()
                    objectives = re.findall(r'^\d+\.\s+(.+?)$', obj_text, re.MULTILINE)
                    lecture_data["learning_objectives"] = [obj.strip() for obj in objectives if obj.strip()]
            
            # Extract INTRODUCTION
            elif re.match(r'^#\s+INTRODUCTION:', section, re.IGNORECASE):
                intro_match = re.search(r'#\s+INTRODUCTION:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if intro_match:
                    lecture_data["introduction"] = intro_match.group(1).strip()
            
            # Extract MAIN_CONTENT with subsections (preserves equations)
            elif re.match(r'^#\s+MAIN_CONTENT:', section, re.IGNORECASE):
                content_match = re.search(r'#\s+MAIN_CONTENT:\s*(.+?)(?=\n#\s+[A-Z_]+:|\Z)', section, re.IGNORECASE | re.DOTALL)
                if content_match:
                    main_text = content_match.group(1).strip()
                    subsections = re.split(r'\n(?=##\s+SECTION:)', main_text)
                    for subsection in subsections:
                        subsection = subsection.strip()
                        if subsection and 'SECTION:' in subsection:
                            section_match = re.search(r'##\s+SECTION:\s+(.+?)\n(.+)', subsection, re.DOTALL)
                            if section_match:
                                section_title = section_match.group(1).strip()
                                section_content = section_match.group(2).strip()
                                lecture_data["main_sections"].append({
                                    "title": section_title,
                                    "content": section_content
                                })
            
            # Extract MATHEMATICAL_DERIVATIONS (CONDITIONAL - may not exist)
            elif re.match(r'^#\s+MATHEMATICAL_DERIVATIONS:', section, re.IGNORECASE):
                deriv_match = re.search(r'#\s+MATHEMATICAL_DERIVATIONS:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if deriv_match:
                    deriv_content = deriv_match.group(1).strip()
                    # Only include if it's not a placeholder/instruction
                    # Check if it contains actual mathematical content
                    if deriv_content and not any(phrase in deriv_content.lower() for phrase in [
                        '[include this section only if',
                        '[if included:',
                        '[if the source materials',
                        'omit this entire section'
                    ]):
                        lecture_data["mathematical_derivations"] = deriv_content
            
            # Extract REAL_WORLD_EXAMPLES
            elif re.match(r'^#\s+REAL_WORLD_EXAMPLES:', section, re.IGNORECASE):
                examples_match = re.search(r'#\s+REAL_WORLD_EXAMPLES:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if examples_match:
                    examples_text = examples_match.group(1).strip()
                    lecture_data["real_world_examples"] = [{"section": "General", "example": examples_text}]
            
            # Extract REAL_WORLD_APPLICATIONS
            elif re.match(r'^#\s+REAL_WORLD_APPLICATIONS:', section, re.IGNORECASE):
                apps_match = re.search(r'#\s+REAL_WORLD_APPLICATIONS:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if apps_match:
                    apps_text = apps_match.group(1).strip()
                    applications = re.findall(r'^\d+\.\s+\*\*(.+?)\*\*:\s+(.+?)$', apps_text, re.MULTILINE)
                    if applications:
                        lecture_data["applications"] = [f"**{app[0]}**: {app[1]}" for app in applications]
                    else:
                        applications = re.findall(r'^\d+\.\s+(.+?)$', apps_text, re.MULTILINE)
                        lecture_data["applications"] = [app.strip() for app in applications if app.strip()]
            
            # Extract COMMON_MISCONCEPTIONS
            elif re.match(r'^#\s+COMMON_MISCONCEPTIONS:', section, re.IGNORECASE):
                misc_match = re.search(r'#\s+COMMON_MISCONCEPTIONS:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if misc_match:
                    misc_text = misc_match.group(1).strip()
                    misconceptions = re.findall(r'^\d+\.\s+\*\*(.+?)\*\*:\s+(.+?)$', misc_text, re.MULTILINE)
                    if misconceptions:
                        lecture_data["misconceptions"] = [f"**{misc[0]}**: {misc[1]}" for misc in misconceptions]
                    else:
                        misconceptions = re.findall(r'^\d+\.\s+(.+?)$', misc_text, re.MULTILINE)
                        lecture_data["misconceptions"] = [misc.strip() for misc in misconceptions if misc.strip()]
            
            # Extract SUMMARY
            elif re.match(r'^#\s+SUMMARY:', section, re.IGNORECASE):
                summary_match = re.search(r'#\s+SUMMARY:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if summary_match:
                    lecture_data["summary"] = summary_match.group(1).strip()
            
            # Extract REVIEW_QUESTIONS
            elif re.match(r'^#\s+REVIEW_QUESTIONS:', section, re.IGNORECASE):
                questions_match = re.search(r'#\s+REVIEW_QUESTIONS:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
                if questions_match:
                    questions_text = questions_match.group(1).strip()
                    questions = re.findall(r'^\d+\.\s+(.+?)$', questions_text, re.MULTILINE)
                    lecture_data["review_questions"] = [q.strip() for q in questions if q.strip()]
        
        return lecture_data
    
    def _detect_and_format_equations(self, text: str) -> List:
        """
        Detect mathematical equations in text and format them properly with wrapping
        Returns a list of Paragraph elements that wrap correctly
        """
        elements = []
        
        # Split text into lines
        lines = text.split('\n')
        current_para = []
        equation_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect equation patterns
            is_equation = (
                '=' in line_stripped and (
                    any(char in line_stripped for char in ['∑', '∫', '∂', 'α', 'β', 'γ', 'π', 'σ', 'μ', 'Π']) or
                    re.search(r'[A-Z]\([A-Z]\|[A-Z]\)', line_stripped) or  # P(A|B) pattern
                    re.search(r'\^|\*\*|_|\\frac|\\sum|\\int', line_stripped) or  # Math notation
                    re.search(r'[a-zA-Z]+\s*=\s*[^a-zA-Z\s]+', line_stripped) or  # variable = expression
                    line_stripped.count('(') > 2 or  # Multiple parentheses
                    re.search(r'\d+\s*[+\-*/]\s*\d+', line_stripped) or  # Arithmetic
                    'P(' in line_stripped  # Probability notation
                )
            )
            
            if is_equation:
                # Flush current paragraph
                if current_para:
                    para_text = ' '.join(current_para)
                    if para_text.strip():
                        elements.append(Paragraph(para_text, self.styles['CustomBody']))
                    current_para = []
                
                # Add equation as Paragraph with Courier font (will wrap)
                equation_text = f'<font name="Courier" size="10" color="#000000">{line_stripped}</font>'
                
                # Create equation style that wraps
                eq_style = ParagraphStyle(
                    name='EquationWrap',
                    parent=self.styles['BodyText'],
                    fontSize=10,
                    leftIndent=30,
                    rightIndent=30,
                    spaceAfter=8,
                    spaceBefore=8,
                    alignment=TA_LEFT,
                    backColor=colors.HexColor('#f5f5f5'),
                    borderPadding=8,
                    wordWrap='CJK'  # Enable word wrap
                )
                
                elements.append(Paragraph(equation_text, eq_style))
                
            else:
                # Regular paragraph line
                if line_stripped:
                    current_para.append(line_stripped)
                elif current_para:
                    # Empty line - flush paragraph
                    para_text = ' '.join(current_para)
                    if para_text.strip():
                        elements.append(Paragraph(para_text, self.styles['CustomBody']))
                    current_para = []
        
        # Flush remaining content
        if current_para:
            para_text = ' '.join(current_para)
            if para_text.strip():
                elements.append(Paragraph(para_text, self.styles['CustomBody']))
        
        return elements if elements else [Paragraph(text, self.styles['CustomBody'])]
    
    def create_pdf(
        self,
        lecture_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Create professional PDF with mathematical equations properly formatted
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        story = []
        
        # Title page
        story.extend(self._create_title_page(lecture_data))
        story.append(PageBreak())
        
        # Table of contents
        story.extend(self._create_table_of_contents(lecture_data))
        story.append(PageBreak())
        
        # Learning objectives
        if lecture_data.get("learning_objectives"):
            story.extend(self._create_learning_objectives(lecture_data["learning_objectives"]))
            story.append(Spacer(1, 0.2 * inch))
        
        # Introduction
        if lecture_data.get("introduction"):
            story.append(Paragraph("Introduction", self.styles['SectionHeading']))
            intro_elements = self._detect_and_format_equations(lecture_data["introduction"])
            story.extend(intro_elements)
            story.append(Spacer(1, 0.3 * inch))
        
        # Main content sections with equations
        for i, section in enumerate(lecture_data.get("main_sections", []), 1):
            story.extend(self._create_content_section_with_math(section, i))
            story.append(Spacer(1, 0.3 * inch))
        
        # Mathematical derivations section (CONDITIONAL - only if content exists)
        if lecture_data.get("mathematical_derivations") and len(lecture_data["mathematical_derivations"].strip()) > 0:
            story.append(PageBreak())
            story.append(Paragraph("Mathematical Derivations", self.styles['SectionHeading']))
            story.append(Spacer(1, 0.2 * inch))
            
            # Split derivations into lines and wrap properly
            deriv_text = lecture_data["mathematical_derivations"]
            deriv_lines = deriv_text.split('\n')
            
            for line in deriv_lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.1 * inch))
                    continue
                
                # Check if line contains equation
                is_equation = (
                    '=' in line and (
                        'P(' in line or  # Probability notation
                        any(char in line for char in ['∑', '∫', '∂', 'α', 'β', 'γ', 'π', 'Π']) or
                        re.search(r'\([A-Z]\|[A-Z]\)', line) or
                        re.search(r'\^|\*\*|\\frac|\\sum', line) or
                        'Step' in line  # Step-by-step derivations
                    )
                )
                
                if is_equation:
                    # Format as equation with wrapping
                    story.append(Paragraph(f'<font name="Courier" size="9">{line}</font>', 
                                         self.styles['DerivationStyle']))
                else:
                    # Regular text
                    story.append(Paragraph(line, self.styles['CustomBody']))
            
            story.append(Spacer(1, 0.3 * inch))
        
        # Real-world examples
        if lecture_data.get("real_world_examples"):
            for example in lecture_data["real_world_examples"]:
                story.extend(self._create_example_box(example["example"]))
        
        # Applications
        if lecture_data.get("applications"):
            story.append(PageBreak())
            story.extend(self._create_applications_section(lecture_data["applications"]))
        
        # Misconceptions
        if lecture_data.get("misconceptions"):
            story.append(Spacer(1, 0.3 * inch))
            story.extend(self._create_misconceptions_section(lecture_data["misconceptions"]))
        
        # Summary
        if lecture_data.get("summary"):
            story.append(PageBreak())
            story.append(Paragraph("Summary & Key Takeaways", self.styles['SectionHeading']))
            summary_elements = self._detect_and_format_equations(lecture_data["summary"])
            story.extend(summary_elements)
            story.append(Spacer(1, 0.3 * inch))
        
        # Review questions
        if lecture_data.get("review_questions"):
            story.extend(self._create_review_questions(lecture_data["review_questions"]))
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        return output_path
    
    def _create_title_page(self, lecture_data: Dict[str, Any]) -> List:
        """Create title page"""
        elements = []
        elements.append(Spacer(1, 2 * inch))
        
        title = lecture_data.get("title", "Lecture Notes")
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5 * inch))
        
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        )
        elements.append(Paragraph("Comprehensive Lecture Notes", subtitle_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        date_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        elements.append(Paragraph(date_text, subtitle_style))
        
        return elements
    
    def _create_table_of_contents(self, lecture_data: Dict[str, Any]) -> List:
        """Create table of contents"""
        elements = []
        elements.append(Paragraph("Table of Contents", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2 * inch))
        
        toc_items = ["Learning Objectives", "Introduction"]
        
        for i, section in enumerate(lecture_data.get("main_sections", []), 1):
            toc_items.append(f"{i}. {section['title']}")
        
        # Only add Mathematical Derivations to TOC if it exists
        if lecture_data.get("mathematical_derivations") and len(lecture_data["mathematical_derivations"].strip()) > 0:
            toc_items.append("Mathematical Derivations")
        
        if lecture_data.get("applications"):
            toc_items.append("Real-World Applications")
        if lecture_data.get("misconceptions"):
            toc_items.append("Common Misconceptions")
        if lecture_data.get("summary"):
            toc_items.append("Summary & Key Takeaways")
        if lecture_data.get("review_questions"):
            toc_items.append("Review Questions")
        
        for item in toc_items:
            elements.append(Paragraph(f"• {item}", self.styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))
        
        return elements
    
    def _create_learning_objectives(self, objectives: List[str]) -> List:
        """Create learning objectives section"""
        elements = []
        elements.append(Paragraph("Learning Objectives", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1 * inch))
        
        objective_style = ParagraphStyle(
            name='Objective',
            parent=self.styles['BodyText'],
            fontSize=11,
            leftIndent=20,
            spaceAfter=8,
        )
        
        for i, obj in enumerate(objectives, 1):
            elements.append(Paragraph(f"{i}. {obj}", objective_style))
        
        return elements
    
    def _create_content_section_with_math(self, section: Dict[str, str], number: int) -> List:
        """Create content section with proper mathematical equation handling"""
        elements = []
        
        title = f"{number}. {section['title']}"
        elements.append(Paragraph(title, self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1 * inch))
        
        content = section['content']
        
        # Use the equation detector
        content_elements = self._detect_and_format_equations(content)
        elements.extend(content_elements)
        
        return elements
    
    def _create_example_box(self, example: str) -> List:
        """Create real-world example box"""
        elements = []
        elements.append(Spacer(1, 0.15 * inch))
        
        header_style = ParagraphStyle(
            name='ExampleHeader',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1565c0'),
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("Real-World Example:", header_style))
        elements.append(Spacer(1, 0.05 * inch))
        
        elements.append(Paragraph(example, self.styles['ExampleBox']))
        elements.append(Spacer(1, 0.15 * inch))
        
        return elements
    
    def _create_applications_section(self, applications: List[str]) -> List:
        """Create applications section"""
        elements = []
        elements.append(Paragraph("Real-World Applications", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2 * inch))
        
        for i, app in enumerate(applications, 1):
            elements.append(Paragraph(f"{i}. {app}", self.styles['CustomBody']))
            elements.append(Spacer(1, 0.15 * inch))
        
        return elements
    
    def _create_misconceptions_section(self, misconceptions: List[str]) -> List:
        """Create misconceptions section"""
        elements = []
        elements.append(Paragraph("Common Misconceptions", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2 * inch))
        
        for i, misc in enumerate(misconceptions, 1):
            box_style = ParagraphStyle(
                name='MiscBox',
                parent=self.styles['BodyText'],
                fontSize=10,
                leftIndent=15,
                rightIndent=15,
                spaceAfter=10,
                backColor=colors.HexColor('#fff3e0')
            )
            elements.append(Paragraph(f"<b>Misconception {i}:</b> {misc}", box_style))
        
        return elements
    
    def _create_review_questions(self, questions: List[str]) -> List:
        """Create review questions section"""
        elements = []
        elements.append(Paragraph("Review Questions", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2 * inch))
        
        for i, question in enumerate(questions, 1):
            elements.append(Paragraph(f"<b>Q{i}.</b> {question}", self.styles['CustomBody']))
            elements.append(Spacer(1, 0.15 * inch))
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Add page numbers"""
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(7.5 * inch, 0.5 * inch, text)
        canvas.restoreState()
    
    def save_lecture_to_text(
        self,
        lecture_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Save the generated lecture content to a text file
        
        Args:
            lecture_data: Structured lecture content
            output_path: Full path where text file should be saved
        
        Returns:
            Path to created text file
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        text_content = []
        
        # Title
        if lecture_data.get("title"):
            text_content.append("=" * 80)
            text_content.append(lecture_data["title"].upper())
            text_content.append("=" * 80)
            text_content.append("")
            text_content.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
            text_content.append("")
        
        # Table of Contents
        text_content.append("-" * 80)
        text_content.append("TABLE OF CONTENTS")
        text_content.append("-" * 80)
        text_content.append("")
        text_content.append("1. Learning Objectives")
        text_content.append("2. Introduction")
        
        for i, section in enumerate(lecture_data.get("main_sections", []), 3):
            text_content.append(f"{i}. {section['title']}")
        
        section_num = len(lecture_data.get("main_sections", [])) + 3
        
        if lecture_data.get("mathematical_derivations"):
            deriv_content = lecture_data["mathematical_derivations"]
            if deriv_content and len(deriv_content.strip()) > 10:
                text_content.append(f"{section_num}. Mathematical Derivations")
                section_num += 1
        
        if lecture_data.get("real_world_examples"):
            text_content.append(f"{section_num}. Real-World Examples")
            section_num += 1
        
        if lecture_data.get("applications"):
            text_content.append(f"{section_num}. Real-World Applications")
            section_num += 1
        
        if lecture_data.get("misconceptions"):
            text_content.append(f"{section_num}. Common Misconceptions")
            section_num += 1
        
        if lecture_data.get("summary"):
            text_content.append(f"{section_num}. Summary & Key Takeaways")
            section_num += 1
        
        if lecture_data.get("review_questions"):
            text_content.append(f"{section_num}. Review Questions")
        
        text_content.append("")
        text_content.append("")
        
        # Learning Objectives
        if lecture_data.get("learning_objectives"):
            text_content.append("=" * 80)
            text_content.append("LEARNING OBJECTIVES")
            text_content.append("=" * 80)
            text_content.append("")
            for i, obj in enumerate(lecture_data["learning_objectives"], 1):
                text_content.append(f"{i}. {obj}")
            text_content.append("")
            text_content.append("")
        
        # Introduction
        if lecture_data.get("introduction"):
            text_content.append("=" * 80)
            text_content.append("INTRODUCTION")
            text_content.append("=" * 80)
            text_content.append("")
            text_content.append(lecture_data["introduction"])
            text_content.append("")
            text_content.append("")
        
        # Main Sections
        for i, section in enumerate(lecture_data.get("main_sections", []), 1):
            text_content.append("=" * 80)
            text_content.append(f"{i}. {section['title'].upper()}")
            text_content.append("=" * 80)
            text_content.append("")
            text_content.append(section['content'])
            text_content.append("")
            text_content.append("")
        
        # Mathematical Derivations
        if lecture_data.get("mathematical_derivations"):
            deriv_content = lecture_data["mathematical_derivations"]
            if deriv_content and len(deriv_content.strip()) > 10:
                text_content.append("=" * 80)
                text_content.append("MATHEMATICAL DERIVATIONS")
                text_content.append("=" * 80)
                text_content.append("")
                text_content.append(deriv_content)
                text_content.append("")
                text_content.append("")
        
        # Real-World Examples
        if lecture_data.get("real_world_examples"):
            text_content.append("=" * 80)
            text_content.append("REAL-WORLD EXAMPLES")
            text_content.append("=" * 80)
            text_content.append("")
            for example in lecture_data["real_world_examples"]:
                text_content.append(example["example"])
            text_content.append("")
            text_content.append("")
        
        # Applications
        if lecture_data.get("applications"):
            text_content.append("=" * 80)
            text_content.append("REAL-WORLD APPLICATIONS")
            text_content.append("=" * 80)
            text_content.append("")
            for i, app in enumerate(lecture_data["applications"], 1):
                text_content.append(f"{i}. {app}")
            text_content.append("")
            text_content.append("")
        
        # Misconceptions
        if lecture_data.get("misconceptions"):
            text_content.append("=" * 80)
            text_content.append("COMMON MISCONCEPTIONS")
            text_content.append("=" * 80)
            text_content.append("")
            for i, misc in enumerate(lecture_data["misconceptions"], 1):
                text_content.append(f"{i}. {misc}")
            text_content.append("")
            text_content.append("")
        
        # Summary
        if lecture_data.get("summary"):
            text_content.append("=" * 80)
            text_content.append("SUMMARY & KEY TAKEAWAYS")
            text_content.append("=" * 80)
            text_content.append("")
            text_content.append(lecture_data["summary"])
            text_content.append("")
            text_content.append("")
        
        # Review Questions
        if lecture_data.get("review_questions"):
            text_content.append("=" * 80)
            text_content.append("REVIEW QUESTIONS")
            text_content.append("=" * 80)
            text_content.append("")
            for i, question in enumerate(lecture_data["review_questions"], 1):
                text_content.append(f"Q{i}. {question}")
            text_content.append("")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_content))
        
        return output_path


async def generate_lecture(
    lecture_topic: str,
    output_pdf_path: str,
    groq_api_key: str,
    website_text: Optional[str] = None,
    website_query: Optional[str] = None,
    video_text: Optional[str] = None,
    video_query: Optional[str] = None,
    pptx_text: Optional[str] = None,
    pptx_query: Optional[str] = None,
    audio_text: Optional[str] = None,
    audio_query: Optional[str] = None,
    pdf_text: Optional[str] = None,
    pdf_query: Optional[str] = None,
    docx_text: Optional[str] = None,
    docx_query: Optional[str] = None,
    model_name: str = "llama-3.3-70b-versatile"
) -> str:
    """
    Generate lecture PDF from multiple sources with mathematical equation support
    """
    print(f"Starting lecture generation: {lecture_topic}")
    print("=" * 60)
    
    generator = LectureGenerator(groq_api_key=groq_api_key, model_name=model_name)
    
    print("\n[Step 1] Extracting content from each source...")
    
    extracted_parts = []
    
    # Process website
    if website_text is not None and website_query is not None:
        print("   -> Processing website content...")
        website_content = await generator.extract_relevant_content(
            text=website_text,
            query=website_query,
            source_type="website"
        )
        extracted_parts.append(f"FROM WEBSITE:\n{website_content}")
        print(f"   [SUCCESS] Extracted {len(website_content)} characters from website")
    else:
        print("   [SKIP] Website: NULL")
    
    # Process video
    if video_text is not None and video_query is not None:
        print("   -> Processing video transcript...")
        video_content = await generator.extract_relevant_content(
            text=video_text,
            query=video_query,
            source_type="video"
        )
        extracted_parts.append(f"FROM VIDEO:\n{video_content}")
        print(f"   [SUCCESS] Extracted {len(video_content)} characters from video")
    else:
        print("   [SKIP] Video: NULL")
    
    # Process PowerPoint
    if pptx_text is not None and pptx_query is not None:
        print("   -> Processing PowerPoint content...")
        pptx_content = await generator.extract_relevant_content(
            text=pptx_text,
            query=pptx_query,
            source_type="presentation"
        )
        extracted_parts.append(f"FROM POWERPOINT:\n{pptx_content}")
        print(f"   [SUCCESS] Extracted {len(pptx_content)} characters from PowerPoint")
    else:
        print("   [SKIP] PowerPoint: NULL")
    
    # Process audio
    if audio_text is not None and audio_query is not None:
        print("   -> Processing audio transcript...")
        audio_content = await generator.extract_relevant_content(
            text=audio_text,
            query=audio_query,
            source_type="audio"
        )
        extracted_parts.append(f"FROM AUDIO:\n{audio_content}")
        print(f"   [SUCCESS] Extracted {len(audio_content)} characters from audio")
    else:
        print("   [SKIP] Audio: NULL")
    
    # Process PDF
    if pdf_text is not None and pdf_query is not None:
        print("   -> Processing PDF content...")
        pdf_content = await generator.extract_relevant_content(
            text=pdf_text,
            query=pdf_query,
            source_type="pdf"
        )
        extracted_parts.append(f"FROM PDF:\n{pdf_content}")
        print(f"   [SUCCESS] Extracted {len(pdf_content)} characters from PDF")
    else:
        print("   [SKIP] PDF: NULL")
    
    # Process DOCX
    if docx_text is not None and docx_query is not None:
        print("   -> Processing DOCX content...")
        docx_content = await generator.extract_relevant_content(
            text=docx_text,
            query=docx_query,
            source_type="docx"
        )
        extracted_parts.append(f"FROM DOCX:\n{docx_content}")
        print(f"   [SUCCESS] Extracted {len(docx_content)} characters from DOCX")
    else:
        print("   [SKIP] DOCX: NULL")
    
    if not extracted_parts:
        raise ValueError("No source content provided. Please provide at least one source with BOTH text AND query.")
    
    print(f"\n    Total sources processed: {len(extracted_parts)}")
    
    print("\n [Step 2] Combining all extracted content...")
    combined_content = "\n\n" + "="*60 + "\n\n".join(extracted_parts)
    print(f"   [SUCCESS] Combined content: {len(combined_content)} total characters")
    
    print("\n  [Step 3] Generating lecture from combined content...")
    lecture_data = await generator.generate_lecture_structure(
        combined_content=combined_content,
        lecture_topic=lecture_topic
    )
    
    print(f"   [SUCCESS] Generated lecture: {lecture_data.get('title', lecture_topic)}")
    print(f"   [SUCCESS] Main sections: {len(lecture_data.get('main_sections', []))}")
    print(f"   [SUCCESS] Learning objectives: {len(lecture_data.get('learning_objectives', []))}")
    
    # Only show mathematical derivations if they exist
    has_derivations = lecture_data.get('mathematical_derivations') and len(lecture_data['mathematical_derivations'].strip()) > 0
    print(f"   [SUCCESS] Mathematical derivations: {'Yes' if has_derivations else 'No (omitted - not in source materials)'}")
    
    print("\n [Step 4] Creating PDF document with equations...")
    pdf_path = generator.create_pdf(
        lecture_data=lecture_data,
        output_path=output_pdf_path
    )
    
    print(f"   [SUCCESS] PDF created: {pdf_path}")
    
    # Save text version
    text_output_path = output_pdf_path.rsplit('.', 1)[0] + '.txt'
    print("\n [Step 5] Saving lecture as text file...")
    text_path = generator.save_lecture_to_text(
        lecture_data=lecture_data,
        output_path=text_output_path
    )
    
    print(f"   [SUCCESS] Text file created: {text_path}")
    
    print("\n" + "=" * 60)
    print(f" Lecture generation complete!")
    print(f" PDF Output: {pdf_path}")
    print(f" Text Output: {text_path}")
    
    return pdf_path


def generate_lecture_sync(*args, **kwargs) -> str:
    """Synchronous wrapper - fixes Windows event loop issue"""
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(generate_lecture(*args, **kwargs))
    finally:
        loop.close()


def load_text(path):
    """Helper function to load text files"""
    return open(path, encoding="utf-8", errors="ignore").read()


# if __name__ == "__main__":
#     # Example usage
#     pdf = generate_lecture_sync(
#         lecture_topic="Machine Learning and Transformer Models",
#         output_pdf_path="output/Machine Learning and Transformer Models18.pdf",

#         website_text=load_text(r"url_text.txt"),
#         website_query="Explain the Machine Learning introduction and types, and basic conceptual understanding of machine learning",

#         video_text=None,
#         video_query=None,

#         pptx_text=load_text(r"text_pptx.txt"),
#         pptx_query="Explain Machine learning topics that will be discussed",
        
#         audio_text=None,
#         audio_query=None,
        
#         docx_text=load_text(r"ns_report_text_docx.txt"),
#         docx_query="Explain the real life applications of Machine Learning and different ways to apply it",
        
#         pdf_text=load_text(r"nips_2017_attention_is_all_you_need_paper_text.txt"),
#         pdf_query="Extract the Conceptual understanding Transformer model, its architecture, and its significance in Machine Learning"
#     )
#     print(f"\n Generated PDF: {pdf}")