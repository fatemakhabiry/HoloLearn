# # # ai/agent/nodes.py
 
# # import asyncio
# # from pathlib import Path
# # from typing import Any
 
# # from langgraph.types import interrupt
 
# # from state import AgentState, LecturePaths, GeneratedContent
# # from wrapper import SimpleGeneratorWrapper
 
 
# # _wrapper = SimpleGeneratorWrapper()
 
 
# # # ROUTING

# # def route_input(state: AgentState) -> AgentState:
# #     """
# #     Reads source.type and sets current_step so the conditional edge
# #     knows which path to take.  No LLM call — pure routing.
# #     """
# #     source_type = state["source"]["type"]
# #     print(f"[route_input] source.type = {source_type}")
# #     return {
# #         **state,
# #         "current_step": "generating_lecture",
# #     }
 
 
# # def _route_input_edge(state: AgentState) -> str:
# #     """Conditional edge function: returns the name of the next node."""
# #     if state["source"]["type"] == "prepared_lecture":
# #         return "set_lecture"
# #     return "generate_lecture"
 
 
# # # PATH 1 — prepared_lecture
 
# # def set_lecture(state: AgentState) -> AgentState:
# #     """
# #     PATH 1: Teacher already has a lecture text.
# #     No LLM call — just copy prepared_text into final_lecture and
# #     build stub LecturePaths (no pdf/json, only txt).
# #     """
# #     prepared_text = state["source"].get("prepared_text") or ""
# #     print(f"[set_lecture] Using prepared lecture ({len(prepared_text)} chars)")
 
# #     meta = state["meta"]
# #     output_dir = Path(meta["output_dir"])
# #     course_code = meta.get("course_code", "")
# #     output_dir.mkdir(parents=True, exist_ok=True)
 
# #     # Persist the text so downstream generators can read a file if needed
# #     txt_path = output_dir / f"{course_code}_lecture.txt"
# #     txt_path.write_text(prepared_text, encoding="utf-8")
 
# #     return {
# #         **state,
# #         "final_lecture": prepared_text,
# #         "lecture_paths": LecturePaths(
# #             pdf=None,
# #             txt=str(txt_path),
# #             json=None,
# #         ),
# #         "current_step": "generating_content",
# #     }
 
 
# # # PATH 2 — generated_lecture

# # def generate_lecture(state: AgentState) -> AgentState:
# #     """
# #     PATH 2: Generate a lecture from uploaded resources using LectureAPIWrapper.
# #     LLM-heavy node.
# #     """
# #     meta   = state["meta"]
# #     source = state["source"]
# #     approval = state.get("lecture_approval")
 
# #     iteration = approval["iteration"] if approval else 0
# #     feedback  = approval.get("teacher_feedback") if approval else None
 
# #     print(f"[generate_lecture] iteration={iteration}"
# #           + (f", feedback='{feedback}'" if feedback else ""))
 
# #     output_dir  = Path(meta["output_dir"])
# #     course_code = meta.get("course_code", "")
# #     title       = meta.get("title", meta.get("course_code", "Lecture"))
 
# #     # build source pairs from state
# #     def _first(entries):
# #         """Return (path, query) for the first SourceFile in a list, or (None, None)."""
# #         if entries:
# #             e = entries[0]
# #             return e.get("text"), e.get("query")
# #         return None, None
 
# #     pdf_path,  pdf_query  = _first(source.get("pdf"))
# #     docx_path, docx_query = _first(source.get("docx"))
# #     pptx_path, pptx_query = _first(source.get("pptx"))
# #     audio_path, audio_query = _first(source.get("audio"))
# #     video_path, video_query = _first(source.get("video"))
# #     web_path,  web_query  = _first(source.get("website"))
 
# #     # Images are already dicts: [{"path": ..., "caption": ...}, ...]
# #     raw_images = source.get("images") or []
# #     images_flat = []
# #     for img in raw_images:
# #         images_flat.extend([img.get("path", ""), img.get("caption", "")])
# #     images_flat = images_flat if images_flat else None
 
# #     # Append teacher feedback to topic if regenerating
# #     lecture_topic = title
# #     if feedback:
# #         lecture_topic = f"{title}\n\n[Teacher feedback for revision]: {feedback}"
 
# #     paths = _wrapper.generate_lecture_api(
# #         lecture_topic=lecture_topic,
# #         output_dir=output_dir,
# #         course_code=course_code,
# #         pdf_path=pdf_path,   pdf_query=pdf_query,
# #         docx_path=docx_path, docx_query=docx_query,
# #         pptx_path=pptx_path, pptx_query=pptx_query,
# #         txt_path=audio_path, txt_query=audio_query,   # audio pre-extracted to text
# #         url_path=web_path,   url_query=web_query,
# #         images=images_flat,
# #     )
 
