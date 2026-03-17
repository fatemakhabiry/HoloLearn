import re
from typing import Dict, List, Any

from Helpers import strip_markdown


# Real-world example parser

def parse_real_world_examples(raw_text: str) -> List[Dict[str, Any]]:
    examples = []
    text = strip_markdown(raw_text).strip()
    numbered = re.split(r'\n(?=\d+\.\s)', text)
    if len(numbered) > 1:
        for chunk in numbered:
            chunk = chunk.strip()
            if not chunk:
                continue
            m = re.match(r'^\d+\.\s+(.+?)(?:\n|:)(.+)?$', chunk, re.DOTALL)
            if m:
                title = m.group(1).strip().rstrip(':')
                body  = (m.group(2) or '').strip()
                examples.append(_build_example_dict(title, body))
            else:
                title = re.sub(r'^\d+\.\s+', '', chunk).strip()
                examples.append(_build_example_dict(title, ''))
        return examples

    chunks = re.split(r'\n{2,}', text)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if not lines:
            continue
        first = lines[0]
        rest  = lines[1:]
        is_title = (
            len(first) <= 80 and
            not first.endswith('.') and
            not first.startswith('-')
        ) or first.endswith(':')
        if is_title and rest:
            title = first.rstrip(':')
            body  = '\n'.join(rest)
        elif first.startswith('-') or first.startswith('•'):
            title = "Example"
            body  = chunk
        else:
            title = "Example"
            body  = chunk
        examples.append(_build_example_dict(title, body))

    return examples if examples else [{"title": "Example", "body": text, "bullets": []}]


def _build_example_dict(title: str, body: str) -> Dict[str, Any]:
    title  = strip_markdown(title).strip().rstrip(':')
    lines  = [l.strip() for l in body.splitlines() if l.strip()]
    bullets: List[str] = []
    para_lines: List[str] = []
    for line in lines:
        if re.match(r'^[-•*]\s+', line):
            bullets.append(re.sub(r'^[-•*]\s+', '', line).strip())
        elif re.match(r'^\d+\.\s+', line):
            bullets.append(re.sub(r'^\d+\.\s+', '', line).strip())
        else:
            para_lines.append(line)
    para_text = ' '.join(para_lines).strip()
    return {"title": title, "body": para_text, "bullets": bullets}


# Lecture response parser

_DERIVATION_PLACEHOLDER_PATTERNS = [
    '[include this section only if',
    '[if included:',
    '[if the source materials',
    'omit this entire section',
    'no mathematical derivations',
    'no mathematical content',
    'no explicit mathematical derivations',
    'no derivations found',
    'not present in the source',
    'source materials do not contain',
    'source materials contain no',
    'not found in the source',
    'none found',
    'n/a',
    'this section is omitted',
    'this section does not apply',
    'mathematical derivations are not',
    'are not applicable',
    'are not present',
    'no equations found',
    'no formulas found',
    'omitted as',
    'section omitted',
    'not applicable',
]


def is_derivation_placeholder(text: str) -> bool:
    lowered = text.lower().strip()
    if not lowered:
        return True
    has_math = bool(re.search(r'[\$\\=\+\-\*\^_\d]', lowered))
    if len(lowered) < 60 and not has_math:
        return True
    return any(p in lowered for p in _DERIVATION_PLACEHOLDER_PATTERNS)


def parse_lecture_response(response: str) -> Dict[str, Any]:
    lecture_data = {
        "title": "", "learning_objectives": [], "introduction": "",
        "main_sections": [], "mathematical_derivations": "",
        "real_world_examples": [],
        "misconceptions": [], "summary": "", "review_questions": []
    }

    sections = re.split(r'\n(?=#\s+[A-Z_]+:)', response)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if re.match(r'^#\s+TITLE:', section, re.IGNORECASE):
            m = re.search(r'#\s+TITLE:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                lecture_data["title"] = strip_markdown(m.group(1).strip())

        elif re.match(r'^#\s+LEARNING_OBJECTIVES:', section, re.IGNORECASE):
            m = re.search(r'#\s+LEARNING_OBJECTIVES:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                objs = re.findall(r'^\d+\.\s+(.+?)$', m.group(1).strip(), re.MULTILINE)
                lecture_data["learning_objectives"] = [strip_markdown(o.strip()) for o in objs if o.strip()]

        elif re.match(r'^#\s+INTRODUCTION:', section, re.IGNORECASE):
            m = re.search(r'#\s+INTRODUCTION:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                lecture_data["introduction"] = strip_markdown(m.group(1).strip())

        elif re.match(r'^#\s+MAIN_CONTENT:', section, re.IGNORECASE):
            m = re.search(r'#\s+MAIN_CONTENT:\s*(.+?)(?=\n#\s+[A-Z_]+:|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                for sub in re.split(r'\n(?=##\s+SECTION:)', m.group(1).strip()):
                    sub = sub.strip()
                    if sub and 'SECTION:' in sub:
                        sm = re.search(r'##\s+SECTION:\s+(.+?)\n(.+)', sub, re.DOTALL)
                        if sm:
                            lecture_data["main_sections"].append({
                                "title":   strip_markdown(sm.group(1).strip()),
                                "content": strip_markdown(sm.group(2).strip())
                            })

        elif re.match(r'^#\s+MATHEMATICAL_DERIVATIONS:', section, re.IGNORECASE):
            m = re.search(r'#\s+MATHEMATICAL_DERIVATIONS:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                dc = m.group(1).strip()
                if dc and not is_derivation_placeholder(dc):
                    dc = re.sub(r'^#{1,6}\s+', '', dc, flags=re.MULTILINE)
                    lecture_data["mathematical_derivations"] = dc

        elif re.match(r'^#\s+REAL_WORLD_EXAMPLES:', section, re.IGNORECASE):
            m = re.search(r'#\s+REAL_WORLD_EXAMPLES:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                lecture_data["real_world_examples"] = parse_real_world_examples(m.group(1).strip())

        elif re.match(r'^#\s+COMMON_MISCONCEPTIONS:', section, re.IGNORECASE):
            m = re.search(r'#\s+COMMON_MISCONCEPTIONS:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                raw_text = m.group(1).strip()
                miscs = re.findall(r'^\d+\.\s+\*\*(.+?)\*\*[:\s]+(.+?)$', raw_text, re.MULTILINE)
                if miscs:
                    lecture_data["misconceptions"] = [
                        strip_markdown(ms[0]) + ": " + strip_markdown(ms[1]) for ms in miscs
                    ]
                else:
                    miscs = re.findall(r'^\d+\.\s+(.+?)$', raw_text, re.MULTILINE)
                    lecture_data["misconceptions"] = [strip_markdown(ms.strip()) for ms in miscs if ms.strip()]

        elif re.match(r'^#\s+SUMMARY:', section, re.IGNORECASE):
            m = re.search(r'#\s+SUMMARY:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                lecture_data["summary"] = strip_markdown(m.group(1).strip())

        elif re.match(r'^#\s+REVIEW_QUESTIONS:', section, re.IGNORECASE):
            m = re.search(r'#\s+REVIEW_QUESTIONS:\s*(.+?)(?=\n#|\Z)', section, re.IGNORECASE | re.DOTALL)
            if m:
                qs = re.findall(r'^\d+\.\s+(.+?)$', m.group(1).strip(), re.MULTILINE)
                lecture_data["review_questions"] = [strip_markdown(q.strip()) for q in qs if q.strip()]

    return lecture_data