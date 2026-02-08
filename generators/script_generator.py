from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from typing import Optional
from langchain.messages import SystemMessage, HumanMessage


class HologramScriptGenerator:
    """Generate comprehensive lecture scripts using Groq Qwen"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found. Set env var or pass api_key.")

        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=8000
        )

    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = "",
        duration: int = 15,
        language: str = "English",
    ) -> str:
        prompt = self._create_prompt(content, course_code, title, duration, language)

        print(f"🤖 Generating {duration}-minute lecture script...")
        print(f"📊 Content length: {len(content)} characters")

        messages = [
            SystemMessage(
                content=(
                    "You are an expert educational content creator. "
                    "You create engaging, comprehensive lecture scripts "
                    "for hologram teachers that cover ALL provided content thoroughly."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        script = response.content

        print(f"✅ Generated script: {len(script)} characters")
        print(f"📝 Estimated words: {len(script.split())}")
        print(f"⏱️  Estimated duration: {len(script.split()) / 150:.1f} minutes")

        return script

    def _create_prompt(
        self,
        content: str,
        course_code: str,
        title: str,
        duration: int,
        language: str,
    ) -> str:
        return f"""Create a COMPLETE lecture script for a hologram teacher.

COURSE INFO:
- Course: {course_code}
- Title: {title}
- Duration: {duration} minutes
- Language: {language}

CONTENT TO COVER (MUST COVER EVERYTHING):
{content}

REQUIREMENTS:

1. STRUCTURE ({duration} minutes total):

   INTRODUCTION (5%):
   - Warm welcome
   - Introduce yourself as hologram teacher
   - State learning objectives
   - Explain why topic matters
   - Preview main concepts

   MAIN CONTENT (85%):
   - Cover EVERY topic from the content above
   - Explain each concept clearly and thoroughly
   - Use real-world examples
   - Use analogies for complex ideas
   - Build from simple to complex
   - Include smooth transitions

   CONCLUSION (10%):
   - Summarize ALL key points
   - Reinforce main takeaways
   - Connect concepts together
   - Encourage further learning

2. STYLE:
   - Conversational and natural
   - Engage students with "you"
   - Ask rhetorical questions
   - Show enthusiasm
   - Be clear and accessible

3. CONTENT DEPTH:
   - Don't skip topics
   - Give proper explanation to each concept
   - Include WHY, not just WHAT
   - Make connections between ideas

4. FORMAT:
   - Write ONLY spoken words
   - Natural paragraphs (no bullets)
   - Use "..." for natural pauses
   - NO headers or labels
   - Continuous speech flow

TARGET LENGTH: Approximately {duration * 150} words for {duration} minutes of speech.

Generate the COMPLETE script in {language} covering ALL content."""

    def generate_and_save(
        self,
        content: str,
        output_path: str,
        course_code: str = "",
        title: str = "",
        duration: int = 45,
        language: str = "English",
    ) -> str:
        script = self.generate(content, course_code, title, duration, language)

        output = f"""{'='*80}
HOLOGRAM LECTURE SCRIPT
{'='*80}
Course: {course_code}
Title: {title}
Duration: {duration} minutes
Language: {language}
Generated: {self._get_timestamp()}
{'='*80}

{script}

{'='*80}
END OF SCRIPT
{'='*80}
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)

        print(f"✅ Script saved to: {output_path}")
        return output_path

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

    generator = HologramScriptGenerator(api_key=api_key)

    # ✅ 1) Put your extracted lecture here (txt file)
    INPUT_LECTURE_TXT = "1_introduction_to_infosec_text.txt"  # <-- change to your file name/path

    # ✅ 2) Output script file
    OUTPUT_SCRIPT_TXT = "hologram_lecture_IS_script.txt"

    # ✅ 3) Read lecture from txt
    lecture_content = read_text_file(INPUT_LECTURE_TXT)

    # ✅ 4) Generate and save script
    generator.generate_and_save(
        content=lecture_content,
        output_path=OUTPUT_SCRIPT_TXT,
        course_code="IS101",                    # optional
        title="Introduction infosec",  # optional
        duration=25,                             # change duration
        language="English",
    )

    print("\n✅ Complete! Check:", OUTPUT_SCRIPT_TXT)