# #     # Read generated txt so final_lecture is always populated
# #     lecture_text = ""
# #     if paths.get("txt"):
# #         try:
# #             lecture_text = Path(paths["txt"]).read_text(encoding="utf-8")
# #         except Exception:
# #             pass
 
# #     new_approval = {
# #         "status": "pending",
# #         "teacher_feedback": None,
# #         "iteration": iteration,
# #         "max_iterations": (approval or {}).get("max_iterations", 3),
# #     }
 
# #     return {
# #         **state,
# #         "final_lecture": lecture_text,
# #         "lecture_paths": LecturePaths(
# #             pdf=paths.get("pdf"),
# #             txt=paths.get("txt"),
# #             json=paths.get("json"),
# #         ),
# #         "lecture_approval": new_approval,
# #         "current_step": "awaiting_approval",
# #     }
 
 
# # # HITL — interrupt_for_approval  (PATH 2 only)

# # def interrupt_for_approval(state: AgentState) -> AgentState:
# #     """
# #     Pauses execution so the teacher can read the generated lecture
# #     and either approve it or reject it with feedback.
 
# #     The interrupt payload is sent to the front-end / caller.
# #     When the graph resumes the caller must update lecture_approval in the state.
# #     """
# #     approval = state.get("lecture_approval", {})
# #     print(f"[interrupt_for_approval] Pausing for teacher review "
# #           f"(iteration {approval.get('iteration', 0)})")
 
# #     # LangGraph interrupt — suspends the graph here
# #     teacher_response: dict[str, Any] = interrupt({
# #         "lecture_pdf":  state.get("lecture_paths", {}).get("pdf"),
# #         "lecture_txt":  state.get("lecture_paths", {}).get("txt"),
# #         "iteration":    approval.get("iteration", 0),
# #         "message":      "Please review the generated lecture and approve or reject with feedback.",
# #     })
 
# #     # teacher_response expected: {"status": "approved"|"rejected", "feedback": "..."}
# #     status   = teacher_response.get("status", "approved")
# #     feedback = teacher_response.get("feedback", "")
 
# #     updated_approval = {
# #         **approval,
# #         "status":           status,
# #         "teacher_feedback": feedback if status == "rejected" else None,
# #     }
 
# #     return {
# #         **state,
# #         "lecture_approval": updated_approval,
# #         "current_step": "awaiting_approval",
# #     }
 
 
# # def _approval_edge(state: AgentState) -> str:
# #     """
# #     Conditional edge after interrupt_for_approval:
# #     - approved              → generate_all_content
# #     - rejected + under cap  → generate_lecture (regen)
# #     - rejected + at cap     → generate_all_content (forced)
# #     """
# #     approval = state.get("lecture_approval", {})
# #     status      = approval.get("status", "approved")
# #     iteration   = approval.get("iteration", 0)
# #     max_iter    = approval.get("max_iterations", 3)
 
# #     if status == "approved":
# #         print("[approval_edge] Approved → generate_all_content")
# #         return "generate_all_content"
 
# #     if iteration < max_iter:
# #         print(f"[approval_edge] Rejected (iter {iteration}/{max_iter}) → regenerate")
# #         # Bump iteration counter before looping back
# #         approval["iteration"] = iteration + 1
# #         return "generate_lecture"
 
# #     print(f"[approval_edge] Max iterations reached → force proceed")
# #     return "generate_all_content"
 
 
# # # CONTENT GENERATION  (both paths converge here)
 
# # def generate_all_content(state: AgentState) -> AgentState:
# #     """
# #     Runs all content generators in parallel (asyncio) using the lecture text.
# #     Generators: hologram_script, summary, worksheet, quiz, knowledge_graph.
# #     """
# #     print("[generate_all_content] Starting parallel content generation...")
 
# #     meta        = state["meta"]
# #     output_dir  = Path(meta["output_dir"])
# #     course_code = meta.get("course_code", "")
# #     title       = meta.get("title", "")
# #     content     = state.get("final_lecture", "")
 
# #     if not content:
# #         print("[generate_all_content] No lecture text found — skipping generators.")
# #         return {
# #             **state,
# #             "generated_content": GeneratedContent(
# #                 script=None, worksheet=None, quiz=None,
# #                 summary=None, knowledge_graph=None,
# #             ),
# #             "current_step": "generating_content",
# #         }
 
# #     async def _run_all():
# #         loop = asyncio.get_event_loop()
 
# #         def _script():
# #             return _wrapper.generate_script(
# #                 content=content, output_dir=output_dir,
# #                 course_code=course_code, title=title,
# #             )
 
# #         def _summary():
# #             return _wrapper.generate_summary(
# #                 content=content, output_dir=output_dir,
# #                 course_code=course_code, title=title,
# #             )
 
