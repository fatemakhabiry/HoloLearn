"""
Tool registry — general domain only.
Tools: web_search (Tavily), wikipedia.
"""
from __future__ import annotations
from typing import Callable, Dict
from schemas import ToolResult


# tools/__init__.py

# ── Tavily web search ────────────────────────────────────────────────────────

def web_search(query: str) -> ToolResult:
    """Search the web via Tavily and return a synthesised answer + sources."""
    try:
        from tavily import TavilyClient
        import os
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        resp = client.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            max_results=1,          # ← changed from 5 to 1
        )
        answer = resp.get("answer") or ""
        sources = [r["url"] for r in resp.get("results", []) if "url" in r]
        content = answer if answer else "\n\n".join(
            r.get("content", "") for r in resp.get("results", [])[:1]   # ← also cap fallback to 1
        )
        return ToolResult(content=content, sources=sources, credibility_score=0.70)
    except Exception as exc:
        return ToolResult(
            content=f"[web_search error: {exc}]",
            sources=[],
            credibility_score=0.0,
        )


# ── Wikipedia ────────────────────────────────────────────────────────────────

def wikipedia_search(query: str) -> ToolResult:
    """Fetch a Wikipedia summary for background knowledge."""
    try:
        import wikipedia as wp
        wp.set_lang("en")

        # Search for the best matching page title first,
        # then fetch that page — avoids the "page id does not match" error
        search_results = wp.search(query, results=1)
        if not search_results:
            return ToolResult(
                content=f"[wikipedia error: No results found for '{query}']",
                sources=[],
                credibility_score=0.0,
            )

        best_title = search_results[0]
        summary = wp.summary(best_title, sentences=6, auto_suggest=False)
        page = wp.page(best_title, auto_suggest=False)
        return ToolResult(
            content=summary,
            sources=[page.url],
            credibility_score=0.75,
        )
    except wp.DisambiguationError as exc:
        # Pick the first unambiguous option
        try:
            best_title = exc.options[0]
            summary = wp.summary(best_title, sentences=6, auto_suggest=False)
            page = wp.page(best_title, auto_suggest=False)
            return ToolResult(content=summary, sources=[page.url], credibility_score=0.75)
        except Exception as inner_exc:
            return ToolResult(
                content=f"[wikipedia error: {inner_exc}]",
                sources=[],
                credibility_score=0.0,
            )
    except Exception as exc:
        return ToolResult(
            content=f"[wikipedia error: {exc}]",
            sources=[],
            credibility_score=0.0,
        )


# ── Registry ─────────────────────────────────────────────────────────────────

GENERAL_TOOLS: Dict[str, Callable[[str], ToolResult]] = {
    "web_search": web_search,
    "wikipedia": wikipedia_search,
}


def build_registry(domain: str = "general") -> Dict[str, Callable[[str], ToolResult]]:
    """Return the tool registry for the given domain.
    Only 'general' is supported in this cut.
    """
    if domain != "general":
        raise ValueError(f"Unsupported domain '{domain}'. This build supports 'general' only.")
    return GENERAL_TOOLS


def list_tools(domain: str = "general") -> list[str]:
    return list(build_registry(domain).keys())
