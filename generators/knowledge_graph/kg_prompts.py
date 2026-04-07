from kg_config import CLUSTER_COLORS

# ─────────────────────────────────────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an expert educational knowledge graph generator.

Your goal is to convert lecture text into a clean, student-friendly knowledge graph
that helps students understand the structure of the lecture and revise key concepts.

The graph must prioritize clarity, consistency, and conceptual relationships.

CRITICAL RULES:

1. Focus ONLY on important lecture concepts.
   - Include: key definitions, core concepts, major methods, important processes, risks/attacks, metrics, and examples.
   - Ignore: minor details, filler explanations, and repeated sentences.

2. Entity consistency is mandatory.
   - If the same concept appears with different names, use ONE canonical name.
   - Example: "AI", "artificial intelligence" → use "artificial intelligence".
   - Never create multiple nodes representing the same concept.

3. Avoid duplicate nodes.
   - Each concept must appear only once in the graph.

4. Prefer higher-level concepts over small details.
   - A node should represent a meaningful idea students should remember.

5. The graph must be educational:
   - Nodes should help students review the lecture quickly.
   - Relationships should explain how concepts connect.

6. Relations must be short and clear.
   - Relation labels must be 1–4 words.
   - Use verbs when possible.

7. The graph must be fully connected.
   - No isolated nodes.

8. Node labels must be:
   - clear
   - complete words
   - no abbreviations unless defined

9. Descriptions must be:
   - 1–2 sentences
   - simple and educational

10. Do not hallucinate.
    - Only use information present in the lecture text.

Output only valid JSON.
"""


def make_human_prompt(text: str, colors: list) -> str:
    return """
Create a knowledge graph from the lecture text below.

Your goal is to build a concept map that helps students:
- understand the lecture structure
- see relationships between concepts
- revise the material quickly

Return ONLY valid JSON with this structure:

{{
  "title": "short lecture title (max 6 words)",
  "subject": "academic field",
  "summary": "2-3 sentence explanation of what this lecture teaches",
  "clusters": [
    {{"id": "C1", "name": "Main Topic", "color": "{color1}"}}
  ],
  "nodes": [
    {{
      "id": "n1",
      "c": "C1",
      "label": "concept name",
      "type": "concept | process | method | metric | system | attack | person",
      "desc": "clear explanation for students"
    }}
  ],
  "edges": [
    {{
      "s": "n1",
      "t": "n2",
      "r": "relationship phrase"
    }}
  ]
}}

STRICT REQUIREMENTS

1. Coverage
- Identify the MAIN topics of the lecture.
- Ensure every major section or heading is represented.

2. No duplicates
- Each concept must appear only once.
- Merge synonyms into a single node.

3. Node quality
- Use clear, full concept names.
- Avoid vague labels like "thing", "example", "idea".

4. Graph size
- Target 35–60 nodes
- Target 50–90 edges

5. Educational relationships
Examples of good relations:
- "defines"
- "causes"
- "uses"
- "prevents"
- "detects"
- "part of"
- "leads to"
- "measured by"
- "implemented by"

6. Graph structure
- The first node must represent the main lecture topic.
- The graph must be fully connected.
- Every node must have at least one edge.

7. Node descriptions
- 1–2 sentences explaining the concept for students.

8. Relationship rules
- 1–4 words maximum
- concise and meaningful

Cluster colors available:
{colors}

LECTURE TEXT:
\"\"\"
{text}
\"\"\"
""".format(
        text=text,
        colors=", ".join(colors),
        color1=colors[0] if colors else "#3873ff"
    )