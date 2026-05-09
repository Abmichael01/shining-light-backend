"""Question Bank: Coverage Gaps Analysis."""

from typing import Any, Dict
from django.db.models import Count

from api.models import Question, Subject
from ..report_generator import ReportHandler, register_handler


@register_handler
class QuestionBankCoverageHandler(ReportHandler):
    slug = "question-bank.coverage"
    name = "Coverage Gaps Analysis"
    description = "Find class/subject combinations with too few questions in the bank."
    page_type = "question-bank"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Question count per subject (with class context)
        subjects_with_counts = list(
            Subject.objects
            .annotate(question_count=Count('questions'))
            .values('id', 'name', 'class_model__name', 'question_count')
            .order_by('question_count')
        )

        verified_count = Question.objects.filter(is_verified=True).count()
        unverified_count = Question.objects.filter(is_verified=False).count()

        by_difficulty = list(
            Question.objects.values('difficulty').annotate(count=Count('id'))
        )

        # Surface the worst offenders explicitly so the AI prioritizes them
        thin_subjects = [s for s in subjects_with_counts if s['question_count'] < 10][:15]

        return {
            "subjects_total": len(subjects_with_counts),
            "verified_count": verified_count,
            "unverified_count": unverified_count,
            "by_difficulty": by_difficulty,
            "thin_subjects": thin_subjects,
            "subjects_full": subjects_with_counts[:30],
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        # ============================================================
        # TODO (HUMAN INPUT): Tune your "good coverage" thresholds
        # ============================================================
        # The current threshold is 10 questions = "thin".
        # You probably want different thresholds per subject type
        # (e.g. Mathematics needs 50+, Civic Education maybe 20+).
        # ============================================================
        return f"""Analyze the school's question bank coverage from the data below.

Overall:
- Total subjects: {data['subjects_total']}
- Verified questions: {data['verified_count']}
- Unverified (AI-drafted, awaiting teacher review): {data['unverified_count']}
- By difficulty: {data['by_difficulty']}

Thin subjects (fewer than 10 questions):
{data['thin_subjects']}

Top 30 subjects by question count:
{data['subjects_full']}

Guidance:
- Lead with the most actionable finding: which subjects need attention NOW.
- Sections: Overall health, Worst-covered subjects, Difficulty balance, Verification backlog.
- Add a bar chart of the top 10 thin subjects (subject name -> question count).
- Add a pie chart of question difficulty distribution if data['by_difficulty'] has 3+ entries.
- Key takeaways should be specific actions the question-bank manager can take this week.

{extra_instruction}
"""
