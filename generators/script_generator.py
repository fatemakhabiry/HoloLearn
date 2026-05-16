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
        output_path: str="hologram_lecture_script.txt",
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


# if __name__ == "__main__":
#     load_dotenv()
#     api_key = os.getenv("GROQ_API_KEY")

#     generator = HologramScriptGenerator(api_key=api_key)

#     # ✅ 1) Put your extracted lecture here (txt file)
#     INPUT_LECTURE_TXT = "1_introduction_to_infosec_text.txt"  # <-- change to your file name/path

#     # ✅ 2) Output script file
#     OUTPUT_SCRIPT_TXT = "hologram_lecture_IS_script.txt"

#     # ✅ 3) Read lecture from txt
#     lecture_content = read_text_file(INPUT_LECTURE_TXT)

#     # ✅ 4) Generate and save script
#     generator.generate_and_save(
#         content=lecture_content,
#         output_path=OUTPUT_SCRIPT_TXT,
#         course_code="IS101",                    # optional
#         title="Introduction infosec",  # optional
#         duration=25,                             # change duration
#         language="English",
#     )

#     print("\n✅ Complete! Check:", OUTPUT_SCRIPT_TXT)


# from langchain_groq import ChatGroq
# from langchain.messages import SystemMessage, HumanMessage
# import os
# from datetime import datetime
# from typing import Optional

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


# class HologramScriptGenerator:
#     """
#     Generate comprehensive hologram lecture scripts.
#     Handles content of any length via chunking — no 413 errors.

#     Strategy:
#     1. Split content into chunks.
#     2. Generate a script SECTION for each chunk.
#     3. Stitch sections together with smooth transitions.
#     4. Wrap with introduction and conclusion.
#     """

#     CHUNK_MAX_CHARS = 6_000
#     CHUNK_OVERLAP   = 300

#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv("GROQ_API_KEY")
#         if not self.api_key:
#             raise ValueError("GROQ_API_KEY not found. Set env var or pass api_key.")

#         self.llm = ChatGroq(
#             groq_api_key=self.api_key,
#             model_name="llama-3.3-70b-versatile",
#             temperature=0.7,
#             max_tokens=8000,
#         )

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

#     def _intro_prompt(
#         self,
#         course_code: str,
#         title: str,
#         duration: int,
#         language: str,
#         topic_overview: str,
#     ) -> str:
#         return f"""Write ONLY the introduction section of a hologram lecture script.

# Course: {course_code}
# Title: {title}
# Language: {language}

# TOPICS COVERED IN THIS LECTURE:
# {topic_overview}

# Write a warm, engaging introduction (approximately {max(1, duration // 10)} minutes of speech):
# - Greet students as a hologram teacher
# - Introduce yourself and the topic
# - State the main learning objectives (based on the topics listed)
# - Explain why this topic matters
# - Preview what will be covered

# Write ONLY spoken words. Natural paragraphs. No headers. No bullets.
# Use "..." for natural pauses. Be conversational and enthusiastic."""

#     def _section_prompt(
#         self,
#         chunk: str,
#         section_num: int,
#         total_sections: int,
#         course_code: str,
#         title: str,
#         language: str,
#         section_duration: int,
#     ) -> str:
#         return f"""Write ONLY the main content section {section_num} of {total_sections}
# for a hologram lecture script.

# Course: {course_code}
# Title: {title}
# Language: {language}
# Target length: approximately {section_duration} minutes of speech (~{section_duration * 150} words)

# CONTENT TO COVER IN THIS SECTION:
# {chunk}

# Requirements:
# - Cover EVERY concept in the content above
# - Explain each idea clearly with analogies and examples
# - Build from simple to complex
# - Use "you" to address students directly
# - Ask rhetorical questions to maintain engagement
# - End with a brief transition phrase leading to the next topic

# Write ONLY spoken words. Natural paragraphs. No headers. No bullets.
# Use "..." for natural pauses."""

#     def _conclusion_prompt(
#         self,
#         course_code: str,
#         title: str,
#         language: str,
#         duration: int,
#         topic_overview: str,
#     ) -> str:
#         return f"""Write ONLY the conclusion section of a hologram lecture script.

# Course: {course_code}
# Title: {title}
# Language: {language}

# TOPICS COVERED IN THIS LECTURE:
# {topic_overview}

# Write a strong conclusion (approximately {max(1, duration // 10)} minutes of speech):
# - Summarise ALL key takeaways from the lecture
# - Reinforce the most important concepts
# - Connect ideas together to show the big picture
# - Encourage further study and curiosity
# - End with a warm, memorable closing

# Write ONLY spoken words. Natural paragraphs. No headers. No bullets.
# Use "..." for natural pauses."""

#     def _transition_prompt(
#         self,
#         prev_topic: str,
#         next_topic: str,
#         language: str,
#     ) -> str:
#         return f"""Write a single short transition sentence (1-2 sentences maximum)
# that naturally bridges from one lecture section to the next.

# Previous section ended covering: {prev_topic}
# Next section will cover: {next_topic}
# Language: {language}

# Write ONLY the transition sentence. Nothing else."""

#     # ── Section generation ────────────────────────────────────────────────────

#     def _generate_intro(
#         self,
#         course_code: str,
#         title: str,
#         duration: int,
#         language: str,
#         chunks: list[str],
#     ) -> str:
#         # Build a brief topic overview from the first sentence of each chunk
#         overview_lines = []
#         for i, chunk in enumerate(chunks, 1):
#             first_sentence = chunk.strip().split(".")[0][:100]
#             overview_lines.append(f"Section {i}: {first_sentence}...")
#         overview = "\n".join(overview_lines)

