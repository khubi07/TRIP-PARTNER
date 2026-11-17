from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


class MissingGeminiKeyError(RuntimeError):
    """Raised when a Gemini request is made without its environment key."""


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGoogleGenerativeAI:
    """Create one lazy Gemini client; secrets are loaded but never logged."""
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=project_root / ".env", override=False)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise MissingGeminiKeyError(
            "Gemini is not configured. Set GOOGLE_API_KEY in the project environment."
        )

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        google_api_key=api_key,
        request_timeout=30,
        retries=0,
    )
