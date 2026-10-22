"""Start the development API server with `python -m autoflow.api`."""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "autoflow.api.app:app",
        host=os.getenv("AUTOFLOW_API_HOST", "127.0.0.1"),
        port=int(os.getenv("AUTOFLOW_API_PORT", "8000")),
        reload=True,
    )
