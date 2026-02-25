from rest_framework import serializers
from api.models import StudentSubject

class StudentSubjectSerializer(serializers.ModelSerializer):
    """Serializer for StudentSubject model with results"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    subject_class_id = serializers.CharField(source='subject.class_model_id', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    term_name = serializers.CharField(source='session_term.term_name', read_only=True, allow_null=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True, allow_null=True)
    grade_description = serializers.CharField(source='grade.grade_description', read_only=True, allow_null=True)
    cleared_by_name = serializers.CharField(source='cleared_by.email', read_only=True, allow_null=True)
    openday_cleared_by_name = serializers.CharField(source='openday_cleared_by.email', read_only=True, allow_null=True)
    can_open_day_clear = serializers.SerializerMethodField()
    
    # Term scores for cumulative reports
    first_term_score = serializers.SerializerMethodField()
    second_term_score = serializers.SerializerMethodField()
    current_term_score = serializers.DecimalField(source='total_score', max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = StudentSubject
        fields = [
            'id', 'student', 'subject', 'subject_name', 'subject_code', 'subject_class_id',
            'session', 'session_name', 'session_term', 'term_name',
            'is_active',
            'cleared', 'cleared_at', 'cleared_by', 'cleared_by_name',
            'openday_cleared', 'openday_cleared_at', 'openday_cleared_by',
            'openday_cleared_by_name', 'openday_clearance_notes', 'openday_clearance_checklist', 'can_open_day_clear',
            # Result fields
            'ca_score', 'objective_score', 'theory_score', 'exam_score', 'total_score', 'current_term_score',
            'first_term_score', 'second_term_score',
            'grade', 'grade_name', 'grade_description',
            'position', 'teacher_comment',
            'highest_score', 'lowest_score', 'subject_average',
            'result_entered_by', 'result_entered_at',
            'registered_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'registered_at', 'updated_at', 'total_score', 'current_term_score',
            'subject_name', 'subject_code', 'session_name', 'term_name',
            'grade', 'grade_name', 'grade_description',
            'first_term_score', 'second_term_score',
            'highest_score', 'lowest_score', 'subject_average',
            'cleared_at', 'cleared_by', 'cleared_by_name',
            'openday_cleared_at', 'openday_cleared_by', 'openday_cleared_by_name', 'can_open_day_clear', 'subject_class_id'
        ]

    def get_can_open_day_clear(self, obj):
        """UI helper: whether current user can clear for Open Day for this subject."""
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return False
        user = request.user
        # Admins/superusers allowed
        if getattr(user, 'is_superuser', False) or getattr(user, 'user_type', '') == 'admin':
            return True
        # Staff must be assigned
        staff = getattr(user, 'staff_profile', None)
        if not staff:
            return False
        subject = obj.subject
        assigned_to_subject = subject.assigned_teachers.filter(pk=staff.pk).exists()
        assigned_class_match = bool(staff.assigned_class_id) and (staff.assigned_class_id == subject.class_model_id)
        in_class_assigned_teachers = subject.class_model.assigned_teachers.filter(pk=staff.pk).exists()
        return assigned_to_subject or assigned_class_match or in_class_assigned_teachers

    def get_first_term_score(self, obj):
        """Retrieve total_score for 1st Term for the same student, subject, and session."""
        return self._get_term_score(obj, '1st Term')

    def get_second_term_score(self, obj):
        """Retrieve total_score for 2nd Term for the same student, subject, and session."""
        return self._get_term_score(obj, '2nd Term')

    def _get_term_score(self, obj, term_name):
        """Helper to find total_score for a specific term name in the current session."""
        try:
            # We look for a registration in the same session, for the same student and subject
            # where the session_term has the specified term_name.
            other_reg = StudentSubject.objects.filter(
                student=obj.student,
                subject=obj.subject,
                session=obj.session,
                session_term__term_name=term_name,
                total_score__isnull=False
            ).first()
            return other_reg.total_score if other_reg else None
        except Exception:
            return None
