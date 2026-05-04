from django.db.models.signals import post_save
from django.dispatch import receiver
from .models.academic import Grade
from .models.student import StudentSubject, TermReport
from django.db.models import Sum
from decimal import Decimal

@receiver(post_save, sender=Grade)
def update_reports_on_grade_change(sender, instance, **kwargs):
    """
    When a Grade configuration is updated, update all matching TermReports
     that have empty reports.
    """
    reports = TermReport.objects.filter(
        average_score__gte=instance.min_score,
        average_score__lte=instance.max_score
    )
    
    all_grades = Grade.objects.all()
    teacher_defaults = {g.teacher_remark for g in all_grades if g.teacher_remark}
    ict_defaults = {g.ict_remark for g in all_grades if g.ict_remark}
    principal_defaults = {g.principal_remark for g in all_grades if g.principal_remark}

    for report in reports:
        updated = False
        if not report.class_teacher_report or report.class_teacher_report in teacher_defaults:
            if instance.teacher_remark:
                report.class_teacher_report = instance.teacher_remark
                updated = True
        
        if not report.ict_report or report.ict_report in ict_defaults:
            if instance.ict_remark:
                report.ict_report = instance.ict_remark
                updated = True
                
        if not report.principal_report or report.principal_report in principal_defaults:
            if instance.principal_remark:
                report.principal_report = instance.principal_remark
                updated = True
        
        if updated:
            report.save()

@receiver(post_save, sender=StudentSubject)
def update_term_report_on_result_change(sender, instance, **kwargs):
    """
    When a student's result is saved, recalculate their TermReport summary
    and apply default remarks if empty.
    """
    student = instance.student
    session = instance.session
    term = instance.session_term
    
    # Get all subjects for this student in this term
    results = StudentSubject.objects.filter(
        student=student,
        session=session,
        session_term=term
    ).exclude(total_score__isnull=True)
    
    if not results.exists():
        return
        
    percentages = [
        percentage for percentage in
        (result.calculate_percentage() for result in results)
        if percentage is not None
    ]
    average_score = None
    if percentages:
        average_score = sum(percentages, Decimal('0')) / Decimal(len(percentages))

    # Calculate raw totals
    summary = results.aggregate(
        total_sum=Sum('total_score')
    )
    
    # Get or create TermReport
    report, created = TermReport.objects.get_or_create(
        student=student,
        session=session,
        session_term=term
    )
    
    report.average_score = average_score
    report.total_score = summary['total_sum']
    
    # Apply default remarks if they are currently empty or if they match a default remark
    if report.average_score is not None:
        matching_grade = Grade.get_grade_for_score(float(report.average_score))
        if matching_grade:
            # Get all existing default remarks to check if we can overwrite the current one
            all_grades = Grade.objects.all()
            teacher_defaults = {g.teacher_remark for g in all_grades if g.teacher_remark}
            ict_defaults = {g.ict_remark for g in all_grades if g.ict_remark}
            principal_defaults = {g.principal_remark for g in all_grades if g.principal_remark}

            # Update class teacher report
            if not report.class_teacher_report or report.class_teacher_report in teacher_defaults:
                if matching_grade.teacher_remark:
                    report.class_teacher_report = matching_grade.teacher_remark
            
            # Update ICT report
            if not report.ict_report or report.ict_report in ict_defaults:
                if matching_grade.ict_remark:
                    report.ict_report = matching_grade.ict_remark
            
            # Update principal report
            if not report.principal_report or report.principal_report in principal_defaults:
                if matching_grade.principal_remark:
                    report.principal_report = matching_grade.principal_remark
    
    report.save()


from django.contrib.auth.signals import user_logged_in
from django.conf import settings
from api.utils.email import send_login_notification_email

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """
    Send email notification when user logs in.
    """
    if getattr(settings, 'ENV', 'development') != 'development':
        send_login_notification_email(user, request)
