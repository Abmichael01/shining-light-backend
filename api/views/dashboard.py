"""
Dashboard statistics views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSchoolAdmin
from api.models import Student, School, FeePayment, Class, Subject, Assignment, Staff
from django.db import models
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_dashboard_stats(request):
    """
    Dashboard stats for staff - scoped to:
    - Classes where the user is class_staff OR in Class.assigned_teachers
    - Subjects directly assigned to the staff via Subject.assigned_teachers

    Totals are computed over the UNION of:
    - Students in assigned classes
    - Students registered in assigned subjects
    """
    user = request.user

    # Resolve staff profile (may be None if user has no Staff profile)
    staff = Staff.objects.filter(user=user).first()

    # Classes assigned either directly (class_staff) or via M2M assigned_teachers
    assigned_classes = Class.objects.filter(
        models.Q(class_staff=user) | models.Q(assigned_teachers__user=user)
    ).distinct()

    # Subjects: all subjects in assigned classes OR directly assigned subjects
    assigned_subjects = Subject.objects.filter(
        models.Q(class_model__in=assigned_classes)
    )
    if staff is not None:
        assigned_subjects = assigned_subjects | Subject.objects.filter(assigned_teachers=staff)
    assigned_subjects = assigned_subjects.distinct()

    # Students in assigned classes
    students_in_classes = Student.objects.filter(
        class_model__in=assigned_classes,
    )

    # Students in assigned subjects (via registration)
    students_in_subjects = Student.objects.filter(
        subject_registrations__subject__in=assigned_subjects,
    )

    # Union of both sets
    visible_students = (students_in_classes | students_in_subjects).distinct()

    total_students = visible_students.count()

    # Subjects total across assigned scope
    total_subjects = assigned_subjects.count()

    today = datetime.now().date()
    new_assignments = Assignment.objects.filter(
        subject__in=assigned_subjects,
        status='published',
        due_date__isnull=False,
        due_date__lte=today
    ).count()

    # Gender breakdown from biodata over visible students
    total_female = visible_students.filter(biodata__gender='female').count()
    total_male = visible_students.filter(biodata__gender='male').count()

    return Response({
        'total_students': total_students,
        'total_subjects': total_subjects,
        'new_assignments_to_check': new_assignments,
        'classes_assigned': assigned_classes.count(),
        'total_female': total_female,
        'total_male': total_male,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_recent_assignments(request):
    """
    Recent assignments for staff (latest 5) scoped to:
    - Subjects in assigned classes
    - Subjects directly assigned to the staff
    """
    user = request.user
    staff = Staff.objects.filter(user=user).first()
    assigned_classes = Class.objects.filter(
        models.Q(class_staff=user) | models.Q(assigned_teachers__user=user)
    ).distinct()
    subjects_scope = Subject.objects.filter(class_model__in=assigned_classes)
    if staff is not None:
        subjects_scope = (subjects_scope | Subject.objects.filter(assigned_teachers=staff)).distinct()

    assignments = (
        Assignment.objects
        .filter(subject__in=subjects_scope)
        .select_related('subject')
        .order_by('-created_at')[:5]
    )

    from api.serializers.academic import AssignmentSerializer
    data = AssignmentSerializer(assignments, many=True).data
    return Response(data)

