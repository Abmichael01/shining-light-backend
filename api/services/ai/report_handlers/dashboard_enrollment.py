"""Dashboard: Student Enrollment Trends."""

from typing import Any, Dict
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count

from api.models import Student, Session
from ..report_generator import ReportHandler, register_handler


@register_handler
class EnrollmentTrendsHandler(ReportHandler):
    slug = "dashboard.enrollment_trends"
    name = "Enrollment Trends"
    description = "Monthly new student enrollment trends across the last 6 months."
    page_type = "dashboard"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = timezone.now()
        months = []
        for i in range(5, -1, -1):
            start = (now - timedelta(days=30 * (i + 1))).replace(day=1)
            end = (now - timedelta(days=30 * i)).replace(day=1)
            count = Student.objects.filter(
                enrollment_date__gte=start,
                enrollment_date__lt=end,
                status='enrolled',
            ).count()
            months.append({
                "month": start.strftime("%b %Y"),
                "new_enrollments": count,
            })

        total_enrolled = Student.objects.filter(status='enrolled').count()
        total_withdrawn = Student.objects.filter(status='withdrawn').count()

        current_session = Session.objects.filter(is_current=True).first()

        return {
            "current_session": current_session.name if current_session else "No active session",
            "total_enrolled": total_enrolled,
            "total_withdrawn": total_withdrawn,
            "monthly_enrollment": months,
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        return f"""Produce an "Enrollment Trends" report from the data below.

Current session: {data['current_session']}
Total enrolled students: {data['total_enrolled']}
Total withdrawn: {data['total_withdrawn']}

Monthly new enrollments (last 6 months):
{data['monthly_enrollment']}

Guidance:
- Open with a brief summary of enrollment health.
- Sections: Growth trend analysis, Concern months (where enrollment dropped), Retention rate estimate.
- Add a line chart of monthly enrollments (month vs new_enrollments).
- key_takeaways: note any month with significant drops or spikes.

{extra_instruction}
"""
