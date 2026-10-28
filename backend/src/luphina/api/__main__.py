"""Start the development API server with `python -m luphina.api`."""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "luphina.api.app:app",
        host=os.getenv("LUPHINA_API_HOST", "127.0.0.1"),
        port=int(os.getenv("LUPHINA_API_PORT", "8000")),
        reload=True,
    )
