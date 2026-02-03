from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User,
    School,
    Session,
    SessionTerm,
    Class,
    Department,
    SubjectGroup,
    Subject,
    Topic,
    Grade,
    Question,
    Exam,
    Assignment,
    StudentExam,
    StudentAnswer,
    Club,
    ExamHall,
    CBTExamCode,
    AdmissionSettings,
    Student,
    BioData,
    Guardian,
    Document,
    Biometric,
    StudentSubject,
    Staff,
    StaffEducation,
    SalaryGrade,
    StaffSalary,
    SalaryPayment,
    LoanApplication,
    LoanPayment,
    FeeType,
    FeePayment,
    PaymentPurpose,
    ApplicationSlip,
    Schedule,
    ScheduleEntry
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model"""
    
    list_display = ['email', 'user_type', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['email']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('User Info'), {'fields': ('user_type',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'user_type', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    """Admin interface for School model"""
    
    list_display = ['name', 'school_type', 'code', 'is_active', 'created_at']
    list_filter = ['school_type', 'is_active', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['school_type', 'name']
    readonly_fields = ['code', 'created_at']


class SessionTermInline(admin.TabularInline):
    """Inline for SessionTerm in Session admin"""
    model = SessionTerm
    extra = 0
    fields = ['term_name', 'start_date', 'end_date', 'is_current']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin interface for Session model"""
    
    list_display = ['name', 'start_date', 'end_date', 'is_current', 'created_at']
    list_filter = ['is_current', 'start_date']
    search_fields = ['name']
    ordering = ['-start_date']
    inlines = [SessionTermInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'start_date', 'end_date', 'is_current')
        }),
    )


