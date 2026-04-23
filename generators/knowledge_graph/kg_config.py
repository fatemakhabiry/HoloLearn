import re
import json
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
MODEL         = "z-ai/glm-4.5-air:free"
CHUNK_SIZE    = 22_000
CHUNK_OVERLAP = 600

CLUSTER_COLORS = [
    "#3873ff", "#00c9a7", "#ff5757", "#ffac30",
    "#a78bfa", "#f472b6", "#34d399", "#fb923c",
]

D3_LOCAL_PATH = Path(__file__).parent / "assets" / "d3.v7.8.5.min.js"


def get_chunk_settings(text_length: int):
    if text_length <= 15_000:
        return 45_000, 0
    elif text_length <= 60_000:
        return 20_000, 1200
    elif text_length <= 120_000:
        return 15_000, 1500
    else:
        return 12_000, 2000


# ─────────────────────────────────────────────────────────────────────────────
# CLEAN
# ─────────────────────────────────────────────────────────────────────────────
_NOISE = re.compile("|".join([
    r'[A-Z][a-z]+ [A-Z]\. \w+ and [A-Z][a-z]+ [A-Z]\. \w+,[^\n]*\n?',
    r'All Rights Reserved\.[^\n]*\n?',
    r'May not be\s*\n?scanned[^\n]*\n?',
    r'scanned, copied or duplicated[^\n]*\n?',
    r'posted to a publicly[^\n]*\n?',
    r'---\s*Page\s+\d+\s*---\n?',
    r'^\s*\d{1,3}\s*$',
]), re.MULTILINE | re.IGNORECASE)


def clean_text(text: str) -> str:
    text = _NOISE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ─────────────────────────────────────────────────────────────────────────────
# PARSE JSON
# ─────────────────────────────────────────────────────────────────────────────
def parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    raw = raw.replace("\u201c", '"').replace("\u201d", '"')
    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON")
    depth, end = 0, None
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise ValueError("Unbalanced braces")
    js = raw[start:end]
    js = re.sub(r",\s*}", "}", js)
    js = re.sub(r",\s*]", "]", js)
    return json.loads(js)


# ─────────────────────────────────────────────────────────────────────────────
# MERGE
# ─────────────────────────────────────────────────────────────────────────────
def merge(fragments: list) -> dict:
    if len(fragments) == 1:
        frag = fragments[0]
        frag["nodes"] = [n for n in frag.get("nodes", []) if n.get("label", "").strip()]
        return _ensure_connected(frag)

    result = {
        "title":    fragments[0].get("title", "Untitled"),
        "subject":  fragments[0].get("subject", ""),
        "summary":  fragments[0].get("summary", ""),
        "clusters": [], "nodes": [], "edges": [],
    }
    seen_labels, seen_clusters, seen_edges = {}, {}, set()
    node_counter = 0

    for frag in fragments:
        id_remap = {}
        for cl in frag.get("clusters", []):
            norm = cl.get("name", "").strip().lower()
            if not norm:
                continue
            if norm not in seen_clusters:
                idx = len(result["clusters"])
                nc = {"id": f"C{idx+1}", "name": cl["name"],
                      "color": CLUSTER_COLORS[idx % len(CLUSTER_COLORS)]}
                result["clusters"].append(nc)
                seen_clusters[norm] = nc

        for node in frag.get("nodes", []):
            label = node.get("label", "").strip()
            if not label:
                continue
            norm = label.lower()
            if norm in seen_labels:
                id_remap[node.get("id", "")] = seen_labels[norm]
                continue
            node_counter += 1
            new_id = f"n{node_counter}"
            id_remap[node.get("id", "")] = new_id
            seen_labels[norm] = new_id
            orig_cl = node.get("c", "")
            new_cl_id = result["clusters"][0]["id"] if result["clusters"] else "C1"
            for cl in frag.get("clusters", []):
                if cl.get("id") == orig_cl:
                    nm = cl.get("name", "").strip().lower()
                    if nm in seen_clusters:
                        new_cl_id = seen_clusters[nm]["id"]
                    break
            result["nodes"].append({"id": new_id, "c": new_cl_id, "label": label,
                                    "type": node.get("type", "concept"),
                                    "desc": node.get("desc", "")})

        for e in frag.get("edges", []):
            ns  = id_remap.get(e.get("s", ""))
            nt  = id_remap.get(e.get("t", ""))
            rel = (e.get("r", "") or "").strip()
            if not ns or not nt or not rel:
                continue
            key_fwd = f"{ns}|{nt}"
            key_rev = f"{nt}|{ns}"
            if key_fwd in seen_edges or key_rev in seen_edges:
                continue
            seen_edges.add(key_fwd)
            result["edges"].append({"s": ns, "t": nt, "r": rel})

    valid_ids = {n["id"] for n in result["nodes"]}
    result["edges"] = [e for e in result["edges"]
                       if e["s"] in valid_ids and e["t"] in valid_ids]
    if not result["clusters"]:
        result["clusters"] = [{"id": "C1", "name": "Main", "color": CLUSTER_COLORS[0]}]
        for n in result["nodes"]:
            n["c"] = "C1"

    return _ensure_connected(result)


def _ensure_connected(graph: dict) -> dict:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes:
        return graph

    root_id = nodes[0]["id"]

    adj = {n["id"]: set() for n in nodes}
    for e in edges:
        if e["s"] in adj and e["t"] in adj:
            adj[e["s"]].add(e["t"])
            adj[e["t"]].add(e["s"])

    visited = set()

    def bfs(start):
        q = [start]
        visited.add(start)
        while q:
            cur = q.pop(0)
            for nb in adj.get(cur, []):
                if nb not in visited:
                    visited.add(nb)
                    q.append(nb)

    bfs(root_id)

    added = 0
    for node in nodes:
        if node["id"] not in visited:
            comp_root = node["id"]
            edges.append({"s": root_id, "t": comp_root, "r": "relates to"})
            adj[root_id].add(comp_root)
            adj[comp_root].add(root_id)
            bfs(comp_root)
            added += 1

    if added:
        print(f"       [connect] Added {added} bridge edge(s) to unify disconnected components")

    graph["edges"] = edges
    return graph