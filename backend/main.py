import os
import uvicorn

if __name__ == "__main__":
    # Safer default: bind to localhost so case data isn't exposed on your LAN.
    # To intentionally expose on your network, set HOST=0.0.0.0
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
