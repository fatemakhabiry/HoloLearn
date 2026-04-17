# # ai/agent/graph.py

# from langgraph.graph import StateGraph, START, END
# from langgraph.checkpoint.memory import MemorySaver

# from state import AgentState
# from nodes import (
#     route_input,
#     _route_input_edge,
#     set_lecture,
#     generate_lecture,
#     interrupt_for_approval,
#     _approval_edge,
#     generate_all_content,
#     save_results,
# )


# def build_graph(checkpointer=None):
#     """
#     Builds and compiles the HoloLearn agent graph.
#     Args:
#         checkpointer: optional LangGraph checkpointer (e.g. MemorySaver,
#                       SqliteSaver).  Required for HITL interrupts to work.

#     Returns:
#         Compiled LangGraph CompiledStateGraph.
#     """

#     builder = StateGraph(AgentState)

#     # Register nodes 
#     builder.add_node("route_input",            route_input)
#     builder.add_node("set_lecture",            set_lecture)
#     builder.add_node("generate_lecture",       generate_lecture)
#     builder.add_node("interrupt_for_approval", interrupt_for_approval)
#     builder.add_node("generate_all_content",   generate_all_content)
#     builder.add_node("save_results",           save_results)

#     # Edges 

#     # Entry point
#     builder.add_edge(START, "route_input")

#     # route_input → PATH 1 or PATH 2
#     builder.add_conditional_edges(
#         "route_input",
#         _route_input_edge,
#         {
#             "set_lecture":      "set_lecture",      # prepared_lecture
#             "generate_lecture": "generate_lecture", # resources / generated
#         },
#     )

#     # PATH 1: set_lecture skips HITL, goes straight to content generation
#     builder.add_edge("set_lecture", "generate_all_content")

#     # PATH 2: generate_lecture → HITL interrupt
#     builder.add_edge("generate_lecture", "interrupt_for_approval")

#     # HITL decision: approve → generate_all_content | reject → generate_lecture (loop)
#     builder.add_conditional_edges(
#         "interrupt_for_approval",
#         _approval_edge,
#         {
#             "generate_lecture":     "generate_lecture",     # rejected, loop
#             "generate_all_content": "generate_all_content", # approved / max-iter
#         },
#     )

#     # Both paths converge: content generation → save → END
#     builder.add_edge("generate_all_content", "save_results")
#     builder.add_edge("save_results",         END)

#     # Compile 
#     if checkpointer is None:
#         checkpointer = MemorySaver()

#     graph = builder.compile(
#         checkpointer=checkpointer,
#         # Only PATH 2 interrupts — declared here so LangGraph knows upfront
#         interrupt_before=["interrupt_for_approval"],
#     )

#     return graph


# # Convenience runner

# def run_agent(initial_state: AgentState, thread_id: str = "default") -> AgentState:
#     """
#     Runs the graph to completion (or first interrupt).

#     For HITL flows (PATH 2) this will pause at interrupt_for_approval.
#     Resume by calling run_agent again with the updated state and the
#     same thread_id after the teacher has set lecture_approval.

#     Args:
#         initial_state: fully populated AgentState dict.
#         thread_id:     LangGraph thread identifier (used by the checkpointer
#                        to persist and resume state across HITL pauses).

#     Returns:
#         Final AgentState after the graph finishes (or pauses).
#     """
#     graph  = build_graph()
#     config = {"configurable": {"thread_id": thread_id}}

#     final_state = None
#     for event in graph.stream(initial_state, config=config):
#         node_name = list(event.keys())[0]
#         node_state = event[node_name]
#         print(f"[graph] ✓ {node_name} → step={node_state.get('current_step')}")
#         final_state = node_state

#     return final_state



# ai/agent/graph.py

# from langgraph.graph import StateGraph, START, END
# from langgraph.checkpoint.memory import MemorySaver

# from state import AgentState
# from nodes import (
#     route_input,
#     _route_input_edge,
#     set_lecture,
#     generate_lecture,
#     interrupt_for_approval,
#     _approval_edge,
#     generate_all_content,
#     save_results,
# )


# def build_graph(checkpointer=None):
#     if checkpointer is None:
#         checkpointer = MemorySaver()

#     builder = StateGraph(AgentState)

#     # Register nodes — no route_input node needed
#     builder.add_node("route_input",     route_input)

#     builder.add_node("set_lecture",            set_lecture)
#     builder.add_node("generate_lecture",       generate_lecture)
#     builder.add_node("interrupt_for_approval", interrupt_for_approval)
#     builder.add_node("generate_all_content",   generate_all_content)
#     builder.add_node("save_results",           save_results)

#     # START → conditional split (no intermediate node)
#     builder.add_edge(START, "route_input")


#     builder.add_conditional_edges(
#         "route_input",
#         _route_input_edge,
#         {
#             "set_lecture":      "set_lecture",
#             "generate_lecture": "generate_lecture",
#         },
#     )

#     # Path A: straight to content
#     builder.add_edge("set_lecture", "generate_all_content")

#     # Path B: generate → HITL → decision
#     builder.add_edge("generate_lecture", "interrupt_for_approval")

#     builder.add_conditional_edges(
#         "interrupt_for_approval",
#         _approval_edge,
#         {
#             "generate_lecture":     "generate_lecture",
#             "generate_all_content": "generate_all_content",
#         },
#     )

#     # Both paths converge
#     builder.add_edge("generate_all_content", "save_results")
#     builder.add_edge("save_results",         END)

#     # No interrupt_before — interrupt() inside the node handles pausing
#     return builder.compile(checkpointer=checkpointer )




# graph.py — full updated file

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from nodes import (
    _route_input_edge,
    set_lecture,
    set_generating_lecture_status,
    generate_lecture,
    interrupt_for_approval,
    _approval_edge,
    set_generating_content_status,
    generate_all_content,
    save_results,
)


def build_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────
    builder.add_node("set_lecture",                    set_lecture)
    builder.add_node("set_generating_lecture_status",  set_generating_lecture_status)
    builder.add_node("generate_lecture",               generate_lecture)
    builder.add_node("interrupt_for_approval",         interrupt_for_approval)
    builder.add_node("set_generating_content_status",  set_generating_content_status)
    builder.add_node("generate_all_content",           generate_all_content)
    builder.add_node("save_results",                   save_results)

    # ── Edges ──────────────────────────────────────────────────────

    # START → split by source type
    builder.add_conditional_edges(
        START,
        _route_input_edge,
        {
            "set_lecture":                   "set_lecture",
            "set_generating_lecture_status": "set_generating_lecture_status",
        },
    )

    # Path A — prepared lecture → straight to content
    builder.add_edge("set_lecture",                   "set_generating_content_status")

    # Path B — generated lecture
    builder.add_edge("set_generating_lecture_status", "generate_lecture")
    builder.add_edge("generate_lecture",              "interrupt_for_approval")

    builder.add_conditional_edges(
        "interrupt_for_approval",
        _approval_edge,
        {
            # Rejected → status node → regenerate
            "set_generating_lecture_status": "set_generating_lecture_status",
            # Approved → status node → generate content
            "set_generating_content_status": "set_generating_content_status",
        },
    )

    # Both paths converge at content generation
    builder.add_edge("set_generating_content_status", "generate_all_content")
    builder.add_edge("generate_all_content",          "save_results")
    builder.add_edge("save_results",                  END)

    return builder.compile(checkpointer=checkpointer , interrupt_before=["interrupt_for_approval"])