"""Dashboard: Academic Health Overview."""

from typing import Any, Dict
from django.db.models import Avg

from api.models import StudentExam, Subject
from ..report_generator import ReportHandler, register_handler


@register_handler
class AcademicHealthHandler(ReportHandler):
    slug = "dashboard.academic_health"
    name = "Academic Health Overview"
    description = "A bird's-eye view of student performance averages across all subjects."
    page_type = "dashboard"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Average percentage across all graded exams
        overall_avg = StudentExam.objects.filter(status='graded').aggregate(avg=Avg('percentage'))['avg'] or 0
        
        # Performance by subject
        subjects = Subject.objects.all()
        subject_stats = []
        for s in subjects:
            avg = StudentExam.objects.filter(exam__subject=s, status='graded').aggregate(avg=Avg('percentage'))['avg']
            if avg is not None:
                subject_stats.append({
                    "name": s.name,
                    "value": round(float(avg), 1),
                })
        
        # Sort by performance
        subject_stats.sort(key=lambda x: x['value'], reverse=True)

        return {
            "overall_average_percentage": round(float(overall_avg), 1),
            "subject_performance": subject_stats,
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        return f"""Produce an "Academic Health Overview" report from the data below.

Overall average percentage (all subjects): {data['overall_average_percentage']}%

Performance by subject:
{data['subject_performance']}

Guidance:
- Open with a clear statement on whether the school's academic performance is meeting standards.
- Sections: Top performing subjects, Subjects needing improvement, Comparative analysis.
- Add a bar chart of performance by subject (name vs value).
- key_takeaways: pinpoint the bottom 2 subjects that need immediate curriculum review.

{extra_instruction}
"""