# #         def _worksheet():
# #             return _wrapper.generate_worksheet(
# #                 content=content, output_dir=output_dir,
# #                 course_code=course_code, title=title,
# #             )
 
# #         def _quiz():
# #             return _wrapper.generate_quiz(
# #                 content=content, output_dir=output_dir,
# #                 course_code=course_code, title=title,
# #             )
 
# #         def _kg():
# #             # KG generator needs a txt file on disk
# #             txt_path = state.get("lecture_paths", {}).get("txt")
# #             if not txt_path:
# #                 # write temp file
# #                 tmp = output_dir / f"{course_code}_lecture_tmp.txt"
# #                 tmp.write_text(content, encoding="utf-8")
# #                 txt_path = str(tmp)
# #             return _wrapper.generate_knowledge_graph(
# #                 txt_path=txt_path, output_dir=output_dir,
# #                 course_code=course_code,
# #             )
 
# #         tasks = [
# #             loop.run_in_executor(None, _script),
# #             loop.run_in_executor(None, _summary),
# #             loop.run_in_executor(None, _worksheet),
# #             loop.run_in_executor(None, _quiz),
# #             loop.run_in_executor(None, _kg),
# #         ]
# #         return await asyncio.gather(*tasks, return_exceptions=True)
 
# #     results = asyncio.run(_run_all())
# #     script_r, summary_r, worksheet_r, quiz_r, kg_r = results
 
# #     def _safe(r):
# #         """Return result dict or None if the task raised."""
# #         if isinstance(r, Exception):
# #             print(f"[generate_all_content] ❌ Generator error: {r}")
# #             return None
# #         return r
 
# #     generated = GeneratedContent(
# #         script=_safe(script_r),
# #         summary=_safe(summary_r),
# #         worksheet=_safe(worksheet_r),
# #         quiz=_safe(quiz_r),
# #         knowledge_graph=_safe(kg_r),
# #     )
 
# #     print("[generate_all_content] All generators finished.")
# #     return {
# #         **state,
# #         "generated_content": generated,
# #         "current_step": "generating_content",
# #     }
 
 
# # # SAVE RESULTS

# # def save_results(state: AgentState) -> AgentState:
# #     """
# #     Persists a summary manifest JSON to the output directory (and optionally
# #     to a database).  Placeholder DB call — replace with your ORM / API layer.
# #     """
# #     import json
 
# #     meta       = state["meta"]
# #     output_dir = Path(meta["output_dir"])
# #     output_dir.mkdir(parents=True, exist_ok=True)
 
# #     manifest = {
# #         "session_id":    meta.get("session_id"),
# #         "teacher_id":    meta.get("teacher_id"),
# #         "course_code":   meta.get("course_code"),
# #         "title":         meta.get("title"),
# #         "lecture_paths": state.get("lecture_paths"),
# #         "generated_content": state.get("generated_content"),
# #         "approval": state.get("lecture_approval"),
# #     }
 
# #     manifest_path = output_dir / "manifest.json"
# #     manifest_path.write_text(
# #         json.dumps(manifest, indent=2, ensure_ascii=False),
# #         encoding="utf-8",
# #     )
# #     print(f"[save_results] Manifest saved → {manifest_path}")
 
# #     # replace with real DB persist
# #     # db.sessions.upsert(manifest)
 
# #     return {
# #         **state,
# #         "current_step": "done",
# #     }










# # ai/agent/nodes.py

# import asyncio
# import json
# from pathlib import Path
# from typing import Any

# from langgraph.types import interrupt

# from state import AgentState, LecturePaths, GeneratedContent
# from wrapper import SimpleGeneratorWrapper

# _wrapper = SimpleGeneratorWrapper()



# def route_input(state: AgentState) -> AgentState:
#     """
#     Reads source.type and sets current_step so the conditional edge
#     knows which path to take.  No LLM call — pure routing.
#     """
#     source_type = state["source"]["type"]
#     print(f"[route_input] source.type = {source_type}")
#     return {
#         **state,
#         "current_step": "generating_lecture",
#     }

# # ── PATH ROUTING ──────────────────────────────────────────────────────────────

# def _route_input_edge(state: AgentState) -> str:
#     src = state["source"]["type"]
#     print(f"[route] source.type = {src}")
#     if src == "prepared_lecture":
#         return "set_lecture"
#     return "set_generating_lecture_status"   # ← routes to status node first





# # ── PATH A: prepared_lecture ──────────────────────────────────────────────────

# def set_lecture(state: AgentState) -> AgentState:
#     """
#     PATH A: Teacher provided their own lecture text.
#     No LLM call. Copy prepared_text → final_lecture, persist to disk.
#     """
#     prepared_text = state["source"].get("prepared_text") or ""
#     print(f"[set_lecture] {len(prepared_text)} chars")

