"""Exams: Recent Exam Performance Summary."""

from typing import Any, Dict
from django.db.models import Avg, Count, Q

from api.models import Exam, StudentExam
from ..report_generator import ReportHandler, register_handler


@register_handler
class ExamPerformanceHandler(ReportHandler):
    slug = "exams.recent_performance"
    name = "Recent Exam Performance Summary"
    description = "Aggregate pass rates, averages and outliers across recent exams."
    page_type = "exams"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Limit to recent graded exams to keep the prompt small + focused
        recent_exams = (
            Exam.objects.filter(status='completed')
            .order_by('-created_at')[:10]
        )

        exam_summaries = []
        for exam in recent_exams:
            attempts = StudentExam.objects.filter(exam=exam, status='graded')
            stats = attempts.aggregate(
                avg_score=Avg('percentage'),
                attempts_count=Count('id'),
                passed=Count('id', filter=Q(passed=True)),
            )
            attempts_count = stats['attempts_count'] or 0
            passed = stats['passed'] or 0
            exam_summaries.append({
                'exam_title': exam.title,
                'subject': exam.subject.name if exam.subject else 'Multi-subject',
                'attempts': attempts_count,
                'avg_percentage': float(stats['avg_score']) if stats['avg_score'] else 0,
                'pass_rate_percent': (passed / attempts_count * 100) if attempts_count else 0,
            })

        return {
            "exams_examined": len(exam_summaries),
            "exam_summaries": exam_summaries,
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        # ============================================================
        # TODO (HUMAN INPUT): Tune what counts as "concerning"
        # ============================================================
        # Pass rate < 60% might be a red flag in this school. Adjust below.
        # Different subjects may have different acceptable averages.
        # ============================================================
        return f"""Summarise recent exam performance from the data below.

Exams examined: {data['exams_examined']} (most recent completed)
Exam summaries:
{data['exam_summaries']}

Guidance:
- Open with the headline: are students performing well, or are there concerns?
- Sections: Overall summary, Subjects performing well, Subjects needing intervention, Notable patterns.
- Bar chart of pass rates per exam (exam title -> pass_rate_percent).
- Flag any exam with pass rate below 60% or average below 50% in key takeaways.
- If only one exam is available, say so and suggest broader analysis once more data exists.

{extra_instruction}
"""
