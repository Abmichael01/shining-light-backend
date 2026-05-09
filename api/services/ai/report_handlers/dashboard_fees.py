"""Dashboard: Fee Collection Insights."""

from typing import Any, Dict
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Q

from api.models import Student, FeePayment, Session
from ..report_generator import ReportHandler, register_handler


@register_handler
class FeeCollectionHandler(ReportHandler):
    slug = "dashboard.fees"
    name = "Fee Collection Insights"
    description = "Payment trends, outstanding balances, and collection patterns over the last 90 days."
    page_type = "dashboard"

    def fetch_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = timezone.now()
        ninety_days_ago = now - timedelta(days=90)
        thirty_days_ago = now - timedelta(days=30)

        current_session = Session.objects.filter(is_current=True).first()

        total_collected_90d = FeePayment.objects.filter(
            payment_date__gte=ninety_days_ago
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_collected_30d = FeePayment.objects.filter(
            payment_date__gte=thirty_days_ago
        ).aggregate(total=Sum('amount'))['total'] or 0

        payment_count_90d = FeePayment.objects.filter(
            payment_date__gte=ninety_days_ago
        ).count()

        enrolled_students = Student.objects.filter(status='enrolled').count()

        return {
            "current_session": current_session.name if current_session else "No active session",
            "enrolled_students": enrolled_students,
            "fee_stats": {
                "total_collected_last_90_days_naira": float(total_collected_90d),
                "total_collected_last_30_days_naira": float(total_collected_30d),
                "total_payments_last_90_days": payment_count_90d,
            },
        }

    def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
        return f"""Produce a "Fee Collection Insights" report from the data below.

Current session: {data['current_session']}
Enrolled students: {data['enrolled_students']}
Fee stats: {data['fee_stats']}

Guidance:
- Open with a one-paragraph summary of collection health.
- Sections: 30-day vs 90-day collection comparison, Collection rate per student, Trends.
- key_takeaways: flag if recent 30-day collection is significantly lower than the 90-day average.
- Format Naira amounts as ₦X,XXX.

{extra_instruction}
"""
