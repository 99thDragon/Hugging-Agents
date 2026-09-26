"""Vercel entrypoint. Locally, run uvicorn hug_guardian.api:app instead."""

from hug_guardian.api import app  # noqa: F401
