from __future__ import annotations

import os

import uvicorn


def _is_streamlit_runtime() -> bool:
    return any(
        key in os.environ
        for key in (
            "STREAMLIT_SERVER_PORT",
            "STREAMLIT_RUNTIME",
        )
    )


def _is_reload_enabled() -> bool:
    """Enable reload only when explicitly requested and not in hosted Streamlit."""
    if _is_streamlit_runtime():
        return False
    return os.getenv("RECONNECT_RELOAD", "0") == "1"


def run() -> None:
    # Safer default: bind to localhost so case data isn't exposed on your LAN.
    # To intentionally expose on your network, set HOST=0.0.0.0
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=_is_reload_enabled(),
    )


if __name__ == "__main__":
    run()
