"""
OpenAI client singleton.

Reads OPENAI_API_KEY from settings, raises a clear error if missing so AI
features fail loudly at request time instead of silently returning bad data.
"""

from functools import lru_cache
from django.conf import settings


@lru_cache(maxsize=1)
def get_openai_client():
    """Return a cached OpenAI client. Raises RuntimeError if key not set."""
    from openai import OpenAI

    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Set it in your .env file to use AI features."
        )

    return OpenAI(api_key=api_key)


def get_default_model() -> str:
    """The default OpenAI model used by AI features."""
    return getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
