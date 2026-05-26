# app/api/v1/endpoints/research.py

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_teacher ,get_current_active_user
from app.models.user import User
from app.core.config import settings

router = APIRouter()


# ── Request / Response models ────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    question: str


class ResearchInvokeRequest(BaseModel):
    question: str
    domain: str = "general"
    thread_id: str | None = None


class ResearchFinding(BaseModel):
    content: str = ""
    sources: list[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    question: str
    findings: dict[str, ResearchFinding] = Field(default_factory=dict)


class ResearchInvokeResponse(BaseModel):
    status: str
    thread_id: str
    poll_url: str | None = None


class ResearchStateResponse(BaseModel):
    status: str
    thread_id: str
    question: str | None = None
    answer: str = ""
    findings: dict[str, ResearchFinding] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _ai_base_url() -> str:
    return settings.AI_SERVICE_URL.rstrip("/")


def _normalize_findings(raw_findings: Any) -> dict[str, ResearchFinding]:
    """Convert the AI service findings into the backend response shape."""
    if not isinstance(raw_findings, dict):
        return {}

    normalized: dict[str, ResearchFinding] = {}

    for key, value in raw_findings.items():
        if not isinstance(value, dict):
            normalized[str(key)] = ResearchFinding(content=str(value))
            continue

        sources = value.get("sources") or []
        if not isinstance(sources, list):
            sources = [str(sources)]

        normalized[str(key)] = ResearchFinding(
            content=value.get("content", "") or "",
            sources=[str(src) for src in sources],
        )

    return normalized



def _extract_research_payload(data: dict[str, Any], fallback_question: str) -> ResearchResponse:
    """
    Supports both shapes:
    1) AI POST /research/run:
       {"status": "completed", "result": {"question": ..., "findings": {...}}}
    2) Older/direct AI shape:
       {"question": ..., "answer": ..., "findings": {...}}
    """
    result = data.get("result") if isinstance(data.get("result"), dict) else data

    question = result.get("question") or fallback_question
    findings = _normalize_findings(result.get("findings", {}))
    return ResearchResponse(
        question=question,
        findings=findings,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=ResearchResponse)
async def research(
    body: ResearchRequest,
    user: User = Depends(get_current_active_user),
):
    """
    Run the Research Agent and wait for the final result.
    Calls the AI service POST /research/run.
    """
    ai_url = f"{_ai_base_url()}/research/run"

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                ai_url,
                json={
                    "question": body.question,
                    "domain": "general",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error {resp.status_code}: {resp.text}",
        )

    return _extract_research_payload(resp.json(), body.question)


@router.post("/invoke", response_model=ResearchInvokeResponse)
async def invoke_research(
    body: ResearchInvokeRequest,
    teacher: User = Depends(get_current_teacher),
):
    """
    Start the Research Agent in the AI service without waiting.
    Frontend/backend can poll GET /research/state/{thread_id}.
    """
    thread_id = body.thread_id or f"research_{uuid4().hex}"
    ai_url = f"{_ai_base_url()}/research/invoke"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                ai_url,
                json={
                    "thread_id": thread_id,
                    "question": body.question,
                    "domain": body.domain,
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return ResearchInvokeResponse(
        status=data.get("status", "started"),
        thread_id=data.get("thread_id", thread_id),
        poll_url=f"/research/state/{data.get('thread_id', thread_id)}",
    )


@router.get("/state/{thread_id}", response_model=ResearchStateResponse)
async def get_research_state(
    thread_id: str,
    teacher: User = Depends(get_current_teacher),
):
    """
    Read async Research Agent status/result from the AI service.
    Calls AI GET /research/state/{thread_id}.
    """
    ai_url = f"{_ai_base_url()}/research/state/{thread_id}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(ai_url)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Research thread_id not found")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    result = data.get("result") if isinstance(data.get("result"), dict) else data

    question = result.get("question") or data.get("question")
    findings = _normalize_findings(result.get("findings", {}))

    return ResearchStateResponse(
        status=data.get("status", "unknown"),
        thread_id=data.get("thread_id", thread_id),
        question=question,
        findings=findings,
        raw=data,
    )