#         prompt = self._intro_prompt(course_code, title, duration, language, overview)
#         messages = [
#             SystemMessage(content="You are an expert educational script writer for hologram teachers."),
#             HumanMessage(content=prompt),
#         ]
#         return self.llm.invoke(messages).content or ""

#     def _generate_section(
#         self,
#         chunk: str,
#         section_num: int,
#         total_sections: int,
#         course_code: str,
#         title: str,
#         language: str,
#         section_duration: int,
#     ) -> str:
#         prompt = self._section_prompt(
#             chunk, section_num, total_sections,
#             course_code, title, language, section_duration,
#         )
#         messages = [
#             SystemMessage(content="You are an expert educational script writer for hologram teachers."),
#             HumanMessage(content=prompt),
#         ]
#         return self.llm.invoke(messages).content or ""

#     def _generate_transition(
#         self,
#         prev_chunk: str,
#         next_chunk: str,
#         language: str,
#     ) -> str:
#         # Use last 200 chars of prev chunk as context for "what we just covered"
#         prev_topic = prev_chunk.strip()[-200:]
#         next_topic = next_chunk.strip()[:200:]
#         prompt = self._transition_prompt(prev_topic, next_topic, language)
#         messages = [
#             SystemMessage(content="You are an expert educational script writer."),
#             HumanMessage(content=prompt),
#         ]
#         return self.llm.invoke(messages).content.strip() or ""

#     def _generate_conclusion(
#         self,
#         course_code: str,
#         title: str,
#         language: str,
#         duration: int,
#         chunks: list[str],
#     ) -> str:
#         overview_lines = []
#         for i, chunk in enumerate(chunks, 1):
#             first_sentence = chunk.strip().split(".")[0][:100]
#             overview_lines.append(f"Section {i}: {first_sentence}...")
#         overview = "\n".join(overview_lines)

#         prompt = self._conclusion_prompt(course_code, title, language, duration, overview)
#         messages = [
#             SystemMessage(content="You are an expert educational script writer for hologram teachers."),
#             HumanMessage(content=prompt),
#         ]
#         return self.llm.invoke(messages).content or ""

#     # ── Main generation (chunked) ─────────────────────────────────────────────

#     def generate(
#         self,
#         content: str,
#         course_code: str = "",
#         title: str = "",
#         duration: int = 15,
#         language: str = "English",
#     ) -> str:
#         """
#         Generate a complete hologram lecture script for content of any length.

#         Strategy:
#         1. Split content into chunks of ~6 000 chars.
#         2. Generate: intro → [section + transition] × N → conclusion.
#         3. Stitch all parts into one continuous script.

#         Duration is distributed proportionally:
#         - 5% intro, 90% main sections, 5% conclusion
#         """
#         chunks = _chunk_text(content, self.CHUNK_MAX_CHARS, self.CHUNK_OVERLAP)
#         n      = len(chunks)

#         print(f"🤖 Generating {duration}-minute hologram script "
#               f"({n} section(s), {self.count_tokens(content):,} tokens total)...")

#         # Duration allocation
#         intro_duration   = max(1, int(duration * 0.05))
#         outro_duration   = max(1, int(duration * 0.05))
#         main_duration    = duration - intro_duration - outro_duration
#         section_duration = max(1, main_duration // n)

#         parts: list[str] = []

#         # Introduction
#         print("   [intro] generating...")
#         parts.append(self._generate_intro(
#             course_code, title, intro_duration, language, chunks,
#         ))

#         # Main sections with transitions between them
#         for i, chunk in enumerate(chunks, 1):
#             print(f"   [section {i}/{n}] generating...")
#             section_text = self._generate_section(
#                 chunk, i, n,
#                 course_code, title, language, section_duration,
#             )
#             parts.append(section_text)

#             # Add a transition between sections (not after the last one)
#             if i < n:
#                 print(f"   [transition {i}→{i+1}] generating...")
#                 transition = self._generate_transition(
#                     chunk, chunks[i], language,
#                 )
#                 parts.append(transition)

#         # Conclusion
#         print("   [conclusion] generating...")
#         parts.append(self._generate_conclusion(
#             course_code, title, language, outro_duration, chunks,
#         ))

#         # Stitch everything with natural paragraph spacing
#         script = "\n\n".join(p.strip() for p in parts if p.strip())

#         print(f"✅ Script: {len(script):,} chars | "
#               f"~{len(script.split()):,} words | "
#               f"~{len(script.split()) / 150:.1f} min estimated")

#         return script

#     # ── Save to file ──────────────────────────────────────────────────────────

#     def generate_and_save(
#         self,
#         content: str,
#         output_path: str = "hologram_lecture_script.txt",
#         course_code: str = "",
#         title: str = "",
#         duration: int = 45,
#         language: str = "English",
#     ) -> str:
#         script = self.generate(content, course_code, title, duration, language)

#         header = (
#             f"{'='*80}\n"
#             f"HOLOGRAM LECTURE SCRIPT\n"
#             f"{'='*80}\n"
#             f"Course:    {course_code}\n"
#             f"Title:     {title}\n"
#             f"Duration:  {duration} minutes\n"
#             f"Language:  {language}\n"
#             f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
#             f"{'='*80}\n\n"
#         )
#         footer = f"\n\n{'='*80}\nEND OF SCRIPT\n{'='*80}\n"

#         with open(output_path, "w", encoding="utf-8") as f:
#             f.write(header + script + footer)

#         print(f"✅ Script saved: {output_path}")
#         return output_path