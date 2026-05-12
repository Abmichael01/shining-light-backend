"""Question Bank: Stale Subjects (no new questions in 60+ days)."""

from typing import Any, Dict
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Max

from api.models import Question, Subject
from ..report_generator import ReportHandler, register_handler


@register_handler
class QuestionBankStaleHandler(ReportHandler):
    slug = "question-bank.stale_subjects"
    name = "Stale Subjects Report"
    description = "Subjects with no new questions added in over 60 days, indicating gaps in question bank maintenance."
    page_type = "question-bank"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sixty_days_ago = timezone.now() - timedelta(days=60)

        subjects = Subject.objects.annotate(
            question_count=Count('questions'),
            last_question=Max('questions__created_at'),
        )

        stale = []
        active = []
        for s in subjects:
            entry = {
                "subject": s.name,
                "question_count": s.question_count,
                "last_added": str(s.last_question.date()) if s.last_question else "Never",
            }
            if not s.last_question or s.last_question < sixty_days_ago:
                stale.append(entry)
            else:
                active.append(entry)

        return {
            "stale_subjects": stale,
            "active_subjects_count": len(active),
            "stale_count": len(stale),
            "total_subjects": len(stale) + len(active),
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        return f"""Produce a "Stale Subjects Report" from the question bank data below.

Total subjects: {data['total_subjects']}
Stale subjects (60+ days no new questions): {data['stale_count']}
Active subjects: {data['active_subjects_count']}

Stale subjects list:
{data['stale_subjects']}

Guidance:
- Open with an overview of question bank freshness.
- Sections: Stale subjects requiring attention, Subjects with zero questions.
- key_takeaways: list the top 3 most urgent subjects teachers should update.

{extra_instruction}
"""
