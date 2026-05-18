"""
LLM client — wraps the Groq API (default) or any OpenAI-compatible endpoint.
Role aliases decouple the pipeline from specific model names.
Switch provider by changing MODEL_FLASH in .env.
"""
from __future__ import annotations
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional

# ── Load .env from Research_Agent folder (works regardless of CWD) ───────────
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass  # rely on shell environment if dotenv not installed

logger = logging.getLogger(__name__)

# ── Role alias → model mapping ────────────────────────────────────────────────
DEFAULT_MODEL = os.getenv("MODEL_FLASH", "llama-3.3-70b-versatile")

ROLE_ALIASES: Dict[str, str] = {
    "reasoner":    DEFAULT_MODEL,
    "tool-caller": DEFAULT_MODEL,
    "summarizer":  DEFAULT_MODEL,
    "flash":       DEFAULT_MODEL,
}


def call_llm(
    messages: List[Dict[str, str]],
    role: str = "flash",
    system: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    retries: int = 3,
) -> str:
    """
    Call the LLM with a role alias.
    Retries up to `retries` times on rate-limit (429) errors.
    """
    model = ROLE_ALIASES.get(role, DEFAULT_MODEL)

    if system:
        full_messages = [{"role": "system", "content": system}] + messages
    else:
        full_messages = messages

    for attempt in range(1, retries + 1):
        try:
            return _call_groq(model, full_messages, temperature, max_tokens)
        except Exception as exc:
            err = str(exc)
            if "429" in err and attempt < retries:
                wait = 2 ** attempt
                logger.warning(f"Rate limited (attempt {attempt}), retrying in {wait}s…")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("LLM call failed after all retries")


def _call_groq(model: str, messages: List[Dict], temperature: float, max_tokens: int) -> str:
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found.\n"
            "  Make sure Research_Agent\\.env exists and contains:\n"
            "  GROQ_API_KEY=gsk_...\n"
            "  Then re-run from any directory."
        )
    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content
