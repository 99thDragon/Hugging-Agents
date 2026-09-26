"""Settings from .env, plus the model factory (OpenRouter via Strands' OpenAI provider)."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
load_dotenv(ROOT / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
GUARDIAN_MODEL = os.getenv("GUARDIAN_MODEL", "anthropic/claude-haiku-4.5")
COACH_MODEL = os.getenv("COACH_MODEL", "anthropic/claude-sonnet-5")
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "hug_guardian")


def make_model(model_id: str, max_tokens: int = 1500, temperature: float = 0.0):
    from strands.models.openai import OpenAIModel

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing from .env")
    return OpenAIModel(
        client_args={"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL},
        model_id=model_id,
        params={"max_tokens": max_tokens, "temperature": temperature},
    )
