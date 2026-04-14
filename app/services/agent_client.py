# app/services/agent_client.py

import httpx
import json
from app.core.config import settings


async def start_agent(thread_id: str, initial_state: dict) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(
            f"{settings.AI_SERVICE_URL}/invoke",
            json={"thread_id": thread_id, "initial_state": initial_state},
        )


async def resume_agent(thread_id: str, status: str, feedback: str = "") -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(
            f"{settings.AI_SERVICE_URL}/resume",
            json={"thread_id": thread_id, "status": status, "feedback": feedback},
        )


# app/services/agent_client.py — replace get_agent_state

async def get_agent_state(thread_id: str) -> dict:
    """Read state via AI service which uses aget_state() for complete merged state."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(
                f"{settings.AI_SERVICE_URL}/state/{thread_id}",
            )
            if r.status_code == 200:
                return r.json()
            return {}
    except httpx.TimeoutException:
        print(f"[agent_client] timeout reading state for {thread_id} — AI service busy")
        return {}
    except httpx.ConnectError:
        print(f"[agent_client] AI service not reachable at {settings.AI_SERVICE_URL}")
        return {}
    except Exception as e:
        print(f"[agent_client] error reading state: {e}")
        return {}
    


async def extract_resource(file_path: str, resource_type: str) -> str:
    """Call AI service to extract text from a resource file."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{settings.AI_SERVICE_URL}/extract",
                json={"file_path": file_path, "resource_type": resource_type},
            )
            if r.status_code == 200:
                return r.json().get("text", "")
            return ""
    except Exception as e:
        print(f"[agent_client] extraction failed: {e}")
        return ""