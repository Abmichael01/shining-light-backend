"""
Dashboard statistics views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSchoolAdmin
from api.models import Student, School, FeePayment
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from decimal import Decimal


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def admin_dashboard_stats(request):
    """
    Get dashboard statistics for admin overview
    Returns counts for applications, students, schools, etc.
    """
    
    stats = {
        'total_applications': Student.objects.filter(source='online_application').count(),
        'pending_applications': Student.objects.filter(
            status__in=['applicant', 'under_review']
        ).count(),
        'accepted_students': Student.objects.filter(status='accepted').count(),
        'rejected_applications': Student.objects.filter(status='rejected').count(),
        'total_students': Student.objects.filter(status='enrolled').count(),
        'active_schools': School.objects.filter(is_active=True).count(),
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def student_growth_chart(request):
    """
    Get student enrollment growth data for the past 12 months
    Returns monthly enrollment counts
    """
    # Get current date
    now = datetime.now()
    twelve_months_ago = now - timedelta(days=365)
    
    # Query student enrollments by month
    monthly_enrollments = (
        Student.objects
        .filter(
            enrollment_date__gte=twelve_months_ago,
            status='enrolled'
        )
        .annotate(month=TruncMonth('enrollment_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    
    # Format data for charts
    chart_data = []
    for entry in monthly_enrollments:
        month_name = entry['month'].strftime('%b')  # Jan, Feb, etc.
        chart_data.append({
            'month': month_name,
            'students': entry['count']
        })
    
    # Fill in missing months with 0
    if len(chart_data) < 12:
        # Create all months
        all_months = []
        for i in range(12):
            month_date = now - timedelta(days=30 * (11 - i))
            all_months.append(month_date.strftime('%b'))
        
        # Fill data
        result = []
        for month in all_months:
            existing = next((d for d in chart_data if d['month'] == month), None)
            result.append({
                'month': month,
                'students': existing['students'] if existing else 0
            })
        chart_data = result
    
    return Response(chart_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def payment_growth_chart(request):
    """
    Get payment/revenue growth data for the past 12 months
    Returns monthly payment totals
    """
    # Get current date
    now = datetime.now()
    twelve_months_ago = now - timedelta(days=365)
    
    # Query fee payments by month
    # Note: FeePayment records represent completed payments, so no status filter needed
    monthly_payments = (
        FeePayment.objects
        .filter(
            payment_date__gte=twelve_months_ago
        )
        .annotate(month=TruncMonth('payment_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    
    # Format data for charts
    chart_data = []
    for entry in monthly_payments:
        month_name = entry['month'].strftime('%b')  # Jan, Feb, etc.
        chart_data.append({
            'month': month_name,
            'amount': float(entry['total']) if entry['total'] else 0
        })
    
    # Fill in missing months with 0
    if len(chart_data) < 12:
        # Create all months
        all_months = []
        for i in range(12):
            month_date = now - timedelta(days=30 * (11 - i))
            all_months.append(month_date.strftime('%b'))
        
        # Fill data
        result = []
        for month in all_months:
            existing = next((d for d in chart_data if d['month'] == month), None)
            result.append({
                'month': month,
                'amount': existing['amount'] if existing else 0
            })
        chart_data = result
    
    return Response(chart_data)