@admin.register(SessionTerm)
class SessionTermAdmin(admin.ModelAdmin):
    """Admin interface for SessionTerm model"""
    
    list_display = ['session', 'term_name', 'start_date', 'end_date', 'is_current']
    list_filter = ['session', 'term_name', 'is_current']
    ordering = ['session', 'term_name']
    
    fieldsets = (
        (None, {
            'fields': ('session', 'term_name', 'start_date', 'end_date', 'is_current')
        }),
    )


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """Admin interface for Class model"""
    
    list_display = ['name', 'class_code', 'school', 'class_staff', 'order']
    list_filter = ['school']
    search_fields = ['name', 'class_code']
    ordering = ['school', 'order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'class_code', 'school')
        }),
        (_('Staff Assignment'), {
            'fields': ('class_staff', 'assigned_teachers')
        }),
        (_('Display'), {
            'fields': ('order',)
        }),
    )
    filter_horizontal = ['assigned_teachers']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Department model"""
    
    list_display = ['name', 'code', 'school', 'created_at']
    list_filter = ['school']
    search_fields = ['name', 'code']
    ordering = ['school', 'name']


@admin.register(SubjectGroup)
class SubjectGroupAdmin(admin.ModelAdmin):
    """Admin interface for SubjectGroup model"""
    
    list_display = ['name', 'code', 'selection_type', 'created_at']
    list_filter = ['selection_type']
    search_fields = ['name', 'code']
    ordering = ['name']
    readonly_fields = ['code']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'selection_type')
        }),
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Admin interface for Subject model"""
    
    list_display = ['name', 'code', 'class_model', 'school', 'department', 'ca_max', 'exam_max']
    list_filter = ['school', 'class_model', 'department', 'subject_group']
    search_fields = ['name', 'code']
    ordering = ['school', 'class_model', 'order', 'name']
    readonly_fields = ['code']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'school', 'class_model')
        }),
        (_('Classification'), {
            'fields': ('department', 'subject_group')
        }),
        (_('Staff Assignment'), {
            'fields': ('assigned_teachers',)
        }),
        (_('Assessment Configuration'), {
            'fields': ('ca_max', 'exam_max')
        }),
        (_('Display'), {
            'fields': ('order',)
        }),
    )
    filter_horizontal = ['assigned_teachers']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin interface for Question model"""
    
    list_display = ['question_text_preview', 'subject', 'topic_model', 'question_type', 'difficulty', 'is_verified', 'usage_count', 'created_at']
    list_filter = ['subject__school', 'subject', 'question_type', 'difficulty', 'is_verified', 'created_at']
    search_fields = ['question_text', 'topic_model__name', 'subject__name']
    ordering = ['-created_at']
    readonly_fields = ['usage_count', 'created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        (None, {
            'fields': ('subject', 'topic_model', 'question_type', 'difficulty', 'marks')
        }),
        (_('Question Content'), {
            'fields': ('question_text',)
        }),
        (_('Options (For Multiple Choice)'), {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'option_e'),
            'classes': ('collapse',)
        }),
        (_('Answer'), {
            'fields': ('correct_answer', 'explanation')
        }),
        (_('Status'), {
            'fields': ('is_verified', 'usage_count')
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_text_preview(self, obj):
        """Show first 100 chars of question"""
        from django.utils.html import strip_tags
        text = strip_tags(obj.question_text)
        return text[:100] + '...' if len(text) > 100 else text
    question_text_preview.short_description = 'Question'
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user if not set"""
        if not obj.pk:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Admin interface for Topic model"""
    
    list_display = ['name', 'subject', 'is_active', 'question_count_display', 'created_at']
    list_filter = ['subject__school', 'subject', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'subject__name']
    ordering = ['subject', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('subject', 'name', 'description', 'is_active')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def question_count_display(self, obj):
        """Display number of questions in this topic"""
        return obj.question_count
    question_count_display.short_description = 'Questions'


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    """Admin interface for Exam model"""
    
    list_display = ['title', 'subject', 'exam_type', 'session_term', 'status', 'total_questions', 'created_by', 'created_at']
    list_filter = ['exam_type', 'status', 'subject__school', 'subject', 'session_term']
    search_fields = ['title', 'subject__name', 'instructions']
    ordering = ['-created_at']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    
    filter_horizontal = ['topics', 'questions']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'subject', 'exam_type', 'session_term', 'status')
        }),
        (_('Configuration'), {
            'fields': ('duration_minutes', 'total_marks', 'pass_mark', 'total_questions')
        }),
        (_('Question Selection'), {
            'fields': ('topics', 'questions')
        }),
        (_('Settings'), {
            'fields': ('shuffle_questions', 'shuffle_options', 'show_results_immediately', 'allow_review')
        }),
        (_('Instructions'), {
            'fields': ('instructions',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user if not set"""
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """Admin interface for Assignment model"""
    list_display = ['title', 'subject', 'class_model', 'staff', 'is_published', 'question_count_display', 'due_date', 'created_at']
    list_filter = ['is_published', 'class_model', 'subject']
    search_fields = ['title', 'subject__name', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'description', 'staff', 'class_model', 'subject', 'is_published', 'due_date')
        }),
        (_('Questions'), {
            'fields': ('questions',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ['questions']

    def question_count_display(self, obj):
        return obj.question_count
    question_count_display.short_description = 'Questions'



@admin.register(ExamHall)
class ExamHallAdmin(admin.ModelAdmin):
    """Admin interface for ExamHall model"""
    
    list_display = ['name', 'number_of_seats', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'number_of_seats', 'is_active')
        }),
        (_('Metadata'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CBTExamCode)
class CBTExamCodeAdmin(admin.ModelAdmin):
    """Admin interface for CBTExamCode model"""
    
    list_display = [
        'code', 
        'get_student_name', 
        'exam_title_display',
        'exam_hall_display',
        'seat_number_display',
        'is_used',
        'expires_at',
        'created_at'
    ]
    list_filter = ['is_used', 'exam', 'exam_hall', 'created_at', 'expires_at']
    search_fields = [
        'code',
        'student__admission_number',
        'student__biodata__surname',
        'student__biodata__first_name',
        'exam__title'
    ]
    ordering = ['-created_at']
    readonly_fields = ['id', 'code', 'created_at', 'used_at']
    
    fieldsets = (
        (_('Passcode Information'), {
            'fields': ('code', 'student', 'exam')
        }),
        (_('Hall Assignment'), {
            'fields': ('exam_hall', 'seat_number')
        }),
        (_('Status'), {
            'fields': ('is_used', 'used_at', 'expires_at')
        }),
        (_('Metadata'), {
            'fields': ('id', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Get student's full name"""
        return obj.student.get_full_name() if hasattr(obj.student, 'get_full_name') else obj.student.admission_number
    get_student_name.short_description = 'Student'
    get_student_name.admin_order_field = 'student__biodata__surname'
    
    def exam_title_display(self, obj):
        """Display exam title"""
        return obj.exam.title if obj.exam else '-'
    exam_title_display.short_description = 'Exam'
    
    def exam_hall_display(self, obj):
        """Display exam hall"""
        return obj.exam_hall.name if obj.exam_hall else '-'
    exam_hall_display.short_description = 'Hall'
    
    def seat_number_display(self, obj):
        """Display seat number"""
        return f"Seat {obj.seat_number}" if obj.seat_number else '-'
    seat_number_display.short_description = 'Seat'


@admin.register(StudentExam)
class StudentExamAdmin(admin.ModelAdmin):
    """Admin interface for StudentExam model"""
    
    list_display = [
        'get_student_name', 
        'get_exam_title', 
        'status', 
        'score', 
        'percentage', 
        'passed', 
        'get_duration', 
        'submitted_at',
        'view_results_link'
    ]
    list_filter = [
        'status', 
        'passed', 
        'exam__exam_type', 
        'exam__subject', 
        'exam__session_term',
        'submitted_at'
    ]
    search_fields = [
        'student__user__email', 
        'student__admission_number', 
        'exam__title',
        'student__biodata__surname',
        'student__biodata__first_name'
    ]
    ordering = ['-submitted_at', '-created_at']
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'score', 
        'percentage', 
        'passed',
        'get_duration',
        'get_exam_summary'
    ]
    list_per_page = 25
    
    fieldsets = (
        (_('Exam Details'), {
            'fields': ('student', 'exam', 'status', 'get_exam_summary')
        }),
        (_('Timing'), {
            'fields': ('started_at', 'submitted_at', 'get_duration', 'time_remaining_seconds')
        }),
        (_('Results'), {
            'fields': ('score', 'percentage', 'passed'),
            'classes': ('collapse',)
        }),
        (_('Question Order'), {
            'fields': ('question_order',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Get student's full name"""
        if obj.student.biodata:
            return f"{obj.student.biodata.surname} {obj.student.biodata.first_name}"
        return obj.student.admission_number
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'student__biodata__surname'
    
    def get_exam_title(self, obj):
        """Get exam title with subject"""
        return f"{obj.exam.title} ({obj.exam.subject.name})"
    get_exam_title.short_description = 'Exam'
    get_exam_title.admin_order_field = 'exam__title'
    
    def get_duration(self, obj):
        """Calculate exam duration"""
        if obj.started_at and obj.submitted_at:
            duration = obj.submitted_at - obj.started_at
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{int(hours)}h {int(minutes)}m"
            else:
                return f"{int(minutes)}m {int(seconds)}s"
        return "N/A"
    get_duration.short_description = 'Duration'
    
    def get_exam_summary(self, obj):
        """Get exam summary information"""
        return f"Subject: {obj.exam.subject.name} | Type: {obj.exam.exam_type} | Total Marks: {obj.exam.total_marks} | Pass Mark: {obj.exam.pass_mark}"
    get_exam_summary.short_description = 'Exam Summary'
    
    actions = ['mark_as_graded', 'export_results']
    
    def mark_as_graded(self, request, queryset):
        """Mark selected exam attempts as graded"""
        updated = queryset.filter(status='submitted').update(status='graded')
        self.message_user(request, f'{updated} exam attempts marked as graded.')
    mark_as_graded.short_description = "Mark as graded"
    
    def export_results(self, request, queryset):
        """Export exam results to CSV"""
        # This would implement CSV export functionality
        self.message_user(request, f'Export functionality will be implemented.')
    export_results.short_description = "Export results"
    
    def get_urls(self):
        """Add custom URLs for detailed views"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:student_exam_id>/results/',
                self.admin_site.admin_view(self.exam_results_view),
                name='student_exam_results'
            ),
        ]
        return custom_urls + urls
    
    def exam_results_view(self, request, student_exam_id):
        """View detailed exam results"""
        from .admin_views import exam_results_view
        return exam_results_view(request, student_exam_id)
    
    def view_results_link(self, obj):
        """Create a link to view detailed results"""
        if obj.status in ['submitted', 'graded']:
            from django.urls import reverse
            from django.utils.html import format_html
            url = reverse('admin:student_exam_results', args=[obj.id])
            return format_html('<a href="{}" target="_blank">View Results</a>', url)
        return "Not Available"
    view_results_link.short_description = 'Results'
    view_results_link.admin_order_field = 'status'


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    """Admin interface for StudentAnswer model"""
    
    list_display = [
        'get_student_name', 
        'get_exam_title', 
        'question_number', 
        'get_question_preview', 
        'answer_text', 
        'is_correct', 
        'marks_obtained', 
        'answered_at'
    ]
    list_filter = [
        'is_correct', 
        'student_exam__exam', 
        'student_exam__exam__subject',
        'answered_at'
    ]
    search_fields = [
        'student_exam__student__user__email', 
        'student_exam__student__admission_number',
        'student_exam__student__biodata__surname',
        'student_exam__student__biodata__first_name',
        'question__question_text'
    ]
    ordering = ['student_exam', 'question_number']
    readonly_fields = [
        'answered_at', 
        'updated_at',
        'get_question_details',
        'get_correct_answer'
    ]
    list_per_page = 50
    
    fieldsets = (
        (_('Student & Exam'), {
            'fields': ('student_exam', 'question_number')
        }),
        (_('Question Details'), {
            'fields': ('question', 'get_question_details', 'get_correct_answer')
        }),
        (_('Student Answer'), {
            'fields': ('answer_text', 'is_correct', 'marks_obtained')
        }),
        (_('Metadata'), {
            'fields': ('answered_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Get student's full name"""
        if obj.student_exam.student.biodata:
            return f"{obj.student_exam.student.biodata.surname} {obj.student_exam.student.biodata.first_name}"
        return obj.student_exam.student.admission_number
    get_student_name.short_description = 'Student'
    get_student_name.admin_order_field = 'student_exam__student__biodata__surname'
    
    def get_exam_title(self, obj):
        """Get exam title"""
        return f"{obj.student_exam.exam.title} ({obj.student_exam.exam.subject.name})"
    get_exam_title.short_description = 'Exam'
    get_exam_title.admin_order_field = 'student_exam__exam__title'
    
    def get_question_preview(self, obj):
        """Get question preview"""
        question_text = obj.question.question_text
        if len(question_text) > 50:
            return question_text[:50] + "..."
        return question_text
    get_question_preview.short_description = 'Question Preview'
    
    def get_question_details(self, obj):
        """Get full question details with options"""
        question = obj.question
        options = []
        if question.option_a:
            options.append(f"A. {question.option_a}")
        if question.option_b:
            options.append(f"B. {question.option_b}")
        if question.option_c:
            options.append(f"C. {question.option_c}")
        if question.option_d:
            options.append(f"D. {question.option_d}")
        if question.option_e:
            options.append(f"E. {question.option_e}")
        
        options_text = "\n".join(options)
        return f"Question: {question.question_text}\n\nOptions:\n{options_text}\n\nMarks: {question.marks}"
    get_question_details.short_description = 'Question Details'
    
    def get_correct_answer(self, obj):
        """Get correct answer"""
        return f"Correct Answer: {obj.question.correct_answer} | Marks: {obj.question.marks}"
    get_correct_answer.short_description = 'Correct Answer'


# ===== Student Management =====

class BioDataInline(admin.StackedInline):
    """Inline for BioData in Student admin"""
    model = BioData
    can_delete = False
    fields = [
        ('surname', 'first_name', 'other_names'),
        ('gender', 'date_of_birth'),
        ('nationality', 'state_of_origin'),
        'permanent_address',
        'lin',
        ('has_medical_condition', 'blood_group'),
        'medical_condition_details'
    ]


class GuardianInline(admin.TabularInline):
    """Inline for Guardian in Student admin"""
    model = Guardian
    extra = 0
    fields = ['guardian_type', 'surname', 'first_name', 'phone_number', 'occupation', 'is_primary_contact']


class DocumentInline(admin.TabularInline):
    """Inline for Document in Student admin"""
    model = Document
    extra = 0
    fields = ['document_type', 'document_file', 'document_number', 'verified', 'verified_by']
    readonly_fields = ['verified_by']


class StudentSubjectInline(admin.TabularInline):
    """Inline for StudentSubject in Student admin"""
    model = StudentSubject
    extra = 0
    fields = ['subject', 'session', 'session_term', 'is_active']


class StudentExamInline(admin.TabularInline):
    """Inline for StudentExam in Student admin"""
    model = StudentExam
    extra = 0
    readonly_fields = [
        'exam', 'status', 'score', 'percentage', 'passed', 
        'started_at', 'submitted_at', 'get_duration'
    ]
    fields = [
        'exam', 'status', 'score', 'percentage', 'passed', 
        'started_at', 'submitted_at', 'get_duration'
    ]
    can_delete = False
    
    def get_duration(self, obj):
        """Calculate exam duration"""
        if obj.started_at and obj.submitted_at:
            duration = obj.submitted_at - obj.started_at
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{int(hours)}h {int(minutes)}m"
            else:
                return f"{int(minutes)}m {int(seconds)}s"
        return "N/A"
    get_duration.short_description = 'Duration'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Admin interface for Student model"""
    
    list_display = [
        'get_student_name', 
        'application_number', 
        'admission_number', 
        'status', 
        'school', 
        'class_model',
        'application_date'
    ]
    list_filter = ['status', 'source', 'school', 'class_model', 'department']
    search_fields = ['application_number', 'admission_number', 'biodata__surname', 'biodata__first_name']
    ordering = ['-created_at']
    readonly_fields = ['application_number', 'admission_number', 'created_at', 'updated_at', 'created_by']
    
    inlines = [BioDataInline, GuardianInline, DocumentInline, StudentSubjectInline, StudentExamInline]
    
    fieldsets = (
        (_('Student Information'), {
            'fields': ('application_number', 'admission_number', 'status', 'source')
        }),
        (_('Academic Information'), {
            'fields': ('school', 'class_model', 'department', 'former_school_attended')
        }),
        (_('Account'), {
            'fields': ('user',)
        }),
        (_('Important Dates'), {
            'fields': (
                'application_date', 
                'review_date', 
                'acceptance_date', 
                'enrollment_date', 
                'graduation_date'
            )
        }),
        (_('Admin Actions'), {
            'fields': ('created_by', 'reviewed_by', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Display student name from biodata"""
        return obj.get_full_name()
    get_student_name.short_description = 'Student Name'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating student"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BioData)
class BioDataAdmin(admin.ModelAdmin):
    """Admin interface for BioData model"""
    
    list_display = ['get_full_name', 'gender', 'date_of_birth', 'get_age', 'state_of_origin']
    list_filter = ['gender', 'nationality', 'has_medical_condition']
    search_fields = ['surname', 'first_name', 'other_names', 'lin']
    ordering = ['surname', 'first_name']
    
    fieldsets = (
        (_('Personal Information'), {
            'fields': (('surname', 'first_name', 'other_names'), ('gender', 'date_of_birth'), 'passport_photo')
        }),
        (_('Location'), {
            'fields': ('nationality', 'state_of_origin', 'permanent_address')
        }),
        (_('Identification'), {
            'fields': ('lin',)
        }),
        (_('Medical Information'), {
            'fields': (('has_medical_condition', 'blood_group'), 'medical_condition_details')
        }),
    )
    
    def get_full_name(self, obj):
        return str(obj)
    get_full_name.short_description = 'Full Name'
    
    def get_age(self, obj):
        return f"{obj.get_age()} years"
    get_age.short_description = 'Age'


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    """Admin interface for Guardian model"""
    
    list_display = ['get_full_name', 'guardian_type', 'phone_number', 'occupation', 'is_primary_contact', 'student']
    list_filter = ['guardian_type', 'is_primary_contact']
    search_fields = ['surname', 'first_name', 'phone_number', 'email']
    ordering = ['student', 'guardian_type']
    
    fieldsets = (
        (_('Guardian Information'), {
            'fields': ('student', 'guardian_type', 'relationship_to_student')
        }),
        (_('Personal Details'), {
            'fields': (('surname', 'first_name'), 'state_of_origin')
        }),
        (_('Contact Information'), {
            'fields': (('phone_number', 'email'), 'is_primary_contact')
        }),
        (_('Employment'), {
            'fields': ('occupation', 'place_of_employment')
        }),
    )
    
    def get_full_name(self, obj):
        return f"{obj.surname} {obj.first_name}"
    get_full_name.short_description = 'Full Name'


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model"""
    
    list_display = ['student', 'document_type', 'document_number', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['student__application_number', 'student__admission_number', 'document_number']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'verified_by', 'verified_at']
    
    fieldsets = (
        (_('Document Information'), {
            'fields': ('student', 'document_type', 'document_file', 'document_number')
        }),
        (_('Verification'), {
            'fields': ('verified', 'verified_by', 'verified_at', 'notes')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set verified_by and verified_at when verifying"""
        if obj.verified and not obj.verified_by:
            obj.verified_by = request.user
            from django.utils import timezone
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Biometric)
class BiometricAdmin(admin.ModelAdmin):
    """Admin interface for Biometric model"""
    
    list_display = ['student', 'has_left_thumb', 'has_right_thumb', 'captured_at', 'captured_by']
    list_filter = ['captured_at']
    search_fields = ['student__application_number', 'student__admission_number']
    ordering = ['-captured_at']
    readonly_fields = ['captured_at', 'captured_by']
    
    fieldsets = (
        (_('Student'), {
            'fields': ('student',)
        }),
        (_('Fingerprints'), {
            'fields': ('left_thumb', 'right_thumb')
        }),
        (_('Capture Information'), {
            'fields': ('captured_by', 'captured_at', 'notes')
        }),
    )
    
    def has_left_thumb(self, obj):
        return bool(obj.left_thumb)
    has_left_thumb.boolean = True
    has_left_thumb.short_description = 'Left Thumb'
    
    def has_right_thumb(self, obj):
        return bool(obj.right_thumb)
    has_right_thumb.boolean = True
    has_right_thumb.short_description = 'Right Thumb'
    
    def save_model(self, request, obj, form, change):
        """Set captured_by when creating"""
        if not change:
            obj.captured_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StudentSubject)
class StudentSubjectAdmin(admin.ModelAdmin):
    """Admin interface for StudentSubject model"""
    
    list_display = ['student', 'subject', 'session', 'session_term', 'is_active', 'registered_at']
    list_filter = ['session', 'session_term', 'is_active', 'registered_at']
    search_fields = [
        'student__application_number', 
        'student__admission_number',
        'subject__name',
        'subject__code'
    ]
    ordering = ['-registered_at']
    readonly_fields = ['registered_at']
    
    fieldsets = (
        (_('Registration'), {
            'fields': ('student', 'subject', 'session', 'session_term', 'is_active')
        }),
    )


# ===========================
# STAFF ADMIN
# ===========================

class StaffEducationInline(admin.TabularInline):
    """Inline for Staff Education records"""
    model = StaffEducation
    extra = 1
    fields = ['level', 'institution_name', 'year_of_graduation', 'degree', 'certificate']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Admin interface for Staff model"""
    
    list_display = [
        'staff_id', 
        'get_full_name', 
        'staff_type',
        'zone',
        'assigned_class',
        'status', 
        'entry_date'
    ]
    list_filter = ['status', 'staff_type', 'zone', 'marital_status', 'entry_date']
    search_fields = [
        'staff_id', 
        'surname', 
        'first_name', 
        'other_names',
        'phone_number',
        'user__email'
    ]
    ordering = ['-entry_date']
    readonly_fields = ['staff_id', 'created_at', 'updated_at']
    inlines = [StaffEducationInline]
    
    fieldsets = (
        (_('Registration & User'), {
            'fields': ('staff_id', 'user', 'created_by')
        }),
        (_('Personal Information'), {
            'fields': (
                'title', 'surname', 'first_name', 'other_names',
                'nationality', 'state_of_origin', 'date_of_birth',
                'permanent_address', 'phone_number',
                'marital_status', 'religion'
            )
        }),
        (_('Employment Details'), {
            'fields': (
                'entry_date', 'staff_type', 'zone', 'assigned_class',
                'number_of_children_in_school', 'status'
            )
        }),
        (_('Account Details'), {
            'fields': ('account_name', 'account_number', 'bank_name')
        }),
        (_('Documents'), {
            'fields': ('passport_photo',)
        }),
        (_('Tracking'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        """Display staff member's full name"""
        return obj.get_full_name()
    get_full_name.short_description = 'Name'


@admin.register(StaffEducation)
class StaffEducationAdmin(admin.ModelAdmin):
    """Admin interface for StaffEducation model"""
    
    list_display = ['staff', 'level', 'institution_name', 'year_of_graduation', 'degree']
    list_filter = ['level', 'degree', 'year_of_graduation']
    search_fields = [
        'staff__staff_id',
        'staff__surname',
        'staff__first_name',
        'institution_name'
    ]
    ordering = ['-year_of_graduation']
    
    fieldsets = (
        (None, {
            'fields': ('staff', 'level', 'institution_name', 'year_of_graduation', 'degree', 'certificate')
        }),
    )


@admin.register(SalaryGrade)
class SalaryGradeAdmin(admin.ModelAdmin):
    """Admin interface for SalaryGrade model"""
    
    list_display = ['grade_number', 'monthly_amount', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['description']
    ordering = ['grade_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('grade_number', 'monthly_amount', 'description', 'is_active')
        }),
        (_('Tracking'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StaffSalary)
class StaffSalaryAdmin(admin.ModelAdmin):
    """Admin interface for StaffSalary model"""
    
    list_display = ['staff', 'salary_grade', 'effective_date', 'assigned_by']
    list_filter = ['salary_grade', 'effective_date']
    search_fields = [
        'staff__staff_id',
        'staff__surname',
        'staff__first_name'
    ]
    ordering = ['-effective_date']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('staff', 'salary_grade', 'effective_date', 'notes')
        }),
        (_('Tracking'), {
            'fields': ('assigned_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    """Admin interface for SalaryPayment model"""
    
    list_display = [
        'staff', 
        'month', 
        'year', 
        'amount', 
        'deductions', 
        'net_amount', 
        'status',
        'payment_date'
    ]
    list_filter = ['status', 'year', 'month', 'payment_date']
    search_fields = [
        'staff__staff_id',
        'staff__surname',
        'staff__first_name',
        'reference_number'
    ]
    ordering = ['-year', '-month', 'staff']
    readonly_fields = ['net_amount', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('Staff & Period'), {
            'fields': ('staff', 'salary_grade', 'month', 'year')
        }),
        (_('Payment Details'), {
            'fields': ('amount', 'deductions', 'net_amount', 'status', 'payment_date', 'reference_number')
        }),
        (_('Notes'), {
            'fields': ('notes',)
        }),
        (_('Tracking'), {
            'fields': ('processed_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class LoanPaymentInline(admin.TabularInline):
    """Inline for Loan Payments"""
    model = LoanPayment
    extra = 0
    fields = ['amount', 'payment_date', 'month', 'year', 'reference_number', 'processed_by']
    readonly_fields = ['processed_by']


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    """Admin interface for LoanApplication model"""
    
    list_display = [
        'application_number',
        'staff',
        'loan_amount',
        'total_amount',
        'monthly_deduction',
        'status',
        'application_date'
    ]
    list_filter = ['status', 'application_date', 'approval_date']
    search_fields = [
        'application_number',
        'staff__staff_id',
        'staff__surname',
        'staff__first_name'
    ]
    ordering = ['-application_date']
    readonly_fields = [
        'application_number', 
        'total_amount', 
        'monthly_deduction',
        'created_at', 
        'updated_at'
    ]
    inlines = [LoanPaymentInline]
    
    fieldsets = (
        (_('Application Info'), {
            'fields': ('application_number', 'staff', 'application_date', 'status')
        }),
        (_('Loan Details'), {
            'fields': (
                'loan_amount', 
                'interest_rate', 
                'total_amount',
                'repayment_period_months',
                'monthly_deduction',
                'purpose'
            )
        }),
        (_('Review'), {
            'fields': (
                'reviewed_by',
                'review_notes',
                'approval_date',
                'disbursement_date',
                'rejection_reason'
            )
        }),
        (_('Tracking'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    """Admin interface for LoanPayment model"""
    
    list_display = [
        'loan_application',
        'amount',
        'payment_date',
        'month',
        'year',
        'reference_number',
        'processed_by'
    ]
    list_filter = ['payment_date', 'year', 'month']
    search_fields = [
        'loan_application__application_number',
        'loan_application__staff__staff_id',
        'reference_number'
    ]
    ordering = ['-payment_date']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': (
                'loan_application',
                'amount',
                'payment_date',
                'month',
                'year',
                'reference_number',
                'notes'
            )
        }),
        (_('Tracking'), {
            'fields': ('processed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


# ===========================
# FEE ADMIN
# ===========================

@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    """Admin interface for FeeType model"""
    
    list_display = [
        'name',
        'amount',
        'school',
        'max_installments',
        'is_mandatory',
        'is_recurring_per_term',
        'is_active',
        'created_at'
    ]
    list_filter = ['school', 'is_mandatory', 'is_recurring_per_term', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['applicable_classes', 'active_terms']
    ordering = ['school', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'amount', 'school')
        }),
        (_('Applicability'), {
            'fields': ('applicable_classes', 'active_terms')
        }),
        (_('Payment Options'), {
            'fields': ('max_installments', 'is_mandatory', 'is_recurring_per_term', 'is_active')
        }),
        (_('Tracking'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    """Admin interface for FeePayment model"""
    
    list_display = [
        'receipt_number',
        'student',
        'fee_type',
        'amount',
        'installment_number',
        'payment_date',
        'payment_method',
        'processed_by'
    ]
    list_filter = ['payment_method', 'payment_date', 'fee_type', 'session', 'session_term']
    search_fields = [
        'receipt_number',
        'reference_number',
        'student__admission_number',
        'student__biodata__surname',
        'student__biodata__first_name',
        'fee_type__name'
    ]
    ordering = ['-payment_date', '-created_at']
    readonly_fields = ['receipt_number', 'created_at']
    
    fieldsets = (
        (_('Payment Information'), {
            'fields': ('student', 'fee_type', 'amount', 'installment_number')
        }),
        (_('Session/Term'), {
            'fields': ('session', 'session_term')
        }),
        (_('Payment Details'), {
            'fields': ('payment_date', 'payment_method', 'reference_number', 'receipt_number')
        }),
        (_('Notes'), {
            'fields': ('notes',)
        }),
        (_('Tracking'), {
            'fields': ('processed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


# ===== Schedule Management =====

class ScheduleEntryInline(admin.TabularInline):
    """Inline for ScheduleEntry in Schedule admin"""
    model = ScheduleEntry
    extra = 0
    fields = ['date', 'start_time', 'end_time', 'title', 'linked_exam', 'target_classes']
    filter_horizontal = ['target_classes']
    fk_name = 'schedule'

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """Admin interface for Schedule model"""
    list_display = ['schedule_type', 'is_active', 'entry_count', 'created_at']
    list_filter = ['schedule_type', 'is_active']
    ordering = ['-created_at']
    
    inlines = [ScheduleEntryInline]
    
    fieldsets = (
        (None, {
            'fields': ('schedule_type', 'is_active', 'start_date', 'end_date')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def entry_count(self, obj):
        return obj.entries.count()
    entry_count.short_description = 'Entries'

@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    """Admin interface for ScheduleEntry model"""
    list_display = ['title', 'schedule', 'date', 'start_time', 'end_time', 'linked_exam', 'supervisor']
    list_filter = ['schedule', 'date', 'target_classes']
    search_fields = ['title', 'schedule__name']
    ordering = ['date', 'start_time']
    filter_horizontal = ['target_classes']
    
    fieldsets = (
        (None, {
            'fields': ('schedule', 'title', 'date')
        }),
        (_('Time Slot'), {
            'fields': ('start_time', 'end_time')
        }),
        (_('Targets & Supervision'), {
            'fields': ('target_classes', 'supervisor')
        }),
        (_('Links'), {
            'fields': ('linked_exam', 'linked_subject')
        }),
    )


# ===== Admission Management =====

@admin.register(AdmissionSettings)
class AdmissionSettingsAdmin(admin.ModelAdmin):
    """Admin interface for AdmissionSettings model"""
    
    list_display = [
        'school',
        'is_admission_open',
        'admission_start_datetime',
        'admission_end_datetime',
        'application_fee_amount',
        'created_by',
        'updated_at'
    ]
    list_filter = ['is_admission_open', 'school', 'admission_start_datetime']
    search_fields = ['school__name']
    ordering = ['-updated_at']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('School'), {
            'fields': ('school',)
        }),
        (_('Admission Status'), {
            'fields': ('is_admission_open',)
        }),
        (_('Admission Period'), {
            'fields': ('admission_start_datetime', 'admission_end_datetime')
        }),
        (_('Fee'), {
            'fields': ('application_fee_amount',)
        }),
        (_('Tracking'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user"""
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PaymentPurpose)
class PaymentPurposeAdmin(admin.ModelAdmin):
    """Admin interface for PaymentPurpose model"""
    
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Purpose Information'), {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApplicationSlip)
class ApplicationSlipAdmin(admin.ModelAdmin):
    """Admin interface for ApplicationSlip model"""
    
    list_display = [
        'get_student_name',
        'application_number',
        'screening_date',
        'get_school_name',
        'generated_at'
    ]
    list_filter = ['student__school', 'generated_at', 'screening_date']
    search_fields = [
        'application_number',
        'student__biodata__surname',
        'student__biodata__first_name'
    ]
    ordering = ['-generated_at']
    readonly_fields = ['generated_at']
    
    fieldsets = (
        (_('Student Information'), {
            'fields': ('student', 'application_number')
        }),
        (_('Screening Details'), {
            'fields': ('screening_date',)
        }),
        (_('Application Slip'), {
            'fields': ('pdf_file', 'generated_at')
        }),
    )
    
    def get_student_name(self, obj):
        """Display student name"""
        return obj.student.get_full_name()
    get_student_name.short_description = 'Student Name'
    
    def get_school_name(self, obj):
        """Display school name"""
        return obj.student.school.name
    get_school_name.short_description = 'School'

