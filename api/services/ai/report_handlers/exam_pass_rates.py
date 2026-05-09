"""Exams: Pass Rate Trends across completed exams."""

from typing import Any, Dict
from django.db.models import Avg, Count, Q

from api.models import Exam, StudentExam
from ..report_generator import ReportHandler, register_handler


@register_handler
class ExamPassRateTrendsHandler(ReportHandler):
    slug = "exams.pass_rate_trends"
    name = "Pass Rate Trends"
    description = "Pass and fail rate breakdown across recent completed exams and subjects."
    page_type = "exams"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        recent_exams = (
            Exam.objects.filter(status='completed')
            .order_by('-created_at')[:15]
        )

        exam_summaries = []
        for exam in recent_exams:
            attempts = StudentExam.objects.filter(exam=exam, status='graded')
            stats = attempts.aggregate(
                avg_score=Avg('percentage'),
                attempts_count=Count('id'),
                passed=Count('id', filter=Q(passed=True)),
            )
            count = stats['attempts_count'] or 0
            passed = stats['passed'] or 0
            if count == 0:
                continue
            exam_summaries.append({
                'exam_title': exam.title,
                'subject': exam.subject.name if exam.subject else 'Multi-subject',
                'attempts': count,
                'avg_percentage': round(float(stats['avg_score']) if stats['avg_score'] else 0, 1),
                'pass_rate_percent': round((passed / count * 100), 1),
                'fail_rate_percent': round(((count - passed) / count * 100), 1),
            })

        return {
            "total_exams_analyzed": len(exam_summaries),
            "exam_summaries": exam_summaries,
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        return f"""Produce a "Pass Rate Trends" report from the exam data below.

Exams analyzed: {data['total_exams_analyzed']}
Exam performance breakdown:
{data['exam_summaries']}

Guidance:
- Open with an overall health summary for exam pass rates.
- Sections: Top performing exams, Exams needing attention, Score distribution analysis.
- Bar chart of pass rates per exam (exam_title vs pass_rate_percent).
- key_takeaways: flag any exam with pass rate below 50% as urgent.

{extra_instruction}
"""
