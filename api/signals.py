from django.db.models.signals import post_save
from django.dispatch import receiver
from .models.academic import Grade
from .models.student import StudentSubject, TermReport
from django.db.models import Avg, Sum

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
    
    for report in reports:
        updated = False
        if not report.class_teacher_report and instance.teacher_remark:
            report.class_teacher_report = instance.teacher_remark
            updated = True
        if not report.ict_report and instance.ict_remark:
            report.ict_report = instance.ict_remark
            updated = True
        if not report.principal_report and instance.principal_remark:
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
        
    # Calculate totals
    summary = results.aggregate(
        avg_score=Avg('total_score'),
        total_sum=Sum('total_score')
    )
    
    # Get or create TermReport
    report, created = TermReport.objects.get_or_create(
        student=student,
        session=session,
        session_term=term
    )
    
    report.average_score = summary['avg_score']
    report.total_score = summary['total_sum']
    
    # Apply default remarks if they are currently empty
    if report.average_score is not None:
        matching_grade = Grade.get_grade_for_score(float(report.average_score))
        if matching_grade:
            if not report.class_teacher_report and matching_grade.teacher_remark:
                report.class_teacher_report = matching_grade.teacher_remark
            if not report.ict_report and matching_grade.ict_remark:
                report.ict_report = matching_grade.ict_remark
            if not report.principal_report and matching_grade.principal_remark:
                report.principal_report = matching_grade.principal_remark
    
    report.save()
