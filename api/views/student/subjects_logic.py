from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, models
from django.utils import timezone
from api.models import (
    Student, StudentSubject, SessionTerm, TermReport, 
    Subject as SubjectModelAlias
)
from api.serializers import StudentSubjectSerializer
from api.permissions import IsAdminOrStaff, IsSchoolAdmin

class SubjectLogicMixin:
    @action(detail=True, methods=['post'], url_path='open-day-clear', permission_classes=[IsAdminOrStaff])
    def open_day_clear(self, request, pk=None):
        student_subject = self.get_object()
        user = request.user
        is_admin_like = getattr(user, 'is_superuser', False) or getattr(user, 'user_type', '') == 'admin'
        if not is_admin_like:
            staff_profile = getattr(user, 'staff_profile', None)
            if staff_profile is None: return Response({'detail': 'Only staff members permitted.'}, status=status.HTTP_403_FORBIDDEN)
            subject = student_subject.subject
            assigned_to_subject = subject.assigned_teachers.filter(pk=staff_profile.pk).exists()
            assigned_class_match = bool(staff_profile.assigned_class_id) and (staff_profile.assigned_class_id == subject.class_model_id)
            in_class_assigned_teachers = subject.class_model.assigned_teachers.filter(pk=staff_profile.pk).exists()
            if not (assigned_to_subject or assigned_class_match or in_class_assigned_teachers):
                return Response({'detail': 'Not permitted to clear this subject.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}
        cleared = str(data.get('cleared', True)).lower() not in ['false', '0', 'no', 'none']
        if cleared:
            student_subject.openday_cleared = True
            student_subject.openday_cleared_by = request.user
            student_subject.openday_cleared_at = timezone.now()
            student_subject.openday_clearance_notes = data.get('notes', '')
            student_subject.openday_clearance_checklist = data.get('checklist', {})
        else:
            student_subject.openday_cleared = False
            student_subject.openday_cleared_by = None
            student_subject.openday_cleared_at = None
            student_subject.openday_clearance_notes = ''
            student_subject.openday_clearance_checklist = {}
        student_subject.save()
        return Response(StudentSubjectSerializer(student_subject).data)

    @action(detail=False, methods=['post'], url_path='upload-results-csv', permission_classes=[IsAdminOrStaff])
    def upload_results_csv(self, request):
        import csv
        import io
        from decimal import Decimal
        
        subject_id = request.data.get('subject')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        file_obj = request.FILES.get('file')
        
        if not all([subject_id, session_id, session_term_id, file_obj]):
            return Response({'error': 'Missing required fields or file'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            decoded_file = file_obj.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            updated_count = 0
            errors = []
            
            with transaction.atomic():
                for row in reader:
                    admission_number = row.get('Admission Number') or row.get('admission_number')
                    exam_score = row.get('Exam Score') or row.get('exam_score') or row.get('Score') or row.get('score')
                    remark = row.get('Remark') or row.get('remark')
                    
                    if not admission_number:
                        continue
                        
                    try:
                        # Find the student subject registration
                        registration = StudentSubject.objects.filter(
                            student__admission_number=admission_number,
                            subject_id=subject_id,
                            session_id=session_id,
                            session_term_id=session_term_id
                        ).first()
                        
                        if registration:
                            if exam_score is not None and str(exam_score).strip():
                                registration.exam_score = Decimal(str(exam_score).strip())
                            if remark is not None:
                                registration.teacher_comment = remark
                            registration.save()
                            updated_count += 1
                        else:
                            errors.append(f"No registration found for student {admission_number}")
                    except Exception as e:
                        errors.append(f"Error updating {admission_number}: {str(e)}")
            
            return Response({
                'message': f'Successfully updated {updated_count} results',
                'updated_count': updated_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response({'error': f'Failed to process CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsSchoolAdmin])
    def calculate_rankings(self, request):
        session_id, session_term_id = request.data.get('session'), request.data.get('session_term')
        if not (session_id and session_term_id): return Response({'error': 'Required fields missing'}, status=status.HTTP_400_BAD_REQUEST)
            
        with transaction.atomic():
            subjects = SubjectModelAlias.objects.filter(student_registrations__session_id=session_id, student_registrations__session_term_id=session_term_id).distinct()
            for subject in subjects:
                regs = StudentSubject.objects.filter(subject=subject, session_id=session_id, session_term_id=session_term_id, total_score__isnull=False).order_by('-total_score')
                if regs.count() < Student.objects.filter(class_model=subject.class_model, status='active').count():
                    regs.update(position=None, highest_score=None, lowest_score=None, subject_average=None)
                else:
                    stats = regs.aggregate(max_score=models.Max('total_score'), min_score=models.Min('total_score'), avg_score=models.Avg('total_score'))
                    current_pos, last_score = 1, None
                    for i, reg in enumerate(regs):
                        if last_score is not None and reg.total_score < last_score: current_pos = i + 1
                        reg.position, reg.highest_score, reg.lowest_score, reg.subject_average = current_pos, stats['max_score'], stats['min_score'], stats['avg_score']
                        reg.save(); last_score = reg.total_score

            student_ids = list(StudentSubject.objects.filter(session_id=session_id, session_term_id=session_term_id, total_score__isnull=False).values_list('student_id', flat=True).distinct())
            for st_id in student_ids:
                regs = StudentSubject.objects.filter(student_id=st_id, session_id=session_id, session_term_id=session_term_id, total_score__isnull=False)
                avg = regs.aggregate(models.Avg('total_score'))['total_score__avg']
                if avg is not None:
                    report, _ = TermReport.objects.get_or_create(student_id=st_id, session_id=session_id, session_term_id=session_term_id)
                    report.average_score, report.total_score = avg, regs.aggregate(models.Sum('total_score'))['total_score__sum']
                    curr_term = SessionTerm.objects.get(id=session_term_id)
                    prev_reports = TermReport.objects.filter(student_id=st_id, session_id=session_id).exclude(id=report.id)
                    
                    if prev_reports.exists():
                        all_avgs = [r.average_score for r in prev_reports if r.average_score] + [avg]
                        report.cumulative_average = sum(all_avgs) / len(all_avgs)
                    else:
                        report.cumulative_average = avg
                    from api.models import Grade
                    grade_obj = Grade.get_grade_for_score(float(avg))
                    if grade_obj:
                        if not report.class_teacher_report: report.class_teacher_report = grade_obj.teacher_remark
                        if not report.principal_report: report.principal_report = grade_obj.principal_remark
                    report.save()

            all_reports = TermReport.objects.filter(session_id=session_id, session_term_id=session_term_id, average_score__isnull=False).select_related('student__class_model')
            from collections import defaultdict
            by_arm, by_set = defaultdict(list), defaultdict(list)
            for r in all_reports: by_arm[r.student.class_model_id].append(r); g_level = r.student.class_model.grade_level; 
            if g_level: by_set[g_level].append(r)
            for arm_code, arm_reps in by_arm.items():
                total = Student.objects.filter(class_model_id=arm_code, status='active').count()
                if len(arm_reps) < total: TermReport.objects.filter(pk__in=[r.id for r in arm_reps]).update(class_position=None, total_students=None)
                else:
                    arm_reps.sort(key=lambda x: x.average_score, reverse=True)
                    pos, last = 1, None
                    for i, r in enumerate(arm_reps):
                        if last is not None and r.average_score < last: pos = i + 1
                        TermReport.objects.filter(pk=r.id).update(class_position=pos, total_students=total); last = r.average_score
        return Response({'message': 'Rankings success'})
