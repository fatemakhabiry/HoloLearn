from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

from Config import OPENROUTER_MODEL
from Parsers import parse_lecture_response
from PDF_builder import SlideBuilder


# OpenRouter client

def _call_openrouter_sync(
    prompt: str,
    api_key: str,
    model: str = OPENROUTER_MODEL,
    max_tokens: int = 8000,
    temperature: float = 0.5,
) -> str:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "https://lecture-generator",
            "X-Title": "LectureGenerator",
        },
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content


# LectureGenerator

class LectureGenerator:

    def __init__(
        self,
        openrouter_api_key: str,
        model_name: str = OPENROUTER_MODEL,
        max_tokens: int = 8000,
        temperature: float = 0.5,
    ):
        self.api_key     = openrouter_api_key
        self.model_name  = model_name
        self.max_tokens  = max_tokens
        self.temperature = temperature

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=500,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        self._slide_builder = SlideBuilder()

    # LLM call

    def _call_llm(self, prompt: str) -> str:
        return _call_openrouter_sync(
            prompt=prompt,
            api_key=self.api_key,
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

    # Content extraction
    
    def extract_relevant_content(self, text: str, query: str, source_type: str) -> str:
        if not text or not query:
            return ""

        system_instructions = """You are an expert content curator for educational materials with strong emphasis on mathematical and technical accuracy.

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
- Keep mathematical notation intact"""

        user_message = (
            "Source Type: " + source_type + "\n\nQuery: " + query + "\n\nSource Text:\n" + text + "\n\n"
            "Extract and organize the relevant information that addresses the query.\n"
            "IMPORTANT: Include ALL mathematical equations, formulas, and derivations found in the source that relate to the query.\n"
            "Provide a clear, structured summary that preserves ALL mathematical content.\n"
            "IMPORTANT: In case of conceptual lectures, make sure all the topics are covered as per the query, "
            "and make sure to NOT include any mathematical content if not present in the source text."
        )

        full_prompt = system_instructions + "\n\n" + user_message

        if len(text) > 12000:
            chunks = self._split_text(text, chunk_size=4000)
            extracted_parts = []
            for chunk in chunks[:3]:
                chunk_prompt = (
                    system_instructions + "\n\nSource Type: " + source_type + "\n\nQuery: " + query + "\n\n"
                    "Source Text:\n" + chunk + "\n\n"
                    "Extract and organize the relevant information that addresses the query.\n"
                    "IMPORTANT: Include ALL mathematical equations, formulas, and derivations found in the source that relate to the query.\n"
                    "Provide a clear, structured summary that preserves ALL mathematical content.\n"
                    "IMPORTANT: In case of conceptual lectures, make sure all the topics are covered as per the query, "
                    "and make sure to NOT include any mathematical content if not present in the source text."
                )
                result = self._call_llm(chunk_prompt)
                extracted_parts.append(result)
            combined_text = "\n\n".join(extracted_parts)
            synthesis_prompt = (
                "You are synthesizing extracted information into a coherent summary.\n"
                "CRITICAL: Preserve ALL mathematical equations, formulas, and derivations exactly as they appear. "
                "Make sure when encountering the * sign in a mathematical expression, it is retained as is.\n\n"
                "Combine these extracted sections into a single, well-organized summary; "
                "Maintaining both Conceptual clarity and Mathematical accuracy.\n"
                "Extracted Sections:\n" + combined_text
            )
            return self._call_llm(synthesis_prompt)
        else:
            return self._call_llm(full_prompt)

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        words = text.split()
        chunks, current_chunk, current_size = [], [], 0
        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1
            if current_size >= chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk, current_size = [], 0
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks

    # Lecture structure generation
    
    def generate_lecture_structure(self, combined_content: str, lecture_topic: str,
                                    image_entries: List[Dict] | None = None) -> Dict[str, Any]:
        # Build an optional image-hint block so the LLM knows images are present
        image_hint = ""
        if image_entries:
            hint_lines = [
                "\nIMAGE RESOURCES AVAILABLE:",
                "The following user-supplied images will be placed on the right side of "
                "the first " + str(len(image_entries)) + " main-content section slide(s).",
                "When writing those sections, keep explanations self-contained in text as well, "
                "but you MAY reference the image naturally (e.g. 'as illustrated in the figure').",
            ]
            for idx, img in enumerate(image_entries, 1):
                hint_lines.append(f"  Image {idx}: {img.get('caption', img.get('path', ''))}")
            image_hint = "\n".join(hint_lines) + "\n"

        lecture_prompt = """You are an expert educator and instructional designer creating professional university-level lectures with strong mathematical content.

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

IMPORTANT: Follow the EXACT format specified. Use EXACT section markers.

Create a comprehensive lecture on: """ + lecture_topic + """

Source Materials:
""" + combined_content[:15000] + """
""" + image_hint + """
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
[Write an engaging introduction (2-3 paragraphs)]

# MAIN_CONTENT:

## SECTION: [Section 1 Title]
[Detailed explanation with 3-5 paragraphs]
[INCLUDE relevant mathematical equations IF FOUND IN SOURCE MATERIALS]

## SECTION: [Section 2 Title]
[Detailed explanation]
[INCLUDE mathematical content IF FOUND IN SOURCE MATERIALS]

## SECTION: [Section 3 Title]
[Detailed explanation]
[INCLUDE mathematical derivations IF FOUND IN SOURCE MATERIALS]

## SECTION: [Section 4 Title]
[Detailed explanation]

## SECTION: [Section 5 Title]
[Detailed explanation]

# MATHEMATICAL_DERIVATIONS:
[INCLUDE THIS SECTION ONLY IF the source materials contain explicit mathematical derivations]
Step 1: ...
Step 2: ...

# REAL_WORLD_EXAMPLES:
[Provide 2-3 real-world examples. For EACH example use this exact format:]

Example Title
Brief 2-3 sentence description of the scenario
- Specific detail or step with concrete information
- Specific detail or step with concrete information
- Specific detail or step with concrete information

# COMMON_MISCONCEPTIONS:
1. [Misconception]: [Explanation and correction]
2. [Misconception]: [Explanation and correction]
3. [Misconception]: [Explanation and correction]
4. [Misconception]: [Explanation and correction]

# SUMMARY:
[Concise summary including key mathematical formulas and concepts]

# REVIEW_QUESTIONS:
1. [Question 1]
2. [Question 2]
3. [Question 3]
4. [Question 4]
5. [Question 5]
6. [Question 6]
7. [Question 7]

CRITICAL: Include ALL mathematical equations, formulas, and derivations from the source materials.
Use these EXACT section headers with # symbols.
DO NOT use markdown bold (**text**), italic (*text*), or heading (###) syntax anywhere in the output.
DO NOT include REAL_WORLD_APPLICATIONS section."""

        result = self._call_llm(lecture_prompt)
        return parse_lecture_response(result)

    # PDF output (delegates to SlideBuilder)
    
    def create_pdf(self, lecture_data: Dict[str, Any], output_path: str,
                   images: List[Dict] | None = None) -> str:
        return self._slide_builder.create_pdf(lecture_data, output_path, images=images)

    # Text output
    
    def save_lecture_to_text(self, lecture_data: Dict[str, Any], output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        lines = []

        if lecture_data.get("title"):
            lines += ["=" * 80, lecture_data["title"].upper(), "=" * 80, "",
                      "Generated: " + datetime.now().strftime('%B %d, %Y'), ""]

        lines += ["-" * 80, "TABLE OF CONTENTS", "-" * 80, "",
                  "1. Learning Objectives", "2. Introduction"]
        for i, s in enumerate(lecture_data.get("main_sections", []), 3):
            lines.append(str(i) + ". " + s['title'])

        sn = len(lecture_data.get("main_sections", [])) + 3
        for key, label in [
            ("mathematical_derivations", "Mathematical Derivations"),
            ("real_world_examples",      "Real-World Examples"),
            ("misconceptions",           "Common Misconceptions"),
            ("summary",                  "Summary & Key Takeaways"),
            ("review_questions",         "Review Questions"),
        ]:
            val = lecture_data.get(key)
            if val and (not isinstance(val, str) or len(val.strip()) > 10):
                lines.append(str(sn) + ". " + label)
                sn += 1

        lines += ["", ""]

        def section(title, content):
            return ["=" * 80, title, "=" * 80, "", content, "", ""]

        if lecture_data.get("learning_objectives"):
            lines += ["=" * 80, "LEARNING OBJECTIVES", "=" * 80, ""]
            for i, o in enumerate(lecture_data["learning_objectives"], 1):
                lines.append(str(i) + ". " + o)
            lines += ["", ""]

        if lecture_data.get("introduction"):
            lines += section("INTRODUCTION", lecture_data["introduction"])

        for i, s in enumerate(lecture_data.get("main_sections", []), 1):
            lines += section(str(i) + ". " + s['title'].upper(), s['content'])

        if lecture_data.get("mathematical_derivations"):
            dc = lecture_data["mathematical_derivations"]
            if len(dc.strip()) > 10:
                lines += section("MATHEMATICAL DERIVATIONS", dc)

        if lecture_data.get("real_world_examples"):
            lines += ["=" * 80, "REAL-WORLD EXAMPLES", "=" * 80, ""]
            for ex in lecture_data["real_world_examples"]:
                lines.append("")
                lines.append(ex['title'])
                lines.append("-" * len(ex['title']))
                if ex.get("body"):
                    lines.append(ex['body'])
                for b in ex.get("bullets", []):
                    lines.append("  • " + b)
                lines.append("")
            lines.append("")

        if lecture_data.get("misconceptions"):
            lines += ["=" * 80, "COMMON MISCONCEPTIONS", "=" * 80, ""]
            for i, m in enumerate(lecture_data["misconceptions"], 1):
                lines.append(str(i) + ". " + m)
            lines += ["", ""]

        if lecture_data.get("summary"):
            lines += section("SUMMARY & KEY TAKEAWAYS", lecture_data["summary"])

        if lecture_data.get("review_questions"):
            lines += ["=" * 80, "REVIEW QUESTIONS", "=" * 80, ""]
            for i, q in enumerate(lecture_data["review_questions"], 1):
                lines.append("Q" + str(i) + ". " + q)
            lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return output_path