#     meta        = state["meta"]
#     output_dir  = Path(meta["output_dir"])
#     course_code = meta.get("course_code", "")
#     output_dir.mkdir(parents=True, exist_ok=True)

#     txt_path = output_dir / f"{course_code}_lecture.txt"
#     txt_path.write_text(prepared_text, encoding="utf-8")

#     return {
#         **state,
#         "final_lecture":    prepared_text,
#         "lecture_paths":    LecturePaths(pdf=None, txt=str(txt_path), json=None),
#         "lecture_approval": None,          # never used in path A
#         "current_step":     "generating_content",
#     }


# # ── PATH B: generated_lecture ─────────────────────────────────────────────────

# # nodes.py — replace generate_lecture with this

# import asyncio
# from concurrent.futures import ThreadPoolExecutor

# async def generate_lecture(state: AgentState) -> AgentState:
#     """
#     PATH B: Generate lecture from source materials via LLM.
#     - Versions the output directory (v1/, v2/, v3/) so each
#       generation attempt is preserved on disk.
#     - Runs the blocking LLM call in a thread executor so the
#       event loop stays free for LangGraph context and status polling.
#     """
#     meta     = state["meta"]
#     source   = state["source"]
#     approval = state.get("lecture_approval") or {}

#     # Increment iteration on every entry to this node
#     # First call: 0 + 1 = 1 → v1/
#     # Second call (after reject): 1 + 1 = 2 → v2/
#     iteration = approval.get("iteration", 0) + 1    # ← INCREMENT HERE
#     feedback  = approval.get("teacher_feedback")
#     max_iter  = approval.get("max_iterations", 3)

#     print(f"[generate_lecture] iteration={iteration}"
#           + (f" feedback='{feedback}'" if feedback else ""))

#     # Version the output directory
#     base_dir   = Path(meta["output_dir"])
#     output_dir = base_dir / f"v{iteration}"          # v1/, v2/, v3/
#     output_dir.mkdir(parents=True, exist_ok=True)

#     course_code = meta.get("course_code", "")
#     title       = meta.get("title", course_code or "Lecture")

#     # ── Extract source file references ────────────────────────────
#     def _first(entries):
#         if entries:
#             e = entries[0]
#             return e.get("text"), e.get("query")
#         return None, None

#     pdf_path,   pdf_query   = _first(source.get("pdf"))
#     docx_path,  docx_query  = _first(source.get("docx"))
#     pptx_path,  pptx_query  = _first(source.get("pptx"))
#     audio_path, audio_query = _first(source.get("audio"))
#     video_path, video_query = _first(source.get("video"))
#     web_path,   web_query   = _first(source.get("website"))

#     raw_images  = source.get("images") or []
#     images_flat = []
#     for img in raw_images:
#         images_flat.extend([img.get("path", ""), img.get("caption", "")])
#     images_flat = images_flat if images_flat else None

#     # ── Append feedback to topic on regeneration ──────────────────
#     lecture_topic = title
#     if feedback:
#         lecture_topic = f"{title}\n\n[Teacher feedback for revision]: {feedback}"

#     # ── Run blocking LLM call in thread executor ──────────────────
#     # Keeps the event loop free so LangGraph context is preserved
#     # and status polling works during the 30-minute generation.
#     def _run_generation():
#         return _wrapper.generate_lecture_api(
#             lecture_topic = lecture_topic,
#             output_dir    = output_dir,
#             course_code   = course_code,
#             pdf_path      = pdf_path,   pdf_query   = pdf_query,
#             docx_path     = docx_path,  docx_query  = docx_query,
#             pptx_path     = pptx_path,  pptx_query  = pptx_query,
#             txt_path      = audio_path, txt_query   = audio_query,
#             url_path      = web_path,   url_query   = web_query,
#             images        = images_flat,
#         )

#     loop  = asyncio.get_event_loop()
#     paths = await loop.run_in_executor(None, _run_generation)

#     # ── Debug ─────────────────────────────────────────────────────
#     print(f"[generate_lecture] wrapper returned paths: {paths}")
#     if paths.get("pdf"):
#         print(f"[generate_lecture] PDF exists on disk: {Path(paths['pdf']).exists()}")

#     # ── Read generated text ───────────────────────────────────────
#     lecture_text = ""
#     if paths.get("txt"):
#         try:
#             lecture_text = Path(paths["txt"]).read_text(encoding="utf-8")
#         except Exception as e:
#             print(f"[generate_lecture] could not read txt: {e}")

#     return {
#         **state,
#         "final_lecture": lecture_text,
#         "lecture_paths": LecturePaths(
#             pdf  = paths.get("pdf"),
#             txt  = paths.get("txt"),
#             json = paths.get("json"),
#         ),
#         "lecture_approval": {
#             "status":           "pending",
#             "teacher_feedback": None,
#             "iteration":        iteration,    # ← save incremented value
#             "max_iterations":   max_iter,
#         },
#         "current_step": "awaiting_approval",
#     }
# # ── HITL: interrupt ───────────────────────────────────────────────────────────
# # nodes.py — replace interrupt_for_approval with this

