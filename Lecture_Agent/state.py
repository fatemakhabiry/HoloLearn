# ai/agent/state.py

from typing import TypedDict, Literal, Optional
from langgraph.graph.message import add_messages



class SourceFile(TypedDict):
    """
    One extracted source file.
    text  — plain text already extracted before the agent starts.
    query — relevance query the lecture generator uses to pull
            content from this source.
    """
    text:  str
    query: str


class LectureSource(TypedDict):
    type: Literal["prepared_lecture", "generated_lecture"]

    # prepared_lecture path only — 
    prepared_text: Optional[str]

    # generated_lecture path only — extracted source files
    pdf:     Optional[list[SourceFile]]   
    docx:    Optional[list[SourceFile]] 
    pptx:    Optional[list[SourceFile]]   
    audio:   Optional[list[SourceFile]]   
    video:   Optional[list[SourceFile]]   
    website: Optional[list[SourceFile]]   
    images:  Optional[list[dict]]         



class LectureApproval(TypedDict):
    status:           Literal["pending", "approved", "rejected"]
    teacher_feedback: Optional[str]
    iteration:        int   # 0 = first attempt, increments each regen
    max_iterations:   int   # hard cap set once at session start


class LecturePaths(TypedDict):
    pdf:  Optional[str]
    txt:  Optional[str]
    json: Optional[str]

class ScriptPaths(TypedDict):
    txt: Optional[str]

class WorksheetPaths(TypedDict):
    questions_pdf: Optional[str]
    answers_pdf:   Optional[str]
    json:          Optional[str]

class QuizPaths(TypedDict):
    quiz_pdf:    Optional[str]
    answers_pdf: Optional[str]

class SummaryPaths(TypedDict):
    pdf: Optional[str]
    txt: Optional[str]


class KnowledgeGraphPaths(TypedDict):
    html: Optional[str]

class GeneratedContent(TypedDict):
    script:          Optional[ScriptPaths]
    worksheet:       Optional[WorksheetPaths]
    quiz:            Optional[QuizPaths]
    summary:         Optional[SummaryPaths]
    knowledge_graph: Optional[KnowledgeGraphPaths]



class SessionMeta(TypedDict):
    session_id:  str
    teacher_id:  str
    course_code: str
    title:       str
    output_dir:  str   



class AgentState(TypedDict):

    # identity 
    meta:   SessionMeta
    source: LectureSource

    final_lecture: Optional[str]
    lecture_paths: Optional[LecturePaths]
    lecture_approval: Optional[LectureApproval]

    generated_content: GeneratedContent

    # control
    current_step: Literal[
        "starting",
        "generating_lecture",   
        "awaiting_approval",    
        "regenerating",        
        "generating_content", 
        "done",
        "failed",
    ]

    error: Optional[str]