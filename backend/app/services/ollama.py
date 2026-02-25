from __future__ import annotations

import os
from typing import Any, Dict

import httpx


def ollama_enabled() -> bool:
    return os.getenv("RECONNECT_OLLAMA", "0").strip().lower() in {"1", "true", "yes", "on"}


def ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434")


def model_name() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.1")


def summarize_case(case_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort summary using local Ollama.
    If Ollama isn't reachable, return a safe fallback.
    """
    if not ollama_enabled():
        return {
            "summary": "AI summary is disabled. Set RECONNECT_OLLAMA=1 and restart to enable local Ollama summaries.",
            "model": model_name(),
            "used_ollama": False,
        }

    url = f"{ollama_url().rstrip('/')}/api/generate"
    model = model_name()

    prompt = (
        "You are assisting a missing-person / genealogy case manager.\n"
        "Rules:\n"
        "- Summarize ONLY what is present in the provided JSON.\n"
        "- Do NOT invent facts.\n"
        "- Do NOT output private addresses, phone numbers, or full government IDs.\n"
        "- If something is uncertain, say it is uncertain.\n\n"
        "Output format:\n"
        "TIMELINE (5 bullets)\n"
        "NEXT ACTIONS (3-5 bullets)\n"
        "SYNOPSIS (1 short paragraph)\n\n"
        "CASE JSON:\n"
        f"{case_payload}\n"
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json={"model": model, "prompt": prompt, "stream": False})
            r.raise_for_status()
            data = r.json()
        return {
            "summary": (data.get("response") or "").strip(),
            "model": model,
            "used_ollama": True,
        }
    except Exception as e:
        return {
            "summary": "Ollama is not available. Add evidence and try again.",
            "error": str(e),
            "model": model,
            "used_ollama": False,
        }
