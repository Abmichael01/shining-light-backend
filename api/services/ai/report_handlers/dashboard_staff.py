"""Dashboard: Staff Overview."""

from typing import Any, Dict
from django.db.models import Count

from api.models import Staff
from ..report_generator import ReportHandler, register_handler


@register_handler
class StaffOverviewHandler(ReportHandler):
    slug = "dashboard.staff_overview"
    name = "Staff Overview"
    description = "Breakdown of teaching and non-teaching staff across departments."
    page_type = "dashboard"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        total = Staff.objects.count()

        by_role = list(
            Staff.objects.values('role')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        by_school = list(
            Staff.objects.values('school__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return {
            "total_staff": total,
            "by_role": by_role,
            "by_school": by_school,
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        return f"""Produce a "Staff Overview" report from the data below.

Total staff: {data['total_staff']}
Staff by role: {data['by_role']}
Staff by school: {data['by_school']}

Guidance:
- Open with a brief summary of staffing levels.
- Sections: Role distribution, School distribution, Staffing recommendations.
- Add a pie chart of staff by role (role vs count).
- key_takeaways: flag any school that appears understaffed relative to others.

{extra_instruction}
"""