# def interrupt_for_approval(state: AgentState) -> AgentState:
#     """
#     Runs AFTER the teacher approves or rejects.
#     LangGraph pauses BEFORE this node via interrupt_before.
#     Reads the decision from lecture_approval which was updated by aupdate_state.
#     """
#     approval  = state.get("lecture_approval", {})
#     status    = approval.get("status", "pending")
#     feedback  = approval.get("teacher_feedback", "")
#     iteration = approval.get("iteration", 0)
#     max_iter  = approval.get("max_iterations", 3)

#     print(f"[interrupt_for_approval] Resumed — status={status}, iteration={iteration}/{max_iter}")

#     return {
#         **state,
#         "lecture_approval": {
#             **approval,
#             "status":           status,
#             "teacher_feedback": feedback if status == "rejected" else None,
#         },
#         "current_step": "awaiting_approval",
#     }


# def _approval_edge(state: AgentState) -> str:
#     approval  = state.get("lecture_approval", {})
#     status    = approval.get("status", "approved")
#     iteration = approval.get("iteration", 0)
#     max_iter  = approval.get("max_iterations", 3)

#     if status == "approved":
#         print("[approval_edge] approved → set_generating_content_status")
#         return "set_generating_content_status"   # ← status node first

#     if iteration < max_iter:
#         print(f"[approval_edge] rejected ({iteration}/{max_iter}) → set_generating_lecture_status")
#         return "set_generating_lecture_status"   # ← status node first

#     print("[approval_edge] max iterations reached → set_generating_content_status")
#     return "set_generating_content_status"


# # ── CONTENT GENERATION (both paths converge here) ─────────────────────────────

# import concurrent.futures

# def generate_all_content(state: AgentState) -> AgentState:
#     """
#     Runs all 6 content generators in parallel using a ThreadPoolExecutor.
#     Regular def — works in both sync graph.stream() and async graph.ainvoke().
#     No event loop required.
#     """
#     print("[generate_all_content] Starting...")

#     meta        = state["meta"]
#     output_dir  = Path(meta["output_dir"])
#     course_code = meta.get("course_code", "")
#     title       = meta.get("title", "")
#     content     = state.get("final_lecture", "")

#     state = {**state, "current_step": "generating_content"}

#     if not content:
#         print("[generate_all_content] No lecture text — skipping")
#         return {
#             **state,
#             "generated_content": GeneratedContent(
#                 script=None, worksheet=None, quiz=None,
#                 summary=None, flowchart=None, knowledge_graph=None,
#             ),
#         }



#     def _get_txt_path() -> str:
#         txt = (state.get("lecture_paths") or {}).get("txt")
#         if txt:
#             return txt
#         tmp = output_dir / f"{course_code}_lecture_tmp.txt"
#         tmp.write_text(content, encoding="utf-8")
#         return str(tmp)

#     # Define all generators as plain callables
#     generators = {
#         "script":    lambda: _wrapper.generate_script(
#             content=content, output_dir=output_dir,
#             course_code=course_code, title=title,
#         ),
#         "summary":   lambda: _wrapper.generate_summary(
#             content=content, output_dir=output_dir,
#             course_code=course_code, title=title,
#         ),
#         "worksheet": lambda: _wrapper.generate_worksheet(
#             content=content, output_dir=output_dir,
#             course_code=course_code, title=title,
#         ),
#         "quiz":      lambda: _wrapper.generate_quiz(
#             content=content, output_dir=output_dir,
#             course_code=course_code, title=title,
#         ),

#         "knowledge_graph": lambda: _wrapper.generate_knowledge_graph(
#             txt_path=_get_txt_path(),
#             output_dir=output_dir,
#             course_code=course_code,
#         ),
#     }

#     results = {}

#     # Run all generators in parallel — no event loop needed
#     with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
#         futures = {
#             executor.submit(fn): name
#             for name, fn in generators.items()
#         }
#         for future in concurrent.futures.as_completed(futures):
#             name = futures[future]
#             try:
#                 results[name] = future.result()
#                 print(f"[generate_all_content] ✓ {name}")
#             except Exception as e:
#                 print(f"[generate_all_content] ❌ {name}: {e}")
#                 results[name] = None

#     return {
#         **state,
#         "generated_content": GeneratedContent(
#             script=results.get("script"),
#             summary=results.get("summary"),
#             worksheet=results.get("worksheet"),
#             quiz=results.get("quiz"),
#             knowledge_graph=results.get("knowledge_graph"),
#         ),
#     }


# # ── SAVE RESULTS ──────────────────────────────────────────────────────────────

