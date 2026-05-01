from rest_framework import serializers
from api.models import ExternalExamBody, ExternalExam, ExternalExamResult, ExternalExamAccess


class ExternalExamBodySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalExamBody
        fields = ['id', 'name', 'short_name']


class ExternalExamSerializer(serializers.ModelSerializer):
    body_name = serializers.CharField(source='body.name', read_only=True)
    body_short_name = serializers.CharField(source='body.short_name', read_only=True)
    sitting_display = serializers.CharField(source='get_sitting_display', read_only=True)
    class_name = serializers.CharField(source='applicable_class.name', read_only=True)
    result_count = serializers.SerializerMethodField()

    class Meta:
        model = ExternalExam
        fields = [
            'id', 'body', 'body_name', 'body_short_name',
            'year', 'sitting', 'sitting_display',
            'applicable_class', 'class_name',
            'result_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_result_count(self, obj):
        return obj.results.count()


class ExternalExamResultSerializer(serializers.ModelSerializer):
    result_file_url = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    student_admission = serializers.CharField(source='student.admission_number', read_only=True, default='')

    class Meta:
        model = ExternalExamResult
        fields = [
            'id', 'exam', 'student', 'student_name', 'student_admission',
            'result_file', 'result_file_url', 'grades',
            'uploaded_at', 'updated_at',
        ]
        read_only_fields = ['id', 'uploaded_at', 'updated_at']
        extra_kwargs = {'result_file': {'write_only': True}}

    def get_result_file_url(self, obj):
        if not obj.result_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.result_file.url)
        return obj.result_file.url

    def get_student_name(self, obj):
        bio = getattr(obj.student, 'biodata', None)
        if bio:
            return f"{bio.first_name} {bio.surname}"
        return str(obj.student)

    def validate(self, data):
        result_file = data.get('result_file') or (self.instance.result_file if self.instance else None)
        grades = data.get('grades') or (self.instance.grades if self.instance else None)
        if not result_file and not grades:
            raise serializers.ValidationError('Provide at least a result file or grades.')
        return data


class ExternalExamAccessSerializer(serializers.ModelSerializer):
    exam_display = serializers.StringRelatedField(source='exam', read_only=True)

    class Meta:
        model = ExternalExamAccess
        fields = ['id', 'student', 'exam', 'exam_display', 'payment', 'granted_at']
        read_only_fields = ['id', 'granted_at']


class StudentExternalExamSerializer(serializers.ModelSerializer):
    """Serializer for student-facing exam list — includes access & result data."""
    body_name = serializers.CharField(source='body.name', read_only=True)
    body_short_name = serializers.CharField(source='body.short_name', read_only=True)
    sitting_display = serializers.CharField(source='get_sitting_display', read_only=True)
    has_access = serializers.SerializerMethodField()
    has_result = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    class Meta:
        model = ExternalExam
        fields = [
            'id', 'body_name', 'body_short_name',
            'year', 'sitting_display',
            'has_result', 'has_access', 'result',
        ]

    def _get_student(self):
        request = self.context.get('request')
        return getattr(request.user, 'student_profile', None) if request else None

    def get_has_access(self, obj):
        student = self._get_student()
        if not student:
            return False
        return ExternalExamAccess.objects.filter(student=student, exam=obj).exists()

    def get_has_result(self, obj):
        student = self._get_student()
        if not student:
            return False
        return ExternalExamResult.objects.filter(student=student, exam=obj).exists()

    def get_result(self, obj):
        student = self._get_student()
        if not student:
            return None
        if not ExternalExamAccess.objects.filter(student=student, exam=obj).exists():
            return None
        result = ExternalExamResult.objects.filter(student=student, exam=obj).first()
        if not result:
            return None
        request = self.context.get('request')
        return ExternalExamResultSerializer(result, context={'request': request}).data
