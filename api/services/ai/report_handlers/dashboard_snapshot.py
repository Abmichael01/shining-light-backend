"""Dashboard: School Health Snapshot."""

from typing import Any, Dict
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum

from api.models import Student, Staff, FeePayment, Session
from ..report_generator import ReportHandler, register_handler


@register_handler
class DashboardSnapshotHandler(ReportHandler):
    slug = "dashboard.snapshot"
    name = "School Health Snapshot"
    description = "A high-level pulse check across enrolment, fees and staffing."
    page_type = "dashboard"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        current_session = Session.objects.filter(is_current=True).first()

        enrolled = Student.objects.filter(status='enrolled').count()
        pending_apps = Student.objects.filter(status__in=['applicant', 'under_review']).count()
        accepted = Student.objects.filter(status='accepted').count()

        new_students_30d = Student.objects.filter(
            status='enrolled',
            enrollment_date__gte=thirty_days_ago,
        ).count()

        staff_total = Staff.objects.count()

        fees_30d = FeePayment.objects.filter(
            payment_date__gte=thirty_days_ago,
        ).aggregate(total=Sum('amount'))['total'] or 0

        students_by_school = list(
            Student.objects.filter(status='enrolled')
            .values('school__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return {
            "current_session": current_session.name if current_session else "No active session",
            "totals": {
                "enrolled_students": enrolled,
                "pending_applications": pending_apps,
                "accepted_students": accepted,
                "total_staff": staff_total,
                "new_students_last_30_days": new_students_30d,
                "fee_revenue_last_30_days_naira": float(fees_30d),
            },
            "students_by_school": students_by_school,
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        # ============================================================
        # TODO (HUMAN INPUT): Tune this prompt for your school's voice
        # ============================================================
        # Things to customize:
        #   - What does "healthy" mean for your school size? (e.g. 5%
        #     month-on-month growth might be exceptional or routine)
        #   - Which numbers are the principal looking at most?
        #   - Naira formatting preferences (₦ vs NGN, lakhs vs full)
        # ============================================================
        return f"""Produce a "School Health Snapshot" report from the data below.

Current session: {data['current_session']}
Totals:
{data['totals']}

Student distribution by school:
{data['students_by_school']}

Guidance:
- Open with a one-paragraph summary the school proprietor can read in 10 seconds.
- Sections: Enrolment health, Application pipeline, Staffing, Fee collection.
- Add a bar chart of students by school IF there are 2+ schools with students.
- Add a callout in key_takeaways for anything that needs attention this week.
- Format Naira amounts as ₦X,XXX.

{extra_instruction}
"""