# def save_results(state: AgentState) -> AgentState:
#     """
#     Writes a manifest.json summarising all output file paths.
#     Replace the comment below with your real DB persist call.
#     """
#     meta       = state["meta"]
#     output_dir = Path(meta["output_dir"])
#     output_dir.mkdir(parents=True, exist_ok=True)

#     manifest = {
#         "session_id":        meta.get("session_id"),
#         "teacher_id":        meta.get("teacher_id"),
#         "course_code":       meta.get("course_code"),
#         "title":             meta.get("title"),
#         "lecture_paths":     state.get("lecture_paths"),
#         "generated_content": state.get("generated_content"),
#         "lecture_approval":  state.get("lecture_approval"),
#     }

#     manifest_path = output_dir / "manifest.json"
#     manifest_path.write_text(
#         json.dumps(manifest, indent=2, ensure_ascii=False),
#         encoding="utf-8",
#     )
#     print(f"[save_results] manifest → {manifest_path}")

#     # TODO: replace with real DB call
#     # await db.sessions.upsert(manifest)

#     return {**state, "current_step": "done"}

# # nodes.py — add these two functions

# def set_generating_lecture_status(state: AgentState) -> AgentState:
#     """
#     Lightweight node — just sets current_step to generating_lecture.
#     LangGraph writes checkpoint after this returns so polling sees it immediately.
#     """
#     print("[set_generating_lecture_status] Status → generating_lecture")
#     return {**state, "current_step": "generating_lecture"}


# def set_generating_content_status(state: AgentState) -> AgentState:
#     """
#     Lightweight node — just sets current_step to generating_content.
#     LangGraph writes checkpoint after this returns so polling sees it immediately.
#     """
#     print("[set_generating_content_status] Status → generating_content")
#     return {**state, "current_step": "generating_content"}


# ai/agent/nodes.py

import asyncio
import json
import concurrent.futures
from pathlib import Path
from typing import Any

from langgraph.types import interrupt

from state import AgentState, LecturePaths, GeneratedContent
from wrapper import SimpleGeneratorWrapper, SimpleExtractorWrapper

_wrapper   = SimpleGeneratorWrapper()
_extractor = SimpleExtractorWrapper()


def route_input(state: AgentState) -> AgentState:
    source_type = state["source"]["type"]
    print(f"[route_input] source.type = {source_type}")
    return {
        **state,
        "current_step": "generating_lecture",
    }


# ── PATH ROUTING ──────────────────────────────────────────────────────────────

def _route_input_edge(state: AgentState) -> str:
    src = state["source"]["type"]
    print(f"[route] source.type = {src}")
    if src == "prepared_lecture":
        return "set_lecture"
    return "set_generating_lecture_status"


# ── SOURCE RESOLUTION ─────────────────────────────────────────────────────────

def _resolve_entry(e: dict) -> tuple:
    """
    Return (text_or_path, query) for a single source entry.

    Tries in order:
      1. 'text'      — pre-extracted content string
      2. 'file_path' — local file (agent extracts here)
      3. 'url'       — web/YouTube URL (agent extracts here)
    """
    query = e.get("query") or None

    text = (e.get("text") or "").strip()
    if text:
        return text, query

    fp = (e.get("file_path") or "").strip()
    if fp:
        print(f"[resolve_entry] Extracting file: {fp}")
        extracted = _extractor.extract_auto(fp)
        return (extracted.strip() or None), query

    url = (e.get("url") or "").strip()
    if url:
        print(f"[resolve_entry] Extracting URL: {url}")
        extracted = _extractor.extract_url(url)
        return (extracted.strip() or None), query

    return None, query


def _first(entries) -> tuple:
    """Return (text_or_path, query) for the first entry in a source list."""
    if not entries:
        return None, None
    return _resolve_entry(entries[0])


# ── Helper: safely read lecture_paths ────────────────────────────────────────
# PostgreSQL checkpointer round-trips state through JSON, so dataclasses
# arrive back as plain dicts. Always use this helper instead of paths.txt

def _get_lecture_paths_field(state: AgentState, field: str):
    """
    Safely read a field from lecture_paths regardless of whether it is
    a LecturePaths dataclass or a plain dict (after checkpoint round-trip).
    """
    paths = state.get("lecture_paths")
    if paths is None:
        return None
    if isinstance(paths, dict):
        return paths.get(field)
    return getattr(paths, field, None)


# ── PATH A: prepared_lecture ──────────────────────────────────────────────────

def set_lecture(state: AgentState) -> AgentState:
    prepared_text = state["source"].get("prepared_text") or ""
    print(f"[set_lecture] {len(prepared_text)} chars")

    meta        = state["meta"]
    output_dir  = Path(meta["output_dir"])
    course_code = meta.get("course_code", "")
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / f"{course_code}_lecture.txt"
    txt_path.write_text(prepared_text, encoding="utf-8")

    return {
        **state,
        "final_lecture":    prepared_text,
        "lecture_paths":    LecturePaths(pdf=None, txt=str(txt_path), json=None),
        "lecture_approval": None,
        "current_step":     "generating_content",
    }


