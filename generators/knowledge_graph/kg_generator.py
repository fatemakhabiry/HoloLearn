import os
import time
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

from kg_config import CLUSTER_COLORS, get_chunk_settings, clean_text, parse_json, merge
from kg_prompts import SYSTEM_PROMPT, make_human_prompt
from kg_render import render_html


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE
# ─────────────────────────────────────────────────────────────────────────────
def generate(txt_path: str, course_code: str = "", output_path: str = "") -> str:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("Set OPENROUTER_API_KEY in your .env")

    raw = Path(txt_path).read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        raise ValueError(f"File is empty: {txt_path}")

    before = len(raw)
    text = clean_text(raw)
    pct = round((before - len(text)) / before * 100) if before else 0
    print(f"[1/4] Cleaned: {before:,} → {len(text):,} chars ({pct}% noise removed)")

    chunk_size, chunk_overlap = get_chunk_settings(len(text))
    print(f"[chunking] chunk_size={chunk_size:,} overlap={chunk_overlap:,}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n\n", "\n\n",
            "\n• ", "\n- ", "\n* ",
            "\n",
            ". ",
            " "
        ]
    )
    chunks = splitter.split_text(text)
    print(f"[2/4] Split into {len(chunks)} chunk(s)")

    llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model_name="arcee-ai/trinity-large-preview:free",
        temperature=0.1,
        max_tokens=16000,
    )

    fragments = []
    for i, chunk in enumerate(chunks):
        print(f"[3/4] Chunk {i+1}/{len(chunks)} ({len(chunk):,} chars)…", end=" ", flush=True)
        t0 = time.time()
        resp = llm.invoke([SystemMessage(content=SYSTEM_PROMPT),
                           HumanMessage(content=make_human_prompt(chunk, CLUSTER_COLORS))])
        raw_text = resp.content
        frag = parse_json(raw_text)
        fragments.append(frag)
        print(f"→ {len(frag.get('nodes', []))} nodes, {len(frag.get('edges', []))} edges ({time.time()-t0:.1f}s)")

    graph = merge(fragments)
    print(f"[3/4] Merged: {len(graph['nodes'])} nodes | {len(graph['edges'])} edges | {len(graph['clusters'])} clusters")

    html = render_html(graph, course_code)
    print(f"[4/4] Rendered: {len(html):,} chars")

    if not output_path:
        output_path = str(Path(txt_path).with_suffix(".html"))
    Path(output_path).write_text(html, encoding="utf-8")
    print(f"\n✅ Saved → {output_path}")
    return output_path


if __name__ == "__main__":
    load_dotenv()
    generate(txt_path="1_introduction_to_infosec_text.txt", course_code="is123", output_path="infosec66_fixed.html")