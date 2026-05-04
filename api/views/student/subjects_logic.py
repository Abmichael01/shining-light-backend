from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
from api.models import (
    ResultScoreSubmission, Student, StudentSubject, SessionTerm, TermReport, SystemSetting,
    Subject as SubjectModelAlias
)
from api.serializers import StudentSubjectSerializer
from api.permissions import IsAdminOrStaff, IsSchoolAdmin

class SubjectLogicMixin:
    def _is_admin_like(self, user):
        return getattr(user, 'is_superuser', False) or getattr(user, 'user_type', '') == 'admin'

    def _can_enter_subject_scores(self, user, subject):
        if self._is_admin_like(user):
            return True

        staff_profile = getattr(user, 'staff_profile', None)
        if staff_profile is None:
            return False

        assigned_to_subject = subject.assigned_teachers.filter(pk=staff_profile.pk).exists()
        assigned_class_match = bool(staff_profile.assigned_class_id) and staff_profile.assigned_class_id == subject.class_model_id
        in_class_assigned_teachers = subject.class_model.assigned_teachers.filter(pk=staff_profile.pk).exists()
        return assigned_to_subject or assigned_class_match or in_class_assigned_teachers

    def _json_ready_scores(self, payload):
        return {
            key: (None if value is None else str(value))
            for key, value in payload.items()
        }

    def _validate_score_payload(self, registration, payload, allow_ca_score_editing):
        serializer = StudentSubjectSerializer(
            registration,
            data=payload,
            partial=True,
            context={
                **self.get_serializer_context(),
                'allow_ca_score_editing': allow_ca_score_editing,
            },
        )
        serializer.is_valid(raise_exception=False)
        return serializer

    def _queue_score_submission(self, registration, payload, user):
        submission = ResultScoreSubmission.objects.filter(
            student_subject=registration,
            status='pending',
        ).first()
        defaults = {
            'proposed_scores': self._json_ready_scores(payload),
            'submitted_by': user,
            'rejection_reason': '',
        }
        if submission:
            for field, value in defaults.items():
                setattr(submission, field, value)
            submission.save()
            return submission
        return ResultScoreSubmission.objects.create(
            student_subject=registration,
            **defaults,
        )

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
        import re
        
        subject_id = request.data.get('subject')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        file_obj = request.FILES.get('file')
        
        if not all([subject_id, session_id, session_term_id, file_obj]):
            return Response({'error': 'Missing required fields or file'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            decoded_file = file_obj.read().decode('utf-8-sig')
            lines = decoded_file.splitlines()
            header_index = next(
                (
                    index for index, line in enumerate(lines)
                    if 'admission number' in line.lower() or 'admission_number' in line.lower()
                ),
                0
            )
            io_string = io.StringIO('\n'.join(lines[header_index:]))
            reader = csv.DictReader(io_string)
            
            updated_count = 0
            errors = []
            settings_obj = SystemSetting.load()
            allow_ca_score_editing = settings_obj.allow_ca_score_editing
            require_approval = settings_obj.require_result_entry_approval and not self._is_admin_like(request.user)

            def normalize(value):
                return re.sub(r'[^a-z0-9]+', '_', str(value or '').strip().lower()).strip('_')

            def row_value(row, *aliases):
                normalized_row = {
                    normalize(key): value
                    for key, value in row.items()
                    if key is not None
                }
                for alias in aliases:
                    alias_key = normalize(alias)
                    for key, value in normalized_row.items():
                        if key == alias_key or key.startswith(f'{alias_key}_'):
                            return value
                return None

            def has_value(value):
                return value is not None and str(value).strip() != ''
            
            with transaction.atomic():
                for row in reader:
                    admission_number = row_value(row, 'Admission Number', 'admission_number')
                    ca_score = row_value(row, 'CA Score', 'ca_score')
                    objective_score = row_value(row, 'Objective Score', 'Obj Score', 'objective_score', 'obj_score')
                    theory_score = row_value(row, 'Theory Score', 'Theory', 'theory_score')
                    exam_score = row_value(row, 'Exam Score', 'exam_score', 'Score', 'score')
                    remark = row_value(row, 'Remark', 'Teacher Comment', 'remark', 'teacher_comment')
                    
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
                            if not self._can_enter_subject_scores(request.user, registration.subject):
                                errors.append(f"Not permitted to update {admission_number}")
                                continue

                            payload = {}
                            if has_value(ca_score):
                                payload['ca_score'] = str(ca_score).strip()
                            if has_value(objective_score):
                                payload['objective_score'] = str(objective_score).strip()
                            if has_value(theory_score):
                                payload['theory_score'] = str(theory_score).strip()
                            if (
                                has_value(exam_score)
                                and not has_value(objective_score)
                                and not has_value(theory_score)
                            ):
                                payload['exam_score'] = str(exam_score).strip()
                            if remark is not None:
                                payload['teacher_comment'] = remark

                            serializer = StudentSubjectSerializer(
                                registration,
                                data=payload,
                                partial=True,
                                context={
                                    **self.get_serializer_context(),
                                    'allow_ca_score_editing': allow_ca_score_editing,
                                },
                            )
                            if serializer.is_valid():
                                if require_approval:
                                    self._queue_score_submission(registration, payload, request.user)
                                else:
                                    serializer.save(
                                        result_entered_by=request.user,
                                        result_entered_at=timezone.now(),
                                    )
                            else:
                                errors.append(f"Error updating {admission_number}: {serializer.errors}")
                                continue
                            updated_count += 1
                        else:
                            errors.append(f"No registration found for student {admission_number}")
                    except Exception as e:
                        errors.append(f"Error updating {admission_number}: {str(e)}")
            
            return Response({
                'message': (
                    f'Successfully submitted {updated_count} results for approval'
                    if require_approval
                    else f'Successfully updated {updated_count} results'
                ),
                'updated_count': updated_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response({'error': f'Failed to process CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrStaff])
    def bulk_update_scores(self, request):
        subject_id = request.data.get('subject')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        updates = request.data.get('updates')

        if not all([subject_id, session_id, session_term_id]) or not isinstance(updates, list):
            return Response(
                {'error': 'subject, session, session_term, and updates list are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_ids = []
        for update in updates:
            if isinstance(update, dict) and update.get('id') is not None:
                update_ids.append(update.get('id'))

        registrations = StudentSubject.objects.select_related(
            'student', 'student__biodata', 'subject', 'session', 'session_term', 'grade'
        ).filter(
            id__in=update_ids,
            subject_id=subject_id,
            session_id=session_id,
            session_term_id=session_term_id,
        )
        registrations_by_id = {registration.id: registration for registration in registrations}
        settings_obj = SystemSetting.load()
        allow_ca_score_editing = settings_obj.allow_ca_score_editing
        require_approval = settings_obj.require_result_entry_approval and not self._is_admin_like(request.user)

        serializers = []
        pending_submissions = []
        errors = []
        editable_fields = {'ca_score', 'objective_score', 'theory_score', 'exam_score', 'teacher_comment'}

        for index, update in enumerate(updates, start=1):
            if not isinstance(update, dict):
                errors.append({'row': index, 'errors': 'Each update must be an object.'})
                continue

            registration_id = update.get('id')
            try:
                registration_id = int(registration_id)
            except (TypeError, ValueError):
                errors.append({'row': index, 'errors': 'A valid registration id is required.'})
                continue

            registration = registrations_by_id.get(registration_id)
            if registration is None:
                errors.append({
                    'id': registration_id,
                    'errors': 'Registration was not found for this subject, session, and term.',
                })
                continue

            if not self._can_enter_subject_scores(request.user, registration.subject):
                errors.append({
                    'id': registration_id,
                    'errors': 'You are not permitted to enter scores for this subject.',
                })
                continue

            payload = {
                field: update[field]
                for field in editable_fields
                if field in update
            }
            serializer = self._validate_score_payload(registration, payload, allow_ca_score_editing)
            if serializer.is_valid():
                if require_approval:
                    pending_submissions.append((registration, payload))
                else:
                    serializers.append(serializer)
            else:
                errors.append({'id': registration_id, 'errors': serializer.errors})

        if errors:
            return Response(
                {
                    'message': 'Score sheet contains invalid rows.',
                    'updated_count': 0,
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if require_approval:
                submissions = [
                    self._queue_score_submission(registration, payload, request.user)
                    for registration, payload in pending_submissions
                ]
                return Response({
                    'message': f'Successfully submitted {len(submissions)} score rows for approval',
                    'updated_count': 0,
                    'submitted_count': len(submissions),
                    'data': [],
                    'errors': [],
                })

            updated = [
                serializer.save(
                    result_entered_by=request.user,
                    result_entered_at=timezone.now(),
                )
                for serializer in serializers
            ]

        return Response({
            'message': f'Successfully updated {len(updated)} score rows',
            'updated_count': len(updated),
            'submitted_count': 0,
            'data': StudentSubjectSerializer(
                updated,
                many=True,
                context=self.get_serializer_context(),
            ).data,
            'errors': [],
        })

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
                percentages = [
                    percentage for percentage in
                    (reg.calculate_percentage() for reg in regs)
                    if percentage is not None
                ]
                avg = sum(percentages, Decimal('0')) / Decimal(len(percentages)) if percentages else None
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
                        all_grades = Grade.objects.all()
                        teacher_defaults = {g.teacher_remark for g in all_grades if g.teacher_remark}
                        principal_defaults = {g.principal_remark for g in all_grades if g.principal_remark}

                        if not report.class_teacher_report or report.class_teacher_report in teacher_defaults:
                            if grade_obj.teacher_remark:
                                report.class_teacher_report = grade_obj.teacher_remark
                        
                        if not report.principal_report or report.principal_report in principal_defaults:
                            if grade_obj.principal_remark:
                                report.principal_report = grade_obj.principal_remark
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