# ── PATH B: generated_lecture ─────────────────────────────────────────────────

async def generate_lecture(state: AgentState) -> AgentState:
    """
    PATH B: Generate lecture from source materials via LLM.
    Versions the output directory (v1/, v2/, v3/).
    Runs the blocking LLM call in a thread executor.
    """
    meta     = state["meta"]
    source   = state["source"]
    approval = state.get("lecture_approval") or {}

    iteration = approval.get("iteration", 0) + 1
    feedback  = approval.get("teacher_feedback")
    max_iter  = approval.get("max_iterations", 3)

    print(f"[generate_lecture] iteration={iteration}"
          + (f" feedback='{feedback}'" if feedback else ""))

    base_dir   = Path(meta["output_dir"])
    output_dir = base_dir / f"v{iteration}"
    output_dir.mkdir(parents=True, exist_ok=True)

    course_code = meta.get("course_code", "")
    title       = meta.get("title", course_code or "Lecture")

    # ── Resolve sources ───────────────────────────────────────────
    pdf_path,   pdf_query   = _first(source.get("pdf"))
    docx_path,  docx_query  = _first(source.get("docx"))
    pptx_path,  pptx_query  = _first(source.get("pptx"))
    audio_path, audio_query = _first(source.get("audio"))
    video_path, video_query = _first(source.get("video"))
    web_path,   web_query   = _first(source.get("website"))

    # Merge audio + video into txt slot
    if audio_path and video_path:
        txt_path  = f"{audio_path}\n\n---\n\n{video_path}"
        txt_query = audio_query or video_query
    else:
        txt_path  = audio_path or video_path
        txt_query = audio_query or video_query

    # Images
    raw_images  = source.get("images") or []
    images_flat = []
    for img in raw_images:
        images_flat.extend([img.get("path", ""), img.get("caption", "")])
    images_flat = images_flat if images_flat else None

    # Append feedback to topic on regeneration
    lecture_topic = title
    if feedback:
        lecture_topic = f"{title}\n\n[Teacher feedback for revision]: {feedback}"

    # Debug
    sources_summary = {
        k: "✓" for k, v in {
            "pdf": pdf_path, "docx": docx_path, "pptx": pptx_path,
            "txt": txt_path, "url":  web_path,
        }.items() if v
    }
    print(f"[generate_lecture] sources resolved: {sources_summary or 'NONE'}")

    # ── Run blocking LLM call in thread executor ──────────────────
    def _run_generation():
        return _wrapper.generate_lecture_api(
            lecture_topic = lecture_topic,
            output_dir    = output_dir,
            course_code   = course_code,
            pdf_path      = pdf_path,  pdf_query  = pdf_query,
            docx_path     = docx_path, docx_query = docx_query,
            pptx_path     = pptx_path, pptx_query = pptx_query,
            txt_path      = txt_path,  txt_query  = txt_query,
            url_path      = web_path,  url_query  = web_query,
            images        = images_flat,
        )

    loop  = asyncio.get_event_loop()
    paths = await loop.run_in_executor(None, _run_generation)

    print(f"[generate_lecture] wrapper returned paths: {paths}")
    if paths.get("pdf"):
        print(f"[generate_lecture] PDF exists on disk: {Path(paths['pdf']).exists()}")

    # Read generated text
    lecture_text = ""
    if paths.get("txt"):
        try:
            lecture_text = Path(paths["txt"]).read_text(encoding="utf-8")
        except Exception as e:
            print(f"[generate_lecture] could not read txt: {e}")

    return {
        **state,
        "final_lecture": lecture_text,
        "lecture_paths": LecturePaths(
            pdf  = paths.get("pdf"),
            txt  = paths.get("txt"),
            json = paths.get("json"),
        ),
        "lecture_approval": {
            "status":           "pending",
            "teacher_feedback": None,
            "iteration":        iteration,
            "max_iterations":   max_iter,
        },
        "current_step": "awaiting_approval",
    }


# ── HITL: interrupt ───────────────────────────────────────────────────────────

def interrupt_for_approval(state: AgentState) -> AgentState:
    approval  = state.get("lecture_approval", {})
    status    = approval.get("status", "pending")
    feedback  = approval.get("teacher_feedback", "")
    iteration = approval.get("iteration", 0)
    max_iter  = approval.get("max_iterations", 3)

    print(f"[interrupt_for_approval] Resumed — status={status}, iteration={iteration}/{max_iter}")

    return {
        **state,
        "lecture_approval": {
            **approval,
            "status":           status,
            "teacher_feedback": feedback if status == "rejected" else None,
        },
        "current_step": "awaiting_approval",
    }


