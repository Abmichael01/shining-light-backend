"""
AI Report Generator

Generates structured reports for any page in the admin portal.

Architecture:
    - Each "report template" has a handler class registered under a slug
    - Handler responsibilities:
        1. fetch_data()  — pull domain data from the DB
        2. build_prompt() — turn data into a prompt for the AI
    - The framework calls OpenAI with a strict JSON schema and returns a
      structured report (title, summary, sections, charts, takeaways).
    - Adding a new template = subclass + register. No new endpoints needed.
"""

import json
from typing import Any, Dict, List

from .openai_client import get_openai_client, get_default_model


# ---------------------------------------------------------------------------
# Structured output schema (strict JSON, OpenAI-enforced)
# ---------------------------------------------------------------------------
# Keeping this flat-and-simple: title + summary + sections + charts + takeaways.
# Charts are an array of typed Recharts-compatible specs that the frontend
# renders inline. Avoids the markdown-renderer dependency entirely.

REPORT_OUTPUT_SCHEMA = {
    "name": "ai_report",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "summary", "sections", "charts", "key_takeaways"],
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["heading", "content"],
                    "properties": {
                        "heading": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            },
            "charts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "chart_type", "data"],
                    "properties": {
                        "title": {"type": "string"},
                        "chart_type": {"type": "string", "enum": ["bar", "line", "pie"]},
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "value"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
            "key_takeaways": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Handler base + registry
# ---------------------------------------------------------------------------

class ReportHandler:
    """Base class for a report template handler."""

    slug: str = ""        # Must be set by subclass — unique key
    name: str = ""        # Display name
    description: str = "" # Short blurb shown on the template card
    page_type: str = ""   # e.g. "dashboard", "question-bank", "exams"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pull DB data needed for this report. Override in subclass."""
        raise NotImplementedError

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        """Turn data into a prompt. Override in subclass."""
        raise NotImplementedError


# Registry: slug -> handler instance
_REGISTRY: Dict[str, ReportHandler] = {}


def register_handler(handler_cls):
    """Decorator to register a handler class. Instantiates it on register."""
    instance = handler_cls()
    if not instance.slug:
        raise ValueError(f"Handler {handler_cls.__name__} missing 'slug' attribute")
    _REGISTRY[instance.slug] = instance
    return handler_cls


def get_handler(slug: str) -> ReportHandler:
    if slug not in _REGISTRY:
        raise ValueError(f"Unknown report template: {slug}")
    return _REGISTRY[slug]


def list_templates_for_page(page_type: str) -> List[Dict[str, Any]]:
    """Return all registered templates for a given page type."""
    return [
        {
            "slug": h.slug,
            "name": h.name,
            "description": h.description,
            "page_type": h.page_type,
        }
        for h in _REGISTRY.values()
        if h.page_type == page_type
    ]


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class ReportGeneratorService:
    """Service entry point for generating AI reports."""

    @staticmethod
    def generate(
        slug: str,
        payload: Dict[str, Any] | None = None,
        extra_instruction: str = "",
    ) -> Dict[str, Any]:
        """Run a registered template handler end-to-end.

        Returns a dict matching REPORT_OUTPUT_SCHEMA.
        """
        handler = get_handler(slug)
        data = handler.fetch_data(payload or {})
        prompt = handler.build_prompt(data, extra_instruction=extra_instruction)

        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_default_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an analytics assistant for a Nigerian secondary school. "
                        "You produce clear, accurate, action-oriented reports based ONLY on "
                        "the data provided. If data is missing or thin, say so plainly — never "
                        "invent numbers. Use Recharts-friendly chart specs only when the data "
                        "supports a meaningful visualisation."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_schema", "json_schema": REPORT_OUTPUT_SCHEMA},
            temperature=0.4,
        )

        raw = response.choices[0].message.content
        return json.loads(raw)


# ---------------------------------------------------------------------------
# Trigger handler registration. Imports below register all handlers
# via the @register_handler decorator at module load time.
# ---------------------------------------------------------------------------
from .report_handlers import dashboard_snapshot  # noqa: F401, E402
from .report_handlers import question_bank_coverage  # noqa: F401, E402
from .report_handlers import exam_performance  # noqa: F401, E402
from .report_handlers import dashboard_fees  # noqa: F401, E402
from .report_handlers import exam_pass_rates  # noqa: F401, E402
from .report_handlers import question_bank_stale  # noqa: F401, E402
from .report_handlers import dashboard_enrollment  # noqa: F401, E402
from .report_handlers import dashboard_staff  # noqa: F401, E402
from .report_handlers import dashboard_academic  # noqa: F401, E402
