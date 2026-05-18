"""Prompt builders for Planner and Executor."""
from __future__ import annotations
import json
from prompts.personas.general import PERSONA, Persona


def build_planner_system_prompt(persona: Persona) -> str:
    few_shot_text = ""
    for ex in persona.planner_few_shot:
        steps_str = "\n".join(f"  - {s}" for s in ex["steps_summary"])
        few_shot_text += (
            f'\nExample question: "{ex["question"]}"\n'
            f"Suggested step structure:\n{steps_str}\n"
        )

    return f"""{persona.planner_role}

=== TOOL RULES ===
{persona.planner_tool_rules}

=== PLANNING RULES ===
{persona.planner_planning_rules}

=== FEW-SHOT EXAMPLES ===
{few_shot_text}

=== OUTPUT FORMAT ===
Respond ONLY with a valid JSON object matching this exact schema — no preamble, no markdown:
{{
  "steps": [
    {{
      "step_id": "step_1",
      "sub_question": "...",
      "tool": "web_search",
      "finding_key": "background_context",
      "depends_on": [],
      "priority": 1,
      "weight": 0.15
    }},
    ...
  ]
}}
All weights must sum to 1.0.
"""


def build_planner_user_prompt(question: str) -> str:
    return f'Research question: "{question}"\n\nProduce the investigation plan now.'


def build_executor_system_prompt() -> str:
    return """You are a precise research executor. 
Given a main research question and a specific sub-question, provide a thorough, factual answer.

Guidelines:
- Write 2-4 clear paragraphs.
- Cite specific facts, figures, and dates where relevant.
- Be objective; avoid speculation.
- End your response with a line starting with 'SOURCES:' followed by 2-4 real, relevant URLs.

Format:
<your answer paragraphs>

SOURCES: https://example.com, https://another.com
"""


def build_executor_user_prompt(main_question: str, sub_question: str) -> str:
    return (
        f'Main research question: "{main_question}"\n\n'
        f'Sub-question to answer: "{sub_question}"\n\n'
        "Provide your answer now."
    )