def _approval_edge(state: AgentState) -> str:
    approval  = state.get("lecture_approval", {})
    status    = approval.get("status", "approved")
    iteration = approval.get("iteration", 0)
    max_iter  = approval.get("max_iterations", 3)

    if status == "approved":
        print("[approval_edge] approved → set_generating_content_status")
        return "set_generating_content_status"

    if iteration < max_iter:
        print(f"[approval_edge] rejected ({iteration}/{max_iter}) → set_generating_lecture_status")
        return "set_generating_lecture_status"

    print("[approval_edge] max iterations reached → set_generating_content_status")
    return "set_generating_content_status"


# ── CONTENT GENERATION ────────────────────────────────────────────────────────

def generate_all_content(state: AgentState) -> AgentState:
    """
    Runs all 5 content generators in parallel using a ThreadPoolExecutor.
    """
    print("[generate_all_content] Starting...")

    meta        = state["meta"]
    output_dir  = Path(meta["output_dir"])
    course_code = meta.get("course_code", "")
    title       = meta.get("title", "")
    content     = state.get("final_lecture", "")

    state = {**state, "current_step": "generating_content"}

    if not content:
        print("[generate_all_content] No lecture text — skipping")
        return {
            **state,
            "generated_content": GeneratedContent(
                script=None, worksheet=None, quiz=None,
                summary=None, flowchart=None, knowledge_graph=None,
            ),
        }

    def _get_txt_path() -> str:
        """
        Return path to the lecture .txt file for knowledge graph generator.

        PostgreSQL checkpointer serializes state to JSON — lecture_paths
        arrives as a plain dict after a checkpoint round-trip, not a
        LecturePaths dataclass. Handle both cases explicitly.
        """
        # Use the helper that handles both dict and dataclass
        txt = _get_lecture_paths_field(state, "txt")

        print(f"[_get_txt_path] txt = {txt}, "
              f"exists = {Path(txt).exists() if txt else False}")

        if txt and Path(txt).exists():
            print(f"[_get_txt_path] ✓ using real txt: {txt}")
            return txt

        # Fallback: write in-memory content to a temp file
        tmp = output_dir / f"{course_code}_lecture_tmp.txt"
        tmp.write_text(content, encoding="utf-8")
        print(f"[_get_txt_path] ⚠ real txt not found — fallback to tmp: {tmp}")
        return str(tmp)

    generators = {
        "script":    lambda: _wrapper.generate_script(
            content=content, output_dir=output_dir,
            course_code=course_code, title=title,
        ),
        "summary":   lambda: _wrapper.generate_summary(
            content=content, output_dir=output_dir,
            course_code=course_code, title=title,
        ),
        "worksheet": lambda: _wrapper.generate_worksheet(
            content=content, output_dir=output_dir,
            course_code=course_code, title=title,
        ),
        "quiz":      lambda: _wrapper.generate_quiz(
            content=content, output_dir=output_dir,
            course_code=course_code, title=title,
        ),
        "knowledge_graph": lambda: _wrapper.generate_knowledge_graph(
            txt_path=_get_txt_path(),
            output_dir=output_dir,
            course_code=course_code,
        ),
    }

    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fn): name
            for name, fn in generators.items()
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
                print(f"[generate_all_content] ✓ {name}")
            except Exception as e:
                print(f"[generate_all_content] ❌ {name}: {e}")
                results[name] = None

    return {
        **state,
        "generated_content": GeneratedContent(
            script=results.get("script"),
            summary=results.get("summary"),
            worksheet=results.get("worksheet"),
            quiz=results.get("quiz"),
            knowledge_graph=results.get("knowledge_graph"),
        ),
    }


# ── SAVE RESULTS ──────────────────────────────────────────────────────────────

def save_results(state: AgentState) -> AgentState:
    meta       = state["meta"]
    output_dir = Path(meta["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "session_id":        meta.get("session_id"),
        "teacher_id":        meta.get("teacher_id"),
        "course_code":       meta.get("course_code"),
        "title":             meta.get("title"),
        "lecture_paths":     state.get("lecture_paths"),
        "generated_content": state.get("generated_content"),
        "lecture_approval":  state.get("lecture_approval"),
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[save_results] manifest → {manifest_path}")

    return {**state, "current_step": "done"}


# ── STATUS NODES ──────────────────────────────────────────────────────────────

def set_generating_lecture_status(state: AgentState) -> AgentState:
    print("[set_generating_lecture_status] Status → generating_lecture")
    return {**state, "current_step": "generating_lecture"}


def set_generating_content_status(state: AgentState) -> AgentState:
    print("[set_generating_content_status] Status → generating_content")
    return {**state, "current_step": "generating_content"}