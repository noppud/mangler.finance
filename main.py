from __future__ import annotations

import os

import uvicorn

from python_backend.api import app


if __name__ == "__main__":
  port = int(os.getenv("PORT", "8000"))
  uvicorn.run("main:app", host="0.0.0.0", port=port)

